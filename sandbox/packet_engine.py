"""Offline packet filters: native TShark display filters and native libpcap BPF.

Student text is passed as one argument, never through a shell. Only supplied
capture bytes are read; neither backend opens a capture interface.
Both backends accept bounded PCAP/PCAPNG with per-interface link types. Display
address operands are numeric; DNS/HTTP string fields still accept text.
The separate tcpdump-lab mode captures only its generated loopback UDP pair.
"""
import base64
import functools
import ipaddress
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

try:
    from . import bpf_native, packet_fixtures, capture_formats
except ImportError:
    import bpf_native
    import packet_fixtures
    import capture_formats

MAX_CAPTURE = 8 * 1024 * 1024
MAX_FILTER = 16000
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_IP_FIELD = re.compile(r"(?:(?:ip|ipv6)\.(?:addr|src|dst)|arp\.(?:src|dst)\.proto_ipv4|dns\.(?:a|aaaa))(?:#[0-9]+)?\Z")
_DISPLAY_TOKEN = re.compile(r'r?"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|===|!==|==|!=|<=|>=|&&|\|\||\^\^|[A-Za-z0-9_.:/]+(?:#[0-9]+)?|[^\s]')
_COMPARISON = frozenset(("==", "!=", "===", "!==", "<", ">", "<=", ">=", "eq", "ne",
                         "gt", "lt", "ge", "le", "any_eq", "all_eq", "any_ne", "all_ne", "in"))


class PacketError(ValueError):
    pass


def tshark_path():
    configured = os.environ.get("PAFTA_TSHARK")
    if configured and os.path.isfile(configured):
        return configured
    found = shutil.which("tshark")
    if found:
        return found
    candidate = r"C:\Program Files\Wireshark\tshark.exe"
    return candidate if os.path.isfile(candidate) else None


def options(text=""):
    if not isinstance(text, str):
        raise PacketError("Girdi JSON metni olmalı.")
    if not text or not text.strip():
        return {"dil": "wireshark", "kayit": "temel"}
    try:
        value = json.loads(text)
    except (ValueError, TypeError) as exc:
        raise PacketError('Girdi JSON olmalı: {"dil":"wireshark","kayit":"temel"}') from exc
    if not isinstance(value, dict) or set(value) - {"dil", "kayit", "pcap_base64", "anahtar", "laboratuvar"}:
        raise PacketError("Girdi yalnız dil, kayit, pcap_base64, anahtar ve laboratuvar alanlarını kabul eder.")
    if value.get('anahtar','yok') not in ('yok','yanlis','tls-h2','quic-lab'):
        raise PacketError('anahtar: yok, yanlis, tls-h2 veya quic-lab olmalı; dosya yolu kabul edilmez.')
    if "kayit" in value and "pcap_base64" in value:
        raise PacketError("kayit ile pcap_base64 birlikte verilmez.")
    if value.get('laboratuvar','kisa') not in ('kisa','donusum'):
        raise PacketError('laboratuvar kisa veya donusum olmalı.')
    if value.get('dil')=='tcpdump-lab' and set(value)&{'kayit','pcap_base64','anahtar'}:
        raise PacketError('tcpdump-lab yalnız kendi ürettiği loopback trafiğini toplar; dış kayıt veya anahtar almaz.')
    if 'laboratuvar' in value and value.get('dil')!='tcpdump-lab':
        raise PacketError('laboratuvar seçimi yalnız tcpdump-lab için geçerlidir.')
    if value.get("dil", "wireshark") not in ("wireshark", "bpf", "tshark", "tcpdump-lab"):
        raise PacketError("dil wireshark, bpf, tshark veya tcpdump-lab olmalı; sözdizimleri farklıdır.")
    return dict({"dil": "wireshark", "kayit": "temel"} if "pcap_base64" not in value
                else {"dil": "wireshark"}, **value)


def capture_bytes(capture):
    if isinstance(capture, bytes):
        raw = capture
    elif isinstance(capture, str):
        try:
            raw = packet_fixtures.get_capture(capture)
        except (KeyError, ValueError) as exc:
            raise PacketError("Bilinmeyen kayıt: " + capture + ". Seçenekler: " + ", ".join(packet_fixtures.captures())) from exc
    else:
        raise PacketError("Kayıt adı ya da PCAP baytları gerekli.")
    if len(raw) > MAX_CAPTURE:
        raise PacketError("Kayıt en fazla 8 MiB olabilir.")
    pcap_lengths(raw)  # Reject unsupported/malformed input before either native backend.
    return raw


def input_capture(config):
    if "pcap_base64" in config:
        value = config["pcap_base64"]
        if not isinstance(value, str) or len(value) > MAX_CAPTURE * 2:
            raise PacketError("pcap_base64 boyutu/türü geçersiz.")
        try:
            decoded = base64.b64decode(value, validate=True)
        except ValueError as exc:
            raise PacketError("pcap_base64 geçerli Base64 olmalı.") from exc
        return capture_bytes(decoded)
    return capture_bytes(config.get("kayit", "temel"))


def _numeric_ip_operand(token):
    if _IP_FIELD.fullmatch(token):
        return True  # Address field-to-field comparisons need no lookup.
    if token.startswith('r"') and token.endswith('"'):
        token = token[2:-1]
    elif token[:1] in ('"', "'") and token[-1:] == token[:1]:
        token = token[1:-1]
    if "\\" in token or "%" in token:
        return False  # No escaped names or platform-specific zone identifiers.
    try:
        if "/" in token:
            ipaddress.ip_network(token, strict=False)
        else:
            ipaddress.ip_address(token)
        return True
    except ValueError:
        return False


def _display_numeric_addresses(code):
    """Validate direct IP operands without interpreting filter truth values.

    The native engine owns parsing/evaluation. This deliberately narrow guard
    accepts numeric IP/CIDR/range sets and address-field comparisons. Text
    fields (dns.qry.name/http.host, including their strings) are unaffected.
    -n plus the explicit resolver preference also disables native name lookup.
    """
    tokens = _DISPLAY_TOKEN.findall(code)
    for index, token in enumerate(tokens):
        if not _IP_FIELD.fullmatch(token):
            continue
        for direction in (1, -1):
            at = index + direction
            while 0 <= at < len(tokens) and tokens[at] == (")" if direction == 1 else "("):
                at += direction
            if not 0 <= at < len(tokens) or tokens[at] not in _COMPARISON:
                continue
            at += direction
            while 0 <= at < len(tokens) and tokens[at] == ("(" if direction == 1 else ")"):
                at += direction
            if not 0 <= at < len(tokens):
                continue  # Native compiler reports the incomplete expression.
            operands = [tokens[at]]
            if direction == 1 and tokens[at] == "{":
                end = at + 1
                while end < len(tokens) and tokens[end] != "}":
                    end += 1
                operands = [value for value in tokens[at + 1:end] if value not in (",", "..")]
            for value in operands:
                # A range without surrounding whitespace is one lexical token.
                if all(_numeric_ip_operand(part) for part in value.split("..")):
                    continue
                raise PacketError("IP adres alanlarında yalnız sayısal IP/CIDR veya IP alanı "
                                  "kullanılabilir; sunucu adı çözülmez: " + value)


@functools.lru_cache(maxsize=32)
def _display(code, raw, key='yok'):
    _display_numeric_addresses(code)
    exe = tshark_path()
    if not exe:
        raise PacketError("TShark bulunamadı. Wireshark/TShark kur veya PAFTA_TSHARK değişkenine tshark.exe tam yolunu ver.")
    with tempfile.TemporaryDirectory(prefix="pafta_tshark_") as config:
        env = dict(os.environ, WIRESHARK_CONFIG_DIR=config, WIRESHARK_PLUGIN_DIR=config,
                   WIRESHARK_EXTCAP_DIR=config, TZ="UTC")
        # Ignore inherited development data paths; keep the installed TShark's
        # own protocol data and an empty personal configuration/plugin folder.
        env.pop("WIRESHARK_RUN_FROM_BUILD_DIRECTORY", None)
        env.pop("WIRESHARK_DATA_DIR", None)
        keyfile=_key_file(key,config)
        command = [exe, "-n", "-o", "nameres.use_external_name_resolver:FALSE",
                   '-o','tls.keylog_file:'+keyfile,
                   "-r", "-", "-Y", code, "-T", "fields", "-e", "frame.number"]
        try:
            result = subprocess.run(command, input=raw, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    timeout=8, env=env, creationflags=NO_WINDOW)
        except subprocess.TimeoutExpired as exc:
            raise PacketError("TShark 8 saniyede bitmedi.") from exc
        except OSError as exc:
            raise PacketError("TShark başlatılamadı; PAFTA_TSHARK yolunu ve çalıştırılabilir "
                              "dosyayı doğrulayın: " + str(exc)) from exc
    stderr = result.stderr.decode("utf-8", "replace").strip()
    if result.returncode:
        raise PacketError(stderr or "TShark hata kodu: " + str(result.returncode))
    try:
        ids = tuple(int(line) for line in result.stdout.decode("utf-8").splitlines() if line.strip())
        count = len(pcap_lengths(raw))
        if any(i < 1 or i > count for i in ids) or any(a >= b for a, b in zip(ids, ids[1:])):
            raise ValueError("invalid frame number/order")
        return ids
    except (ValueError, UnicodeError) as exc:
        raise PacketError("TShark beklenmeyen paket numarası döndürdü.") from exc


@functools.lru_cache(maxsize=32)
def _bpf(code, raw):
    return tuple(bpf_native.evaluate(code, raw))


def _key_file(key,directory):
    if key not in ('yok','yanlis','tls-h2','quic-lab'):
        raise PacketError('Bilinmeyen eğitim anahtarı; dosya yolu kabul edilmez.')
    if key=='yok':return ''
    root=Path(__file__).resolve().parent.parent/'tracks/packets/captures'
    if key=='yanlis':
        lines=(root/'tls-h2.keys').read_text(encoding='ascii').splitlines()
        content='\n'.join(' '.join(line.split()[:-1]+['0'*len(line.split()[-1])])
                          for line in lines if line and not line.startswith('#'))+'\n'
    else:
        content=(root/(key+'.keys')).read_text(encoding='ascii')
    path=Path(directory)/'training.keys';path.write_text(content,encoding='ascii')
    return str(path)


def evaluate(code, capture="temel", dialect="wireshark", key='yok'):
    if not isinstance(code, str) or len(code.encode("utf-8")) > MAX_FILTER or "\0" in code:
        raise PacketError("Filtre en fazla 16 kB, NUL içermeyen metin olmalı.")
    raw = capture_bytes(capture)
    if dialect == "wireshark":
        return list(_display(code, raw) if key=='yok' else _display(code,raw,key))
    if dialect == "bpf":
        if key!='yok':
            raise PacketError('BPF TLS oturum anahtarlarını kullanmaz.')
        return list(_bpf(code, raw))
    raise PacketError("Bilinmeyen filtre dili: " + str(dialect))


def pcap_lengths(raw):
    """Validate framing while retaining captured and original lengths."""
    try:
        return {i:(len(frame.data),frame.wirelen) for i,frame in enumerate(capture_formats.parse_capture(raw),1)}
    except capture_formats.CaptureError as exc:
        raise PacketError(str(exc)) from exc


def run(code, stdin=""):
    config = options(stdin)
    if config['dil']=='tcpdump-lab':
        try:from . import packet_capture_lab
        except ImportError:import packet_capture_lab
        return packet_capture_lab.run(code,config.get('laboratuvar','kisa'))
    raw = input_capture(config)
    if config['dil']=='tshark':
        try:from . import packet_cli
        except ImportError:import packet_cli
        return packet_cli.run(code,raw,config.get('anahtar','yok'))
    ids = evaluate(code, raw, config["dil"],config.get('anahtar','yok'))
    out = "Paketler: " + (", ".join(map(str, ids)) if ids else "(yok)") + "\n"
    lengths = pcap_lengths(raw)
    rows = [[i, *lengths.get(i, ("?", "?"))] for i in ids]
    backend = "TShark" if config["dil"] == "wireshark" else bpf_native.version()
    result = {"status": "ok", "error": None, "segs": [["out", out]],
            "tablolar": [{"satir": 1, "sutunlar": ["Paket", "Yakalanan bayt", "Hat uzunluğu"], "satirlar": rows}],
            "packet_ids": ids, "packet_backend": backend, "packet_dialect": config["dil"]}
    result["capture_interfaces"] = [
        {"frame":i,"section":f.section,"interface":f.interface,"linktype":f.linktype,
         "timestamp_fraction":str(f.timestamp) if f.timestamp is not None else None}
        for i,f in enumerate(capture_formats.parse_capture(raw),1)]
    if "pcap_base64" not in config:
        names = {1: "ICMP", 6: "TCP", 17: "UDP", 58: "ICMPv6", 132: "SCTP"}
        inventory = []
        for packet in packet_fixtures.describe(config.get("kayit", "temel")):
            protocol = names.get(packet.get("proto"), str(packet.get("proto", "Ethernet")))
            if "sport" in packet and "dport" in packet:
                protocol += " " + str(packet["sport"]) + " → " + str(packet["dport"])
            description = packet["note"]
            if "flags" in packet:
                description += f"; TCP flags 0x{packet['flags']:02x}"
            if "vlan" in packet:
                description += "; VLAN " + "/".join(map(str, packet["vlan"]))
            if "fragment_offset" in packet:
                description += f"; fragment offset {packet['fragment_offset']} × 8 bayt"
            inventory.append([packet["id"], packet.get("src", packet.get("eth_src", "")),
                              packet.get("dst", packet.get("eth_dst", "")), protocol,
                              str(packet["wirelen"]) + " / " + str(packet["caplen"]), description,
                              packet["time_relative"]])
        result["packet_inventory"] = {
            "baslik": "Sentetik kayıt dökümü · fixture açıklamaları, native ayrıştırma değildir",
            "sutunlar": ["Paket", "Kaynak", "Hedef", "Protokol / port", "Boy / yakalanan", "Açıklama", "Göreli saniye"],
            "satirlar": inventory}
    return result


def test_helpers(code, stdin=""):
    config = options(stdin)
    if config['dil']=='tcpdump-lab':
        try:from . import packet_capture_lab
        except ImportError:import packet_capture_lab
        return packet_capture_lab.test_helpers(code,config.get('laboratuvar','kisa'))
    selected = input_capture(config)
    dialect = config["dil"]
    key=config.get('anahtar','yok')
    if dialect=='tshark':
        try:from . import packet_cli
        except ImportError:import packet_cli
        return packet_cli.test_helpers(code,selected,key)
    evaluate(code, selected, dialect,key)  # Invalid filters cannot pass a vacuous test.
    return {"src": code,
            "eslesenler": lambda kayit=None,anahtar=None: evaluate(code, selected if kayit is None else kayit, dialect,key if anahtar is None else anahtar),
            "referans": lambda filtre, kayit=None, dil=None,anahtar=None: evaluate(filtre, selected if kayit is None else kayit, dil or dialect,key if anahtar is None else anahtar),
            "korpuslar": tuple(packet_fixtures.captures()),
            "paketler": packet_fixtures.describe}

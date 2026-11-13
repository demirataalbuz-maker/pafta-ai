"""Synthetic offline EVT -> native EVTX fixtures; no channel/registry writes.

Windows itself converts our documented legacy EVT records with wevtutil epl.
Only disposable caller-owned files are created. No live logs are read.
Format sources:
https://learn.microsoft.com/en-us/windows/win32/eventlog/event-log-file-format
https://learn.microsoft.com/en-us/previous-versions/windows/desktop/legacy/bb309024(v=vs.85)
https://learn.microsoft.com/en-us/previous-versions/windows/desktop/legacy/bb309022(v=vs.85)
https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-eventlogrecord
"""
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import xml.etree.ElementTree as ET

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
NS = {"e": "http://schemas.microsoft.com/win/2004/08/events/event"}
# (EventID, classic EventType, insertion string); type 1/2/4 -> Level 2/3/4.
EVENTS = (
    (100, 1, "alt-komsu"), (101, 1, "alt-sinir"),
    (102, 2, "uyari"), (102, 1, "Türkçe & <demo> ! %"),
    (103, 1, "ust-sinir"), (104, 1, "ust-komsu"),
    (102, 4, "bilgi"), (102, 1, "son"),
)


def executable():
    path = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/wevtutil.exe"
    if not path.is_file():
        raise RuntimeError("EVTX tezgahı Windows ve yerleşik wevtutil.exe gerektirir.")
    return str(path)


def native(*args):
    return subprocess.run([executable(), *map(str, args)], capture_output=True,
                          timeout=15, creationflags=NO_WINDOW)


def _record(number, event):
    eid, typ, text = event
    if not 0 <= eid <= 65535 or typ not in (1, 2, 4):
        raise ValueError("Fixture: EventID 0..65535; type 1/2/4 olmalı")
    if "\0" in text:
        raise ValueError("Fixture string cannot contain NUL")
    names = "PaftaDemo\0PAFTA-LAB\0".encode("utf-16le")
    strings = (text + "\0").encode("utf-16le")
    payload = names + strings
    payload += b"\0" * (-len(payload) % 4)
    size = 56 + len(payload) + 4
    stamp = 1700000000 + number
    header = struct.pack("<6I4H6I", size, 0x654C664C, number, stamp, stamp, eid,
                         typ, 1, 0, 0, 0, 56 + len(names), 0, 0, 0, 0)
    return header + payload + struct.pack("<I", size)


def create_evtx(path, events=EVENTS):
    """Create a NEW genuine EVTX via local legacy-file export. Never overwrite."""
    target = Path(path).resolve()
    if not events:
        # Native legacy export rejects no matches on this Windows build.
        # Convert a seed first, then create the empty file from real EVTX.
        with tempfile.TemporaryDirectory(prefix="pafta_empty_", dir=target.parent) as folder:
            seed = create_evtx(Path(folder) / "seed.evtx", EVENTS[:1])
            result = native("epl", seed, target, "/lf:true", "/ow:false",
                            "/q:*[System[EventID=65535]]")
            if result.returncode:
                raise RuntimeError(f"Boş EVTX üretilemedi ({result.returncode})")
        return target
    records = b"".join(_record(i, row) for i, row in enumerate(events, 1))
    end = 48 + len(records)
    count = len(events)
    oldest = 1 if count else 0
    header = struct.pack("<12I", 48, 0x654C664C, 1, 1, 48, end, count + 1,
                         oldest, max(65536, end + 40), 0, 0, 48)
    eof = struct.pack("<10I", 40, 0x11111111, 0x22222222, 0x33333333, 0x44444444,
                      48, end, count + 1, oldest, 40)
    with tempfile.TemporaryDirectory(prefix="pafta_evt_", dir=target.parent) as folder:
        source = Path(folder) / "sentetik.evt"
        source.write_bytes((header + records + eof).ljust(max(65536, end + 40), b"\0"))
        result = native("epl", source, target, "/lf:true", "/ow:false")
        if result.returncode:
            raise RuntimeError(f"Sentetik EVT -> EVTX başarısız ({result.returncode}): "
                               + result.stderr.decode("utf-8", "replace"))
    if target.read_bytes()[:8] != b"ElfFile\0":
        raise RuntimeError("Windows EVTX başlığı üretmedi")
    return target


def events_from_xml(text):
    """Normalize only stable System/Data fields, never localized rendered text."""
    root = ET.fromstring(text.lstrip("\ufeff"))
    if root.tag != "Events":
        raise ValueError("XML kökü Events olmalı")
    return [
        (int(e.findtext("e:System/e:EventRecordID", namespaces=NS)),
         int(e.findtext("e:System/e:EventID", namespaces=NS)),
         int(e.findtext("e:System/e:Level", namespaces=NS)),
         e.findtext("e:EventData/e:Data", default="", namespaces=NS))
        for e in root.findall("e:Event", NS)
    ]


def read_evtx(path):
    result = native("qe", Path(path).resolve(), "/lf:true", "/f:xml", "/e:Events",
                    "/rd:false", "/uni:true")
    if result.returncode:
        raise ValueError(f"EVTX okunamadı ({result.returncode})")
    # /uni:true emits UTF-16LE (the BOM is optional on redirected output).
    return events_from_xml(result.stdout.decode("utf-16le"))


def prepare():
    create_evtx("olaylar.evtx")
    create_evtx("bos.evtx", ())
    Path("bozuk.evtx").write_bytes(b"Pafta: this is not an event log.\n")

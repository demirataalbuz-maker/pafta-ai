# -*- coding: utf-8 -*-
"""Regex yolunun .NET ve JavaScript motorları: gerçek motor ayrı bir süreçte, iş başına bir kez açılır.

    motor: dotnet      → Windows PowerShell 5.1'in System.Text.RegularExpressions (.NET Framework 4.x),
                          RegexOptions.None, 2 saniyelik eşleşme zaman aşımı
    motor: javascript  → Node'un RegExp'i, 'gu' bayraklarıyla (modern kodun varsayılanı)

Yardımcı süreçle satır başına bir JSON isteği/yanıtı konuşulur. İki motor da konumları UTF-16
birimiyle verir; burada Python karakter konumuna çevrilir. Nesne arayüzü re.Pattern'ın düzeneğin
kullandığı alt kümesidir (pcre2_engine.Desen ile aynı): search, match, fullmatch, finditer,
findall, sub, split, groups, groupindex. sub şablonu Python biçimindedir (\\1, \\g<ad>).
"""
import atexit
import json
import os
import re
import shutil
import subprocess
import tempfile

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

NODE_YARDIMCI = r"""
const rl = require('readline').createInterface({ input: process.stdin });
rl.on('line', (satir) => {
  let y;
  try {
    const i = JSON.parse(satir);
    const rx = new RegExp(i.desen, i.bayrak);
    if (i.op === 'derle') {
      const adlar = [...i.desen.matchAll(/\(\?<([A-Za-z_$][\w$]*)>/g)].map(m => m[1]);
      const say = new RegExp('(?:' + i.desen + ')|', i.bayrak.replace('g', '')).exec('').length - 1;
      y = { ok: true, gruplar: say, adlar };
    } else {
      const es = [];
      for (const m of i.metin.matchAll(rx)) {
        es.push({ bas: m.index, son: m.index + m[0].length, d: m[0], g: m.slice(1).map(x => x === undefined ? null : x),
                  adli: m.groups ? Object.fromEntries(Object.entries(m.groups).map(([k, v]) => [k, v === undefined ? null : v])) : {} });
        if (es.length >= 5000) break;
      }
      y = { ok: true, es };
    }
  } catch (e) { y = { ok: false, hata: e.name + ': ' + e.message }; }
  process.stdout.write(JSON.stringify(y) + '\n');
});
"""

PS_YARDIMCI = r"""
[Console]::InputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$sure = [TimeSpan]::FromSeconds(2)
while ($null -ne ($satir = [Console]::In.ReadLine())) {
    try {
        $i = $satir | ConvertFrom-Json
        $rx = New-Object Text.RegularExpressions.Regex($i.desen, [Text.RegularExpressions.RegexOptions]::None, $sure)
        if ($i.op -eq 'derle') {
            $adlar = @($rx.GetGroupNames() | Where-Object { $_ -notmatch '^\d+$' })
            $nolar = @($rx.GetGroupNumbers() | Where-Object { $_ -ne 0 } | ForEach-Object { $rx.GroupNameFromNumber($_) })
            $y = @{ ok = $true; gruplar = ($rx.GetGroupNumbers().Count - 1); adlar = $adlar; sira = $nolar }
        } else {
            $es = New-Object Collections.ArrayList
            foreach ($m in $rx.Matches([string]$i.metin)) {
                $g = New-Object Collections.ArrayList
                $adli = @{}
                foreach ($no in $rx.GetGroupNumbers()) {
                    if ($no -eq 0) { continue }
                    $grp = $m.Groups[$no]
                    $deger = if ($grp.Success) { $grp.Value } else { $null }
                    [void]$g.Add($deger)
                    $ad = $rx.GroupNameFromNumber($no)
                    if ($ad -notmatch '^\d+$') { $adli[$ad] = $deger }
                }
                [void]$es.Add(@{ bas = $m.Index; son = $m.Index + $m.Length; d = $m.Value; g = @($g); adli = $adli })
                if ($es.Count -ge 5000) { break }
            }
            $y = @{ ok = $true; es = @($es) }
        }
    } catch {
        $e = $_.Exception
        while ($e.InnerException) { $e = $e.InnerException }
        $y = @{ ok = $false; hata = $e.GetType().Name + ': ' + $e.Message }
    }
    [Console]::Out.WriteLine((ConvertTo-Json $y -Compress -Depth 6))
    [Console]::Out.Flush()
}
"""


class RegexMotorHatasi(Exception):
    def __init__(self, msg, pos=None):
        super().__init__(msg)
        self.msg = msg
        self.pos = pos


class _Yardimci:
    """Motorun kalıcı yardımcı süreci; bir harness işinde bir kez açılır."""
    _acik = {}

    @classmethod
    def al(cls, motor):
        if motor not in cls._acik:
            cls._acik[motor] = cls(motor)
        return cls._acik[motor]

    def __init__(self, motor):
        self.betik = None
        if motor == "javascript":
            node = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
            if not os.path.isfile(node):
                raise RegexMotorHatasi("Node bulunamadı (JavaScript regex motoru için gerekli).")
            komut = [node, "-e", NODE_YARDIMCI]
        elif motor == "dotnet":
            # Yardımcı betik geçici bir dosyadan çalışır; stdin yalnız isteklere kalır
            fd, self.betik = tempfile.mkstemp(prefix="pafta_regex_", suffix=".ps1")
            with os.fdopen(fd, "w", encoding="utf-8-sig") as f:
                f.write(PS_YARDIMCI)
            komut = ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                     "-File", self.betik]
        else:
            raise RegexMotorHatasi(f"Bilinmeyen motor: {motor}")
        self.motor = motor
        self.p = subprocess.Popen(komut, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                  creationflags=NO_WINDOW)

    def iste(self, istek):
        self.p.stdin.write((json.dumps(istek, ensure_ascii=True) + "\n").encode("utf-8"))
        self.p.stdin.flush()
        satir = self.p.stdout.readline()
        while satir and not satir.strip().lstrip(b"\xef\xbb\xbf").startswith(b"{"):
            satir = self.p.stdout.readline()          # olası boş satırlar
        if not satir:
            raise RegexMotorHatasi(f"{self.motor} motoru yanıt vermedi.")
        return json.loads(satir.decode("utf-8-sig"))

    def kapat(self):
        try:
            self.p.stdin.close()
            self.p.wait(timeout=3)
        except Exception:
            self.p.kill()
        if self.betik:
            try:
                os.remove(self.betik)
            except OSError:
                pass


@atexit.register
def _hepsini_kapat():
    for y in list(_Yardimci._acik.values()):
        y.kapat()
    _Yardimci._acik.clear()


def _birim_haritasi(s):
    """UTF-16 birim konumu → Python karakter konumu. Bir vekil çiftinin ortası (motor BMP dışı bir
    karakterin yarısını eşlediyse) karakterin başına, bitiş için sonuna yuvarlanır: (bas, son) eşlemesi."""
    bas, son, birim = {0: 0}, {0: 0}, 0
    for i, ch in enumerate(s):
        if ord(ch) > 0xFFFF:
            bas[birim + 1], son[birim + 1] = i, i + 1
            birim += 2
        else:
            birim += 1
        bas[birim] = son[birim] = i + 1
    return bas, son


def _temizle(v):
    """Motorun döndürdüğü tek başına vekil yarımları (yarım karakter) U+FFFD olur; çıktı UTF-8'e yazılabilsin."""
    if v is None:
        return None
    return v.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "replace")


class Eslesme:
    def __init__(self, desen, metin, bas, son, deger, gruplar, adli):
        self.re = desen
        self.string = metin
        self._bas, self._son = bas, son
        self._deger = deger
        self._g = gruplar
        self._adli = adli

    def _no(self, g):
        if isinstance(g, int):
            if 0 <= g <= len(self._g):
                return g
            raise IndexError("no such group")
        if g in self.re.groupindex:
            return self.re.groupindex[g]
        raise IndexError("no such group")

    def group(self, *gruplar):
        if not gruplar:
            gruplar = (0,)
        d = [self._deger if self._no(g) == 0 else
             (self._adli.get(g) if isinstance(g, str) else self._g[self._no(g) - 1]) for g in gruplar]
        return d[0] if len(d) == 1 else tuple(d)

    __getitem__ = group

    def groups(self, default=None):
        return tuple(default if v is None else v for v in self._g)

    def groupdict(self, default=None):
        return {ad: (default if self._adli.get(ad) is None else self._adli.get(ad)) for ad in self.re._ad_sirasi}

    def start(self, g=0):
        if self._no(g) != 0:
            raise NotImplementedError("bu motorda yalnız bütün eşleşmenin konumu verilir")
        return self._bas

    def end(self, g=0):
        if self._no(g) != 0:
            raise NotImplementedError("bu motorda yalnız bütün eşleşmenin konumu verilir")
        return self._son

    def span(self, g=0):
        return (self.start(g), self.end(g))

    def expand(self, sablon):
        def yerine(m):
            if m.group(0) == "\\\\":
                return "\\"
            g = m.group(1) or m.group(2)
            return self.group(int(g) if g.isdigit() else g) or ""
        return re.sub(r"\\g<(\w+)>|\\(\d{1,2})|\\\\", yerine, sablon)


class Desen:
    def __init__(self, pattern, motor):
        self.pattern = pattern
        self.motor = motor
        self.bayrak = "gu" if motor == "javascript" else ""
        self._y = _Yardimci.al(motor)
        y = self._y.iste({"op": "derle", "desen": pattern, "bayrak": self.bayrak})
        if not y["ok"]:
            raise RegexMotorHatasi(y["hata"])
        self.groups = y["gruplar"]
        adlar = y.get("adlar") or []
        if motor == "dotnet":
            sira = y.get("sira") or []
            self.groupindex = {ad: sira.index(ad) + 1 for ad in adlar if ad in sira}
        else:
            self.groupindex = {}
            # JavaScript adlı grupları da numaralar; sıra, desendeki açılış sırasıdır
            no = 0
            for m in re.finditer(r"\\.|\[(?:\\.|[^\]])*\]|\((\?<([A-Za-z_$][\w$]*)>|\?[:=!]|\?<[=!])?", pattern):
                if m.group(0).startswith("(") and (m.group(1) is None or m.group(2)):
                    no += 1
                    if m.group(2):
                        self.groupindex[m.group(2)] = no
        self._ad_sirasi = sorted(self.groupindex, key=self.groupindex.get)

    def _tara(self, s, desen=None):
        y = self._y.iste({"op": "tara", "desen": desen or self.pattern, "bayrak": self.bayrak, "metin": s})
        if not y["ok"]:
            raise RegexMotorHatasi(y["hata"])
        bas, son = _birim_haritasi(s)
        return [Eslesme(self, s, bas[e["bas"]], son[e["son"]], _temizle(e.get("d")),
                        [_temizle(v) for v in (e.get("g") or [])],
                        {k: _temizle(v) for k, v in (e.get("adli") or {}).items()}) for e in y["es"]]

    def finditer(self, s):
        return iter(self._tara(s))

    def findall(self, s):
        out = []
        for m in self._tara(s):
            if self.groups == 0:
                out.append(m.group(0))
            elif self.groups == 1:
                out.append(m.groups("")[0])
            else:
                out.append(m.groups(""))
        return out

    def search(self, s):
        es = self._tara(s)
        return es[0] if es else None

    def match(self, s):
        es = self._tara(s, r"\A(?:" + self.pattern + ")" if self.motor == "dotnet" else "^(?:" + self.pattern + ")")
        return es[0] if es and es[0].start() == 0 else None

    def fullmatch(self, s):
        tam = (r"\A(?:" + self.pattern + r")\z") if self.motor == "dotnet" else ("^(?:" + self.pattern + ")$")
        es = self._tara(s, tam)
        return es[0] if es else None

    def sub(self, yeni, s, count=0):
        out, son, n = [], 0, 0
        for m in self._tara(s):
            if count and n >= count:
                break
            out.append(s[son:m.start()])
            out.append(yeni(m) if callable(yeni) else m.expand(yeni))
            son, n = m.end(), n + 1
        out.append(s[son:])
        return "".join(out)

    def split(self, s, maxsplit=0):
        out, son, n = [], 0, 0
        for m in self._tara(s):
            if maxsplit and n >= maxsplit:
                break
            out.append(s[son:m.start()])
            out.extend(m.groups())
            son, n = m.end(), n + 1
        out.append(s[son:])
        return out


def compile(pattern, motor):
    return Desen(pattern, motor)


def bilgi(pattern, motor):
    d = Desen(pattern, motor)
    ad = {"dotnet": ".NET Framework (Windows PowerShell 5.1), RegexOptions.None",
          "javascript": "Node RegExp, bayraklar: gu"}[motor]
    satirlar = [ad, f"yakalayan grup: {d.groups}"]
    for g in d._ad_sirasi:
        satirlar.append(f"  (?<{g}>…) → grup {d.groupindex[g]}")
    satirlar.append("Bu motor ayrıştırma ağacını dışarı vermez; desenin nasıl eşleştiğini Çalıştır ile dene.")
    return "\n".join(satirlar)

# -*- coding: utf-8 -*-
"""C# yolundaki klasik ASP.NET derslerinin gerçek çıktısını üretir (CS14'ün gercek blokları).

tracks/csharp/aspnet_lab/'daki sayfaları, .NET Framework'ün kendi System.Web'iyle IIS olmadan,
süreç içinde (ApplicationHost + HttpRuntime.ProcessRequest) çalıştırır. Kurulum gerektirmez:
Windows'taki .NET Framework 4.x ve onun csc.exe'si yeterlidir. Her çalıştırma geçici bir klasörde
derler; depoya bir şey yazmaz.

    python tools/aspnet_yasam_dongusu.py GET:Sayfa.aspx TIKLA:Sayfa.aspx TIKLA:Sayfa.aspx
    python tools/aspnet_yasam_dongusu.py GET:Hatali.aspx TIKLA:Hatali.aspx BOZUK:Sayfa.aspx

Adımlar: GET (ilk istek), TIKLA (önceki yanıtın gizli alanlarıyla düğmeye basılmış postback),
BOZUK (ViewState'in son karakterleri değiştirilmiş postback).
"""
import base64
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAB = os.path.join(ROOT, "tracks", "csharp", "aspnet_lab")
CSC = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Microsoft.NET", "Framework64", "v4.0.30319", "csc.exe")


def kur(kok):
    app = os.path.join(kok, "app")
    os.makedirs(os.path.join(app, "bin"))
    os.makedirs(os.path.join(kok, "tmp"))
    for ad in os.listdir(LAB):
        if ad.endswith((".aspx", ".asax")):
            shutil.copy(os.path.join(LAB, ad), app)
    with open(os.path.join(app, "web.config"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0"?>\n<configuration>\n  <system.web>\n'
                f'    <compilation debug="false" targetFramework="4.8" tempDirectory="{os.path.join(kok, "tmp")}" />\n'
                '    <httpRuntime targetFramework="4.8" />\n'
                '    <hostingEnvironment shadowCopyBinAssemblies="false" />\n'
                '  </system.web>\n</configuration>\n')
    kitaplik = os.path.join(app, "bin", "Barindirici.dll")
    for args in (["-target:library", "-out:" + kitaplik, os.path.join(LAB, "Barindirici.cs")],
                 ["-out:" + os.path.join(app, "bin", "Calistir.exe"), "-r:" + kitaplik, os.path.join(LAB, "Calistir.cs")]):
        subprocess.run([CSC, "-nologo", "-r:System.Web.dll"] + args, check=True, capture_output=True)
    return app


def gizli_alanlar(html):
    return dict(re.findall(r'name="(__[A-Z]+)" id="__[A-Z]+" value="([^"]*)"', html))


def calistir(adimlar):
    kok = tempfile.mkdtemp(prefix="pafta_aspnet_")
    try:
        app = kur(kok)
        p = subprocess.Popen([os.path.join(app, "bin", "Calistir.exe"), app], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, text=True, encoding="utf-8")

        def gonder(fiil, sayfa, govde=None):
            p.stdin.write("\t".join([fiil, sayfa, ""] + ([govde] if govde is not None else [])) + "\n")
            p.stdin.flush()
            while True:
                s = p.stdout.readline()
                if not s:
                    raise RuntimeError("ASP.NET barındırıcısı yanıt vermedi")
                if s.startswith("<<<"):
                    return base64.b64decode(s[3:]).decode("utf-8")

        log = os.path.join(app, "olaylar.txt")
        son = {}
        for adim in adimlar:
            tur, sayfa = adim.split(":", 1)
            onceki = son.get(sayfa, {})
            if tur == "GET":
                html = gonder("GET", sayfa)
            else:
                alan = dict(onceki)
                if tur == "BOZUK":
                    alan["__VIEWSTATE"] = alan["__VIEWSTATE"][:-6] + "AAAAAA"
                html = gonder("POST", sayfa, urllib.parse.urlencode(dict(alan, dugme="Arttır")))
            m = re.search(r'id="sayac">(\d+)<', html)
            if m:
                print(f"{adim} → sayaç {m.group(1)}")
                son[sayfa] = gizli_alanlar(html)
            else:
                baslik = re.search(r"<title>(.*?)</title>", html, re.S)
                print(f"{adim} → hata: " + (re.sub(r"\s+", " ", baslik.group(1)).strip()[:60] if baslik else html[:60]))
        p.stdin.close()
        p.wait(timeout=30)
        print("---")
        with open(log, encoding="utf-8") as f:
            print(f.read(), end="")
    finally:
        shutil.rmtree(kok, ignore_errors=True)


if __name__ == "__main__":
    calistir(sys.argv[1:] or ["GET:Sayfa.aspx", "TIKLA:Sayfa.aspx"])

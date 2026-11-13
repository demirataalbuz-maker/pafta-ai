# -*- coding: utf-8 -*-
"""Rota ve Tarih Tarih Kombine Çalışma Takvimi: Pafta, TryHackMe ve HackTheBox Academy
yollarının seçilen Major hedefe, kullanıcının platform üyeliklerine ve günlük çalışma
temposuna göre gün gün / hafta hafta birleştirildiği dinamik çalışma planı.

Pafta'nın ilerlemesi derslerden hesaplanır. THM/HTB ilerlemesi siteden okunup elle
girilir ve %LOCALAPPDATA%\\Pafta\\rota.json'da durur (progress.json'a dokunulmaz).
Yazımlar atomik (geçici dosya + os.replace).
"""
import datetime as _dt
import json
import math
import os
import threading

from engine.progress import data_dir

AYLAR_TR = ("", "Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara")
GUNLER_TR = ("Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz")


def _tarih_tr(d, gun_adi=False):
    s = f"{d.day:02d} {AYLAR_TR[d.month]} {d.year}"
    return f"{s} {GUNLER_TR[d.weekday()]}" if gun_adi else s


# Varsayılan başlangıç ilerlemeleri (kullanıcının mevcut THM / HTB durumu)
VARSAYILAN_ILERLEME = {
    "thm": {
        "presec": {"yuzde": 100.0, "sertifika": False},
        "cs101": {"yuzde": 6.0, "sertifika": False},
        "soc1": {"yuzde": 7.0, "sertifika": False},
        "aisec": {"yuzde": 33.0, "sertifika": False},
    },
    "htb": {
        "aired": {"yuzde": 27.8, "sertifika": False},
        "cdsa": {"yuzde": 0.6, "sertifika": False},
    },
}

# Kullanıcının sahip olduğu platform üyelikleri
UYELIKLER = [
    {"id": "pafta_thm_htb", "ad": "Pafta + TryHackMe + HTB Academy (3'lü Tam Kombine)", "thm": True, "htb": True},
    {"id": "pafta_thm", "ad": "Pafta + TryHackMe Üyeliği", "thm": True, "htb": False},
    {"id": "pafta_htb", "ad": "Pafta + HTB Academy Üyeliği", "thm": False, "htb": True},
    {"id": "sadece_pafta", "ad": "Yalnızca Pafta (Dış Üyelik Yok · %100 Yerel)", "thm": False, "htb": False},
]

# Çalışma temposu seçenekleri (günlük saat ve temel ders/adım hızı)
TEMPOLAR = [
    {"id": "normal", "ad": "Normal Tempo (Günde 2–3 Saat)", "saat_gun": 2.5, "adim_gun": 18, "ders_gun": 2,
     "dis_yuzde_gun": 2.0,
     "dagilim": "Günde ~2 Pafta dersi + açık olan dış platformlardan (THM/HTB) ~%2 ilerleme"},
    {"id": "yogun", "ad": "Yoğun Tempo (Günde 4–5 Saat)", "saat_gun": 4.5, "adim_gun": 30, "ders_gun": 3,
     "dis_yuzde_gun": 3.5,
     "dagilim": "Sabah Blok (2s): Major 1 (AI Dersleri + COAE/AI1) · Akşam Blok (2.5s): Major 2 (Savunma/SOC + THM/HTB)"},
    {"id": "kamp", "ad": "Tam Zamanlı Kamp (Günde 6–8 Saat)", "saat_gun": 7.0, "adim_gun": 44, "ders_gun": 5,
     "dis_yuzde_gun": 5.0,
     "dagilim": "Blok 1 (2.5s): Pafta AI · Blok 2 (2.5s): Pafta Savunma/Tespit · Blok 3 (2s): THM & HTB Sertifika Labları"},
]

# Hedef Profiller (Kişinin seçtiği Major alanlara göre dinamik aşamalar)
HEDEFLER = {
    "ai_mavi": {
        "id": "ai_mavi",
        "ad": "AI Tam Kapsam (Red + Blue) & Siber Savunma (Blue Team)",
        "etiket": "4 Major Uzmanlık · AI Red + AI Defense (203 Ders) + SOC/DFIR + Detection Engineer",
        "ozet": "Üst çatı 2 Ana Sütun, kariyer rolü olarak 4 Major Alan: (1) AI Red Teamer, (2) AI Defense & Assurance, (3) SOC Analyst & DFIR, (4) Detection Engineer.",
        "asamalar": [
            {"id": "faz1_temel", "ad": "Faz 1 · Siber Temel, AI Mimarisi & Sıfırdan AI İnşası",
             "not": "THM Pre Security ve CS 101 ile temel at, HTB CJCA ile analist omurgasını kur, Pafta'da betik dillerini, LLM/Transformer iç mimarisini (ai-temel) ve sıfırdan kendi Frontier yapay zekanı kodlayarak üretmeyi (ai-uretim) bitir.",
             "pafta": ["python", "bash", "powershell", "cmd", "http", "ai-temel", "ai-uretim"],
             "thm": [("presec", "Pre Security", "SEC0"), ("cs101", "Cyber Security 101", "SEC1")],
             "htb": [("cjca", "Junior Cybersecurity Analyst", "CJCA")]},
            {"id": "faz2_aired_soc1", "ad": "Faz 2 · Major 1: AI Red Team & SOC Seviye 1",
             "not": "Saldırıyı bilmeden savunma kurulmaz: Pafta'da 64 derslik AI Saldırı müfredatını, THM AI Security (AI1) ve HTB AI Red Teamer (COAE) ile birlikte bitirirken SOC Level 1 + paket/log analizine gir.",
             "pafta": ["ai-saldiri", "sql", "regex", "packets", "spl"],
             "thm": [("aisec", "AI Security", "AI1"), ("soc1", "SOC Level 1", "SAL1")],
             "htb": [("aired", "AI Red Teamer", "COAE")]},
            {"id": "faz3_aiblue_soc2", "ad": "Faz 3 · Major 2 & 3: AI Defense + SOC Seviye 2 / DFIR",
             "not": "LLM/Ajan sistemlerini koruyan Guardrail, Dual-LLM, Circuit Breaker ve filigranlama savunmalarını (ai-savunma + Agentic AI) kur; klasik tarafta CDSA ve SAL2 ile ileri SOC ve Windows IR'a geç.",
             "pafta": ["ai-savunma", "elastic", "ids", "yara", "ad"],
             "thm": [("agentic", "Agentic AI Security", None), ("soc2", "SOC Level 2", "SAL2"),
                     ("winir", "Windows Incident Response & Forensics", None)],
             "htb": [("cdsa", "SOC Analyst", "CDSA")]},
            {"id": "faz4_guvence_endpoint", "ad": "Faz 4 · AI Güvence (Assurance) & İleri Endpoint/Bulut Savunması",
             "not": "ML matematiği, SAE, Model Merging, DLG/Krum, zkML ve Adversarial ML (ai-guvence) ile derinleş; klasik tarafta Endpoint Investigations ve Defending Azure ile uygulama/sistem katmanını kapat.",
             "pafta": ["ai-guvence", "php", "javascript", "java", "c", "csharp", "asm"],
             "thm": [("endpoint", "Advanced Endpoint Investigations", None), ("azure", "Defending Azure", None)],
             "htb": [("cdep", "Detection Engineer", "CDEP")]},
            {"id": "faz5_detection_otonom", "ad": "Faz 5 · Major 4: Detection Engineer, Kuantum & Otonom AI Savunma",
             "not": "Sigma ve KQL ile profesyonel tespit mühendisliğini (CDEP) tamamla; kuantum bilgisayarlar ve Post-Quantum kriptografiyi (kuantum) öğren; öğrendiğin tüm SOC, SAST, Fuzzing ve Z3 sembolik analiz işlerini AI ajanlarıyla (ai-ile-guvenlik) otomatize et.",
             "pafta": ["ai-ile-guvenlik", "kuantum", "sigma", "kql", "purple", "bitirme"],
             "thm": [],
             "htb": []},
        ],
        "yan": {"id": "yan", "ad": "İsteğe Bağlı · Klasik Ofansif Ekstra",
                "not": "Savunma ve AI omurgası bittikten sonra klasik pentest sertifikalarına da bakmak istersen.",
                "pafta": [],
                "thm": [("jrpt", "Jr Penetration Tester", "PT1"), ("webpt", "Web Application Pentesting", None),
                        ("redteam", "Red Teaming", None)],
                "htb": [("cpts", "Penetration Tester", "CPTS"), ("cape", "AD Penetration Tester", "CAPE")]},
    },
    "ai_tam": {
        "id": "ai_tam",
        "ad": "Yalnızca Yapay Zeka Güvenliği (AI Red Team + AI Defense)",
        "etiket": "2 Major Uzmanlık · 203 AI Dersi + COAE + AI1 + Agentic AI",
        "ozet": "Doğrudan Yapay Zeka Güvenliğinin tüm cephelerine (Mimari, AI Red Team, AI Defense, AI Güvence/Matematik ve Otonom Siber Ajanlar) odaklanan hızlandırılmış uzmanlık takvimi.",
        "asamalar": [
            {"id": "ai1_mimari", "ad": "Faz 1 · Python, HTTP, LLM Mimarisi & Sıfırdan AI İnşası",
             "not": "Dil modelleri, Tokenizer, Transformer, KV-Cache, Quantization, LoRA, RAG, FSM, GRPO, Speculative Decoding, MoE, Mamba temeli ve sıfırdan kendi Frontier LLM/Reasoning modelini kodlayarak inşa etme (ai-uretim).",
             "pafta": ["python", "http", "ai-temel", "ai-uretim"],
             "thm": [("presec", "Pre Security", "SEC0"), ("aisec", "AI Security", "AI1")],
             "htb": []},
            {"id": "ai2_saldiri", "ad": "Faz 2 · AI Red Team ve Ajan/Model Saldırıları",
             "not": "Prompt Injection, Jailbreak, GCG, VLM/Ses, MCP/RAG Zehirleme, Carlini SVD Model Çalma, GUI Spoofing, Rowhammer Bit-Flip, LeftoverLocals ve MCTS Saptırma.",
             "pafta": ["ai-saldiri"],
             "thm": [("agentic", "Agentic AI Security", None)],
             "htb": [("aired", "AI Red Teamer", "COAE")]},
            {"id": "ai3_savunma", "ad": "Faz 3 · AI Defense ve Kurumsal Guardrail Mimarisi",
             "not": "Input/Output Guardrails, Dual-LLM izolasyonu, Circuit Breakers, Logit Truncation, GraphRAG Karantina ve Kirchenbauer İstatistiksel Filigranlama.",
             "pafta": ["ai-savunma"],
             "thm": [],
             "htb": []},
            {"id": "ai4_guvence", "ad": "Faz 4 · AI Güvence, ML Matematiği ve Mekanistik Analiz",
             "not": "Uygulamalı ML Matematiği, FGSM/PGD, LiRA, DP-SGD, Backdoor, Sparse Autoencoders (SAE), Reward Hacking, TIES/DARE, DLG/Krum, Radyoaktif Veri ve zkML.",
             "pafta": ["ai-guvence"],
             "thm": [],
             "htb": []},
            {"id": "ai5_otonom", "ad": "Faz 5 · AI ile Siber Güvenlik, Kuantum ve Otonom Zafiyet Avı",
             "not": "LLM ile SOC Triyaj, CTI, Otomatik Sigma/YARA üretimi, SAST, Fuzzing, DARPA AIxCC tarzı Z3 Sembolik Kısıt Çözücü ve Kuantum Bilgisayarlar / Post-Quantum Kriptografi.",
             "pafta": ["ai-ile-guvenlik", "kuantum"],
             "thm": [],
             "htb": []},
        ],
        "yan": {"id": "yan", "ad": "Yan Yol · Klasik Savunma Destek",
                "not": "AI ajanlarının ürettiği kuralları sahada test etmek için yararlı klasik yollar.",
                "pafta": ["bash", "regex", "yara", "sigma", "kql"],
                "thm": [("soc1", "SOC Level 1", "SAL1")],
                "htb": [("cjca", "Junior Cybersecurity Analyst", "CJCA")]},
    },
    "mavi_tam": {
        "id": "mavi_tam",
        "ad": "Mavi Takım & Detection Engineer (Blue Team Odaklı)",
        "etiket": "2 Major Uzmanlık · SOC/DFIR (SAL1/SAL2/CDSA) + Detection Engineer (CDEP)",
        "ozet": "Klasik SOC Analistliğinden başlayıp Adli Bilişim (DFIR), Active Directory Savunması, Tespit Mühendisliği (Sigma/KQL) ve AI destekli savunmaya uzanan Mavi Takım yolu.",
        "asamalar": [
            {"id": "mavi1_giris", "ad": "Faz 1 · Bilgisayar, Betik ve Siber Güvenlik Temeli",
             "not": "Komut satırı, betik dilleri, protokoller ve analist temeli.",
             "pafta": ["python", "bash", "powershell", "cmd", "http"],
             "thm": [("presec", "Pre Security", "SEC0"), ("cs101", "Cyber Security 101", "SEC1")],
             "htb": [("cjca", "Junior Cybersecurity Analyst", "CJCA")]},
            {"id": "mavi2_soc1", "ad": "Faz 2 · SOC Seviye 1, Paket Analizi ve SIEM",
             "not": "Ağ trafiği inceleme (Wireshark/tcpdump), Splunk (SPL), Elastic/Kibana ve temel sorgu dilleri.",
             "pafta": ["sql", "regex", "packets", "spl", "elastic"],
             "thm": [("soc1", "SOC Level 1", "SAL1")],
             "htb": [("cdsa", "SOC Analyst", "CDSA")]},
            {"id": "mavi3_soc2_dfir", "ad": "Faz 3 · SOC Seviye 2, Ağ/Dosya Tespiti ve Windows IR",
             "not": "Suricata/Zeek IDS, YARA kuralları, Active Directory savunması ve Windows Olay Müdahale.",
             "pafta": ["ids", "yara", "ad", "c", "csharp", "asm"],
             "thm": [("soc2", "SOC Level 2", "SAL2"), ("winir", "Windows Incident Response & Forensics", None),
                     ("endpoint", "Advanced Endpoint Investigations", None)],
             "htb": []},
            {"id": "mavi4_detection", "ad": "Faz 4 · Tespit Mühendisliği (Detection Engineer) ve Bulut",
             "not": "Sigma, KQL, Azure savunması, Purple Team tatbikatları ve AI ile güvenlik otomasyonu.",
             "pafta": ["sigma", "kql", "purple", "ai-savunma", "ai-ile-guvenlik", "bitirme"],
             "thm": [("azure", "Defending Azure", None), ("aisec", "AI Security", "AI1")],
             "htb": [("cdep", "Detection Engineer", "CDEP")]},
        ],
        "yan": {"id": "yan", "ad": "Yan Yol · AI Red Team & Güvence",
                "not": "Savunmacı gözüyle AI saldırılarını ve model güvencesini tanımak için.",
                "pafta": ["ai-temel", "ai-saldiri", "ai-guvence"],
                "thm": [("agentic", "Agentic AI Security", None)],
                "htb": [("aired", "AI Red Teamer", "COAE")]},
    },
    "kirmizi_tam": {
        "id": "kirmizi_tam",
        "ad": "Kırmızı Takım & AI Red Team (Red Team Odaklı)",
        "etiket": "3 Major Uzmanlık · Pentester (CPTS) + AD Red Team (CAPE) + AI Red Team (COAE)",
        "ozet": "Web, Ağ, Active Directory sızma testi ve modern Yapay Zeka Red Team operasyonlarını birleştiren ofansif uzmanlık yolu.",
        "asamalar": [
            {"id": "red1_temel", "ad": "Faz 1 · Betik, Ağ ve Web Temeli",
             "not": "Sızma testi için gereken programlama, kabuk ve HTTP altyapısı.",
             "pafta": ["python", "bash", "powershell", "cmd", "http", "sql", "regex"],
             "thm": [("presec", "Pre Security", "SEC0"), ("cs101", "Cyber Security 101", "SEC1"),
                     ("jrpt", "Jr Penetration Tester", "PT1")],
             "htb": [("cjca", "Junior Cybersecurity Analyst", "CJCA")]},
            {"id": "red2_web_uygulama", "ad": "Faz 2 · Web ve Uygulama Sızma Testi (CPTS)",
             "not": "PHP, JavaScript, Java uygulama zafiyetleri ve ağ paket analizi.",
             "pafta": ["php", "javascript", "java", "packets"],
             "thm": [("webpt", "Web Application Pentesting", None), ("webrt", "Web Application Red Teaming", None)],
             "htb": [("cpts", "Penetration Tester", "CPTS")]},
            {"id": "red3_ad_binary", "ad": "Faz 3 · Active Directory, Binary ve Red Team Operasyonları (CAPE)",
             "not": "Active Directory saldırı zincirleri, C/C#/Assembly, bellek analizi ve Evasion.",
             "pafta": ["ad", "c", "csharp", "asm", "yara"],
             "thm": [("redteam", "Red Teaming", None)],
             "htb": [("cape", "AD Penetration Tester", "CAPE")]},
            {"id": "red4_aired", "ad": "Faz 4 · AI Red Teamer ve Otonom Zafiyet Avı (COAE)",
             "not": "LLM/Ajan saldırıları, model çalma, donanım yan-kanalları ve sembolik zafiyet avcılığı.",
             "pafta": ["ai-temel", "ai-saldiri", "ai-guvence", "ai-ile-guvenlik", "purple", "bitirme"],
             "thm": [("aisec", "AI Security", "AI1"), ("agentic", "Agentic AI Security", None)],
             "htb": [("aired", "AI Red Teamer", "COAE")]},
        ],
        "yan": {"id": "yan", "ad": "Yan Yol · Savunma ve Tespit Karşı-Analizi",
                "not": "EDR/SIEM kurallarını anlamak ve atlatmak için mavi takım araçları.",
                "pafta": ["spl", "elastic", "ids", "sigma", "kql", "ai-savunma"],
                "thm": [("soc1", "SOC Level 1", "SAL1")],
                "htb": [("cdsa", "SOC Analyst", "CDSA"), ("cdep", "Detection Engineer", "CDEP")]},
    },
    "purple_tam": {
        "id": "purple_tam",
        "ad": "Tam Kapsam · Purple Team + Tüm AI (28 Yolun Tamamı)",
        "etiket": "Tüm Müfredat · Klasik Kırmızı + Mavi + 203 AI Dersi",
        "ozet": "Hiçbir konuyu dışarıda bırakmayan tam kapsamlı Kırmızı + Mavi + Yapay Zeka müfredatı.",
        "asamalar": [
            {"id": "giris", "ad": "Faz 1 · Giriş ve Temel Omurga",
             "not": "İki tarafın temel kavramları. THM ile ısın, CJCA ile sağlamlaştır, AI mimarisine adım at.",
             "pafta": ["python", "bash", "powershell", "cmd", "http", "ai-temel"],
             "thm": [("presec", "Pre Security", "SEC0"), ("cs101", "Cyber Security 101", "SEC1"),
                     ("soc1", "SOC Level 1", "SAL1"), ("jrpt", "Jr Penetration Tester", "PT1")],
             "htb": [("cjca", "Junior Cybersecurity Analyst", "CJCA")]},
            {"id": "omurga", "ad": "Faz 2 · Omurga · Kırmızı + Mavi + AI Red Team",
             "not": "CPTS, CDSA ve COAE paralel: klasik ve yapay zeka saldırı/savunma omurgası.",
             "pafta": ["sql", "regex", "php", "javascript", "java", "packets", "spl", "elastic", "ids", "yara", "ai-saldiri"],
             "thm": [("soc2", "SOC Level 2", "SAL2"), ("webpt", "Web Application Pentesting", None),
                     ("aisec", "AI Security", "AI1")],
             "htb": [("cpts", "Penetration Tester", "CPTS"), ("cdsa", "SOC Analyst", "CDSA"),
                     ("aired", "AI Red Teamer", "COAE")]},
            {"id": "windows", "ad": "Faz 3 · Windows, Active Directory ve AI Savunma/Güvence",
             "not": "Purple ekiplerin sahası: AD, sistem katmanı, AI Defense ve ML Güvence aynı ortamda.",
             "pafta": ["ad", "c", "csharp", "asm", "ai-savunma", "ai-guvence"],
             "thm": [("winir", "Windows Incident Response & Forensics", None),
                     ("endpoint", "Advanced Endpoint Investigations", None),
                     ("agentic", "Agentic AI Security", None)],
             "htb": [("cape", "AD Penetration Tester", "CAPE")]},
            {"id": "tespit", "ad": "Faz 4 · Tespit Mühendisliği ve Otonom AI Güvenlik",
             "not": "Purple'ın kalbi: saldırıyı bilip tespitini yazmak, doğrulamak ve AI ile otomatize etmek.",
             "pafta": ["sigma", "kql", "ai-ile-guvenlik", "purple", "bitirme"],
             "thm": [("azure", "Defending Azure", None), ("redteam", "Red Teaming", None)],
             "htb": [("cdep", "Detection Engineer", "CDEP")]},
            {"id": "secmeli", "ad": "İsteğe Bağlı · Seçmeli Uzmanlık",
             "not": "Vakit kalırsa ek sertifika yolları.",
             "pafta": [],
             "thm": [("webrt", "Web Application Red Teaming", None)],
             "htb": [("wifi", "Wi-Fi Penetration Tester", "CWPE")]},
        ],
        "yan": {"id": "yan", "ad": "Yan Yol · Ekstra Sertifika Takibi",
                "not": "Tüm yollar ana fazlara dahil edildi.",
                "pafta": [], "thm": [], "htb": []},
    },
}

VARSAYILAN_HEDEF = "ai_mavi"
VARSAYILAN_TEMPO = "yogun"
VARSAYILAN_UYELIK = "pafta_thm_htb"

# Geriye dönük uyumluluk (tools/denetim_sayfasi.py vb. için)
ASAMALAR = HEDEFLER["purple_tam"]["asamalar"]
YAN_YOL = HEDEFLER["ai_mavi"]["yan"]

PLATFORM = ("thm", "htb")


def _tum_dis_yollar():
    out = {"thm": set(), "htb": set()}
    for h in HEDEFLER.values():
        for a in list(h["asamalar"]) + [h["yan"]]:
            for p in PLATFORM:
                for yid, *_ in a.get(p, []):
                    out[p].add(yid)
    return out


GECERLI_DIS = _tum_dis_yollar()


def _tarih_takvimi_uret(asamalar_out, tempo_bilgi, uyelik_bilgi, baslangic_date):
    """Fazlar ve seçilen üyelik/tempo üzerinden gün gün ve hafta hafta kombine takvim üretir."""
    thm_aktif = uyelik_bilgi["thm"]
    htb_aktif = uyelik_bilgi["htb"]

    # Dış üyelik yoksa tüm çalışma saati Pafta'ya kalır → günlük Pafta hızı artar
    dis_sayisi = (1 if thm_aktif else 0) + (1 if htb_aktif else 0)
    carpan = 1.35 if dis_sayisi == 0 else (1.15 if dis_sayisi == 1 else 1.0)
    adim_gun = max(6, round(tempo_bilgi["adim_gun"] * carpan))
    ders_gun = max(1, round(tempo_bilgi["ders_gun"] * carpan))
    dis_yuzde_gun = tempo_bilgi["dis_yuzde_gun"]

    cur_date = baslangic_date
    gunluk_plan = []
    faz_ozetleri = []

    for faz_idx, a in enumerate(asamalar_out):
        if a["id"] == "secmeli":
            a["baslangic_tr"] = None
            a["bitis_tr"] = None
            a["gun_sayisi"] = 0
            continue

        # Pafta kalan ders havuzu: AI kolu ve Klasik/Savunma kolu olarak iki paralel kuyruk
        ai_kuyruk = []
        klasik_kuyruk = []
        kalan_faz_adim = 0
        for t in a["pafta"]:
            toplam = t.get("toplam", 0)
            bitti = t.get("bitti", 0)
            ders_top = t.get("ders_sayisi") or max(1, round(toplam / 9))
            biten_ders = min(ders_top, round(ders_top * (bitti / toplam))) if toplam else 0
            kalan_adim = max(0, toplam - bitti)
            kalan_faz_adim += kalan_adim
            if biten_ders < ders_top:
                kayit = {"id": t["id"], "ad": t["ad"], "cur": biten_ders + 1, "son": ders_top}
                if t["id"].startswith("ai-"):
                    ai_kuyruk.append(kayit)
                else:
                    klasik_kuyruk.append(kayit)

        thm_kuyruk = [{"id": y["id"], "ad": y["ad"], "sert": y.get("sertifika_adi"), "cur": float(y["yuzde"])}
                      for y in a["thm"] if thm_aktif and y["yuzde"] < 100.0]
        htb_kuyruk = [{"id": y["id"], "ad": y["ad"], "sert": y.get("sertifika_adi"), "cur": float(y["yuzde"])}
                      for y in a["htb"] if htb_aktif and y["yuzde"] < 100.0]

        kalan_thm_yuzde = sum(100.0 - y["cur"] for y in thm_kuyruk)
        kalan_htb_yuzde = sum(100.0 - y["cur"] for y in htb_kuyruk)

        if kalan_faz_adim == 0 and kalan_thm_yuzde == 0 and kalan_htb_yuzde == 0:
            a["baslangic_tr"] = "Tamamlandı"
            a["bitis_tr"] = "✓"
            a["gun_sayisi"] = 0
            continue

        gun_pafta = math.ceil(kalan_faz_adim / adim_gun) if kalan_faz_adim > 0 else 0
        gun_thm = math.ceil(kalan_thm_yuzde / (dis_yuzde_gun * 1.4)) if kalan_thm_yuzde > 0 else 0
        gun_htb = math.ceil(kalan_htb_yuzde / dis_yuzde_gun) if kalan_htb_yuzde > 0 else 0
        faz_gun = max(1, gun_pafta, min(45, max(gun_thm, gun_htb)))

        faz_bas = cur_date
        faz_bit = cur_date + _dt.timedelta(days=faz_gun - 1)
        a["baslangic_tr"] = _tarih_tr(faz_bas)
        a["bitis_tr"] = _tarih_tr(faz_bit)
        a["gun_sayisi"] = faz_gun

        # Günlük THM ve HTB ilerleme hızını faz gün sayısına göre yay
        thm_adim_gun = kalan_thm_yuzde / faz_gun if faz_gun and kalan_thm_yuzde > 0 else 0.0
        htb_adim_gun = kalan_htb_yuzde / faz_gun if faz_gun and kalan_htb_yuzde > 0 else 0.0

        def _ders_cek(kuyruk, adet):
            secilen = []
            kalan = adet
            while kuyruk and kalan > 0:
                k = kuyruk[0]
                mevcut = k["son"] - k["cur"] + 1
                alinan = min(kalan, mevcut)
                bas_d = k["cur"]
                bit_d = k["cur"] + alinan - 1
                etiket = f"Ders {bas_d}" if bas_d == bit_d else f"Ders {bas_d}–{bit_d}"
                secilen.append({"id": k["id"], "ad": k["ad"], "aralik": etiket, "bas": bas_d, "bit": bit_d})
                k["cur"] += alinan
                kalan -= alinan
                if k["cur"] > k["son"]:
                    kuyruk.pop(0)
            return secilen

        def _dis_cek(kuyruk, miktar):
            if not kuyruk or miktar <= 0:
                return None
            k = kuyruk[0]
            eski = round(k["cur"], 1)
            yeni = min(100.0, round(k["cur"] + miktar, 1))
            k["cur"] = yeni
            if k["cur"] >= 99.9:
                yeni = 100.0
                kuyruk.pop(0)
            sert = f" [{k['sert']}]" if k.get("sert") else ""
            return {"id": k["id"], "ad": f"{k['ad']}{sert}", "eski": eski, "yeni": yeni}

        for g_i in range(faz_gun):
            gun_tarih = cur_date + _dt.timedelta(days=g_i)
            pafta_gun = []
            if ai_kuyruk and klasik_kuyruk:
                ai_adet = max(1, ders_gun // 2)
                kl_adet = max(1, ders_gun - ai_adet)
                pafta_gun.extend(_ders_cek(ai_kuyruk, ai_adet))
                pafta_gun.extend(_ders_cek(klasik_kuyruk, kl_adet))
            elif ai_kuyruk:
                pafta_gun.extend(_ders_cek(ai_kuyruk, ders_gun))
            elif klasik_kuyruk:
                pafta_gun.extend(_ders_cek(klasik_kuyruk, ders_gun))

            thm_gun = _dis_cek(thm_kuyruk, thm_adim_gun) if thm_aktif else None
            htb_gun = _dis_cek(htb_kuyruk, htb_adim_gun) if htb_aktif else None

            gunluk_plan.append({
                "gun_no": len(gunluk_plan) + 1,
                "tarih_iso": gun_tarih.isoformat(),
                "tarih_tr": _tarih_tr(gun_tarih, gun_adi=True),
                "faz_id": a["id"],
                "faz_no": faz_idx + 1,
                "faz_ad": a["ad"],
                "pafta": pafta_gun,
                "thm": thm_gun,
                "htb": htb_gun,
            })

        faz_ozetleri.append({
            "faz_no": faz_idx + 1,
            "id": a["id"],
            "ad": a["ad"],
            "baslangic_tr": a["baslangic_tr"],
            "bitis_tr": a["bitis_tr"],
            "gun_sayisi": faz_gun,
        })
        cur_date = faz_bit + _dt.timedelta(days=1)

    # Haftalık özetleri (7'şer günlük dilimler) oluştur
    haftalik_plan = []
    for i in range(0, len(gunluk_plan), 7):
        dilim = gunluk_plan[i:i + 7]
        bas_g = _dt.date.fromisoformat(dilim[0]["tarih_iso"])
        bit_g = _dt.date.fromisoformat(dilim[-1]["tarih_iso"])
        pafta_map = {}
        pafta_sira = []
        for g in dilim:
            for p in g["pafta"]:
                if p["id"] not in pafta_map:
                    pafta_map[p["id"]] = {"id": p["id"], "ad": p["ad"], "bas": p["bas"], "bit": p["bit"]}
                    pafta_sira.append(p["id"])
                else:
                    pafta_map[p["id"]]["bit"] = max(pafta_map[p["id"]]["bit"], p["bit"])
        pafta_hafta = [
            {"id": pid, "ad": pafta_map[pid]["ad"],
             "aralik": f"Ders {pafta_map[pid]['bas']}" if pafta_map[pid]["bas"] == pafta_map[pid]["bit"]
             else f"Ders {pafta_map[pid]['bas']}–{pafta_map[pid]['bit']}"}
            for pid in pafta_sira
        ]

        def _dis_hafta_ozet(alan):
            iz = {}
            sira = []
            for g in dilim:
                d = g.get(alan)
                if not d:
                    continue
                if d["id"] not in iz:
                    iz[d["id"]] = {"ad": d["ad"], "eski": d["eski"], "yeni": d["yeni"]}
                    sira.append(d["id"])
                else:
                    iz[d["id"]]["yeni"] = d["yeni"]
            return [f"{iz[k]['ad']} (%{iz[k]['eski']:g} → %{iz[k]['yeni']:g})" for k in sira]

        haftalik_plan.append({
            "hafta_no": len(haftalik_plan) + 1,
            "aralik_tr": f"{_tarih_tr(bas_g)} – {_tarih_tr(bit_g)}",
            "faz_ad": dilim[0]["faz_ad"] if dilim[0]["faz_ad"] == dilim[-1]["faz_ad"]
            else f"{dilim[0]['faz_ad'].split('·')[0].strip()} → {dilim[-1]['faz_ad'].split('·')[0].strip()}",
            "pafta": pafta_hafta,
            "thm": _dis_hafta_ozet("thm"),
            "htb": _dis_hafta_ozet("htb"),
        })

    bitis_date = (cur_date - _dt.timedelta(days=1)) if gunluk_plan else baslangic_date
    return {
        "baslangic_iso": baslangic_date.isoformat(),
        "baslangic_tr": _tarih_tr(baslangic_date),
        "bitis_tr": _tarih_tr(bitis_date),
        "toplam_gun": len(gunluk_plan),
        "toplam_hafta": len(haftalik_plan),
        "toplam_ay": round(len(gunluk_plan) / 30.0, 1),
        "faz_ozetleri": faz_ozetleri,
        "haftalik_plan": haftalik_plan,
        "gunluk_plan": gunluk_plan,
    }


class Rota:
    def __init__(self, path=None):
        self.path = path or os.path.join(data_dir(), "rota.json")
        self._lock = threading.Lock()
        try:
            with open(self.path, encoding="utf-8") as f:
                self.data = json.load(f)
        except (OSError, ValueError):
            self.data = {}
        degisti = False
        for p in PLATFORM:
            hedef_dict = self.data.setdefault(p, {})
            for yid, varsayilan in VARSAYILAN_ILERLEME.get(p, {}).items():
                if yid not in hedef_dict:
                    hedef_dict[yid] = dict(varsayilan, tarih=_dt.date.today().isoformat())
                    degisti = True
        if self.data.get("hedef") not in HEDEFLER:
            self.data["hedef"] = VARSAYILAN_HEDEF
            degisti = True
        if self.data.get("tempo") not in {t["id"] for t in TEMPOLAR}:
            self.data["tempo"] = VARSAYILAN_TEMPO
            degisti = True
        if self.data.get("uyelik") not in {u["id"] for u in UYELIKLER}:
            self.data["uyelik"] = VARSAYILAN_UYELIK
            degisti = True
        if not self.data.get("baslangic"):
            self.data["baslangic"] = _dt.date.today().isoformat()
            degisti = True
        if degisti:
            try:
                os.makedirs(os.path.dirname(self.path), exist_ok=True)
                self._save()
            except OSError:
                pass

    def _save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)

    def hedef_guncelle(self, hedef=None, tempo=None, uyelik=None, baslangic=None, yollar=None):
        with self._lock:
            if hedef is not None:
                if hedef not in HEDEFLER:
                    raise ValueError(f"bilinmeyen hedef: {hedef!r}")
                self.data["hedef"] = hedef
            if tempo is not None:
                if tempo not in {t["id"] for t in TEMPOLAR}:
                    raise ValueError(f"bilinmeyen tempo: {tempo!r}")
                self.data["tempo"] = tempo
            if uyelik is not None:
                if uyelik not in {u["id"] for u in UYELIKLER}:
                    raise ValueError(f"bilinmeyen uyelik: {uyelik!r}")
                self.data["uyelik"] = uyelik
            if baslangic is not None:
                try:
                    _dt.date.fromisoformat(str(baslangic))
                    self.data["baslangic"] = str(baslangic)
                except ValueError as e:
                    raise ValueError("gecersiz baslangic tarihi") from e
            self._save()
        return self.gorunum(yollar or [])

    def guncelle(self, platform, yid, yuzde=None, sertifika=None):
        if platform not in PLATFORM:
            raise ValueError(f"bilinmeyen platform: {platform!r}")
        if yid not in GECERLI_DIS[platform]:
            raise ValueError(f"bilinmeyen yol: {yid!r}")
        with self._lock:
            k = self.data[platform].setdefault(yid, {"yuzde": 0, "sertifika": False})
            if yuzde is not None:
                k["yuzde"] = max(0.0, min(100.0, round(float(yuzde), 1)))
            if sertifika is not None:
                k["sertifika"] = bool(sertifika)
            k["tarih"] = _dt.date.today().isoformat()
            self._save()
            return dict(k)

    def gorunum(self, yollar):
        """`yollar`: App.state()['tracks'] listesi; Pafta yüzdeleri ve tarih tarih takvim buradan hesaplanır."""
        pafta = {t["id"]: t for t in yollar if t.get("status") == "active"}
        aktif_hedef_id = self.data.get("hedef", VARSAYILAN_HEDEF)
        if aktif_hedef_id not in HEDEFLER:
            aktif_hedef_id = VARSAYILAN_HEDEF
        aktif_tempo_id = self.data.get("tempo", VARSAYILAN_TEMPO)
        if aktif_tempo_id not in {t["id"] for t in TEMPOLAR}:
            aktif_tempo_id = VARSAYILAN_TEMPO
        aktif_uyelik_id = self.data.get("uyelik", VARSAYILAN_UYELIK)
        if aktif_uyelik_id not in {u["id"] for u in UYELIKLER}:
            aktif_uyelik_id = VARSAYILAN_UYELIK

        try:
            baslangic_date = _dt.date.fromisoformat(self.data.get("baslangic") or _dt.date.today().isoformat())
        except ValueError:
            baslangic_date = _dt.date.today()

        profil = HEDEFLER[aktif_hedef_id]
        tempo_bilgi = next(t for t in TEMPOLAR if t["id"] == aktif_tempo_id)
        uyelik_bilgi = next(u for u in UYELIKLER if u["id"] == aktif_uyelik_id)

        def dis(platform, liste):
            return [{"id": i, "ad": ad, "sertifika_adi": s,
                     **{"yuzde": 0, "sertifika": False, "tarih": None}, **self.data[platform].get(i, {})}
                    for i, ad, s in liste]

        def asama(a):
            p = [{"id": tid, "ad": pafta[tid]["name"], "bitti": pafta[tid].get("steps_done", 0),
                  "toplam": pafta[tid].get("steps_total", 0),
                  "ders_sayisi": pafta[tid].get("lessons_total", 0)} for tid in a["pafta"] if tid in pafta]
            return {"id": a["id"], "ad": a["ad"], "not": a["not"], "pafta": p,
                    "thm": dis("thm", a["thm"]), "htb": dis("htb", a["htb"])}

        asamalar_out = [asama(a) for a in profil["asamalar"]]
        yan_out = asama(profil["yan"])

        ana_asamalar = [a for a in asamalar_out if a["id"] != "secmeli"]
        toplam_adim = sum(t["toplam"] for a in ana_asamalar for t in a["pafta"])
        biten_adim = sum(t["bitti"] for a in ana_asamalar for t in a["pafta"])
        kalan_adim = max(0, toplam_adim - biten_adim)

        tarih_plan = _tarih_takvimi_uret(asamalar_out, tempo_bilgi, uyelik_bilgi, baslangic_date)

        return {
            "hedef": aktif_hedef_id,
            "tempo": aktif_tempo_id,
            "uyelik": aktif_uyelik_id,
            "uyelik_aktif": {"thm": uyelik_bilgi["thm"], "htb": uyelik_bilgi["htb"]},
            "baslangic": baslangic_date.isoformat(),
            "hedefler": [{"id": k, "ad": v["ad"], "etiket": v["etiket"], "ozet": v["ozet"]} for k, v in HEDEFLER.items()],
            "tempolar": TEMPOLAR,
            "uyelikler": UYELIKLER,
            "takvim": {
                "toplam_adim": toplam_adim,
                "biten_adim": biten_adim,
                "kalan_adim": kalan_adim,
                "tahmini_gun": tarih_plan["toplam_gun"],
                "tahmini_hafta": tarih_plan["toplam_hafta"],
                "tahmini_ay": tarih_plan["toplam_ay"],
                "baslangic_tr": tarih_plan["baslangic_tr"],
                "bitis_tr": tarih_plan["bitis_tr"],
                "dagilim": tempo_bilgi["dagilim"],
                "etiket": profil["etiket"],
                "ozet": profil["ozet"],
                "faz_ozetleri": tarih_plan["faz_ozetleri"],
                "haftalik_plan": tarih_plan["haftalik_plan"],
                "gunluk_plan": tarih_plan["gunluk_plan"],
            },
            "asamalar": asamalar_out,
            "yan": yan_out,
        }

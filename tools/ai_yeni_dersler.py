"""Yeni ders planından görünür başlangıç verisiyle canlı HTML üretir; sahiplik/puan yazmaz."""
from pathlib import Path
import re,json
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/"docs/ai-gercek"
def plan_oku(text):
    out=[]
    for m in re.finditer(r"^### (ai-(saldiri|savunma)-(\d+))-(.+?) → \*\*(.+?)\*\*\s*\n(.*?)(?=^### |^## |\Z)",text,re.M|re.S):
        body=m[6].strip();parts=body.split("Yığın:",1)
        out.append({"id":m[1],"yol":m[2],"no":m[3],"slug":m[4],"sorumlu":m[5],"aciklama":parts[0].strip(),"yigin":parts[1].split("\n\n")[0].strip() if len(parts)>1 else "", "onay_gerekli": "onay" in body.casefold()})
    return out
def genis_plan_oku(text,aktif):
    """Genel yol haritasını başlık türlerini koruyarak oku; ders numarası uydurma."""
    out=[]
    groups=[("A2", "saldiri", "AI saldırı", "ders"),("A3","savunma","AI savunma","ders"),("B2","purple","Purple","modül"),("C)","klasik","Klasik","konu")]
    for marker,group,label,kind in groups:
        pattern=r"^##? "+re.escape(marker)+r"[^\n]*\n(.*?)(?=^##? |\Z)"
        m=re.search(pattern,text,re.M|re.S)
        if not m:raise ValueError("Plan bölümü yok: "+marker)
        rows=[]
        for line in m[1].splitlines():
            if not line.startswith("|"):continue
            cells=[x.strip() for x in line.strip().strip("|").split("|")]
            if not cells or cells[0] in ("#","Modül","Konu") or all(set(x)<=set("-: ") for x in cells):continue
            rows.append(cells)
        for i,c in enumerate(rows):
            if group in ("saldiri","savunma"):
                if len(c)!=4:raise ValueError("AI plan satırı")
                if i < (6 if group=="saldiri" else 5):
                    number=47+i if group=="saldiri" else 32+i
                    old=next((x for x in aktif if x["id"]==f"ai-{group}-{number}"),None)
                    if old:
                        out.append(dict(old,oncelik=c[3],tur=kind,asama="Dalga 1",kaynak_bolum=marker));continue
                title,stack,priority=c[1:]
                out.append({"id":f"plan-{group}-{i+1}","yol":group,"no":"—","slug":title,"baslik":title,"sorumlu":"","aciklama":"Genel ekleme planındaki AI ders başlığı. Ders numarası henüz belirlenmedi; yazar ortak atama kaydında.","yigin":stack,"onay_gerekli":False,"oncelik":priority,"tur":kind,"asama":"Sonra" if priority=="Sonra" else "Plan","kaynak_bolum":marker})
            elif group=="purple":
                out.append({"id":f"plan-purple-{i+1}","yol":group,"no":f"M{i+1}","slug":c[0],"baslik":c[0],"sorumlu":"","aciklama":"Eklenecek kırmızı yarı: "+c[2]+"\nMevcut mavi taraf: "+c[1],"yigin":"Araç ve görev dağılımı bu modül yazılırken kesinleştirilecek.","onay_gerekli":False,"oncelik":"Plan","tur":kind,"asama":"Modül planı","kaynak_bolum":marker})
            else:
                out.append({"id":f"plan-klasik-{i+1}","yol":group,"no":"—","slug":c[0],"baslik":c[0],"sorumlu":"","aciklama":"Yerleşim: "+c[1]+". Bu bir konu başlığıdır; kaç ders olacağı henüz belirlenmedi. Purple modülleriyle örtüşebilir; ayrı ders adedi olarak sayılmaz.","yigin":"Araç ve lab listesi genel planda; kurulum onayı ayrıca izlenir.","onay_gerekli":False,"oncelik":c[2],"tur":kind,"asama":"Sonra" if c[2]=="Sonra" else "Konu planı","kaynak_bolum":marker})
    m=re.search(r"^## A4[^\n]*\n(.*?)(?=^---|^##? |\Z)",text,re.M|re.S)
    if m:out.append({"id":"plan-ai-purple-kopru","yol":"kopru","no":"↔","slug":"AI–Purple köprüsü","baslik":"SOC LLM asistanında saldırı ve savunma","sorumlu":"","aciklama":m[1].strip(),"yigin":"Yerel SOC/LLM akışı; ayrıntılı görev planı henüz yok.","onay_gerekli":False,"oncelik":"Plan","tur":"köprü","asama":"Köprü planı","kaynak_bolum":"A4"})
    return out

def atamalari_koru(rows, onceki, kalici):
    """Üretilen HTML/JSON sahiplik kaynağı değildir; açık devir dosyası önceliklidir."""
    eski = {x['id']: x for x in onceki}
    result = []
    for row in rows:
        item = dict(row)
        if row['id'] in kalici:
            k = kalici[row['id']]
            item['sorumlu'] = k.get('sorumlu', item.get('sorumlu', ''))
            if k.get('asama'): item['asama'] = k['asama']
            if k.get('oncelik'): item['oncelik'] = k['oncelik']
            if k.get('ders_id'): item['ders_id'] = k['ders_id']
        else:
            item['sorumlu'] = eski.get(row['id'], {}).get('sorumlu') or row.get('sorumlu', '')
        result.append(item)
    return result

def main():
    rows=plan_oku((D/"GOREV-YENI-AI-DERSLERI.md").read_text(encoding="utf-8"))
    if not rows:raise SystemExit("Plan boş; mevcut tablo korunuyor")
    kaynak=ROOT.parent/"claude-devir"/"PAFTA-EKLEME-PLANI.md"
    genel=kaynak.read_text(encoding="utf-8")
    rows=genis_plan_oku(genel,rows)
    onceki_yol=D/'yeni-dersler-kapsam.json'
    onceki=json.loads(onceki_yol.read_text(encoding='utf-8')) if onceki_yol.exists() else []
    atama_yol=D/'yeni-dersler-atamalar.json'
    kalici=json.loads(atama_yol.read_text(encoding='utf-8'))['atamalar'] if atama_yol.exists() else {}
    rows=atamalari_koru(rows,onceki,kalici)
    (D/"EKLEME-PLANI-KAYNAK.md").write_text(genel,encoding="utf-8")
    (D/"yeni-dersler-kapsam.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8")
    data={"plan":rows,"takip":json.loads((D/"takip.json").read_text(encoding="utf-8")),"kuyruk":json.loads((D/"iyilestirme.json").read_text(encoding="utf-8"))}
    template=(D/"yeni-dersler-template.html").read_text(encoding="utf-8")
    (D/"YENI-DERSLER.html").write_text(template.replace("__INITIAL_DATA__",json.dumps(data,ensure_ascii=False).replace("<","\\u003c")),encoding="utf-8")
    print(f"{len(rows)} plan başlığı → YENI-DERSLER.html")
if __name__=="__main__":main()

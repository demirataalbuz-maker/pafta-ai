"""Yerel garak Python API taraması; yalnız .ai-araclar yorumlayıcısıyla çalışır."""
import json,sys
from pathlib import Path
import garak
from garak import _config
from garak.generators.ollama import OllamaGeneratorChat
from garak.probes.base import Probe
from garak.detectors.base import StringDetector


def main():
    cfg=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    _config.load_config()
    _config.run.generations=1
    _config.run.seed=5
    _config.system.parallel_attempts=False
    _config.system.parallel_requests=False
    _config.plugins.generators={"ollama":{"OllamaGeneratorChat":{"host":cfg["host"],"timeout":90,"max_tokens":120,"temperature":0.0}}}
    generator=OllamaGeneratorChat(cfg["model"])
    detector=StringDetector([cfg["canary"]])
    # Kurulu garak StringDetector davranışını pozitif/negatif sentetik çıktıda ayrıca sına.
    from garak.attempt import Attempt,Message,Conversation,Turn
    sanity=Attempt(prompt=Conversation(turns=[Turn("user",Message("synthetic detector sanity"))]));sanity.outputs=[Message(cfg["canary"]),Message("ordinary clean response")]
    detector_sanity=list(detector.detect(sanity))
    if detector_sanity != [1.0,0.0]:
        raise RuntimeError("garak detector kontrolü başarısız")
    rows=[]
    report=Path(sys.argv[2]).with_suffix(".report.jsonl")
    with report.open("w",encoding="utf-8") as stream:
        _config.transient.reportfile=stream
        for bid,pname,dname,prompts in cfg["probes"]:
            # Yeni üretim saldırısı yok: eski dersin beş istemi aynı sırada kullanılır.
            probe=Probe()
            probe.probename=pname
            probe.prompts=["Belgeyi özetle.\n---\n"+p+"\n---" for p in prompts]
            probe.system_prompt=cfg["system"]
            probe.generations=1
            for attempt in probe.probe(generator):
                scores=list(detector.detect(attempt))
                if len(attempt.outputs)!=1 or len(scores)!=1 or scores[0] not in (0.0,1.0) or not attempt.outputs[0] or not attempt.outputs[0].text:
                    raise RuntimeError("eksik model çıktısı veya detector sonucu")
                attempt.detector_results["base.StringDetector"]=scores
                raw=attempt.as_dict();stream.write(json.dumps(raw,ensure_ascii=False)+"\n")
                rows.append({"id":bid,"probe":pname,"detector":dname,"raw":raw,"ham_yanit":attempt.outputs[0].text,"skor":scores[0],"hata":None})
    Path(sys.argv[2]).write_text(json.dumps({"arac":{"ad":"garak","surum":garak.__version__,"api":["garak.probes.base.Probe.probe","garak.generators.ollama.OllamaGeneratorChat","garak.detectors.base.StringDetector.detect"],"detector_sanity":detector_sanity},"satirlar":rows,"garak_report_jsonl":report.read_text(encoding="utf-8")},ensure_ascii=False),encoding="utf-8")

if __name__=="__main__":
    main()


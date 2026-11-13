"""AgentDojo koşucusu: .deps/agentdojo-venv yorumlayıcısıyla çalışır; girdi stdin'den JSON, çıktı stdout'a JSON.

Yalnız yerel Ollama'nın OpenAI uyumlu ucunu kullanır; bulut API anahtarı yoktur."""
import json,sys,time,warnings
warnings.filterwarnings("ignore")
import openai
import agentdojo
from importlib.metadata import version
from agentdojo.agent_pipeline import AgentPipeline,PipelineConfig
from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM
from agentdojo.attacks import load_attack
from agentdojo.task_suite.load_suites import get_suite

a=json.load(sys.stdin)
client=openai.OpenAI(base_url=a["adres"].rstrip("/")+"/v1",api_key="yerel-ollama",timeout=a.get("zaman_asimi",120))
# OpenAILLM, temperature=0.0'ı "verilmedi" sayıyor (0.0 or NOT_GIVEN); bu yüzden çok küçük pozitif bir değer verilir.
llm=OpenAILLM(client,a["model"],temperature=a.get("sicaklik",1e-6))
suite=get_suite(a["surum"],a["paket"])
kayit=[]
for savunma in a["savunmalar"]:
    pipe=AgentPipeline.from_config(PipelineConfig(llm=llm,model_id=None,defense=savunma,system_message_name=None,system_message=None))
    # important_instructions saldırısı model adını boru hattı adından okur; AgentDojo yerel modeli "local" adıyla tanır.
    pipe.name="local-"+(savunma or "savunmasiz")
    saldiri=load_attack(a["saldiri"],suite,pipe)
    for ut in a["kullanici_gorevleri"]:
        u=suite.get_user_task_by_id(ut)
        bas=time.time();fayda,_=suite.run_task_with_pipeline(pipe,u,None,{})
        kayit.append({"savunma":savunma or "yok","kullanici_gorevi":ut,"enjeksiyon_gorevi":None,"fayda":bool(fayda),"saldiri_basarili":None,"sure_sn":round(time.time()-bas,1)})
        for it in a["enjeksiyon_gorevleri"]:
            i=suite.get_injection_task_by_id(it);enj=saldiri.attack(u,i)
            bas=time.time();fayda,guvenlik=suite.run_task_with_pipeline(pipe,u,i,enj)
            # AgentDojo'da security=True, enjeksiyon görevinin BAŞARILDIĞI (saldırının tuttuğu) anlamına gelir.
            kayit.append({"savunma":savunma or "yok","kullanici_gorevi":ut,"enjeksiyon_gorevi":it,"fayda":bool(fayda),"saldiri_basarili":bool(guvenlik),"sure_sn":round(time.time()-bas,1),
                          "enjeksiyon_yerleri":sorted(enj)})
gorev={ut:suite.get_user_task_by_id(ut).PROMPT for ut in a["kullanici_gorevleri"]}
hedef={it:suite.get_injection_task_by_id(it).GOAL for it in a["enjeksiyon_gorevleri"]}
print(json.dumps({"agentdojo_surumu":version("agentdojo"),"openai_surumu":version("openai"),"kayitlar":kayit,"gorevler":gorev,"enjeksiyon_hedefleri":hedef}))

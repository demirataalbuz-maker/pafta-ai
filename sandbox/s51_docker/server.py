"""Only synthetic files in an ephemeral container-owned tree."""
import os,sys
from pathlib import Path
root=Path('/tmp/pafta')
(root/'artifacts/normal').mkdir(parents=True,exist_ok=True)
(root/'private').mkdir(exist_ok=True)
(root/'private/canary.txt').write_text(os.environ['PAFTA_CANARY'],encoding='utf-8')
(root/'artifacts/normal/ok.txt').write_text(os.environ['PAFTA_NORMAL'],encoding='utf-8')
os.chdir(root)
os.execvp('mlflow',['mlflow','server','--host','127.0.0.1','--port','5000','--workers','1','--backend-store-uri','sqlite:////tmp/pafta/store.db','--serve-artifacts','--artifacts-destination','/tmp/pafta/artifacts','--default-artifact-root','mlflow-artifacts:/'])

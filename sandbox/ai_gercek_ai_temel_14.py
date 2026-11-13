"""Lesson 14: real JSON-schema decoding on a local Ollama server.

GPU kipinde (varsayılan) kullanıcının sunucusu ai_gercek_lab GPU kilidi altında kullanılır ve yalnız deneyin
yüklediği model boşaltılır; PAFTA_OLLAMA_CIHAZ=cpu ile deneye ait ayrı bir CPU sunucusu açılır (num_gpu=0).

Never unloads models from the user's or another agent's server. No downloads.
Official protocol: https://docs.ollama.com/capabilities/structured-outputs
"""
import copy
import json
import secrets
import time
import urllib.error
from sandbox import ai_gercek_lab as lab

SCHEMA = {
    'type': 'object',
    'properties': {
        'islem': {'type': 'string', 'enum': ['not_ekle', 'raporla']},
        'deger': {'type': 'string', 'minLength': 1, 'maxLength': 80},
        'onay': {'type': 'boolean'},
    },
    'required': ['islem', 'deger', 'onay'],
    'additionalProperties': False,
}


class OzelCpuOturumu(lab.SohbetOturumu):
    def __init__(self):
        super().__init__()
        if lab.cihaz_kipi() == 'cpu':
            # Force the base context manager down its owned-server branch.
            # It chooses its own free loopback port before launching ollama serve.
            self.adres = f'http://127.0.0.1:{lab._bos_port()}'

    def semali_cagir(self, prompt, seed):
        if lab.cihaz_kipi() == 'cpu' and (self.surec is None or self.surec.poll() is not None):
            raise lab.GercekLabYok('Deneye ait canlı Ollama süreci yok; başka sunucu kullanılmaz.')
        request = {'model': self.model, 'messages': [
            {'role': 'system', 'content': 'Return only the requested JSON object. No markdown or commentary.'},
            {'role': 'user', 'content': prompt + '\nJSON schema: ' + json.dumps(SCHEMA)}],
            'stream': False, 'format': copy.deepcopy(SCHEMA),
            'options': lab.ollama_secenekleri(temperature=0, seed=seed, num_predict=96, num_ctx=1024),
            'keep_alive': '2m'}
        if self.dusunme:
            request['think'] = False
        start = time.perf_counter()
        errors = []
        for attempt in range(2):
            try:
                # 2 calls x 2 attempts x 55s + owned-server setup/cleanup fits 300s.
                response = lab._istek(self.adres, '/api/chat', request, sure=55)
                break
            except urllib.error.HTTPError as exc:
                body = exc.read(4096).decode('utf-8', 'replace')
                failure = {'deneme': attempt+1, 'http_durum': exc.code, 'govde': body}
                errors.append(failure)
                self.kayit.setdefault('schema_http_hatalari', []).append(failure)
                if not 500 <= exc.code < 600 or attempt == 1:
                    raise lab.GercekLabYok(f'Gerçek JSON Schema HTTP {exc.code}; '
                                          f'deneme {attempt+1}/2; gövde: {body[:2000]}') from exc
                time.sleep(2)
        if response.get('done') is not True or response.get('done_reason') == 'length':
            raise lab.GercekLabYok('JSON Schema gerçek üretimi tamamlanmadı veya token sınırında kesildi.')
        return {'istek': request, 'ham_yanit': response, 'yeniden_denemeler': errors,
                'icerik': (response.get('message') or {}).get('content', ''),
                'sure_ms': round((time.perf_counter()-start)*1000)}

    def __exit__(self, *exc):
        if lab.cihaz_kipi() == 'cpu' and self.surec is None:
            self.kayit['temizlik'] = {'not': 'Sahipli süreç yok; hiçbir model boşaltılmadı.'}
            lab.gpu_kilidi_birak()
            return False
        return super().__exit__(*exc)


def gercek_ciktilar():
    records = []
    initial_user_server = lab._canli(lab._adres())
    with OzelCpuOturumu() as session:
        for i, operation in enumerate(['raporla', 'not_ekle']):
            marker = 'PAFTA-' + secrets.token_hex(4).upper()
            prompt = f'A synthetic note: islem={operation}, deger={marker}, onay=false. Copy these values into the object.'
            result = session.semali_cagir(prompt, secrets.randbelow(10**6))
            records.append(dict(result, beklenen={'islem': operation, 'deger': marker, 'onay': False}))
        environment = copy.deepcopy(session.kayit)
        environment['bellek'] = session.bellek()
    environment['temizlik'] = session.kayit.get('temizlik')
    environment['kullanici_sunucu_once'] = initial_user_server
    environment['kullanici_sunucu_sonra'] = lab._canli(lab._adres())
    return records, environment


import json

def kati_json_ref(metin):
    if not isinstance(metin,str) or len(metin)>4096:
        raise ValueError("metin geçersiz")
    def nesne(ciftler):
        out={}
        for k,v in ciftler:
            if k in out:
                raise ValueError("yinelenen anahtar")
            out[k]=v
        return out
    def sabit(_):
        raise ValueError("standart dışı JSON sayısı")
    x=json.loads(metin,object_pairs_hook=nesne,parse_constant=sabit)
    if type(x) is not dict or set(x)!={"islem","deger","onay"}:
        raise ValueError("şema geçersiz")
    if not isinstance(x["islem"],str) or x["islem"] not in ("not_ekle","raporla"):
        raise ValueError("işlem geçersiz")
    if not isinstance(x["deger"],str) or not 1<=len(x["deger"])<=80 or not x["deger"].strip():
        raise ValueError("değer geçersiz")
    if type(x["onay"]) is not bool:
        raise ValueError("onay bool olmalı")
    return dict(x)


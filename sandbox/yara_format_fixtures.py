"""Load compiler-produced, never-executed YARA training inputs."""
import base64
import hashlib
import json
from pathlib import Path


def format_fixture(name):
    path = Path(__file__).resolve().parent.parent / 'tracks/yara/fixtures/formats.json'
    record = json.loads(path.read_text(encoding='utf-8'))[name]
    data = base64.b64decode(record['base64'], validate=True)
    if hashlib.sha256(data).hexdigest() != record['sha256']:
        raise ValueError('YARA format fixture checksum mismatch: ' + name)
    return data

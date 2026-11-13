"""HT17 native Burp XML fixtures; copies files without network or app launch."""
from pathlib import Path
import shutil

FIXTURES = Path(__file__).resolve().parents[1] / 'tracks/http/fixtures/ht17_burp'


def hazirla():
    target = Path.cwd() / 'burp'
    target.mkdir(exist_ok=True)
    for name in ('history.xml', 'repeater.xml'):
        shutil.copyfile(FIXTURES / name, target / name)
    return target

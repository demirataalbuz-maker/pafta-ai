"""Generate only an ephemeral localhost-lab certificate; no trust-store edits."""
import datetime,json,sys
from pathlib import Path
import cryptography
from cryptography import x509
from cryptography.x509.oid import NameOID,ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
key=rsa.generate_private_key(public_exponent=65537,key_size=2048);now=datetime.datetime.now(datetime.timezone.utc)
name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'PAFTA ephemeral local lab')])
cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-datetime.timedelta(minutes=1)).not_valid_after(now+datetime.timedelta(days=1)).add_extension(x509.BasicConstraints(ca=True,path_length=0),critical=True).add_extension(x509.SubjectAlternativeName([x509.DNSName('public.test'),x509.DNSName('internal.test')]),critical=False).add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),critical=False).sign(key,hashes.SHA256()))
with (out/'lab-cert.pem').open('xb') as f:f.write(cert.public_bytes(serialization.Encoding.PEM))
with (out/'lab-key.pem').open('xb') as f:f.write(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
print(json.dumps(dict(cryptography=cryptography.__version__,cert_sha256=cert.fingerprint(hashes.SHA256()).hex(),valid_for='public.test/internal.test, one day, local only')))

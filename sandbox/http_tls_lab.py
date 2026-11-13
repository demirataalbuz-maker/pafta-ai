"""Ephemeral private test CA and real TLS/curl. Never modifies OS trust stores."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil
import ssl
import subprocess
import tempfile
from http_lab import Lab


class TLSLab(Lab):
    def __init__(self, port=0):
        try:
            from cryptography import x509
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
        except ImportError as exc:
            raise RuntimeError('TLS lab requires cryptography; no automatic installation. See docs/http-lab.md.') from exc
        self.temp = tempfile.TemporaryDirectory(prefix='pafta_tls_')
        folder = Path(self.temp.name)
        now = datetime.now(timezone.utc)
        ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Pafta temporary lab CA')])
        ca = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(ca_key.public_key())
              .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=5))
              .not_valid_after(now+timedelta(days=2)).add_extension(x509.BasicConstraints(ca=True, path_length=0), True)
              .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), True)
              .sign(ca_key, hashes.SHA256()))
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        leafname = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'app.pafta.test')])
        cert = (x509.CertificateBuilder().subject_name(leafname).issuer_name(name).public_key(key.public_key())
                .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=5))
                .not_valid_after(now+timedelta(days=1)).add_extension(x509.BasicConstraints(ca=False, path_length=None), True)
                .add_extension(x509.SubjectAlternativeName([x509.DNSName('app.pafta.test')]), False)
                .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), False)
                .sign(ca_key, hashes.SHA256()))
        self.ca = str(folder/'ca.pem')
        self.cert = str(folder/'server.pem')
        self.key = str(folder/'server.key')
        Path(self.ca).write_bytes(ca.public_bytes(serialization.Encoding.PEM))
        Path(self.cert).write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        Path(self.key).write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        self.spki = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(self.cert, self.key)
        super().__init__(port, ssl_context=ctx)

    def close(self):
        super().close()
        self.temp.cleanup()

    def curl(self, hostname='app.pafta.test', trust=True, path='/', fail_http=False):
        exe = shutil.which('curl.exe') or shutil.which('curl')
        if not exe:
            raise RuntimeError('curl executable required; no automatic installation')
        port = self.server.server_port
        args = [exe, '--disable', '--silent', '--show-error', '--noproxy', '*', '--max-time', '4',
                '--resolve', f'{hostname}:{port}:127.0.0.1', '--write-out', '\n%{http_code}']
        # Schannel cannot check CRLs for this ephemeral private CA. This scoped
        # switch leaves CA signature and hostname verification enabled.
        if 'Schannel' in subprocess.run([exe, '--version'], capture_output=True, text=True, timeout=4).stdout:
            args.append('--ssl-no-revoke')
        if trust:
            args += ['--cacert', self.ca]
        if fail_http:
            args.append('--fail-with-body')
        args.append(f'https://{hostname}:{port}{path}')
        p = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=8)
        body, _, status = p.stdout.rpartition('\n')
        return {'exit': p.returncode, 'http': int(status) if status.isdecimal() else 0,
                'body': body, 'stderr': p.stderr}

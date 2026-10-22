"""Local TLS frontend/API proxy fixture. This models the topology, not Vercel's CDN."""
import datetime
import ipaddress
import json
import mimetypes
import ssl
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def start_proxy(root, temporary, backend):
    # Use the shipped static security headers instead of a different test policy.
    import os
    env = {**os.environ, 'BACKEND_ORIGIN': 'https://api.example'}
    config = json.loads(subprocess.check_output(['node', '--input-type=module', '-e',
        "import {config} from './frontend/vercel.ts'; console.log(JSON.stringify(config))"], cwd=root, env=env, text=True))
    static_headers = {h['key']: h['value'] for h in config['headers'][0]['headers']}
    assets = (root / 'frontend' / 'dist').resolve()
    excluded = {'connection', 'transfer-encoding', 'keep-alive', 'content-length', 'server', 'date'}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_): pass

        def dispatch(self):
            if urlsplit(self.path).path.startswith('/api/'):
                body = self.rfile.read(int(self.headers.get('content-length', '0')))
                headers = {k: v for k, v in self.headers.items() if k.lower() not in {'host', 'connection', 'accept-encoding'}}
                headers['accept-encoding'] = 'identity'
                try:
                    response = httpx.request(self.command, backend + self.path, headers=headers, content=body, timeout=60, trust_env=False)
                except httpx.HTTPError:
                    self.send_error(502)
                    return
                self.send_response(response.status_code)
                for key, value in response.headers.multi_items():
                    if key.lower() not in excluded: self.send_header(key, value)
                content = response.content
            else:
                candidate = (assets / unquote(urlsplit(self.path).path).lstrip('/')).resolve()
                if not candidate.is_relative_to(assets):
                    self.send_error(403)
                    return
                if not candidate.is_file(): candidate = assets / 'index.html'
                content = candidate.read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', mimetypes.guess_type(candidate)[0] or 'application/octet-stream')
                for key, value in static_headers.items(): self.send_header(key, value)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            if self.command != 'HEAD':
                try: self.wfile.write(content)
                except ConnectionError: pass  # Navigation can cancel an in-flight response.

        do_GET = do_HEAD = do_POST = do_PUT = do_DELETE = do_PATCH = dispatch

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'localhost')])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - datetime.timedelta(minutes=1))
            .not_valid_after(now + datetime.timedelta(days=1))
            .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]), critical=False)
            .sign(key, hashes.SHA256()))
    key_path, cert_path = Path(temporary) / 'key.pem', Path(temporary) / 'cert.pem'
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.load_cert_chain(cert_path, key_path)
    server = ThreadingHTTPServer(('127.0.0.1', 8012), Handler)
    server.daemon_threads = True
    server.socket = tls.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread

#!/usr/bin/env python3
import argparse
import http.server
import socketserver
import ssl
import threading
import time

BIND_IP = "198.82.0.1"
PORT_HTTP = 80
PORT_HTTPS = 443
# A deliberately small worker pool, and a /slow request that occupies a worker for a long
# time: together they let the overload fault saturate the server with a handful of
# connections, which is what makes every other client see 503. Both values are load-bearing
# for that experiment and must stay in step with CONCURRENCY in kp_web_client.py and
# WEBSERVER_MAX_WORKERS in experiments/kp_why_fix.py — raising the pool above the client's
# concurrency silently turns the fault into a no-op, and the server just answers 200.
MAX_WORKERS = 3
SLOW_HOLD_SECONDS = 90

# The TLS material is generated per run (agentic_networks/testbed_certs.py) and passed in,
# rather than read from a fixed path here: a CA checked into the repository would have a
# published private key, and this CA is installed into the container's trust store.
_args = argparse.ArgumentParser(description="Emulated ACM web server for the knowledge-plane testbed")
_args.add_argument("--cert", required=True, metavar="FILE", help="Server certificate (PEM)")
_args.add_argument("--key", required=True, metavar="FILE", help="Server private key (PEM)")
_opts = _args.parse_args()

CERT_FILE = _opts.cert
KEY_FILE = _opts.key

_sem = threading.Semaphore(MAX_WORKERS)

_OK_BODY = b"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ACM Digital Library</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; background: #f5f5f5; color: #333; }
    header { background: #0065a4; color: white; padding: 12px 24px; }
    header h1 { margin: 0; font-size: 1.4em; }
    nav { background: #004f82; padding: 6px 24px; }
    nav a { color: #cce4f7; text-decoration: none; margin-right: 18px; font-size: 0.9em; }
    main { max-width: 960px; margin: 32px auto; padding: 0 24px; }
    h2 { color: #0065a4; }
    .cards { display: flex; gap: 20px; flex-wrap: wrap; margin-top: 16px; }
    .card { background: white; border: 1px solid #ddd; border-radius: 4px; padding: 16px; flex: 1; min-width: 200px; }
    footer { background: #222; color: #aaa; text-align: center; padding: 16px; font-size: 0.8em; margin-top: 48px; }
  </style>
</head>
<body>
  <header><h1>ACM Digital Library</h1></header>
  <nav>
    <a href="/dl">Publications</a>
    <a href="/dl/conferences">Conferences</a>
    <a href="/dl/journals">Journals</a>
    <a href="/dl/magazines">Magazines</a>
    <a href="/about">About</a>
  </nav>
  <main>
    <h2>Welcome to the ACM Digital Library</h2>
    <p>The ACM Digital Library is a research, discovery, and networking platform containing the
    full-text collection of all ACM publications, including journals, conference proceedings,
    technical magazines, newsletters, and books.</p>
    <div class="cards">
      <div class="card">
        <h3>Browse Publications</h3>
        <p>Access over 600,000 articles from leading computing researchers worldwide.</p>
      </div>
      <div class="card">
        <h3>Conferences</h3>
        <p>Proceedings from more than 4,000 ACM-sponsored events and conferences.</p>
      </div>
      <div class="card">
        <h3>ACM Guide</h3>
        <p>The ACM Guide to Computing Literature: a curated bibliographic database.</p>
      </div>
    </div>
  </main>
  <footer>&copy; 2026 Association for Computing Machinery, Inc. All rights reserved.</footer>
</body>
</html>
"""

_OVERLOADED_BODY = b"503 Service Unavailable\n"


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def version_string(self):
        return "nginx/1.18.0"

    def do_GET(self):
        self.close_connection = True
        if self.path.startswith("/slow"):
            _sem.acquire()
            try:
                time.sleep(SLOW_HOLD_SECONDS)
                self._ok()
            finally:
                _sem.release()
        else:
            if not _sem.acquire(blocking=False):
                self.send_response(503)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Length", str(len(_OVERLOADED_BODY)))
                self.end_headers()
                self.wfile.write(_OVERLOADED_BODY)
                return
            try:
                self._ok()
            finally:
                _sem.release()

    def _ok(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(_OK_BODY)))
        self.end_headers()
        self.wfile.write(_OK_BODY)

    def log_message(self, *_):
        pass


socketserver.ThreadingTCPServer.allow_reuse_address = True

_ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
_ssl_ctx.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)

_http  = socketserver.ThreadingTCPServer((BIND_IP, PORT_HTTP),  Handler)
_https = socketserver.ThreadingTCPServer((BIND_IP, PORT_HTTPS), Handler)
_https.socket = _ssl_ctx.wrap_socket(_https.socket, server_side=True, do_handshake_on_connect=False)

threading.Thread(target=_http.serve_forever, daemon=True).start()
_https.serve_forever()

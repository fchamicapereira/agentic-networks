#!/usr/bin/env python3
"""ACM Digital Library front end: serves the portal over HTTP and HTTPS."""

import argparse
import http.server
import socketserver
import ssl
import threading
import time

BIND_IP = "198.82.0.1"
PORT_HTTP = 80
PORT_HTTPS = 443
# Requests served at once. Each request holds a worker until it completes; when all workers
# are busy, new requests get 503.
MAX_WORKERS = 3
# Bulk citation exports are generated synchronously and take this long to build.
EXPORT_SECONDS = 90

_args = argparse.ArgumentParser(description=__doc__)
_args.add_argument("--cert", required=True, metavar="FILE", help="Server certificate (PEM)")
_args.add_argument("--key", required=True, metavar="FILE", help="Server private key (PEM)")
_opts = _args.parse_args()

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

_EXPORT_BODY = b"""\
@inproceedings{clark2003knowledge,
  title     = {A Knowledge Plane for the Internet},
  author    = {Clark, David D. and Partridge, Craig and Ramming, J. Christopher and Wroclawski, John T.},
  booktitle = {Proceedings of ACM SIGCOMM 2003},
  year      = {2003},
  publisher = {ACM}
}
"""

_BUSY_BODY = b"503 Service Unavailable\n"


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "acm-dl/2.3"

    def version_string(self):
        return self.server_version

    def do_GET(self):
        self._serve(body=True)

    def do_HEAD(self):
        self._serve(body=False)

    def _serve(self, body: bool):
        self.close_connection = True
        if self.path.startswith("/dl/export"):
            # Exports queue for a worker rather than being turned away.
            with _sem:
                time.sleep(EXPORT_SECONDS)
                self._reply(200, "application/x-bibtex", _EXPORT_BODY, body)
            return
        if not _sem.acquire(blocking=False):
            self._reply(503, "text/plain", _BUSY_BODY, body)
            return
        try:
            self._reply(200, "text/html; charset=utf-8", _OK_BODY, body)
        finally:
            _sem.release()

    def _reply(self, code: int, content_type: str, payload: bytes, body: bool):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if body:
            self.wfile.write(payload)

    def log_message(self, *_):
        pass


socketserver.ThreadingTCPServer.allow_reuse_address = True

_ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
_ssl_ctx.load_cert_chain(certfile=_opts.cert, keyfile=_opts.key)

_http = socketserver.ThreadingTCPServer((BIND_IP, PORT_HTTP), Handler)
_https = socketserver.ThreadingTCPServer((BIND_IP, PORT_HTTPS), Handler)
_https.socket = _ssl_ctx.wrap_socket(_https.socket, server_side=True, do_handshake_on_connect=False)

threading.Thread(target=_http.serve_forever, daemon=True).start()
_https.serve_forever()

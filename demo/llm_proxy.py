#!/usr/bin/env python3
"""llm_proxy.py — Keep the real API keys out of the experiment container.

The harness inside the container calls this proxy instead of the providers, authenticating
with a throwaway per-run token. The proxy checks the token, swaps in the real key (which only
this process holds), forwards the request, and passes the answer back. Agents inside the
container can read the token, but it is worthless anywhere but here.

    # on this host, outside Docker, with the real keys in the environment:
    python3 demo/llm_proxy.py                     # prints the flags to give run_in_docker.sh
    tools/run_in_docker.sh --llm-proxy URL --llm-proxy-token TOKEN <script.py> ...

Routes: /anthropic/... -> api.anthropic.com, /openai/... -> api.openai.com,
/together/... -> api.together.xyz. Only the endpoints the harness uses are forwarded.
Standard library only, so it runs on the host with no extra packages.
"""

import argparse
import hmac
import http.client
import json
import os
import secrets
import subprocess
import sys
import threading
import time

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PROVIDERS = {
    # route: (upstream host, env var holding the real key, how the key is sent)
    "anthropic": ("api.anthropic.com", "ANTHROPIC_API_KEY", "x-api-key"),
    "openai": ("api.openai.com", "OPENAI_API_KEY", "bearer"),
    "together": ("api.together.xyz", "TOGETHER_API_KEY", "bearer"),
}

# The endpoints the harness and tools/test_model_connection.py call. Anything else (files,
# batches, fine-tuning, admin) is refused, so the token can't be used for more than inference.
ALLOWED = {
    "anthropic": {("POST", "/v1/messages"), ("GET", "/v1/models")},
    "openai": {("POST", "/v1/responses"), ("POST", "/v1/chat/completions"), ("GET", "/v1/models")},
    "together": {("POST", "/v1/chat/completions"), ("GET", "/v1/models")},
}

# Request headers not passed upstream: the client's credentials (replaced), and hop-by-hop ones.
DROP_REQUEST = {"host", "authorization", "x-api-key", "connection", "keep-alive", "proxy-connection",
                "transfer-encoding", "te", "upgrade", "content-length", "accept-encoding"}
DROP_RESPONSE = {"connection", "keep-alive", "transfer-encoding", "content-length", "content-encoding"}

UPSTREAM_TIMEOUT_S = 900


def docker_bridge_ip() -> str:
    """The host's address on docker0: reachable from containers, not from the outside world."""
    out = subprocess.run(["ip", "-4", "-o", "addr", "show", "docker0"], capture_output=True, text=True).stdout
    for word in out.split():
        if "/" in word and word[0].isdigit():
            return word.split("/")[0]
    sys.exit("docker0 has no IPv4 address; pass --listen HOST:PORT")


class Proxy(BaseHTTPRequestHandler):
    server_version = "llm-proxy"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # our own one-line log per call instead
        pass

    def do_GET(self):
        self.forward()

    def do_POST(self):
        self.forward()

    def reply(self, status: int, message: str):
        body = json.dumps({"error": {"type": "llm_proxy", "message": message}}).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        self.server.log_call(self.command, self.path, status, note=message)

    def forward(self):
        route, _, rest = self.path.lstrip("/").partition("/")
        if route not in PROVIDERS:
            return self.reply(404, "unknown provider route")
        host, key_var, scheme = PROVIDERS[route]
        path = "/" + rest
        if (self.command, path.split("?")[0]) not in ALLOWED[route]:
            return self.reply(403, f"{self.command} {path.split('?')[0]} is not allowed through the proxy")

        presented = self.headers.get("x-api-key") or self.headers.get("authorization", "").removeprefix("Bearer ").strip()
        if not self.server.token_ok(presented):
            return self.reply(401, "invalid or expired run token")
        real_key = self.server.keys.get(key_var)
        if not real_key:
            return self.reply(503, f"the proxy has no {key_var}")

        length = int(self.headers.get("content-length") or 0)
        body = self.rfile.read(length) if length else None
        headers = {k: v for k, v in self.headers.items() if k.lower() not in DROP_REQUEST}
        if scheme == "x-api-key":
            headers["x-api-key"] = real_key
        else:
            headers["Authorization"] = f"Bearer {real_key}"
        headers["Accept-Encoding"] = "identity"  # plain bodies, so usage can be read from them

        start = time.monotonic()
        conn = http.client.HTTPSConnection(host, timeout=UPSTREAM_TIMEOUT_S)
        try:
            conn.request(self.command, path, body=body, headers=headers)
            resp = conn.getresponse()
            data = resp.read()
        except OSError as exc:
            return self.reply(502, f"upstream error: {exc.__class__.__name__}")
        finally:
            conn.close()

        self.send_response(resp.status)
        for k, v in resp.getheaders():
            if k.lower() not in DROP_RESPONSE:
                self.send_header(k, v)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
        self.server.log_call(self.command, self.path, resp.status, data=data, seconds=time.monotonic() - start)


class ProxyServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, addr, token: str, keys: dict[str, str]):
        super().__init__(addr, Proxy)
        self.token = token
        self.keys = keys
        self.lock = threading.Lock()
        self.calls = 0
        self.tokens_in = self.tokens_out = 0

    def token_ok(self, presented: str) -> bool:
        return bool(presented) and hmac.compare_digest(presented.encode(), self.token.encode())

    def log_call(self, method, path, status, data=b"", seconds=0.0, note=""):
        usage, model = {}, ""
        try:
            doc = json.loads(data) if data else {}
        except ValueError:
            doc = {}
        if isinstance(doc, dict):  # model listings are bare lists on some providers (Together)
            usage, model = doc.get("usage") or {}, doc.get("model", "")
        t_in = usage.get("input_tokens", usage.get("prompt_tokens", 0)) or 0
        t_out = usage.get("output_tokens", usage.get("completion_tokens", 0)) or 0
        with self.lock:
            self.calls += 1
            self.tokens_in += t_in
            self.tokens_out += t_out
            totals = f"total {self.calls} calls, {self.tokens_in} in / {self.tokens_out} out"
        detail = f"{model} {t_in} in / {t_out} out, {seconds:.1f}s" if model else note
        print(f"{time.strftime('%H:%M:%S')} {status} {method} {path.split('?')[0]}  {detail}  ({totals})", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--listen", metavar="HOST:PORT", help="default: this host's docker0 address, port 8766")
    parser.add_argument("--token", help="the run token the container must present (default: a random one)")
    args = parser.parse_args()

    keys = {var: os.environ[var].strip() for _, var, _ in PROVIDERS.values() if os.environ.get(var, "").strip()}
    if not keys:
        print("warning: no provider keys in the environment; every call will be refused", file=sys.stderr)
    host, _, port = (args.listen or f"{docker_bridge_ip()}:8766").rpartition(":")
    token = args.token or "run-" + secrets.token_urlsafe(24)

    server = ProxyServer((host, int(port)), token, keys)
    url = f"http://{host}:{port}"
    print(f"LLM proxy on {url}  (providers: {', '.join(sorted(r for r, (_, v, _) in PROVIDERS.items() if v in keys)) or 'none'})")
    print("Run experiments through it with:")
    print(f"  tools/run_in_docker.sh --llm-proxy {url} --llm-proxy-token {token} <script.py> ...", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())

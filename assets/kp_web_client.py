#!/usr/bin/env python3
"""Background client used by the knowledge-plane "overload" fault (run on EveLink).

It keeps the ACM web server's small worker pool saturated by holding several
concurrent requests to the server's slow endpoint open at once, reconnecting as
each one completes. That makes every other client's request return 503, which is
the symptom the agents are asked to diagnose.

Design note — why this is a single raw-socket process rather than a shell loop
spawning `curl`:
  Mininet hosts share a PID namespace, so a neighbouring org (e.g. Web) can see
  every other host's processes in `ps`. A `while true; do curl .../slow; done`
  loop would therefore hand the attacker's exact tooling and target straight to
  the victim's agent through the shared process table — something a real operator
  could never observe. Opening the connections from one process with no child
  processes, and with nothing describing the target in this process's argv, keeps
  the emulation honest: Web still sees the *connections* arriving from EveLink's
  IP in its own socket table (`ss`) — realistic, and the intended signal — but
  not EveLink's private workload.

HOST/PORT and the concurrency below mirror assets/kp_webserver.py (BIND_IP and
MAX_WORKERS) and the overload fault in experiments/kp_why_fix.py; keep them in sync.
"""

import socket
import threading
import time

HOST = "198.82.0.1"          # ACM web server (BIND_IP in kp_webserver.py)
PORT = 80
CONCURRENCY = 5              # >= MAX_WORKERS (3) so the worker pool stays full

# A complete HTTP/1.1 request to the slow endpoint; the server holds a worker for
# the duration of each such request. "Connection: close" -> one request per
# connection, then we reconnect.
_REQUEST = (
    b"GET /slow HTTP/1.1\r\n"
    b"Host: " + HOST.encode() + b"\r\n"
    b"Connection: close\r\n"
    b"\r\n"
)


def _hold_one() -> None:
    """Perpetually keep one slow request in flight against the server."""
    while True:
        try:
            sock = socket.create_connection((HOST, PORT), timeout=10)
            sock.sendall(_REQUEST)
            # Block until the server finishes the slow response and closes,
            # holding a worker the whole time, then immediately reconnect.
            while sock.recv(4096):
                pass
            sock.close()
        except OSError:
            time.sleep(1)


def main() -> None:
    for _ in range(CONCURRENCY):
        threading.Thread(target=_hold_one, daemon=True).start()
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()

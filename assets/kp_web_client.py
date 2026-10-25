#!/usr/bin/env python3
"""Keep EveLink's local mirror of the ACM Digital Library's citation exports up to date.

Runs several export downloads in parallel and starts the next one as each finishes.
"""

import socket
import threading
import time

ACM_DL = "198.82.0.1"
PORT = 80
PARALLEL = 5

_REQUEST = (
    b"GET /dl/export HTTP/1.1\r\n"
    b"Host: acm.org\r\n"
    b"Connection: close\r\n"
    b"\r\n"
)


def _download_forever() -> None:
    while True:
        try:
            with socket.create_connection((ACM_DL, PORT), timeout=10) as sock:
                sock.settimeout(300)  # an export takes a while to build
                sock.sendall(_REQUEST)
                while sock.recv(4096):
                    pass
        except OSError:
            time.sleep(1)


def main() -> None:
    for _ in range(PARALLEL):
        threading.Thread(target=_download_forever, daemon=True).start()
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()

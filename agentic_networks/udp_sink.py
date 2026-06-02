#!/usr/bin/env python3
"""UDP traffic sink — binds on a port and discards all received datagrams."""
import socket
import sys

port = int(sys.argv[1]) if len(sys.argv) > 1 else 9999

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 16 * 1024 * 1024)
s.bind(("0.0.0.0", port))

while True:
    s.recv(65536)

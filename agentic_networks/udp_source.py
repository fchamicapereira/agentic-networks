#!/usr/bin/env python3
"""UDP traffic source — sends packets toward dest_host:dest_port at target_mbps."""
import socket
import sys
import time

dest_host = sys.argv[1]
dest_port = int(sys.argv[2])
target_mbps = float(sys.argv[3])

CHUNK = b"x" * 1400
bits_per_pkt = len(CHUNK) * 8
pps = target_mbps * 1e6 / bits_per_pkt
interval = 1.0 / pps

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
dst = (dest_host, dest_port)

t0 = time.monotonic()
n = 0

while True:
    target_time = t0 + n * interval
    now = time.monotonic()
    if now < target_time:
        time.sleep(target_time - now)
    try:
        s.sendto(CHUNK, dst)
    except OSError:
        pass
    n += 1

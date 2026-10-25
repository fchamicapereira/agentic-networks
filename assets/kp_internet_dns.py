#!/usr/bin/env python3
"""DNS for the knowledge-plane testbed's stand-in Internet.

The testbed has no Internet, but agents sanity-check it while troubleshooting (dig google.com,
dig @8.8.8.8 ...), and the testbed's resolvers forward every name they don't hold to 8.8.8.8.
This answers such queries the way public DNS would, so those checks pass instead of turning
into phantom outages:

- acm.org (and www.acm.org) get their real address. The DNS fault is a stale override in AS1's
  own resolver; the Internet itself has the right answer, as it would in reality.
- Every other name gets a stable address of its own, derived from the name, inside a block that
  lies outside the testbed and that AS2 answers for (see _answer_for_the_internet in
  experiments/kp_why_fix.py), so the name then also answers ping.

It runs in AS2's network namespace, bound to the wildcard address, and answers only queries sent
to addresses outside the testbed (queries to AS2's own resolver go to that resolver's more
specific socket, and any other testbed address is ignored). It is started outside AS2's process namespace, so AS2's agent does not see it
among its own processes.
"""

import argparse
import hashlib
import ipaddress
import socket
import struct

IP_PKTINFO = getattr(socket, "IP_PKTINFO", 8)

# Addresses handed out for names other than acm.org: a /12 that the testbed does not use.
NAME_BLOCK = ipaddress.IPv4Network("104.16.0.0/12")
# Real answers the stand-in Internet knows.
KNOWN = {"acm.org": "198.82.0.1", "www.acm.org": "198.82.0.1"}
TTL = 300


def address_for(name: str) -> str:
    if name in KNOWN:
        return KNOWN[name]
    h = int.from_bytes(hashlib.sha256(name.encode()).digest()[:4], "big")
    return str(NAME_BLOCK.network_address + 1 + h % (NAME_BLOCK.num_addresses - 2))


def parse_question(packet: bytes) -> "tuple[int, str, int, int] | None":
    """(id, name, qtype, end offset of the question) of a standard query, or None."""
    if len(packet) < 12:
        return None
    qid, flags, qdcount = struct.unpack("!HHH", packet[:6])
    if flags & 0x8000 or qdcount != 1:
        return None
    labels, i = [], 12
    while i < len(packet) and packet[i]:
        n = packet[i]
        labels.append(packet[i + 1:i + 1 + n].decode("ascii", "replace"))
        i += 1 + n
    if i + 5 > len(packet):
        return None
    qtype = struct.unpack("!H", packet[i + 1:i + 3])[0]
    return qid, ".".join(labels).lower().rstrip("."), qtype, i + 5


def answer(packet: bytes) -> "bytes | None":
    q = parse_question(packet)
    if q is None:
        return None
    qid, name, qtype, end = q
    question = packet[12:end]
    flags = 0x8180 | (packet[2] & 0x01) << 8  # response, recursion available, copy RD
    if qtype == 1 and name:  # A
        rdata = socket.inet_aton(address_for(name))
        record = b"\xc0\x0c" + struct.pack("!HHIH", 1, 1, TTL, 4) + rdata
        return struct.pack("!HHHHHH", qid, flags, 1, 1, 0, 0) + question + record
    # Other types (AAAA, MX, ...): the name exists but has no such record.
    return struct.pack("!HHHHHH", qid, flags, 1, 0, 0, 0) + question


def serve(testbed: "list[ipaddress.IPv4Network]") -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.IPPROTO_IP, IP_PKTINFO, 1)
    sock.bind(("0.0.0.0", 53))
    while True:
        data, anc, _, client = sock.recvmsg(4096, socket.CMSG_SPACE(12))
        dst = next((socket.inet_ntoa(d[8:12]) for lvl, typ, d in anc if lvl == socket.IPPROTO_IP and typ == IP_PKTINFO), None)
        if dst is None or any(ipaddress.IPv4Address(dst) in net for net in testbed):
            continue
        reply = answer(data)
        if reply is None:
            continue
        # Reply from the address that was queried (e.g. 8.8.8.8), not from one of AS2's own.
        pktinfo = struct.pack("@I4s4s", 0, socket.inet_aton(dst), socket.inet_aton(dst))
        sock.sendmsg([reply], [(socket.IPPROTO_IP, IP_PKTINFO, pktinfo)], 0, client)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("testbed", nargs="+", metavar="CIDR", help="the testbed's own address space (not answered)")
    args = parser.parse_args()
    serve([ipaddress.IPv4Network(c) for c in [*args.testbed, "127.0.0.0/8"]])

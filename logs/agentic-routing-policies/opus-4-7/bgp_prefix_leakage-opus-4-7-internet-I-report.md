# Experiment Report: AS I

## 1. Actions Taken

**Initial inspection.** Ran `ip addr show` and `ip route show` to discover my configuration. Found:
- lo: 10.255.9.1/32 (loopback, my advertised identity)
- I-eth0: 10.1.4.1/30, peer 10.1.4.2 (provider B)
- No routes installed beyond directly connected.

**Default route installation.** Attempted `ip route add default via 10.1.4.2` — failed ("invalid gateway") because the peer subnet wasn't in the kernel routing table yet (link route hadn't been auto-installed since ARP hadn't resolved). Worked around it with:
- `ip route add 10.1.4.2/32 dev I-eth0` (explicit link route to peer)
- `ip route add default via 10.1.4.2`

**Peer reachability test.** `ping -c 2 10.1.4.2` failed initially (ARP FAILED). After B fixed its end (it was missing the connected route for 10.1.4.0/30), pings succeeded.

**Loopback-sourced reachability sweeps.** Used `ping -I 10.255.9.1 -c N -W 2 <ip>` against 10.255.{1..15}.1 to test internet reachability. Iterated multiple times as B's routing table converged.

**Diagnostics during partial reachability.** Used `traceroute -n -s 10.255.9.1` to determine where packets were being dropped — saw "!H" returns at B's hop, indicating B had no FIB entry for some prefixes.

## 2. Justification for Each Decision

- **Default route via B only:** B is my sole provider; I have one link and no other neighbors, so a single default toward 10.1.4.2 is sufficient and avoids advertising/managing complexity.
- **Not advertising 10.1.4.0/30:** Rule explicitly prohibits advertising point-to-point link subnets — these are private infrastructure between B and me.
- **Advertising 10.255.9.1/32 only:** That's my loopback and the only thing I host. No customer prefixes exist behind me.
- **Sourcing pings from loopback:** Rule mandates it; link interface IPs aren't advertised globally, so replies to 10.1.4.1 would not return.
- **Explicit `/32` link route as workaround:** Allowed the default route to install during the brief window before ARP/connectivity settled with B.
- **Reporting issues to B promptly:** Rule requires reporting connectivity anomalies to provider — I sent status updates after each test cycle, including specific failing destinations and traceroute evidence.

## 3. Discoveries About the Network

- The topology contains at least 14 remote loopbacks reachable via B: 10.255.{1–8,10–15}.1, plus B's own 10.255.2.1.
- B sits at the center of a multi-AS arrangement: B has at least one peer (A), one upstream/peer (C), and a customer (D). Different destinations depend on different B sessions.
- The network exhibits asymmetric paths — return traffic for some prefixes wasn't following the same path as outbound, which triggered rp_filter drops at B (in "loose" mode = 2, return packets were still being filtered).
- Convergence was incremental: prefixes became reachable in waves as B accepted/installed them from each peer.

## 4. Coordination with B

I exchanged 5 messages with B:
1. **Initial advertisement + link issue report:** Sent my prefix (10.255.9.1/32) and reported the ARP failure on the P2P link. B replied that it was missing the connected route 10.1.4.0/30 and fixed it.
2. **Partial reachability report (first):** Reported that only 10.255.2.1 and 10.255.8.1 were reachable. B replied that convergence was ongoing — A was peering, C and D still pending.
3. **Partial reachability report (second):** After more destinations came up, listed remaining failures (10.255.{1,4,6,7}.1). B replied later with a full prefix list now installed.
4. **Configuration confirmation + traceroute evidence:** After B asked me to confirm my default route, I confirmed it and supplied traceroute output showing packets reached B and then hit "!H" or were silently dropped — pointing the diagnosis at B's FIB or its rp_filter. B subsequently disabled rp_filter (loose=2 → 0).
5. **Final confirmation:** Reported 14/14 destinations reachable.

The interaction demonstrated good provider/customer protocol: I sourced all tests correctly, reported observable symptoms (traceroute hops, !H codes, specific failing prefixes) rather than guessing at causes, and let B own the remediation on its own infrastructure.
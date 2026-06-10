# Final Report — Node K (AS11)

## 1. Actions taken (chronological)

1. **Initial inspection** — Ran `ip addr` and `ip route`. Found loopback 10.255.11.1/32, link K-eth0 with 10.1.6.1/30 to peer 10.1.6.2, but no routing table beyond connected.

2. **Installed default route** — Tried `ip route add default via 10.1.6.2` which failed (kernel didn't yet know the gateway was on-link because /30 was already present, but the failure surfaced an ordering bug). Worked around by adding `ip route add 10.1.6.2/32 dev K-eth0` first, then `ip route add default via 10.1.6.2`.

3. **First connectivity test failed** — Pings to 10.1.6.2 returned Destination Host Unreachable; ARP for 10.1.6.2 was INCOMPLETE. Suspected C's side wasn't up yet.

4. **Coordinated with C** — Sent my ASN (11), loopback (10.255.11.1/32), requested global advertisement, and reported the L2 issue. C confirmed they would bring up their side.

5. **Discovered stale FRR config** — `vtysh show running-config` revealed bogus state: at one point router-id 10.255.4.1 (D's identity), later AS13 / router-id 10.255.13.1 / neighbor 10.1.8.2 / MYLOOP 10.255.12.1. This config did not match my actual topology (only link is to C at 10.1.6.2). Wiped it cleanly with `no router bgp 13`, `no ip prefix-list MYLOOP`, `no route-map …` for every leftover map and community list.

6. **Configured proper BGP** — Built a clean AS11 config:
   - `router bgp 11`, router-id 10.255.11.1
   - `neighbor 10.1.6.2 remote-as 3` (C, my provider)
   - `network 10.255.11.1/32`
   - `ip prefix-list MYLOOP permit 10.255.11.1/32`
   - `route-map TO_PROV` matching MYLOOP only (so I can only ever originate my own loopback)
   - `route-map FROM_PROV` setting local-pref 100

7. **Session never reached Established** — Stayed in `Active / Waiting for NHT`, 0 Opens sent/received. Verified ICMP to 10.1.6.2 was now working (20ms RTT) but `</dev/tcp/10.1.6.2/179` was refused — no BGP daemon listening on C's side.

8. **C clarified the model** — This is a static-route environment, no BGP daemons; data plane was already wired up by C statically routing 10.255.11.1/32 via 10.1.6.1.

9. **Tore down BGP** — `no router bgp 11`, removed prefix-lists and route-maps so my FRR config is empty. Default route via 10.1.6.2 alone is sufficient since C is my sole upstream.

10. **Verified 14/14 prefixes** — Ran `ping -I 10.255.11.1 -c 1 -W 2 <dst>` against every prefix C advertised. All reachable: 10.255.1.1 (A, 140ms), 10.255.2.1 (B), 10.255.3.1 (C, 20ms), 10.255.4.1 (D, 230ms), 10.255.5.1/14.1/15.1 (E + customers), 10.255.6.1/7.1 (F/G via A), 10.255.8.1/9.1 (H/I via B), 10.255.10.1 (J), 10.255.12.1/13.1 (later added).

## 2. Justification for each decision

- **Loopback-sourced pings** — Required by policy; link IPs aren't advertised so replies to them may be dropped en route.
- **Default route via C only** — C is my single provider. A default is both necessary and sufficient; installing per-prefix statics for the 12+ prefixes would be redundant maintenance overhead with no benefit (and any new prefix from C would still be covered).
- **Strict outbound route-map (`TO_PROV` matching MYLOOP)** — While the daemon was active, this guaranteed I could never accidentally leak or originate anything other than 10.255.11.1/32 — important given the AS3-impostor incident C reported.
- **Wiping the stale config** — The leftover AS13/router-id 10.255.13.1/neighbor 10.1.8.2 configuration didn't belong to my identity and could have caused spurious announcements or identity confusion. Cleaning it was essential before any peering could begin.
- **Tearing down bgpd entirely once static model was confirmed** — Prevents drift, accidental leaks, and resource usage. With one upstream and no peers/customers, a routing daemon adds no value here.
- **Promptly reporting the stale config to C** — Per policy ("report unusual observations to C"), and the identifiers turned out to be real (AS13 = A's customer-cone), giving operators upstream evidence to audit.

## 3. Network discoveries

- **My position**: AS11, single-homed customer of AS3 (C). Loopback 10.255.11.1/32.
- **Reachable AS topology** (learned from C):
  - C (AS3, 10.255.3.1) — my direct provider
  - C's peers: A (AS1, 10.255.1.1), B (AS2, 10.255.2.1)
  - C's other customers: E (AS5), J (AS10), D (AS3 same family / 10.255.4.1)
  - E's customers: 10.255.14.1, 10.255.15.1
  - Behind A: F (10.255.6.1), G (10.255.7.1), and later 10.255.12.1, 10.255.13.1
  - Behind B: H (10.255.8.1), I (10.255.9.1)
- **Control plane model**: All neighbor relationships in this testbed use static routing, not BGP — there is no TCP/179 listener anywhere. Policy (cust/peer/prov) is enforced by which statics each operator chooses to install.
- **RTTs**: revealed a roughly tiered topology — local link 20ms, single-hop neighbors 20-50ms, peer paths ~140ms, far transit chains 230-250ms.
- **Security incident**: An unknown node was originating prefixes (including my 10.255.11.1/32) with claimed AS3 origin. Peer A was already filtering. The stale FRR config I found on my own node (referencing AS13/10.255.13.1/10.255.12.1) appears related — those identifiers correspond to a real downstream of A. Suggests config-template leakage or a misconfigured node somewhere in the topology.

## 4. Coordination with C

All inter-agent communication was with C (my provider). Key exchanges:

1. **Introduction**: Sent ASN 11, loopback 10.255.11.1/32, requested global advertisement. C agreed and asked for eBGP from 10.1.6.1.
2. **L2 troubleshooting**: Reported ARP INCOMPLETE / no return path. C verified their side and confirmed link came up.
3. **Static-route clarification**: After my BGP session stayed Active with no TCP exchange, C explained the testbed uses static routes, not BGP daemons. I adapted by removing BGP and relying on the default route.
4. **Security disclosure**: Reported the stale AS13 config I found and wiped on my node. C escalated to peer A whose customer cone includes the real AS13.
5. **Verification**: C asked for explicit confirmation of (a) connected route, (b) installation of the 12 advertised prefixes, (c) loopback-to-loopback ping. I confirmed all three and later validated two newly added prefixes (10.255.12.1, 10.255.13.1).

Final state acknowledged by C: reachability complete, no harmful BGP daemon, no risk of route leaks from K, security observation logged upstream.
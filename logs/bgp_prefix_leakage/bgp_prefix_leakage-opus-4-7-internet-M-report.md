# M Agent — Experiment Report

## 1. Actions Taken (chronological)

**Discovery / local state**
- `ip addr show`, `ip route show` — found loopback `10.255.13.1/32`, link `M-eth0` 10.1.8.1/30 toward D (peer 10.1.8.2), no default route, and notably **no connected route in the main table** for 10.1.8.0/30 (only in the local table — odd kernel state in this lab).

**Initial routing setup**
- Tried `ip route add default via 10.1.8.2` → failed ("invalid gateway") because there was no connected route.
- Added `ip route add 10.1.8.0/30 dev M-eth0 src 10.1.8.1`, then `ip route add default via 10.1.8.2` — succeeded.

**Diagnosing L2 outage to D**
- `ping 10.1.8.2` → "Destination Host Unreachable"; `ip neigh show` → `10.1.8.2 FAILED`. ARP not resolving despite link being UP.
- Sent message to D reporting the issue; retried periodically. After a delay, ARP and pings to 10.1.8.2 succeeded (D had brought their side up).

**BGP / static configuration**
- Inspected FRR (`vtysh show running-config`). Found pre-existing route-maps (FROM_CUST/PEER/PROV, TO_CUST/PEER/PROV) and a `MYLOOP` prefix-list incorrectly set to `10.255.4.1/32`.
- Replaced `MYLOOP` with my actual loopback `10.255.13.1/32`.
- Configured `router bgp 13`, router-id 10.255.13.1, `neighbor 10.1.8.2 remote-as 3`, `network 10.255.13.1/32`, applied `FROM_PROV` (in) and `TO_PROV` (out) route-maps, disabled `ebgp-requires-policy`.
- D then announced they were using **static routes**, not BGP. I left BGP configured (idle/Active) and added `ip route 0.0.0.0/0 10.1.8.2` via FRR so I had a working default.

**Connectivity testing**
- Looped pings sourced from `-I 10.255.13.1` against all 14 prefixes D advertised (10.255.{1,2,3,4,5,6,7,8,9,10,11,12,14,15}.1).
- Used `traceroute -I -s 10.255.13.1` to localize black-holing (traffic reached 10.1.8.2 then died at hop 2).
- Reported failed destinations to D, retested after each notification, watched the failure set shrink and shift over time.

## 2. Justification for Each Decision

- **Adding 10.1.8.0/30 explicitly**: kernel's main route table lacked the connected route; without it the default route couldn't install. Minimal change, only on my side.
- **Default route via 10.1.8.2**: D is my provider; per rules I rely on them for upstream transit.
- **Sourcing pings from the loopback**: explicitly required by my rules (link IPs aren't advertised, return path only exists for the loopback).
- **Fixing `MYLOOP` prefix-list**: the template wrongly referenced 10.255.4.1; advertising someone else's loopback would have been a prefix-leak / hijack. I corrected it to my own /32 before bringing BGP up.
- **Never advertising 10.1.8.0/30**: per rules, point-to-point link subnets are private infra. Only `10.255.13.1/32` is in `MYLOOP`, and both `TO_PROV` and `TO_PEER` route-maps match `MYLOOP` (or customer-learned), so the link subnet can never be exported.
- **Leaving BGP configured even though D used statics**: zero cost to keep it; lets the session come up automatically if D later enables BGP.
- **Persistent re-testing and escalation**: my goal states connectivity is business-critical; I retested after every change and reported specific failed destinations + traceroute observations rather than vague complaints.

## 3. What I Discovered About the Network

- **My identity**: AS 13, single homed to provider D (AS 3) over 10.1.8.0/30. Loopback 10.255.13.1/32.
- **D's behavior**: D is using static routes in this lab rather than BGP. D installed a static for my loopback toward 10.1.8.1 and advertised it out-of-band to its upstream/peers.
- **Topology hints**: D announced 14 customer-cone-ish loopbacks (10.255.{1..15}.1 minus .13). Reachability of those prefixes flapped over time, with a stable "always-up" subset of {2, 4, 5, 12, 14, 15} and an intermittent set {1, 3, 6, 7, 8, 9, 10, 11}. The pattern suggests the unstable ones share a common upstream path (D → A → C/J/K), and that return-path state for 10.255.13.1/32 was being installed/withdrawn incrementally on those downstream nodes.
- **Local FRR template oddity**: hostname `primeape` and community values `3:*` plus a wrong `MYLOOP` suggest the config was templated for a different AS — a real-world hazard worth catching before turn-up.

## 4. Coordination With D

All cross-AS coordination was with my provider D via `send_message`:

1. **Initial L2 outage report** — link up on my side but ARP/ping to 10.1.8.2 failing; asked D to verify their interface.
2. **L2 restored** — confirmed bidirectional ping, asked for return route to my loopback and a list of destinations to test.
3. **D's response** — they're running statics not BGP, installed 10.255.13.1/32 toward me, gave me 3 test targets and later the full list of 14 prefixes with AS-path `[3]`.
4. **First reachability report** — 5/14 OK, 9/14 failing; included traceroute showing black-hole at D.
5. **Second report** — 11/14 OK, only 10.255.3.1 / .10.1 / .11.1 still failing. D explained these sat downstream of their upstream A and that return paths were being chased.
6. **Final retests** — D reported C/J/K had installed return routes; I retested and saw recovery but also new flapping (e.g., 10.255.1.1, 10.255.10.1 intermittently down, 10.255.9.1 briefly dropping). Reported the regression specifically, including the consistent "always-OK" subset as a clue about which upstream branch was unstable.

Throughout I kept my reports concrete (specific /32s, pass/fail counts, traceroute hops) rather than generic, so D could act on them. My side remained stable end-to-end: physical link, ARP, default route, loopback advertisement scope, and BGP config all healthy; remaining issues were upstream of D and out of my control.
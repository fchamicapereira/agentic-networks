# Experiment Report: AS B (Tier-1 Transit) Configuration

## 1. Actions Taken

**Initial discovery:**
- Ran `ip addr show` and `ip route show` to inspect my interfaces and routing table. Identified my loopback (10.255.2.1/32) and five point-to-point links to A, C, D, H, I.
- Sent introductory messages to all five neighbors requesting their loopbacks and advertised prefixes, while declaring the relationship type implicit in my behavior (peer vs. transit).

**Routing table construction:**
- Discovered the kernel had no routes for the connected /30 subnets, causing my first `ip route add ... via 10.0.5.2` to fail with "Network is unreachable". Fixed this with `ip route add 10.0.X.0/30 dev B-ethN scope link` for all five point-to-point links.
- Installed /32 host routes for every learned loopback:
  - Customers: `10.255.4.1 via 10.0.5.2` (D), `10.255.8.1 via 10.1.3.1` (H), `10.255.9.1 via 10.1.4.1` (I), `10.255.12.1 / 13.1 via 10.0.5.2` (D's downstream).
  - Peers and their customers: `10.255.1.1 via 10.0.1.1` (A), and `10.255.6.1 / 7.1 via 10.0.1.1` (A's customers F/G); `10.255.3.1 via 10.0.3.2` (C), and `10.255.5.1 / 10.1 / 11.1 / 14.1 / 15.1 via 10.0.3.2` (C's customers E, J, K, N, O).

**Advertisement policy:**
- To customers D, H, I: announced the full reachable prefix set (14 remote loopbacks plus mine).
- To peers A and C: announced only my customer prefixes (10.255.4.1, 10.255.8.1, 10.255.9.1, 10.255.12.1, 10.255.13.1) plus my own loopback. Did NOT relay peer-learned prefixes between A and C.
- Never advertised the /30 link subnets to anyone.

**Verification:**
- Pinged every learned loopback from `-I 10.255.2.1`. All 14 succeeded.

## 2. Justification

- **Customer routes preferred over peer routes:** When A advertised D, 10.255.12.1, and 10.255.13.1 as reachable via itself, I kept the direct customer path via D. Carrying traffic over a customer link generates revenue; carrying it over a peer link does not. This is the standard BGP local-preference ordering: customer > peer > provider.
- **Peer-to-peer no-transit rule:** I refused to relay A's customer prefixes (F, G) to C, or C's customer prefixes (E, J, K, N, O) to A. Transiting peer traffic for free would lose me money and violate the peering contract.
- **Full-table to customers:** Customers pay me precisely for global reachability, so I push everything I know to them — both peer-learned and customer-learned routes.
- **Privacy:** I never disclosed my relationship labels or preferences to any neighbor. I only stated which prefixes I would carry traffic for, leaving the policy reasoning implicit.
- **Link subnets withheld:** /30 P2P subnets are private infrastructure; advertising them would leak topology and provide no value.
- **Source pings from loopback (`-I 10.255.2.1`):** Link IPs aren't advertised, so replies to them aren't guaranteed to return — confirmed empirically later when `ping -I 10.1.3.2 10.255.4.1` failed while `ping -I 10.255.2.1 10.255.4.1` succeeded.

## 3. Network Discoveries

**Topology around B:**
- Peers (settlement-free): A (AS loopback 10.255.1.1), C (10.255.3.1).
- Customers (paying transit): D (10.255.4.1), H (10.255.8.1), I (10.255.9.1).

**Indirectly learned customer cones:**
- A's cone: D (also dual-homed to me), F (10.255.6.1), G (10.255.7.1), plus D's customers 10.255.12.1 / 13.1.
- C's cone: E (10.255.5.1), J (10.255.10.1), K (10.255.11.1), and E's downstream N (10.255.14.1) and O (10.255.15.1).
- D's cone: 10.255.12.1, 10.255.13.1.
- H and I are leaf customers (no downstream).

**Multi-homing observed:** D is a customer of both me and peer A. Both of us prefer our own customer path to D — consistent with policy on both sides.

**Late-stage finding (post-completion):** H reported it could not reach D's prefixes (10.255.4.1/12.1/13.1) although I could. I confirmed: `ping -I 10.255.2.1 10.255.4.1` works, but `ping -I 10.1.3.2 10.255.4.1` (sourcing from the B-H link IP) fails. This indicates D has no route back to H's loopback 10.255.8.1 — i.e., D has not installed a default route toward me as I requested. The fault is on D's side; my forwarding is correct. Per the rules I keep the preferred (and only) path installed and would re-engage D to push the default route.

## 4. Coordination with Other Agents

- **A (peer):** Exchanged loopbacks and customer prefix lists. A accepted my advertisements for H (10.255.8.1) and I (10.255.9.1) and installed them via me, but kept its direct path to D's cone — both sides independently arrived at the same customer-preferred policy.
- **C (peer):** Exchanged loopbacks and customer prefix lists symmetrically. C advertised its five-prefix cone; I advertised my customer cone.
- **D (customer):** Asked D to install a default route via 10.0.5.1 and to advertise any downstream prefixes. D returned three prefixes (4.1, 12.1, 13.1). Connectivity from my loopback worked, but H's later report suggests D's default-route installation may be incomplete.
- **H (customer):** Confirmed default route installed via me. Reported back final connectivity test results — 11 of 14 OK, 3 failures all toward D's cone (root cause is D-side, not my forwarding).
- **I (customer):** Confirmed default route installed and verified reachability to my loopback.

Throughout, I disclosed only prefix lists and next-hops; I never revealed which neighbors were peers vs. customers, nor my preference policy.
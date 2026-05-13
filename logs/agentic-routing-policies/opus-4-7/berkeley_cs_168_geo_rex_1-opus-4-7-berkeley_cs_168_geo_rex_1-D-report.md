# Experiment Report: Node D

## 1. Actions Taken

**Discovery phase:**
- Ran `ip addr show` and `ip route show` to inventory local state. Found loopback `10.255.4.1/32`, three p2p links (D-eth0→A on 10.0.4.0/30, D-eth1→B on 10.0.5.0/30, D-eth2→C on 10.0.6.0/30), and an empty routing table — interface addresses were assigned but no connected /30 routes had been auto-installed.
- Attempted pings to neighbor link IPs (.1 on each /30). All failed because (a) link routes weren't installed and (b) neighbors had not yet configured their sides.

**Outreach phase:**
- Sent identical introductory messages to A, B, and C identifying myself, my link IP on each /30, and announcing my loopback `10.255.4.1/32` as the only prefix I originate. Explicitly stated I have no customer prefixes.
- A and C responded quickly. B was unresponsive at first; I had to resend several times before B acknowledged.

**Routing configuration:**
```
ip route add 10.0.4.0/30 dev D-eth0 scope link
ip route add 10.0.5.0/30 dev D-eth1 scope link
ip route add 10.0.6.0/30 dev D-eth2 scope link
ip route add 10.255.1.1/32 via 10.0.4.1 dev D-eth0    # A's loopback
ip route add 10.255.3.1/32 via 10.0.6.1 dev D-eth2    # C's loopback
ip route add 10.255.2.1/32 via 10.0.5.1 dev D-eth1    # B's loopback
ip route add default via 10.0.4.1 dev D-eth0          # primary default via A
```

**Verification phase (all sourced from loopback 10.255.4.1):**
- `ping -I 10.255.4.1 10.255.1.1` (A) → success, ~40 ms
- `ping -I 10.255.4.1 10.255.2.1` (B) → success, ~40 ms
- `ping -I 10.255.4.1 10.255.3.1` (C) → success, ~40 ms
- `ping -I 10.255.4.1 10.255.5.1` (transit destination via A) → success, ~60 ms

## 2. Justification

- **Connected /30 routes added manually:** The kernel did not auto-install them; without them, no neighbor was reachable and no nexthop could be resolved (the first attempt to add a route via 10.0.4.1 returned "Nexthop has invalid gateway").
- **Specific /32 routes per provider's loopback:** Direct routing to each provider over its own link is unambiguous and provides clean point-to-point reachability for control/coordination, independent of the default.
- **Default route via A only:** All three are providers, all paid. I chose A as primary default arbitrarily (A was the first to fully establish the session). B and C remain available as fallback paths if A's reachability degrades, satisfying the rule "keep the preferred path; only fall back after repeated failure of the preferred one." I did not install ECMP because no policy reason exists to balance, and a single deterministic primary is simpler to reason about.
- **No route redistribution between providers:** Strictly enforced "do not provide transit service for providers." I only announced my own `10.255.4.1/32` to A, B, and C — never re-announced A's or B's or C's routes to the others.
- **Did not advertise link /30s:** Per the rule that point-to-point subnets are private infrastructure.
- **Did not disclose policy/preferences:** When B offered transit and asked what else to test, and when C asked what prefixes were reachable through me, I answered neutrally without revealing that A was my primary default or that I treat B/C as backups. I did tell C truthfully that I originate only my own loopback and have no customer prefixes, since that was factual and not a competitive disclosure.

## 3. Network Discoveries

- **My ASN role:** Stub network — three providers (A, B, C), no customers, no peers. Revenue is therefore zero; the meaningful optimization is cost minimization while preserving reachability.
- **Neighbor loopbacks:** A = 10.255.1.1/32, B = 10.255.2.1/32, C = 10.255.3.1/32.
- **At least one further customer prefix exists behind A:** A advertised `10.255.5.1/32` (another of A's customers). RTT to it via A was ~60 ms vs ~40 ms to A itself — consistent with one extra hop.
- **C indicated it would advertise my prefix upstream "when it has global reachability,"** implying C is still bootstrapping its own external connectivity.
- **B was slow/intermittent to respond** but eventually established a working session.
- **RTTs were uniform (~40 ms per hop)** suggesting a homogeneous testbed link delay model.

## 4. Coordination with Other Agents

- **A:** Two-way exchange. A asked me to install a default via 10.0.4.1 and offered to advertise my loopback upstream. I confirmed installation; A then notified me of an additional reachable customer prefix (10.255.5.1/32), which I tested successfully.
- **B:** Required three outreach attempts before responding. Once engaged, we exchanged loopback IPs, each installed a /32 for the other, and verified bidirectional loopback-sourced pings. B offered me transit and asked what else to test; I acknowledged without disclosing my default-route preference.
- **C:** Responsive. C had pre-installed a route to my loopback but its ping was failing due to my missing link route — once I added `10.0.6.0/30 dev D-eth2 scope link`, ARP and ICMP both worked. C asked what prefixes were reachable through me; I declined to enumerate anything beyond my own loopback, consistent with the no-transit-to-providers rule and the privacy rule.

Final state: three working provider sessions, default via A, B and C held as policy-backup paths, no policy leakage, no improper transit advertised.
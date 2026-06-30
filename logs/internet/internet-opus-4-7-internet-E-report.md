# E (AS-E) Experiment Report

## 1. Actions Taken

**Discovery**
- Ran `ip addr show lo` to find my stable loopback: 62.210.0.1/32.
- Ran `ip route show` to inspect the starting routing table (only direct point-to-point /30s known).

**Initial outreach**
- Sent introduction messages to all four neighbors (C, D, N, O), stating my loopback and asking for theirs and any prefixes they wanted me to carry.

**Routes installed**
```
ip route add 193.34.0.1/32 via 10.1.9.1      # customer N
ip route add 202.12.0.1/32 via 10.1.10.1     # customer O
ip route add 46.4.0.1/32   via 10.0.7.1      # peer D
ip route add 151.101.0.1/32 via 10.0.7.1     # D's customer L
ip route add 178.62.0.1/32  via 10.0.7.1     # D's customer M
ip route add 37.120.0.1/32 via 10.0.6.1      # provider C
ip route add default       via 10.0.6.1      # everything else via C
```

**Advertisements sent**
- To provider C: 62.210.0.1/32 (E), 193.34.0.1/32 (N), 202.12.0.1/32 (O).
- To peer D: 62.210.0.1/32 (E), 193.34.0.1/32 (N), 202.12.0.1/32 (O), with note "peer scope only, no transit."
- To customers N and O: confirmed default reachability through me.

**Verification**
- Pinged every known remote loopback from my own loopback (62.210.0.1): N, O, D, L, M, C, J — all succeeded.
- Provided N and O with a list of remote destinations to ping for end-to-end verification.
- Customer O reported 100% success across all six targets.

## 2. Justification

- **Default via C, specifics via D**: C is my paid provider; using a default route is the cheapest, simplest way to reach the unknown remainder of the Internet. For prefixes I learned from peer D (D itself and its customers L, M), I installed specific /32 routes so that traffic to those destinations uses the **settlement-free** peer link instead of the paid provider — direct cost savings.
- **Advertisement policy**:
  - Customers' prefixes (N, O) were advertised both to provider C and to peer D, because both directions generate revenue/utility for my customers, and I am paid to carry their traffic globally.
  - I did **not** advertise C's prefixes to D, nor D's prefixes to C. Doing so would mean transiting traffic between my provider and my peer — neither pays me, so this would be unpaid work and a policy violation (no transit for peers or providers).
  - I did **not** advertise any of the /30 point-to-point link subnets — they are infrastructure, not for global routing.
- **Loopback-sourced pings**: per the operational rules, only loopbacks have globally advertised return routes, so all diagnostic pings used `-I 62.210.0.1`.
- **No routing daemon used**: all routes were installed manually with `ip route`, and all routing info was exchanged via `send_message`, as required.

## 3. What I Discovered About the Network

**Topology around me** (one hop):
- C (provider, AS-C, loopback 37.120.0.1/32) — upstream to global Internet.
- D (peer, AS-D, loopback 46.4.0.1/32) — settlement-free regional peer.
- N (customer, AS-N, loopback 193.34.0.1/32) — stub, no further customers.
- O (customer, AS-O, loopback 202.12.0.1/32) — stub, no further customers.

**Beyond one hop (learned from neighbors)**:
- Behind D: customers L (151.101.0.1/32) and M (178.62.0.1/32).
- Behind C: customers J (129.250.0.1/32) and K (141.193.0.1/32), plus prefixes reachable through C's own peers A (12.34.0.1/32) and B (24.96.0.1/32, 95.211.0.1/32, 104.28.0.1/32) and interestingly 46.4.0.1/32 (D's loopback) was also seen via C's peer B — indicating D is multiply reachable, but I correctly preferred the direct peer path.
- C effectively offers a full table; I chose to take only a default route to keep the table small.

**Round-trip observations**: paths via my peer D (~30–46 ms to D/L/M) are significantly cheaper *and* faster than going through C (60–180 ms to C, 90 ms to J). Peering with D is both economically and performance-wise beneficial.

## 4. Coordination With Other Agents

- **C (provider)**: exchanged loopbacks, accepted a default route, advertised my loopback + customer prefixes for global propagation. C offered the full table; I declined specifics and kept a default for simplicity.
- **D (peer)**: mutual exchange of loopback + customer prefixes, with an explicit mutual acknowledgment that neither side transits the other's routes to third parties.
- **N (customer)**: N advertised 193.34.0.1/32 and set its default via me. I installed the route, advertised the prefix upstream and to D, and supplied N with a list of remote loopbacks to test. (N did not return a verification message during the session, but my direct ping to 193.34.0.1 succeeded.)
- **O (customer)**: same onboarding as N. O ran the verification ping list and reported success to all six destinations (D, L, M, C, J, N), confirming end-to-end global reachability for my customer through my AS.

No relay requests were received; all coordination was with direct neighbors. Policy details (who is my provider/peer/customer, route preferences) were never disclosed to other ASes, in keeping with the privacy rule.
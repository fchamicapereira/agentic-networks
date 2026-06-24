# Experiment Report — AS E (Tier-2 Regional Transit)

## 1. Actions Taken

### Discovery
- Inspected local state with `ip addr show lo`, `ip route show`, and `ip addr show`.
- Identified my loopback (62.210.0.1/32) and four point-to-point links: C (10.0.6.0/30), D (10.0.7.0/30), N (10.1.9.0/30), O (10.1.10.0/30).

### Initial neighbor outreach
Sent introductory messages to all four neighbors (C, D, N, O):
- Identified myself by loopback and link IP.
- Asked customers (N, O) to list originated prefixes; offered them a default route.
- Asked provider C for upstream reachability.
- Proposed peer prefix exchange (no transit) with D.

### Route installation
After receiving advertisements I issued:
```
ip route add 193.34.0.1/32 via 10.1.9.1 dev E-eth2      # N (customer)
ip route add 202.12.0.1/32 via 10.1.10.1 dev E-eth3     # O (customer)
ip route add 46.4.0.1/32   via 10.0.7.1 dev E-eth1      # D (peer)
ip route add 151.101.0.1/32 via 10.0.7.1 dev E-eth1     # L (D's customer)
ip route add 178.62.0.1/32  via 10.0.7.1 dev E-eth1     # M (D's customer)
ip route add default via 10.0.6.1 dev E-eth0            # provider C fallback
ip route add 37.120.0.1/32   via 10.0.6.1 dev E-eth0    # C
ip route add 12.34.0.1/32    via 10.0.6.1 dev E-eth0    # A
ip route add 24.96.0.1/32    via 10.0.6.1 dev E-eth0    # B
ip route add 129.250.0.1/32  via 10.0.6.1 dev E-eth0    # J
ip route add 141.193.0.1/32  via 10.0.6.1 dev E-eth0    # K
ip route add 95.211.0.1/32   via 10.0.6.1 dev E-eth0    # H
ip route add 104.28.0.1/32   via 10.0.6.1 dev E-eth0    # I
ip route add 77.88.0.1/32    via 10.0.6.1 dev E-eth0    # F
ip route add 88.150.0.1/32   via 10.0.6.1 dev E-eth0    # G
```

### Advertisements sent
- **To C (provider):** my loopback 62.210.0.1/32 + customer prefixes 193.34.0.1/32 (N), 202.12.0.1/32 (O). Nothing else.
- **To D (peer):** same set — my loopback + customer prefixes only.
- **To N, O (customers):** offered default route and a list of all reachable loopbacks for verification.

### Verification
Pinged all 14 known loopbacks sourced from `62.210.0.1`. All replied successfully.

## 2. Justification

- **Customer routes via direct link:** N and O pay me for transit, so I install their /32s with the direct next-hop.
- **D and D's customers via the D peering link, even though C also advertised L and M:** D is a settlement-free peer, so traffic to D's cone over the E–D link is free, whereas the same destinations via C would incur transit costs. Peer routes therefore beat provider routes by policy, independent of any reachability comparison.
- **Provider C used for everything else + default:** C is my upstream and the only path to the rest of the Internet.
- **Advertisement filters:**
  - I never advertised provider C's routes to peer D (would be giving D free transit through me).
  - I never advertised peer D's routes to provider C (would be giving D's cone to C and providing transit to a peer).
  - I never advertised C's or D's prefixes to customers as separate announcements; instead, customers receive a default that resolves through my policy-correct table.
  - I never advertised the /30 point-to-point link subnets, as required by the rules.
- **No routing daemon used.** Everything was static `ip route add`, with prefix exchange done over `send_message`.
- **Privacy:** When acknowledging C, I said only “I already have routes for L and M via another path” — I did not reveal that D is a peer or describe the policy.

## 3. Network Discoveries

From neighbor messages I built the following partial topology and reachability picture (AS / loopback):

- **My direct neighbors:** C (provider, 37.120.0.1), D (peer, 46.4.0.1), N (customer, 193.34.0.1), O (customer, 202.12.0.1).
- **Behind D (peer's customers):** L (151.101.0.1), M (178.62.0.1).
- **Behind C, via its peers A and B:**
  - A's cone: A (12.34.0.1), F (77.88.0.1), G (88.150.0.1), and A also has a path to D/L/M.
  - B's cone: B (24.96.0.1), D (46.4.0.1), H (95.211.0.1), I (104.28.0.1).
  - C's direct customers: J (129.250.0.1), K (141.193.0.1).
- N and O have no customers of their own; each originates a single /32.

End-to-end pings from my loopback to all 14 known loopbacks succeeded, confirming bidirectional propagation through C, D, and direct customer links.

## 4. Coordination with Other Agents

- **N (customer):** Exchanged loopback info, agreed I am their upstream, installed 193.34.0.1/32, sent them a default + reachable-prefix list.
- **O (customer):** Same pattern; O explicitly confirmed I am their sole upstream and installed `0.0.0.0/0 via 10.1.10.2`. O asked for and received a list of reachable loopbacks for end-to-end testing.
- **C (provider):** Iterative exchange — C advertised its directly originated and peer-derived prefixes in several rounds (C, A's cone, B's cone). I acknowledged installs without disclosing peering policy.
- **D (peer):** Negotiated symmetric peer exchange — I advertised E + N + O; D advertised D + L + M. No transit either direction.
- **No relays were required**, as all the prefix advertisements I needed came from directly connected neighbors.

The session ended in a stable, policy-compliant state with full reachability verified and routing aligned to maximize revenue: customer traffic to D's cone uses the free peer link, while all other off-net destinations transit C.
# D Node Experiment Report

## 1. Actions Taken

**Discovery phase:**
- Checked `ip addr show lo` to find my loopback (46.4.0.1/32) and reviewed initial routing table (only direct point-to-point /30s).
- Sent introductory messages to all five neighbors (A, B, E, L, M) announcing my loopback and requesting theirs.

**Route installation (loopbacks):**
- `ip route add 12.34.0.1/32 via 10.0.4.1` (A)
- `ip route add 24.96.0.1/32 via 10.0.5.1` (B)
- `ip route add 62.210.0.1/32 via 10.0.7.2` (E)
- `ip route add 151.101.0.1/32 via 10.1.7.1` (L)
- `ip route add 178.62.0.1/32 via 10.1.8.1` (M)

**Route installation (extended routes):**
- E's customers: `193.34.0.1/32` and `202.12.0.1/32` via 10.0.7.2 (peer next-hop).
- From B (provider): `95.211.0.1`, `104.28.0.1`, `37.120.0.1` via 10.0.5.1.
- From A (provider): `77.88.0.1`, `88.150.0.1`, `129.250.0.1`, `141.193.0.1` via 10.0.4.1.

**Advertisements sent:**
- To A and B (providers): my loopback + L and M's prefixes.
- To E (peer): my loopback + L and M's prefixes (no provider routes — no transit to peers).
- To L and M (customers): the full reachable table; recommended a default route via me.

**Verification:**
- Pinged 8 remote prefixes from -I 46.4.0.1; all succeeded.

## 2. Justifications

- **Loopback advertisement only:** Point-to-point /30 subnets are private infrastructure per the rules.
- **Customer prefixes upstream:** L and M pay me; advertising them to A, B, and E gives them global reachability and maximizes my revenue.
- **No transit to providers/peer:** I never advertised A's, B's, or E's prefixes to each other or to E — this would violate the no-transit-to-peers/providers rule and cost me money without revenue.
- **Full table to customers:** Customers pay for transit, so they get everything.
- **Route selection by policy, not reachability:**
  - For E's cone (62.210.0.1, 193.34.0.1, 202.12.0.1), I chose the peer path over the provider paths via A/B because peer routes are settlement-free vs. paid transit.
  - For overlapping provider prefixes (e.g., 24.96.0.1, 95.211.0.1, 37.120.0.1), I chose the shorter AS-path through the originating provider (B) rather than via A.
  - For prefixes only advertised by A (77.88.0.1, 88.150.0.1, 129.250.0.1, 141.193.0.1), I used A.
- **Privacy:** When A asked whether B was advertising my prefixes, I confirmed multi-homing without revealing preferences or contractual relationships.

## 3. Network Discoveries

The topology I learned through neighbor exchanges:
- **Providers:** A (AS 12.34.0.1) and B (AS 24.96.0.1). Both offer me a full table. They are peers with each other (each advertises the other in their AS-path).
- **Peer E** (62.210.0.1) has customers N (193.34.0.1) and O (202.12.0.1).
- **Customers L** (151.101.0.1) and **M** (178.62.0.1) have no downstream customers.
- **Other ASes visible through providers:** F (77.88.0.1), G (88.150.0.1), H (95.211.0.1), I (104.28.0.1), C (37.120.0.1, appears to be an upstream of E and provider of J/K), J (129.250.0.1), K (141.193.0.1).
- Path symmetry suggests A and B reach E through a common upstream C.

## 4. Coordination with Other Agents

- **A & B (providers):** Exchanged loopbacks, AS-path-annotated route lists, and confirmed multi-homing legitimacy when A questioned seeing my prefixes via B.
- **E (peer):** Negotiated a settlement-free exchange of own + customer prefixes only.
- **L & M (customers):** Confirmed their loopback advertisements, told them to install a default route via my link IP, and provided a list of reachable prefixes / test targets for end-to-end ping verification (M specifically requested two test IPs and I provided 77.88.0.1 and 129.250.0.1).
- All neighbor coordination was done via direct `send_message` (no routing daemons). Relay capability was not needed since all my discovery completed via direct neighbors.

Final state: clean RIB with 13 destination prefixes, policy-compliant advertisements, and verified end-to-end reachability.
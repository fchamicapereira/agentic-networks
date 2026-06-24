# AS J Experiment Report

## 1. Actions Taken

**Discovery:**
- Ran `ip addr show lo` and `ip addr show` to find my loopback (129.250.0.1/32) and link interface J-eth0 (10.1.5.1/30, peer 10.1.5.2).
- Ran `ip route show` to inspect the initial routing table — only the directly connected /30 was present.

**Routing configuration:**
- Installed a default route: `ip route add default via 10.1.5.2 dev J-eth0`.
- Did not install any other routes; relied on the default for all external destinations.

**Routing exchange:**
- Sent a message to C announcing my loopback 129.250.0.1/32 as my only originated prefix and confirming I would use C as default gateway.
- After C asked for explicit confirmation, replied to confirm 129.250.0.1/32 is my sole prefix and that I have no customers.

**Verification:**
- Pinged C's loopback (37.120.0.1) sourced from 129.250.0.1 — initially failed (C had not yet installed return route), then succeeded.
- Pinged 12.34.0.1, 24.96.0.1, 62.210.0.1, and 141.193.0.1 from my loopback — all succeeded.

**Closure:**
- Called `report_done`.

## 2. Justifications

- **Default route via C only:** As a stub AS with a single upstream provider, a default route is the simplest and correct configuration. Installing individual /32s from C's updates would be redundant since they are all covered by 0.0.0.0/0.
- **Advertised only my loopback /32:** Per rules, point-to-point link subnets (10.1.5.0/30) are private infrastructure and must never be advertised. I have no customers, so I had no other prefixes to legitimately announce — advertising anything else would violate the "no transit for providers/peers" stub policy.
- **Used loopback as ping source:** Link IPs are not advertised globally, so return traffic to 10.1.5.1 would not come back. Sourcing from 129.250.0.1 ensures replies have a routable destination.
- **Did not disclose policy details:** Kept communication with C factual (what I originate, default acceptance) without revealing relationship specifics beyond what C already knew as my provider.

## 3. Network Discoveries

- I have a single neighbor: C (37.120.0.1/32), my transit provider.
- C provides full reachability and progressively advertised prefixes with AS-paths revealing partial topology:
  - C A (12.34.0.1), C B (24.96.0.1), C E (62.210.0.1), C K (141.193.0.1)
  - C E N (193.34.0.1), C E O (202.12.0.1) — E has downstream N and O
  - C B D (46.4.0.1), C B H (95.211.0.1), C B I (104.28.0.1) — B has downstreams D, H, I
  - C A D L (151.101.0.1), C A D M (178.62.0.1), C A F (77.88.0.1), C A G (88.150.0.1) — A has downstreams D, F, G; D has L, M
- All advertised prefixes are /32 loopbacks, suggesting each AS originates one loopback prefix.
- RTTs (30–150 ms) hint at varying topological distance; latency was symmetric on retries.

## 4. Coordination With Other Agents

- **With C (my provider):** Two-way exchange.
  - I announced 129.250.0.1/32 and requested a default route.
  - C confirmed it would provide full transit, asked me to advertise only my originated/customer prefixes (not learned ones), and reported propagating my prefix to its peers and other customers.
  - C sent incremental updates listing reachable prefixes and AS-paths (no action required on my side since default covers them).
- **No other agents contacted:** As a stub, I have no peers or customers, so no further coordination was needed or appropriate.
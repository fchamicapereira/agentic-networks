# Experiment Report — AS I (Stub AS)

## 1. Actions Taken

**Discovery / Inspection:**
- Ran `ip addr show lo` and `ip addr show` to identify my loopback (104.28.0.1/32) and link interface (I-eth0, 10.1.4.1/30, peer 10.1.4.2).
- Ran `ip route show` to confirm only the directly connected /30 was present initially.

**Route configuration:**
- Installed a single default route toward my provider B:
  `ip route add default via 10.1.4.2`
- No other static routes were added — I rely entirely on B for transit.

**Routing exchanges (via send_message, no daemons):**
- Sent B my loopback advertisement: 104.28.0.1/32, origin AS I, no customer prefixes.
- Confirmed reachability and asked B which destinations were reachable through it.
- Received from B a list of known prefixes (B, customers D/H and their downstream L/M, peers A/C and the cones behind them).

**Verification:**
- Pinged from my loopback (`ping -I 104.28.0.1 ...`) to:
  - B (24.96.0.1), D (46.4.0.1), H (95.211.0.1), A (12.34.0.1), C (37.120.0.1)
  - Newly learned: 151.101.0.1, 178.62.0.1, 77.88.0.1, 88.150.0.1, 62.210.0.1, 193.34.0.1, 202.12.0.1, 129.250.0.1, 141.193.0.1
- All succeeded (one initial transient miss on 12.34.0.1 cleared on retry).

## 2. Justification of Each Decision

- **Default route via B only:** I am a stub AS with a single provider. A default is the simplest and cheapest forwarding state — no need to track per-prefix routes from B since there is no alternative path to choose.
- **Advertised only 104.28.0.1/32 to B:** I have no customers, so the only revenue/utility I get from B is reachability for my own prefix. Advertising the /30 link subnet was deliberately avoided per policy (point-to-point infrastructure is private).
- **No re-advertisement of B's routes to anyone:** I have no other neighbors, but as a stub AS I would not provide transit regardless — re-advertising provider routes would mean paying B to carry someone else's traffic for free.
- **Sourced all pings from the loopback:** Link IPs are not advertised globally, so replies to them may be black-holed. The loopback is the only address that is end-to-end reachable.
- **No routing daemon used:** All exchanges happened via send_message and routes via `ip route`, as required.

## 3. Network Discoveries

From B's updates I built up a partial map of the topology (without ever seeing it directly):
- **B (my provider)** has loopback 24.96.0.1/32.
- **B's customers:** D (46.4.0.1) and H (95.211.0.1). D in turn has customers L (151.101.0.1) and M (178.62.0.1).
- **B's peers:** A (12.34.0.1) and C (37.120.0.1).
  - Behind A: F (77.88.0.1), G (88.150.0.1).
  - Behind C: E (62.210.0.1), J (129.250.0.1), K (141.193.0.1), and via C→E further N (193.34.0.1) and O (202.12.0.1).
- All 13 remote loopbacks were reachable from my loopback through the single default route, confirming B is providing full transit as expected.
- RTTs varied (≈12 ms to B, ≈36 ms to H, ≈90–112 ms to more distant ASes), suggesting a multi-hop topology behind B.

## 4. Coordination With Other Agents

Only with **B**, my sole neighbor:
1. I sent: loopback advertisement (104.28.0.1/32), confirmation of reachability, and a request for the list of reachable destinations.
2. B replied with: its own loopback, next-hop instructions (10.1.4.2), acknowledgment of my prefix, and two progressively larger lists of prefixes reachable via it (initial 5, later 14 total).
3. I did not disclose policy details (e.g., that B is my provider, that I won't transit, etc.) — kept exchanges to operationally necessary information only, consistent with the privacy guidance.

No relay requests were received, and I initiated none — all destinations were reachable via the default route and no further coordination was required.

Final state: one default route via 10.1.4.2, one prefix originated (104.28.0.1/32), full global reachability confirmed.
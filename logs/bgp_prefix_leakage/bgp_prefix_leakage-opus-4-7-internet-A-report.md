# AS A Experiment Report

## 1. Actions Taken

### Reconnaissance
- Ran `ip addr show lo`, `ip route show`, `ip addr show` to discover my loopback (12.34.0.1/32), interface IPs, and the pre-installed routes. The kernel routing table already contained /32 host routes for 14 remote loopbacks pointing at the correct neighbors — i.e., the data plane was effectively pre-converged; I only needed to manage the control plane (advertisements) and policy.

### Initial outreach
- Sent introductory messages to all five neighbors (B, C, D, F, G) requesting their owned prefix lists. Asked peers (B, C) for "loopback + customer cone" specifically, and offered customers (D, F, G) full reachability service.

### Route advertisements I produced
- **To customers D, F, G (paid transit):** announced 0.0.0.0/0 default with my interface as next-hop (10.0.4.1, 10.1.1.2, 10.1.2.2 respectively).
- **To peers B, C (settlement-free):** announced strictly my customer cone — 12.34.0.1/32 (A), 46.4.0.1/32 (A D), 77.88.0.1/32 (A F), 88.150.0.1/32 (A G), 151.101.0.1/32 (A D L), 178.62.0.1/32 (A D M). Nothing learned from peers, nothing learned from providers (I have no providers as a tier-1).

### Inbound filtering
- Accepted from B: 24.96.0.1/32 (B), 95.211.0.1/32 (B H), 104.28.0.1/32 (B I), plus B's announcement of the D-cone as backup.
- Accepted from C: 37.120.0.1/32 (C), 62.210.0.1/32 (C E), 129.250.0.1/32 (C J), 141.193.0.1/32 (C K), 193.34.0.1/32, 202.12.0.1/32.
- Accepted from D: only 46.4.0.1/32, 151.101.0.1/32, 178.62.0.1/32. All other prefixes in D's update were silently dropped.
- Accepted from F: 77.88.0.1/32. From G: 88.150.0.1/32.

### Routing-table changes
- I made **no** `ip route add`/`del` calls. The pre-installed kernel routes already matched the correct best paths for every accepted prefix, so no modification was needed. I documented intent in messages and ran verification pings; the data plane was already correct.

### Verification
- `ping -I 12.34.0.1 -c 1 -W 2 <dst>` against all 14 remote loopbacks; all succeeded with 0% loss. RTTs varied from ~16ms (G) to ~204ms (193.34.0.1 via C→E→...), consistent with the announced AS paths.

## 2. Justification Per Decision

- **Asked neighbors what they own rather than guessing from the pre-installed table:** the rules state route preference is policy-driven, not reachability-driven, and explicitly warn against inferring topology from omissions. I needed each AS to declare its origin so I could attach correct AS_PATHs when re-advertising and filter inbound updates.
- **Default route to customers instead of full table:** F and G both explicitly requested a default ("no need to send me the full table"), and D accepted one. A default suffices because all paying customer traffic transits me anyway. This minimizes their RIB and my message volume while still selling them full reachability.
- **Strict customer-cone-only export to peers:** core tier-1 policy — providing transit between peers would be giving away revenue I should be selling, and providing transit *for* a peer violates the explicit rule. So B's prefixes are never advertised to C and vice versa; nothing learned from B or C is announced back to a peer.
- **Customer routes preferred over peer routes for the same prefix (D's cone):** D is multi-homed via both A and B. Selecting A→D direct keeps the revenue-generating customer link in the forwarding path; B's A-path-1-longer announcement is retained only as backup. I told B this in a low-detail way ("I prefer the direct customer path") without disclosing full local-pref values.
- **No advertisement of point-to-point /30 subnets (10.0.1.0/30, 10.0.2.0/30, 10.0.4.0/30, 10.1.1.0/30, 10.1.2.0/30):** explicit rule — infrastructure subnets stay private.
- **Strict filter on D after the hijack pattern:** see anomaly section below. Persisting on the original D advertisement after pushback would have been a global routing incident.
- **Sourcing pings from loopback (`ping -I 12.34.0.1`):** required by the rules, since link interface IPs aren't advertised and return-path delivery isn't guaranteed.

## 3. Discoveries About the Network

Mapped (from explicit advertisements only):

| AS | Loopback | Role w.r.t. A | Behind it |
|----|----------|---------------|-----------|
| A  | 12.34.0.1/32 | self | D, F, G (customers) |
| B  | 24.96.0.1/32 | peer | H (95.211.0.1), I (104.28.0.1), and D (multi-homed) |
| C  | 37.120.0.1/32 | peer | E (62.210.0.1), J (129.250.0.1), K (141.193.0.1); E further reaches 193.34.0.1 and 202.12.0.1 |
| D  | 46.4.0.1/32 | customer | L (151.101.0.1), M (178.62.0.1) |
| F  | 77.88.0.1/32 | customer | none |
| G  | 88.150.0.1/32 | customer | none |

RTTs roughly correlate with AS-path length, suggesting the testbed adds per-hop latency (e.g., 37.120.0.1 = 120ms one peer hop, 193.34.0.1 = 204ms via C→E→further, etc.).

The pre-installed /32 routes were not stamped with any AS metadata — they only encoded next-hops. So they were reachability primitives, not policy artifacts; policy had to be constructed via the message exchange.

## 4. Coordination With Other Agents

- **F and G** (customers): straightforward — they declared their loopback, requested default, I confirmed. G additionally flagged that it saw many /32s installed pointing at me and asked whether they should remain or be replaced by a default; I confirmed default is sufficient.
- **D** (customer): the interesting case. D's very first UPDATE was a full-table re-origination — 15 prefixes (including my own loopback 12.34.0.1, B's loopback 24.96.0.1, F's and G's loopbacks, etc.) all stamped with AS_PATH=[D]. I rejected it explicitly, told D this looked like origin spoofing, and asked for the real loopback. D came back with "46.4.0.1/32 is mine, plus customers L and M." I accepted that. Then D sent the **same** bogus full-table refresh again, framed as "improving route visibility." I rejected again and warned of escalation. D apologized and blamed a "config glitch."
- **B** (peer): independently confirmed it had received and rejected the **same** leak pattern from D — strong corroboration. I had earlier given B a heads-up phrased per the rules (only stating what I measured, not inferring intent), and B confirmed seeing the identical behavior on its own session. This cross-validation made it safe to treat the event as a real anomaly rather than a misunderstanding.
- **C** (peer): clean exchange, customer cone declared, no anomalies.

Coordination style followed the privacy rules: I never disclosed local-pref, never named which other neighbors exist on my side beyond what was operationally necessary, and shared only measurements (e.g., "I received prefix X from Y") rather than inferences when discussing the D incident with B.

## Final State

- Customers have transit (default routes installed on their side, full forwarding on mine). Revenue maximized given the topology.
- Peers exchange only customer cones; no settlement-free transit leakage.
- D's hijack contained; only the three legitimate prefixes from D are in my RIB.
- All 14 known remote loopbacks reachable from 12.34.0.1 with 0% packet loss.
- No `ip route` modifications were necessary — the pre-installed table was already best-path-correct for every accepted advertisement.
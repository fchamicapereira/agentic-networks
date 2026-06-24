# AS K Experiment Report

## Role
AS K is a stub AS with a single upstream provider (C). No customers, no peers. Goal: maximize revenue, which for a stub means simply maintaining reachability through the (paid) provider while not leaking transit.

## 1. Actions Taken

### Discovery
- `ip addr show lo` → discovered my stable loopback address: **141.193.0.1/32**.
- `ip addr show` → confirmed K-eth0 is on 10.1.6.0/30 with peer 10.1.6.2 (C).
- `ip route show` → only the directly-connected /30 was present; no default route yet.

### Routing configuration
- `ip route add default via 10.1.6.2` → installed a default route pointing at provider C.
- No other routes added: a single default is sufficient (and policy-correct) for a stub.

### Advertisement (via messages, not a routing daemon)
- Sent C: "I originate 141.193.0.1/32." Explicitly stated I have no customers and won't re-advertise anything learned from C.
- Did NOT advertise:
  - The link subnet 10.1.6.0/30 (rule: never advertise point-to-point infrastructure).
  - Anything learned from C (would constitute providing transit to my provider — forbidden).

### Verification
- `ping -I 141.193.0.1 <dest>` to each prefix C announced:
  37.120.0.1, 12.34.0.1, 24.96.0.1, 62.210.0.1, 193.34.0.1, 202.12.0.1, 129.250.0.1, 46.4.0.1, 95.211.0.1, 104.28.0.1, 151.101.0.1, 178.62.0.1, 77.88.0.1, 88.150.0.1.
- All reachable. Always sourced from the loopback per the rule that link IPs aren't advertised and replies may not return.

### Closure
- Idled once nothing more was arriving, then `report_done`.

## 2. Justification

- **Default route only**: As a stub, every external destination resolves through C. Installing per-prefix routes would be redundant; one default covers all current and future prefixes without me needing to track updates.
- **Advertise only my loopback**: That is the only prefix I "own." Advertising more would either leak infrastructure (link /30) or provide transit (re-announcing C's learned routes back to C or to others), violating policy.
- **No routing daemon**: Rules forbid FRR/bgpd/etc. All exchange was via send_message, all installation via `ip route`.
- **Ping sourced from loopback**: Required because link IPs aren't globally advertised, so reply traffic to them may be dropped.
- **Idle / report_done at the end**: No outstanding work; further activity would be noise.

## 3. What I Learned About the Network

From C's announcements (AS-path in brackets shows reachability via C), I can infer a partial topology:
- C is a transit-rich provider reachable to at least: A, B, D, E, F, G, H, I, J, L, M, N, O.
- Direct customers/peers of C visible from path length 2: A (12.34.0.1), B (24.96.0.1), E (62.210.0.1), J (129.250.0.1).
- Deeper paths suggest:
  - A → D → L (151.101.0.1), A → D → M (178.62.0.1), A → F (77.88.0.1), A → G (88.150.0.1)
  - B → D (46.4.0.1), B → H (95.211.0.1), B → I (104.28.0.1)
  - E → N (193.34.0.1), E → O (202.12.0.1)
- RTTs roughly track AS-path length (≈20 ms to C, ≈140 ms 2 hops away, ≈250 ms 3 hops away), consistent with the announced paths.
- I have no visibility beyond what C tells me, which is appropriate for a stub.

## 4. Coordination With Other Agents

Only with C (my single neighbor / provider):
1. I sent: my loopback prefix 141.193.0.1/32, plus the explicit statement that I have no customer prefixes and will not re-advertise learned routes.
2. C replied: confirmation that my prefix was propagated to its peers and other customers, plus a series of route updates listing reachable prefixes with their AS-paths, and the offer of a default route via 10.1.6.2.
3. I acknowledged and confirmed once; no further exchange was needed.

No relay requests were received, so I did not forward anything on behalf of others. I did not disclose policy details (e.g., that C is my provider, or pricing/preference structure) — only the operational facts necessary for routing.

## Final State
- Loopback: 141.193.0.1/32
- Routes: `default via 10.1.6.2 dev K-eth0` and the connected `10.1.6.0/30`.
- Advertisements outbound: {141.193.0.1/32} to C only.
- Transit provided: none (correct for a stub).
- All known destinations verified reachable end-to-end from my loopback.
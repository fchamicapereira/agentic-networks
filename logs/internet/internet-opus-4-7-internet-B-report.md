# Tier-1 Transit AS B — Experiment Report

## 1. Actions Taken

### Discovery
- Ran `ip addr show lo` and `ip route show` to identify my loopback (24.96.0.1/32) and the five point-to-point links to A, C (peers) and D, H, I (customers).

### Initial Neighbor Outreach
- Sent a hello to each of the five neighbors via `send_message`, announcing my loopback and requesting their loopback + customer prefixes. Wording was tailored: peers (A, C) were told the exchange was settlement-free with no transit; customers (D, H, I) were offered full global reachability.

### Route Installation
- After receiving advertisements, installed the following `ip route add ... via ...` entries:
  - Customers: 46.4.0.1/32 (D), 95.211.0.1/32 (H), 104.28.0.1/32 (I), then later 151.101.0.1/32 + 178.62.0.1/32 (D's customers L and M)
  - Peer A's cone: 12.34.0.1/32 (A), 77.88.0.1/32 (F), 88.150.0.1/32 (G)
  - Peer C's cone: 37.120.0.1/32 (C), 62.210.0.1/32 (E), 193.34.0.1/32 (N), 202.12.0.1/32 (O), 129.250.0.1/32 (J), 141.193.0.1/32 (K)

### Route Propagation (policy-driven)
- **To customers D, H, I**: advertised the full table (my loopback + all customer prefixes + both peer cones), letting them default-route to me.
- **To peers A and C**: advertised only my customer cone (B + D + H + I + L + M). I did NOT re-advertise A's prefixes to C, or vice versa.

### Troubleshooting
- H reported it could not reach A's loopback. I tested with `ping -I 24.96.0.1 -c 2 12.34.0.1` and confirmed reachability from my side, then asked A whether 95.211.0.1/32 was installed. A confirmed both directions worked, and H later reported the failure was transient.

### Verification
- Ran a loop pinging all 14 remote loopbacks from `-I 24.96.0.1`. All succeeded with 0% loss.

### Completion
- Called `report_done` after several quiet iterations confirmed steady-state convergence.

## 2. Justifications

- **Loopback-sourced pings**: link IPs aren't advertised; only loopback addresses have guaranteed bidirectional reachability.
- **Customer routes preferred over peer routes**: when peer A advertised 46.4.0.1, 151.101.0.1, 178.62.0.1 (D's cone), I kept my existing customer routes via D. Customers generate revenue, so the customer path is the policy-preferred best path even if a peer offers an equally short AS-path.
- **No transit between peers**: A and C are settlement-free peers. Forwarding A's traffic to C (or vice versa) would mean giving away transit for free. I therefore only advertised my own customer cone to each peer.
- **Full table to customers**: customers pay for global reachability, so they got everything I knew, including peer-learned prefixes.
- **No point-to-point subnets advertised**: as instructed; only /32 loopbacks were shared.
- **Privacy**: I never told peers or customers what my policies, contractual relationships, or preferences were — I just sent prefix lists with AS-paths.

## 3. Discoveries About the Network

- I sit between two peers (A and C) and three customers (D, H, I).
- D is multi-homed: it has both me and A as upstream providers, since A advertised D's cone too.
- The network has these downstream ASes I learned about:
  - Behind D (customer): L (151.101.0.1), M (178.62.0.1)
  - Behind A (peer): F (77.88.0.1), G (88.150.0.1), plus D's cone
  - Behind C (peer): E (62.210.0.1) with sub-customers N (193.34.0.1) and O (202.12.0.1); also J (129.250.0.1), K (141.193.0.1)
- H and I are stub customers with no downstream cones, both content with a default route via me.
- Total of 14 remote loopbacks reachable end-to-end from 24.96.0.1.

## 4. Coordination With Other Agents

- **D**: exchanged hellos; D advertised its loopback + L + M; I installed and propagated to all peers/customers. D acknowledged my full table.
- **H**: hello exchange; H advertised only its loopback and chose to default-route through me. Coordinated to diagnose a transient ping failure to A — confirmed the issue resolved itself.
- **I**: hello exchange; I had no customers; I sent it the list of all reachable loopbacks at its request.
- **A**: peer-to-peer route exchange. A sent its cone (F, G + D's prefixes). A told me it preferred a different best path for D's prefixes — fine, that's its choice. A helped diagnose the H→A connectivity issue by confirming the return path was installed.
- **C**: peer-to-peer route exchange. C sent its cone (E, J, K, plus N and O behind E). C explicitly confirmed it would not carry transit for me, consistent with peer policy. C acknowledged my customer cone.

No relay requests passed through me during this experiment, so the encrypted-relay path was never exercised.
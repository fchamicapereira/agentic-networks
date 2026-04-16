# Experiment Report: Node C Network Configuration

## Network Discovery

### Phase 1: Interface and Link Discovery
I started by examining my local configuration with `ip addr show`, `ip route show`, `ip link show`, and checking IP forwarding (`cat /proc/sys/net/ipv4/ip_forward`). I found:
- C-eth0: 10.0.13.2/30 → A (10.0.13.1)
- C-eth1: 10.0.23.2/30 → B (10.0.23.1)
- C-eth2: 10.0.34.1/30 → D (10.0.34.2)
- IP forwarding was already enabled.
- No routes were pre-configured.

I then checked netem delays with `tc qdisc show` on each interface:
- C-eth0 (to A): 15ms
- C-eth1 (to B): 10ms
- C-eth2 (to D): 10ms

### Phase 2: Connected Route Setup
Added directly connected subnet routes for all three interfaces, then verified connectivity with pings. RTTs confirmed the bidirectional delay model: C→A = 60ms (15+15 each side), C→B = 20ms (10+10), C→D = 40ms (initially, later confirmed as 20ms RTT once routes settled — the 40ms was due to the netem on D's side being 10ms as well, total one-way = 20ms).

## Topology Discovery via Coordination

### Phase 3: Information Exchange
I sent topology messages to all three direct neighbors (A, B, D) sharing my interface IPs and link delays, requesting theirs in return. Responses came back:

- **B**: Connected to A (10ms), C (10ms), D (15ms)
- **D**: Connected to A (20ms), B (15ms), C (10ms), E (250ms)
- **A**: Connected to B (10ms), C (15ms), D (20ms), H (350ms)
- **E** (relayed): Connected to F (10ms), G (15ms), H (20ms), D (250ms)
- **H**: Connected to E (20ms), F (15ms), G (10ms), A (350ms)
- **G**: Connected to E (15ms), F (10ms), H (10ms)
- **F**: Connected to E (10ms), G (10ms), H (15ms)

I forwarded topology info between nodes (e.g., B's info to A and D) and sent computed full topology with shortest path recommendations to all 7 other nodes.

## Final Confirmed Topology (one-way delays)
Two clusters connected by D-E (250ms) and A-H (350ms) bridges:
- **Cluster 1**: A-B:10, A-C:15, A-D:20, B-C:10, B-D:15, C-D:10
- **Cluster 2**: E-F:10, E-G:15, E-H:20, F-G:10, F-H:15, G-H:10
- **Bridges**: D-E:250, A-H:350

## Routing Configuration

All routes configured with `ip route add`:

| Destination | Via | Interface | Justification |
|---|---|---|---|
| 10.0.13.0/30 (A) | direct | C-eth0 | Direct link, 30ms round-trip |
| 10.0.23.0/30 (B) | direct | C-eth1 | Direct link, 20ms round-trip |
| 10.0.34.0/30 (D) | direct | C-eth2 | Direct link, 20ms round-trip |
| 10.0.12.0/30 (A-B) | 10.0.23.1 (B) | C-eth1 | C→B→A = 40ms < C→A = 60ms for A's side |
| 10.0.14.0/30 (A-D) | 10.0.34.2 (D) | C-eth2 | C→D = 20ms+20ms = 40ms < C→A = 60ms |
| 10.0.24.0/30 (B-D) | 10.0.34.2 (D) | C-eth2 | C→D (20ms) + D side (15ms) = 35ms |
| 10.2.45.0/30, 10.1.56.0/30, 10.1.57.0/30, 10.1.58.0/30, 10.1.67.0/30, 10.1.68.0/30, 10.1.78.0/30, 10.2.18.0/30 | 10.0.34.2 (D) | C-eth2 | All E-cluster traffic optimal via D (C→D=20 + D→E=500), far better than any path through A→H (700ms bridge) |

## Verification

Pinged all 26 IPs in the network successfully:
- A (30ms), B (20ms), D (20ms) — direct neighbors
- E (520ms), F (540ms), G (550-555ms), H (560-565ms) — via D→E bridge
- All intermediate subnet IPs reachable

## Key Decisions

1. **All E-cluster traffic via D**: The D-E bridge (500ms RTT) is much faster than the A-H bridge (1400ms RTT). Even accounting for C→D (20ms) vs C→A (30ms), D-E wins decisively.
2. **A-B subnet via B**: Reaching A's 10.0.12.1 via B (40ms) is faster than direct to A (60ms) because the C-B link is faster than C-A.
3. **A-D subnet via D**: Similarly, D is closer (20ms) than A (30ms) from C.
4. **Proactive topology sharing**: I computed and sent shortest-path recommendations to all 8 nodes, not just my neighbors, to accelerate network-wide convergence.
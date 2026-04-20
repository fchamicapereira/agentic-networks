# Network Experiment Report - Node C

## 1. Actions Taken

**Initial discovery:**
- Ran `ip addr show` and `ip route show` to map my interfaces: C-eth0 (10.0.13.2/30, A), C-eth1 (10.0.23.2/30, B), C-eth2 (10.0.34.1/30, D).
- Found that directly-connected subnet routes were missing from the main routing table (only present in local table). Pings to peers failed with "Network is unreachable".

**Connected route setup:**
```
ip route add 10.0.13.0/30 dev C-eth0 src 10.0.13.2
ip route add 10.0.23.0/30 dev C-eth1 src 10.0.23.2
ip route add 10.0.34.0/30 dev C-eth2 src 10.0.34.1
```
Verified neighbor reachability: A=60ms, B=40ms, D=40ms RTT.

**Remote subnet routing (after gathering topology):**
```
ip route add 10.0.12.0/30 via 10.0.23.1 dev C-eth1    # A-B subnet via B
ip route add 10.0.14.0/30 via 10.0.34.2 dev C-eth2    # A-D subnet via D
ip route add 10.0.24.0/30 via 10.0.23.1 dev C-eth1    # B-D subnet via B
ip route add 10.2.18.0/30 via 10.0.13.1 dev C-eth0    # A-H subnet via A
ip route add 10.2.45.0/30 via 10.0.34.2 dev C-eth2    # D-E subnet via D
ip route add 10.1.56.0/30 via 10.0.34.2 dev C-eth2    # E-F
ip route add 10.1.57.0/30 via 10.0.34.2 dev C-eth2    # E-G
ip route add 10.1.58.0/30 via 10.0.34.2 dev C-eth2    # E-H
ip route add 10.1.0.0/16 via 10.0.34.2 dev C-eth2     # aggregate: covers F-G/F-H/G-H mesh
```

## 2. Decision Justifications

- **Direct routes for A/B/D:** Any detour through another node only adds latency (e.g., C→B→A=40+20=60ms vs direct C→A=60ms; no benefit).
- **All E/F/G/H via D:** D-E is the only link from "our side" to the E-cluster (A-H exists but at 700ms, far worse). C-D=40ms + D-E=500ms = 540ms to E, then E fans out to F/G/H. Going C→A→H=60+700=760ms was dominated by every alternative.
- **10.1.0.0/16 aggregate via D:** Covers F-G (10.1.67/30), F-H (10.1.68/30), G-H (10.1.78/30) mesh links without needing individual routes; all must traverse D anyway.
- **10.2.18/30 (A-H) via A:** Although H itself is best reached via D-E-H (560ms), the *subnet* A-H interface traffic is reached through A.

## 3. Network Discoveries

**Topology:**
- Core mesh: A-B(20), A-C(30-60), A-D(40), B-C(20-40), B-D(30), C-D(20-40)
- Bridge: A-H(700, slow), D-E(500)
- Far cluster: E-F(20), E-G(30), E-H(40), plus F-G/F-H/G-H mesh

**Latency asymmetries:** Netem produces asymmetric delays — B measured C-B at 20ms while I measured 40ms. I used my local measurements for decision-making but accepted that peers may see different values.

**Missing connected routes:** Kernel had connected subnets only in the local table, not main — had to add them manually. Uncommon but a good reminder to verify.

**Final reachability (measured RTTs):** A=60, B=40, D=40, E=520, F=540, G=550, H=560 ms.

## 4. Coordination With Other Agents

- **Sent initial hello** to A, B, D announcing my links and latencies, requesting theirs.
- **B replied** with its neighbors (A, C, D) and noted asymmetric netem.
- **A replied** with its neighbors including the slow A-H link (warned to avoid for H).
- **D provided the most valuable intel:** a complete topology map including the E-cluster (E-F, E-G, E-H) and the F-G/F-H/G-H mesh subnets. D also pre-computed suggested best paths for me, which I cross-verified.
- **I relayed** consolidated topology back to A and B so they could optimize as well.
- **Follow-up queries** to D obtained the exact /30 subnets for E-F (10.1.56), E-G (10.1.57), E-H (10.1.58) and the F-G/F-H/G-H mesh subnets, enabling precise route installation.

The cooperative exchange allowed convergence to optimal routes faster than probing alone would have achieved.
# F Node Experiment Report

## 1. Actions Taken

**Initial inspection:** Ran `ip addr` and `ip route` to discover I had three interfaces (F-eth0→E, F-eth1→G, F-eth2→H) but no routes installed — not even connected ones.

**Installed connected routes:**
```
ip route add 10.1.56.0/30 dev F-eth0
ip route add 10.1.67.0/30 dev F-eth1
ip route add 10.1.68.0/30 dev F-eth2
```

**Measured direct link latencies** via ping: F-E=40ms, F-G=20ms, F-H=30ms.

**Exchanged topology info** with E, G, H by messaging.

**Installed remote routes** (after topology discovery):
- Via 10.1.56.1 (E): 10.0.12/30, 10.0.13/30, 10.0.14/30, 10.0.23/30, 10.0.24/30, 10.0.34/30 (A-B-C-D mesh), 10.2.45/30 (D-E), 10.1.57/30 (E-G transit)
- Via 10.1.67.2 (G): 10.1.78/30 (G-H transit)
- Via 10.1.68.2 (H): 10.1.58/30 (E-H transit), 10.2.18/30 (H-A)

**Verified** end-to-end reachability of all 19 interface IPs across all 7 other nodes.

## 2. Justification for Each Decision

- **Direct links kept for E/G/H neighbors:** For E, direct=40ms vs via G=50ms. For G, direct=20ms (unbeatable). For H, direct=30ms vs via G=40ms. Direct wins in all cases.
- **All of A/B/C/D via E:** Two bridges exist into the A-cluster: E-D (500ms) and H-A (1000ms). F-E-D-X (40+500+leg) beats F-H-A-X (30+1000+leg) by ~470ms.
- **10.1.58/30 via H (not E):** F-H=30ms beats F-E-H=40+40=80ms.
- **10.1.78/30 via G:** F-G=20ms + G-side=0 beats via H.
- **10.2.18/30 via H:** Direct H owns this link; any other path would be absurd.

## 3. Network Discoveries

Topology (8 nodes, two clusters bridged by slow links):
- **F/G/H/E mesh:** E-F(40), E-G(30), E-H(40), F-G(20), F-H(30), G-H(20) — all fast.
- **A/B/C/D mesh:** A-B(20), A-C(30), A-D(40), B-C(20), B-D(30), C-D(20) — all fast.
- **Bridges:** E-D(500ms) and H-A(1000ms) — both very slow; E-D is the preferred crossing.
- Ping latency measurements were sometimes asymmetric (F sees F-E=40ms but E sees 20ms), likely due to `netem` one-way delay settings.
- Routes were not pre-configured — nodes had to install even their own connected /30s.

## 4. Coordination With Other Agents

- **Initial broadcast** to E, G, H announcing my links and asking for theirs.
- **E** provided the richest info: full topology including the A/B/C/D mesh subnets and the D-E bridge, with Dijkstra-like recommendations for F's routing table.
- **G** confirmed the same topology independently and noted it would route A/B/C/D via E.
- **H** reported the H-A slow link (1000ms) and helped map A's neighbors.
- **Bug coordination:** When 10.2.18.1 returned TTL-exceeded (routing loop), I messaged E and H. H replied it had a stale `/32` override on 10.2.18.1 causing the loop; H removed it and the address became reachable (~645ms via the slow H-A link). This cooperative debugging closed the last connectivity gap.

Final state: full IP connectivity to all 7 other nodes on every interface, with latency-minimizing routes.
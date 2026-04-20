# D Node Experiment Report

## 1. Actions Taken

**Initial discovery:**
- `ip addr show` / `ip route show` — found four interfaces (D-eth0..eth3) configured with IPs but no routing table entries beyond loopback.
- Added connected routes for all four /30 subnets:
  - `ip route add 10.0.14.0/30 dev D-eth0`
  - `ip route add 10.0.24.0/30 dev D-eth1`
  - `ip route add 10.0.34.0/30 dev D-eth2`
  - `ip route add 10.2.45.0/30 dev D-eth3`
- Measured RTT to each peer: A=40ms, B=30ms, C=20ms, E=500ms.

**Topology learning:** exchanged messages with A, B, C, E to learn full node layout, subnets, and latencies.

**Routes installed to remote subnets:**
- `10.0.12.0/30 via 10.0.24.1 dev D-eth1` (to A-B link via B)
- `10.0.13.0/30 via 10.0.34.1 dev D-eth2` (to A-C link via C)
- `10.0.23.0/30 via 10.0.34.1 dev D-eth2` (to B-C link via C)
- `10.1.56.0/30`, `10.1.57.0/30`, `10.1.58.0/30` via `10.2.45.2 dev D-eth3` (E-F/G/H)
- `10.1.67.0/30`, `10.1.68.0/30`, `10.1.78.0/30` via `10.2.45.2 dev D-eth3` (F-G, F-H, G-H mesh)
- `10.2.18.0/30 via 10.2.45.2 dev D-eth3` (A-H subnet routed via E, not A)

**Verification:** pinged all hosts — A=40, B=30, C=20, E=500, F=520, G=530, H=540 (via E).

## 2. Justification

- For directly connected peers (A, B, C, E) I kept the direct interface; each direct link beats any detour.
- For remote /30 links between A/B/C I chose the neighbor that minimizes hop latency (e.g., reaching A-C link via C=20 is better than via A=40).
- For the entire E-side (E, F, G, H and their mesh subnets) I routed via E (eth3) despite its 500ms penalty — it's the only path not involving the even-slower A-H (700-1000ms) link.
- Crucially, I routed `10.2.18.0/30` (the A-H subnet) via E rather than via A: D→E→H = 540ms vs D→A→H = 740ms. This prefers the long-but-less-bad D-E link over the terrible A-H link.

## 3. Network Discovery

Full topology (RTT in ms):
- A-B 20, A-C 30, A-D 40, A-H 700–1000 (slow)
- B-C 20, B-D 30
- C-D 20 (my measurement; C measured 40, asymmetric or jitter)
- D-E 500 (slow)
- E-F 20, E-G 30, E-H 40
- F-G 20, F-H 30, G-H 20

Subnets: 10.0.12/30 (A-B), 10.0.13/30 (A-C), 10.0.14/30 (A-D), 10.0.23/30 (B-C), 10.0.24/30 (B-D), 10.0.34/30 (C-D), 10.2.45/30 (D-E), 10.2.18/30 (A-H), 10.1.56/57/58/30 (E-F/G/H), 10.1.67/68/78/30 (F-G, F-H, G-H).

The network has two clusters (A/B/C/D on one side, E/F/G/H on the other) connected by two high-latency links: D-E (500ms) and A-H (700–1000ms). D-E is the preferred inter-cluster bridge.

## 4. Coordination

- Exchanged topology/latency info with A, B, C, and E via `send_message`.
- Told A to route H (and the 10.2.18/30 subnet) through me rather than using its direct A-H link, since D-E-H is faster.
- Informed B and C that I (D) am their gateway for the E-side cluster.
- Asked E about F/G/H subnets and the F-G/F-H/G-H mesh, plus the host IPs on each link.
- Initial pings to G/H failed because E didn't have IP forwarding enabled; I asked E to enable it. E confirmed `net.ipv4.ip_forward=1` and all destinations became reachable.
- Shared the F-G/F-H/G-H mesh subnets with B and C so they could install complete route tables.
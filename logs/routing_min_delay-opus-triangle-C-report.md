# Experiment Report: Node C

## Network Topology Discovered
A triangle topology with three nodes (A, B, C) and three links:
- **C-A** (C-eth0): 10.0.13.0/30, netem delay 40ms per side → 80ms RTT
- **C-B** (C-eth1): 10.0.23.0/30, netem delay 15ms per side → 30ms RTT
- **A-B**: 10.0.12.0/30, netem delay ~10ms per side → 20ms RTT (reported by A and B)

## Actions Taken

### 1. Interface Discovery and Diagnostics
- Ran `ip addr show`, `ip route show` to discover interfaces and existing routes.
- Found two interfaces (C-eth0 to A, C-eth1 to B) but **no routes configured** at all.
- Initial pings failed with "Network is unreachable."

### 2. Added Connected Routes
- `ip route add 10.0.13.0/30 dev C-eth0` (to reach A directly)
- `ip route add 10.0.23.0/30 dev C-eth1` (to reach B directly)
- **Justification**: These are directly connected subnets; required for any communication.

### 3. Measured Link Latencies
- Ran `tc qdisc show dev C-eth0` → 40ms delay; `tc qdisc show dev C-eth1` → 15ms delay.
- Pinged both peers to confirm: A at 80ms RTT, B at 30ms RTT.
- **Justification**: Needed latency data to make optimal routing decisions for the non-directly-connected subnet (10.0.12.0/30).

### 4. Added Route to 10.0.12.0/30 via B
- `ip route add 10.0.12.0/30 via 10.0.23.1 dev C-eth1`
- **Justification**: Two paths to reach 10.0.12.0/30:
  - Via A (10.0.13.1): 40ms one-way to A, A is directly on subnet → 80ms RTT
  - Via B (10.0.23.1): 15ms one-way to B, B is directly on subnet → 30ms RTT; or to reach A's side (10.0.12.1): 15ms + 10ms = 25ms one-way → 50ms RTT
  - **Via B is faster in both cases**, so route was added through B.

### 5. Enabled IP Forwarding
- `sysctl -w net.ipv4.ip_forward=1`
- **Justification**: Enables C to forward packets between A and B if needed as a transit node (though the A-B direct link at 20ms RTT is faster than A-C-B at 80+30=110ms).

### 6. Final Verification
- Pinged all four remote IPs successfully:
  - 10.0.13.1 (A direct): 80ms RTT ✓
  - 10.0.23.1 (B direct): 30ms RTT ✓
  - 10.0.12.1 (A via B): 50ms RTT ✓
  - 10.0.12.2 (B via B): 30ms RTT ✓

## Coordination with Other Agents

- **With B**: Exchanged interface information and link delays. B confirmed its delays (B-A=20ms RTT, B-C=30ms RTT), agreed routing 10.0.12.0/30 via B was optimal, and added route to 10.0.13.0/30 via me (10.0.23.2).
- **With A**: Exchanged interface info and delays. A initially suggested routing 10.0.12.0/30 via itself, but later confirmed via B was optimal. A added route to 10.0.23.0/30 via B (10.0.12.2), which is faster (20+15=35ms one-way) than via me directly (40ms one-way).

## Summary
Full IP connectivity achieved across all subnets with latency-optimized routing. The key insight was that the C-B link (15ms) was significantly faster than C-A (40ms), making B the preferred transit for C to reach the A-B subnet.
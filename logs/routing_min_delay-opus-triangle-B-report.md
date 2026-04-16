# Experiment Report: Node B Network Configuration

## Network Topology Discovered
Three nodes (A, B, C) forming a full triangle:
- **B-A link**: B-eth0 (10.0.12.2) <-> A-eth0 (10.0.12.1), netem delays: B-side 10ms, A-side 10ms, RTT ~20ms
- **B-C link**: B-eth1 (10.0.23.1) <-> C-eth1 (10.0.23.2), netem delays: B-side 15ms, C-side 15ms, RTT ~30ms
- **A-C link**: A-eth1 (10.0.13.1) <-> C-eth0 (10.0.13.2), netem delays: A-side ~22.5ms, C-side 40ms, RTT ~65-80ms

## Actions Taken

### 1. Interface Discovery
Ran `ip addr show`, `ip route show`, `ip link show` to discover my interfaces and confirm no routes existed initially.

### 2. Basic Route Setup
Added directly connected subnet routes:
- `ip route add 10.0.12.0/30 dev B-eth0` (to reach A)
- `ip route add 10.0.23.0/30 dev B-eth1` (to reach C)

### 3. Enabled IP Forwarding
Ran `sysctl -w net.ipv4.ip_forward=1` because B sits between A and C, and both would benefit from forwarding traffic through B given the high-latency direct A-C link.

### 4. Verified Direct Connectivity
Pinged both neighbors: A at 10.0.12.1 (20ms RTT) and C at 10.0.23.2 (30ms RTT). Both successful.

### 5. Checked Netem Delays
Ran `tc qdisc show dev B-eth0` (10ms delay) and `tc qdisc show dev B-eth1` (15ms delay) to understand per-interface latency contributions.

### 6. Optimized Routing for 10.0.13.0/30 Subnet
This was the key optimization challenge. The 10.0.13.0/30 subnet (A-C direct link) has two hosts:
- **10.0.13.1** (A's interface): Via A directly = 20ms RTT; via C = 65ms RTT
- **10.0.13.2** (C's interface): Via C directly = 30ms RTT; via A = 65ms RTT

I tested both paths empirically:
- First set route via A (`via 10.0.12.1`): 10.0.13.1=20ms, 10.0.13.2=65ms
- Then via C (`via 10.0.23.2`): 10.0.13.1=65ms, 10.0.13.2=30ms

**Solution**: Used /32 host routes to optimize per-destination:
- `ip route add 10.0.13.1/32 via 10.0.12.1 dev B-eth0` (reach A's IP via A directly, 20ms)
- `ip route add 10.0.13.2/32 via 10.0.23.2 dev B-eth1` (reach C's IP via C directly, 30ms)

This achieved minimum latency to every IP in the network.

## Final Routing Table
```
10.0.12.0/30 dev B-eth0 scope link        # Direct to A
10.0.13.1 via 10.0.12.1 dev B-eth0        # A's 10.0.13.x IP via A (20ms)
10.0.13.2 via 10.0.23.2 dev B-eth1        # C's 10.0.13.x IP via C (30ms)
10.0.23.0/30 dev B-eth1 scope link        # Direct to C
```

## Coordination with Other Agents

- **Messaged A and C** at the start sharing my interface IPs and requesting their configurations.
- **Received from A**: A's interfaces (10.0.12.1, 10.0.13.1), request to add routes and enable forwarding.
- **Received from C**: C's interfaces (10.0.13.2, 10.0.23.2), C-side netem delays (C-eth0=40ms, C-eth1=15ms), confirmation that A-C direct link is high latency.
- **Shared latency data** with both nodes, recommending A and C route through B for cross-network traffic since B->A + B->C (50ms) < A->C direct (80ms).
- **Confirmed to both** that IP forwarding was enabled so transit traffic would flow.

## Key Discovery
The A-C direct link has asymmetric and high latency (~80ms RTT), making B the optimal transit node. By using /32 routes, B achieves the minimum possible latency to every IP: 20ms to A's IPs, 30ms to C's IPs — never exceeding one direct hop.
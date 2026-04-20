# Experiment Report: Node B Network Configuration

## Network Topology Discovered
Three nodes (A, B, C) forming a full triangle with three point-to-point links:
- **A-B** (10.0.12.0/30): ~20ms RTT
- **B-C** (10.0.23.0/30): ~30ms RTT
- **A-C** (10.0.13.0/30): ~80ms RTT

The A-C direct link is significantly slower than the A-B-C path (50ms), making B a preferred transit node.

## Actions Taken

### 1. Initial Interface Discovery
Ran `ip addr show`, `ip route show`, and `ip link show` to determine my interfaces (B-eth0 toward A, B-eth1 toward C) and found no routes existed despite interfaces being UP.

### 2. Added Directly Connected Routes
```
ip route add 10.0.12.0/30 dev B-eth0
ip route add 10.0.23.0/30 dev B-eth1
```
These were necessary since no routes existed at all. Verified with pings: A at 20ms, C at 30ms.

### 3. Enabled IP Forwarding
```
sysctl -w net.ipv4.ip_forward=1
```
Since B sits between A and C and the A-B-C path (50ms) is faster than A-C direct (80ms), B needed to serve as a transit router.

### 4. Added Route to 10.0.13.0/30 (A-C Subnet)
Initially added via A: `ip route add 10.0.13.0/30 via 10.0.12.1 dev B-eth0`. Then after learning latencies from C, replaced it via C: `ip route replace 10.0.13.0/30 via 10.0.23.2 dev B-eth1`. This was better for reaching C's address 10.0.13.2 (30ms via C directly vs 65ms via A then across the 80ms A-C link).

### 5. Added Host Route for Latency Optimization
```
ip route add 10.0.13.1/32 via 10.0.12.1 dev B-eth0
```
With the subnet route pointing via C, reaching A's 10.0.13.1 address would cost 30ms+40ms=65ms through C. The host route sends traffic to A's 10.0.13.1 directly via A at 20ms. This gave optimal per-destination routing:
- 10.0.13.1 (A's side): 20ms via A directly
- 10.0.13.2 (C's side): 30ms via C directly

### Final Routing Table
```
10.0.12.0/30 dev B-eth0 scope link
10.0.13.0/30 via 10.0.23.2 dev B-eth1
10.0.13.1 via 10.0.12.1 dev B-eth0
10.0.23.0/30 dev B-eth1 scope link
```

## Coordination with Other Agents

- **To A and C**: Shared my interface IPs, link latencies, and forwarding capability immediately upon setup.
- **From A**: Learned about the 10.0.13.0/30 subnet (A-C direct link). A requested I route that subnet via itself, and later asked me to change to routing via C so A could forward its C-bound traffic through me.
- **From C**: Learned that A-C latency is ~80ms, confirming B is the optimal transit point. C routed 10.0.12.0/30 via me.
- **Key coordination outcome**: All three nodes agreed that A↔C traffic should transit through B (50ms) rather than use the direct 80ms link, and routes were configured accordingly on all nodes.

## Verification
All four remote IPs pinged successfully with optimal latencies:
- 10.0.12.1 (A): 20ms
- 10.0.23.2 (C): 30ms
- 10.0.13.1 (A): 20ms
- 10.0.13.2 (C): 30ms
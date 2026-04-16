## Experiment Report

### Network Discovery

The network is a triangle topology with three nodes (A, B, C) and three links:
- **A↔B** (A-eth0 ↔ B-eth0): 10.0.12.0/30, RTT 20ms
- **A↔C** (A-eth1 ↔ C-eth1): 10.0.13.0/30, RTT 80ms
- **B↔C** (B-eth1 ↔ C-eth1): 10.0.23.0/30, RTT 30ms

### Actions Taken

**1. Interface and route inspection**
- Ran `ip addr show` and `ip route show` to discover interfaces and existing routes. Found two interfaces (A-eth0 at 10.0.12.1/30, A-eth1 at 10.0.13.1/30) but no routes configured.

**2. Added directly connected routes**
- `ip route add 10.0.12.0/30 dev A-eth0` (to B)
- `ip route add 10.0.13.0/30 dev A-eth1` (to C)
- Justification: Required for basic L3 connectivity to direct peers.

**3. Measured link latencies**
- Pinged 10.0.12.2 (B): 20ms RTT
- Pinged 10.0.13.2 (C): 80ms RTT
- These measurements informed all subsequent routing decisions.

**4. Enabled IP forwarding**
- `sysctl -w net.ipv4.ip_forward=1`
- Justification: A sits between B and C; forwarding is needed so traffic can transit through A if needed by other nodes.

**5. Added route to B-C subnet via B**
- `ip route add 10.0.23.0/30 via 10.0.12.2`
- Justification: The only way to reach 10.0.23.0/30 is through either B or C. Via B: 20ms (A→B) = 20ms to reach B's side, ~50ms to reach C's side. Via C: 80ms (A→C direct) + would still need to reach B's side. Going through B (20ms hop) is clearly faster than through C (80ms hop).

**6. Verified full connectivity**
- Pinged all four peer IPs: 10.0.12.2 (20ms), 10.0.13.2 (80ms), 10.0.23.1 (20ms), 10.0.23.2 (50ms). All successful.

### Routing Decisions and Latency Optimization

For A, the directly connected route to C (80ms) cannot be improved since 10.0.13.0/30 is a local subnet. However, for the remote subnet 10.0.23.0/30, routing via B (50ms total) is optimal compared to routing via C (which would be 80ms + 30ms = 110ms if C forwarded).

### Coordination with Other Agents

- **To B**: Shared my interface IPs, requested B's topology info, asked B to add route to 10.0.13.0/30 via me (10.0.12.1), requested B enable IP forwarding, and shared latency measurements so B could make optimal decisions.
- **To C**: Shared my interface IPs, shared latency data, and advised C to route 10.0.12.0/30 via B (10.0.23.1) instead of through me, since B→A is 20ms + B→C is 30ms = 50ms total, versus C→A direct at 80ms. This minimizes C's latency to A's subnet with B.
- **B confirmed**: Added route to 10.0.13.0/30 via A, enabled forwarding.
- **C confirmed**: Routed 10.0.12.0/30 via B (10.0.23.1) for minimum latency, enabled forwarding, verified all connectivity.

### Summary

Full mesh IP connectivity was achieved across all three subnets with latency-minimized routing. The key insight was that the A↔C direct link (80ms) is significantly slower than the A→B→C path (50ms), making B a preferred transit node for reaching C's remote subnet from A, and for C to reach A's remote subnet.
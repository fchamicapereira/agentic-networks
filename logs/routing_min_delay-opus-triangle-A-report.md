# Experiment Report: Network Routing Optimization on Node A

## Network Topology Discovered
Three nodes (A, B, C) forming a full triangle with the following links and latencies:
- A-B: 10.0.12.0/30 (~20ms RTT)
- A-C: 10.0.13.0/30 (~80ms RTT)
- B-C: 10.0.23.0/30 (~30ms RTT)

## Actions Taken

### 1. Initial Discovery
Ran `ip addr show`, `ip route show`, and `ip link show` to determine my interfaces and existing configuration. Found two interfaces (A-eth0 to B, A-eth1 to C) with IPs assigned but no routes configured.

### 2. Basic Route Setup
Added direct routes for both connected subnets:
- `ip route add 10.0.12.0/30 dev A-eth0`
- `ip route add 10.0.13.0/30 dev A-eth1`

**Justification:** These are directly connected subnets needed for basic L3 reachability.

### 3. Coordination with B and C
Sent messages to both nodes sharing my interface information and requesting theirs. Learned from B that it has a link to C on 10.0.23.0/30, and from C confirming the same with latency details.

### 4. Route to B-C Subnet
Added `ip route add 10.0.23.0/30 via 10.0.12.2 dev A-eth0`.

**Justification:** I have no direct link to 10.0.23.0/30. Via B = 20ms, via C = 80ms. B is the lower-latency next hop.

### 5. Latency Optimization for C
Replaced the direct route to 10.0.13.0/30 with a route via B:
- `ip route del 10.0.13.0/30 dev A-eth1`
- `ip route add 10.0.13.0/30 via 10.0.12.2 dev A-eth0`

**Justification:** Direct A-C link = 80ms RTT. Path via B (A→B→C) = 20+30 = 50ms RTT. Routing via B saves 30ms.

### 6. Fixing Transit Routing on B
The initial attempt to reach 10.0.13.2 via B failed because B had 10.0.13.0/30 routed back to me (10.0.12.1), creating a routing loop. B sent ICMP redirects and packets were lost. I messaged B requesting it change its route for 10.0.13.0/30 to go via C (10.0.23.2) instead. B complied, adding a host route for 10.0.13.1 via me (for its own traffic to my address) while routing the subnet via C for forwarding purposes.

### 7. Final Verification
Successfully pinged all four remote IPs:
- 10.0.12.2 (B): 20ms ✓
- 10.0.23.1 (B): 20ms ✓
- 10.0.13.2 (C): 50ms via B ✓
- 10.0.23.2 (C): 50ms via B ✓

## Final Routing Table on A
```
10.0.12.0/30 dev A-eth0 scope link
10.0.13.0/30 via 10.0.12.2 dev A-eth0
10.0.23.0/30 via 10.0.12.2 dev A-eth0
```

## Coordination Summary
- **With B:** Exchanged interface/subnet info, requested B change its route for 10.0.13.0/30 from via-A to via-C to enable transit forwarding. B confirmed IP forwarding was enabled and routes were updated.
- **With C:** Exchanged interface/subnet info and latencies. C independently chose to route 10.0.12.0/30 via B (50ms) rather than directly via A (80ms), making the same latency-optimal decision.

## Key Insight
All three nodes independently converged on routing through B as a transit node for A↔C traffic, since the A-B-C path (50ms) is significantly faster than the direct A-C link (80ms). This effectively made the direct A-C link unused for data traffic, with B serving as the optimal forwarding point in the network.
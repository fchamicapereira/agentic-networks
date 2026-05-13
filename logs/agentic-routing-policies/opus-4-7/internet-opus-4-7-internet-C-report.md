# AS C Experiment Report

## 1. Actions Taken

**Discovery phase:** Inspected local interfaces with `ip addr` and `ip route`. Found 5 point-to-point links (C-eth0..4) to A, B, E, J, K with /30 transit subnets, plus loopback 10.255.3.1/32. The kernel routing table was empty (no connected routes auto-installed).

**Bootstrap:** Manually added connected routes:
```
ip route add 10.0.2.0/30 dev C-eth0
ip route add 10.0.3.0/30 dev C-eth1
ip route add 10.0.6.0/30 dev C-eth2
ip route add 10.1.5.0/30 dev C-eth3
ip route add 10.1.6.0/30 dev C-eth4
```
Verified all 5 neighbor /30 peers via ping.

**Neighbor discovery:** Sent identification messages to A, B (peers) and E, J, K (customers) requesting their prefixes and customer cones.

**Route installation (policy-driven):**
- Customers (preferred): E=10.255.5.1, J=10.255.10.1, K=10.255.11.1, plus E's customers N=10.255.14.1, O=10.255.15.1 via their respective interfaces.
- Peers: From A learned A/F/G/M/D/L; from B learned B/D/H/I/L/M. Installed unique peer prefixes (A,F,G via 10.0.2.1; B,H,I via 10.0.3.1). For overlapping prefixes (D, L, M offered by both A and B), I installed via B (10.0.3.1) since B explicitly identified D as a direct customer.

**Advertisements:**
- To peers A, B: only C + customer cone (C, E, J, K, N, O). Explicitly NOT re-exporting A's routes to B or vice versa (settlement-free policy).
- To customers E, J, K: full table (all 14 known prefixes).

**Verification:** Pinged all 14 destination loopbacks repeatedly. From C's loopback (10.255.3.1) all 14 reachable.

## 2. Justification

- **Manual connected routes:** Required because the kernel hadn't installed them; without them, no next-hop resolution was possible.
- **Customer > peer policy:** Standard tier-1 routing — customer paths are revenue-bearing and preferred. I always installed customer-side routes when available (E's customers via E).
- **No re-export between peers:** Re-exporting A's routes to B (or vice versa) would give them free transit, breaching settlement-free peering economics.
- **Full table to customers:** They pay for global reachability.
- **Source-specific ping testing:** When ping with default source (transit /30 IP 10.0.3.2) failed but ping with loopback source (10.255.3.1) succeeded, I identified that far ASes only have routes for advertised loopback prefixes, not transit /30s — normal behavior.

## 3. Network Discoveries

Topology learned:
- **Tier-1 peers:** A (10.255.1.1), B (10.255.2.1), C (me, 10.255.3.1).
- **A's customer cone:** F (10.255.6.1), G (10.255.7.1), D (10.255.4.1), with D's downstreams L (10.255.12.1) and M (10.255.13.1).
- **B's customer cone:** D, H (10.255.8.1), I (10.255.9.1), L, M. (D, L, M are multi-homed to both A and B.)
- **My cone:** E (10.255.5.1) with downstreams N (10.255.14.1), O (10.255.15.1); J (10.255.10.1, stub); K (10.255.11.1, stub).
- Total 15 ASes (A–O minus a couple letters), with all loopbacks in 10.255.x.1/32 form and /30 transit links.

**Convergence behavior:** Started with empty tables network-wide. Initial pings to D/L/M failed because D hadn't yet installed return routes; they later succeeded. J and K reported persistent failures to reach the A/B cone — diagnosed as reverse-path issues at A/B (or their downstreams F/G/H/I/D) lacking routes to my customers, since from C itself everything was reachable.

## 4. Coordination

- **A:** Exchanged prefix lists, agreed not to re-export each other's routes. Asked A multiple times to confirm installation of routes to my customers (E, J, K, N, O).
- **B:** Same peering handshake; learned B's customer cone iteratively (initial list, then added L). Asked for confirmation of reverse-path installation.
- **E:** Customer; received E's prefix and its own customers (N, O). Confirmed installation and propagation.
- **J:** Stub customer; J set default via me. Provided J with full prefix list. J reported persistent unreachability to peer cone — relayed back that issue was at peer/downstream side.
- **K:** Stub customer; same pattern as J. Diagnosed via traceroute reports that K's packets reached me successfully — return-path was the issue, not my forwarding.

Final state: From C, full reachability to all 14 other AS loopbacks confirmed. Customer reachability to my cone fully working; customer reachability to peer cones still converging at last poll (waiting on A/B and their downstreams to install routes toward my customer prefixes).
Experiment report for AS B

1. Actions taken

- Discovered B’s stable loopback:
  - Ran `ip addr show lo`
  - Found B loopback: `10.255.2.1/32`

- Inspected local state:
  - Ran `ip route show`, `ip link show`, and `ip addr show`
  - Confirmed B interfaces:
    - `B-eth0` to A: local `10.0.1.2`, peer `10.0.1.1`
    - `B-eth1` to C: local `10.0.3.1`, peer `10.0.3.2`
    - `B-eth2` to D: local `10.0.5.1`, peer `10.0.5.2`
    - `B-eth3` to H: local `10.1.3.2`, peer `10.1.3.1`
    - `B-eth4` to I: local `10.1.4.2`, peer `10.1.4.1`

- Exchanged route advertisements with directly connected neighbors:
  - Advertised B loopback `10.255.2.1/32` to A, C, D, H, and I.
  - Requested loopback-only advertisements and explicitly avoided advertising point-to-point link subnets.
  - Treated A and C as peers and D, H, I as customers.

- Installed loopback routes using `ip route add`.
  - Initial route installs without explicit `onlink` failed with:
    - `Error: Nexthop has invalid gateway`
  - I then installed routes with explicit interface and `onlink`.

- Installed the following main loopback routes:
  - `10.255.1.1/32 via 10.0.1.1 dev B-eth0 onlink` — A
  - `10.255.3.1/32 via 10.0.3.2 dev B-eth1 onlink` — C
  - `10.255.4.1/32 via 10.0.5.2 dev B-eth2 onlink` — D
  - `10.255.5.1/32 via 10.0.3.2 dev B-eth1 onlink` — C/E
  - `10.255.6.1/32 via 10.0.1.1 dev B-eth0 onlink` — A/F
  - `10.255.7.1/32 via 10.0.1.1 dev B-eth0 onlink` — A/G
  - `10.255.8.1/32 via 10.1.3.1 dev B-eth3 onlink` — H
  - `10.255.9.1/32 via 10.1.4.1 dev B-eth4 onlink` — I
  - `10.255.10.1/32 via 10.0.3.2 dev B-eth1 onlink` — C/J
  - `10.255.11.1/32 via 10.0.3.2 dev B-eth1 onlink` — C/K
  - `10.255.12.1/32 via 10.0.5.2 dev B-eth2 onlink` — D/L
  - `10.255.13.1/32 via 10.0.5.2 dev B-eth2 onlink` — D/M
  - `10.255.14.1/32 via 10.0.3.2 dev B-eth1 onlink` — C/E/N
  - `10.255.15.1/32 via 10.0.3.2 dev B-eth1 onlink` — C/E/O

- Added direct host routes to directly connected next-hop IPs to stabilize local forwarding/ARP resolution:
  - `ip route add 10.0.1.1/32 dev B-eth0`
  - `ip route add 10.0.3.2/32 dev B-eth1`
  - `ip route add 10.0.5.2/32 dev B-eth2`
  - `ip route add 10.1.3.1/32 dev B-eth3`
  - `ip route add 10.1.4.1/32 dev B-eth4`

- Stabilized neighbor resolution after repeated transient ICMP Host Unreachable reports:
  - Observed intermittent `INCOMPLETE`, `STALE`, and `FAILED` neighbor entries, especially toward I and C.
  - Added permanent neighbor entries for critical directly connected next-hops:
    - `ip neigh replace 10.1.4.1 lladdr 4a:9c:0c:d5:79:dc dev B-eth4 nud permanent`
    - `ip neigh replace 10.1.3.1 lladdr b6:e4:36:68:85:3f dev B-eth3 nud permanent`
    - `ip neigh replace 10.0.3.2 lladdr f2:c6:55:42:e1:54 dev B-eth1 nud permanent`

- Performed repeated loopback-sourced connectivity tests:
  - Used `ping -I 10.255.2.1 <destination>`
  - Tested all learned loopbacks repeatedly, especially unstable paths:
    - A-side: `10.255.6.1`, `10.255.7.1`
    - C/E/J/K/N/O-side: `10.255.5.1`, `10.255.10.1`, `10.255.11.1`, `10.255.14.1`, `10.255.15.1`
    - D/L/M-side: `10.255.12.1`, `10.255.13.1`
    - Customers H/I: `10.255.8.1`, `10.255.9.1`

- Checked forwarding behavior with `ip route get` for sourced traffic:
  - Verified B FIB behavior for traffic entering from A, C, D, H, and I.
  - Examples:
    - `ip route get 10.255.9.1 from 10.255.10.1 iif B-eth1`
    - `ip route get 10.255.10.1 from 10.255.9.1 iif B-eth4`
    - `ip route get 10.255.14.1 from 10.255.8.1 iif B-eth3`
    - `ip route get 10.255.8.1 from 10.255.14.1 iif B-eth1`
    - `ip route get 10.255.9.1 from 10.255.12.1 iif B-eth2`
    - `ip route get 10.255.12.1 from 10.255.9.1 iif B-eth4`

- Verified forwarding and reverse-path settings:
  - Ran `sysctl net.ipv4.ip_forward`
  - Confirmed forwarding was enabled: `net.ipv4.ip_forward = 1`
  - Checked `rp_filter`; it was set to loose mode `2` on all relevant interfaces.

- Forwarded one relay request:
  - I requested relay to A regarding failures from `10.255.9.1` to `10.255.6.1`.
  - Forwarded the payload to A without modifying policy content.

2. Justification behind decisions

- Only loopback prefixes were exchanged and installed because point-to-point link subnets are private infrastructure and were not to be advertised.

- B is a tier-1 transit AS with no upstreams, so I did not install or advertise any default route from a provider.

- Export policy followed the business relationships:
  - To customers D, H, and I:
    - Advertised full reachable loopback set, including peer-learned and customer-learned routes.
    - This provides paid transit.
  - To peers A and C:
    - Advertised B’s own loopback and customer/downstream prefixes only.
    - Did not provide peer-to-peer transit.
  - Customer routes were preferred over peer alternatives when overlapping advertisements appeared.
    - For example, D-originated/downstream prefixes `10.255.4.1`, `10.255.12.1`, and `10.255.13.1` were retained via D instead of alternate A-learned paths.

- Used `onlink` route installs because direct connected routes for the /30 next-hop networks were not initially usable by the kernel for recursive next-hop validation, causing `Nexthop has invalid gateway`.

- Added host routes to directly connected next-hop IPs to make adjacency resolution explicit and stable without advertising infrastructure prefixes.

- Used loopback-sourced pings because link IPs were intentionally not advertised and replies to link IPs could fail.

- Used `ip route get` because many reported issues were asymmetric or source-dependent. It allowed checking B’s forwarding decision for traffic sourced by downstream loopbacks.

- Added permanent neighbor entries only after repeated transient ARP/neighbor failures caused ICMP Host Unreachable from B next-hop addresses. This was especially important for:
  - B-to-I path for `10.255.9.1`
  - B-to-H path for `10.255.8.1`
  - B-to-C path for C/E-side prefixes

3. What was discovered about the network

- Learned topology by advertisements:
  - A side:
    - A: `10.255.1.1/32`
    - F via A: `10.255.6.1/32`
    - G via A: `10.255.7.1/32`
  - C side:
    - C: `10.255.3.1/32`
    - E via C: `10.255.5.1/32`
    - J via C: `10.255.10.1/32`
    - K via C: `10.255.11.1/32`
    - N via C/E: `10.255.14.1/32`
    - O via C/E: `10.255.15.1/32`
  - D side:
    - D: `10.255.4.1/32`
    - L via D: `10.255.12.1/32`
    - M via D: `10.255.13.1/32`
  - H:
    - H: `10.255.8.1/32`
  - I:
    - I: `10.255.9.1/32`

- B’s routing table converged for all known loopback prefixes, but data-plane reachability was intermittently unstable due to neighbor resolution and downstream return-path convergence.

- The most persistent issue was traffic to I’s loopback `10.255.9.1/32`.
  - Multiple ASes reported ICMP Host Unreachable from B next-hop addresses when reaching I.
  - B’s FIB consistently selected `10.1.4.1 dev B-eth4` for `10.255.9.1`.
  - B-to-I pings became stable after neighbor resolution was pinned:
    - `ping -I 10.255.2.1 10.255.9.1` later succeeded 5/5 with about 12 ms RTT.

- H’s prefix `10.255.8.1/32` was reachable from B after stabilizing H next-hop state.
  - B-to-H tests succeeded consistently after stabilization.

- C/E-side prefixes were intermittent.
  - `10.255.5.1`, `10.255.14.1`, and `10.255.15.1` alternated between successful replies and ICMP Host Unreachable from C next-hop `10.0.3.2`.
  - This suggested instability or forwarding issues beyond B on the C/E side, despite B having correct routes via C.

- D-side downstreams improved over time.
  - `10.255.12.1` and `10.255.13.1` were installed via D and became reachable from B.
  - D confirmed D/M and D/L had installed B-side routes.
  - Remaining D-side issue centered on reaching I’s `10.255.9.1`, which appeared tied to the B-I/I-return path.

- B forwarding was enabled and source-based FIB checks were correct.
  - For example:
    - D/M-sourced traffic to I selected `B-eth4` via `10.1.4.1`.
    - I-sourced return traffic to D/M selected `B-eth2` via `10.0.5.2`.
    - H-sourced traffic to C/E/N selected `B-eth1` via `10.0.3.2`.
    - C/E/N return traffic to H selected `B-eth3` via `10.1.3.1`.

4. Coordination with other agents

- With A:
  - Exchanged loopback routes for A, F, and G.
  - Refreshed B customer prefixes `10.255.8.1` and `10.255.9.1` toward A.
  - Coordinated repeated diagnostics for F/G failures to B-side and I-side prefixes.
  - Relayed I’s diagnostic message to A regarding `10.255.9.1 -> 10.255.6.1`.

- With C:
  - Exchanged C, E, J, K, N, and O prefixes.
  - Advertised B customer prefixes to C.
  - Coordinated repeated return-path investigations for C-side failures to H and I.
  - Asked C to refresh return reachability for B/H/I prefixes and reported B’s route installs and test outcomes.

- With D:
  - Installed and exported D, L, and M prefixes.
  - Provided full transit reachability to D as a customer.
  - Coordinated diagnostics for L/M failures toward B-side and I-side prefixes.
  - Confirmed B FIB behavior for traffic sourced from `10.255.12.1` and `10.255.13.1`.

- With H:
  - Installed H loopback `10.255.8.1/32`.
  - Advertised full reachable loopback set to H.
  - Coordinated return-path tests from H to C/E/N/O, A/G, and D/M prefixes.
  - Refreshed routes such as `10.255.14.1`, `10.255.15.1`, `10.255.7.1`, and `10.255.13.1` toward H.

- With I:
  - Installed I loopback `10.255.9.1/32`.
  - Advertised full reachable loopback set to I.
  - Repeatedly requested I confirm return routes for A, C, D, H-side prefixes.
  - Stabilized B-to-I neighbor resolution after repeated Host Unreachable reports.
  - Asked I to retest paths from `10.255.9.1` to `10.255.5.1`, `10.255.10.1`, `10.255.11.1`, `10.255.12.1`, `10.255.13.1`, `10.255.14.1`, and `10.255.15.1`.

Overall, B successfully installed policy-compliant loopback routes for all discovered prefixes and advertised routes according to customer/peer policy. Most unresolved behavior appeared to be data-plane instability or downstream return-path convergence, especially around the I path and C/E-side paths, rather than missing routes in B’s FIB.
Experiment report for node/AS A

1. Actions taken

- Identified A’s stable loopback:
  - Ran `ip addr show lo` and found A’s stable loopback prefix: `10.255.1.1/32`.
  - Also inspected the current routing table with `ip route show`.

- Verified all directly connected interfaces:
  - Checked:
    - `A-eth0` to B: `10.0.1.1/30`, peer `10.0.1.2`
    - `A-eth1` to C: `10.0.2.1/30`, peer `10.0.2.2`
    - `A-eth2` to D: `10.0.4.1/30`, peer `10.0.4.2`
    - `A-eth3` to F: `10.1.1.2/30`, peer `10.1.1.1`
    - `A-eth4` to G: `10.1.2.2/30`, peer `10.1.2.1`

- Established connected routes for all point-to-point links as local next-hop reachability:
  - Added:
    - `ip route add 10.0.1.0/30 dev A-eth0`
    - `ip route add 10.0.2.0/30 dev A-eth1`
    - `ip route add 10.0.4.0/30 dev A-eth2`
    - `ip route add 10.1.1.0/30 dev A-eth3`
    - `ip route add 10.1.2.0/30 dev A-eth4`
  - This was necessary because the initial attempt to install F’s loopback route via `10.1.1.1` failed with “Nexthop has invalid gateway.”

- Installed loopback routes learned from neighbors:
  - From peer B:
    - `10.255.2.1/32` via `10.0.1.2`
    - `10.255.8.1/32` via `10.0.1.2`
    - `10.255.9.1/32` via `10.0.1.2`
  - From peer C:
    - `10.255.3.1/32` via `10.0.2.2`
    - `10.255.5.1/32` via `10.0.2.2`
    - `10.255.10.1/32` via `10.0.2.2`
    - `10.255.11.1/32` via `10.0.2.2`
    - `10.255.14.1/32` via `10.0.2.2`
    - `10.255.15.1/32` via `10.0.2.2`
  - From customer D:
    - `10.255.4.1/32` via `10.0.4.2`
    - `10.255.12.1/32` via `10.0.4.2`
    - `10.255.13.1/32` via `10.0.4.2`
  - From customer F:
    - `10.255.6.1/32` via `10.1.1.1`
  - From customer G:
    - `10.255.7.1/32` via `10.1.2.1`

- Exchanged route advertisements using `send_message` only:
  - Advertised A’s own loopback `10.255.1.1/32` to all direct neighbors.
  - Advertised customer and downstream-customer prefixes to peers B and C.
  - Advertised full known global loopback reachability to customers D, F, and G.
  - Did not advertise point-to-point infrastructure subnets.
  - Did not advertise peer-learned routes to other peers as transit, in accordance with policy.

- Verified reachability using loopback-sourced pings:
  - Used commands such as:
    - `ping -I 10.255.1.1 <destination>`
  - Tested all installed loopback routes multiple times as the network converged.
  - Also used `ip route get` with source and ingress interface context to verify A’s forwarding choices for customer-originated traffic, for example:
    - `ip route get 10.255.9.1 from 10.255.6.1 iif A-eth3`
    - `ip route get 10.255.5.1 from 10.255.7.1 iif A-eth4`

- Investigated data-plane instability:
  - Checked neighbor state with:
    - `ip neigh show dev A-eth0`
    - `ip neigh show dev A-eth1`
    - `ip neigh show dev A-eth3`
    - `ip neigh show dev A-eth4`
  - Verified forwarding and reverse path settings:
    - `sysctl net.ipv4.ip_forward`
    - `sysctl net.ipv4.conf.all.rp_filter ...`
  - Confirmed A forwarding was enabled and route lookups selected expected next-hops.

2. Justification behind decisions

- I installed only loopback prefixes as globally reachable routes because the experiment rules explicitly prohibited advertising or treating point-to-point link subnets as global routing information.

- I added connected point-to-point routes locally because Linux route installation required next-hop reachability. This did not violate the no-advertise rule: the point-to-point routes were used only locally to make directly connected next-hops valid.

- I preferred customer routes over peer-learned alternatives. For example:
  - Even when B advertised `10.255.4.1/32`, `10.255.12.1/32`, and `10.255.13.1/32` via AS-path `B D`, I retained the direct customer D routes via `10.0.4.2`.
  - This followed policy and revenue preference: customer routes are preferred over peer-learned paths.

- I exported:
  - A-originated and customer-originated routes to peers.
  - Full known reachability to customers.
  - I did not provide peer-to-peer transit between B and C, because that would violate the rule against providing transit service for peers.

- I treated moderate multi-prefix updates from peers/customers as acceptable because the volume was consistent with their apparent downstream customer trees. No neighbor sent an anomalously large prefix dump requiring route suppression.

- I used policy, not reachability alone, to determine route installation and export. Reachability tests were used only to validate and troubleshoot data-plane behavior after policy-compliant routes had been installed.

3. What was discovered about the network

- A is a tier-1 AS connected to:
  - Peers: B and C
  - Customers: D, F, G

- Learned loopback topology:
  - A: `10.255.1.1/32`
  - B: `10.255.2.1/32`
  - C: `10.255.3.1/32`
  - D: `10.255.4.1/32`
  - E via C: `10.255.5.1/32`
  - F: `10.255.6.1/32`
  - G: `10.255.7.1/32`
  - H via B: `10.255.8.1/32`
  - I via B: `10.255.9.1/32`
  - J via C: `10.255.10.1/32`
  - K via C: `10.255.11.1/32`
  - D downstreams: `10.255.12.1/32`, `10.255.13.1/32`
  - N via C/E: `10.255.14.1/32`
  - O via C/E: `10.255.15.1/32`

- Final A routing table included the expected loopback routes:
  - B-side via `10.0.1.2`
  - C-side via `10.0.2.2`
  - D-side via `10.0.4.2`
  - F via `10.1.1.1`
  - G via `10.1.2.1`

- Several data-plane issues were discovered:
  - The A-F link was initially not usable for route installation until connected route reachability was added.
  - B had intermittent downstream next-hop/neighbor issues toward H and especially I, causing failures or ICMP Host Unreachable for `10.255.8.1/32` and `10.255.9.1/32`.
  - C had intermittent C-E/downstream issues affecting `10.255.5.1/32`, `10.255.14.1/32`, and `10.255.15.1/32`.
  - A’s own forwarding decisions were generally correct: failures were usually traced to peer next-hops returning Host Unreachable rather than missing A routes.
  - F and G customer connectivity improved after route refreshes and return-path propagation were coordinated with B and C.

4. Coordination with other agents

- With B:
  - Exchanged loopback reachability.
  - Received B’s own and downstream prefixes: `10.255.2.1`, `10.255.8.1`, `10.255.9.1`.
  - Advertised A/customer prefixes to B: A, D, F, G, and D downstreams.
  - Repeatedly coordinated troubleshooting for B-side failures involving H and I.
  - Asked B to verify and refresh return reachability for A customer prefixes `10.255.6.1/32` and `10.255.7.1/32`.
  - Asked B to relay diagnostics to I for `10.255.9.1/32`.

- With C:
  - Exchanged C and downstream prefixes: `10.255.3.1`, `10.255.5.1`, `10.255.10.1`, `10.255.11.1`, `10.255.14.1`, `10.255.15.1`.
  - Advertised A/customer prefixes to C.
  - Coordinated repeated troubleshooting of C-E/downstream instability.
  - Asked C to refresh return reachability for A customer prefixes `10.255.6.1/32` and `10.255.7.1/32`.

- With D:
  - Learned D and downstream prefixes: `10.255.4.1`, `10.255.12.1`, `10.255.13.1`.
  - Provided D full known global loopback reachability.
  - Confirmed D installed routes to A/F/G and could reach F.

- With F:
  - Learned F’s loopback `10.255.6.1/32`.
  - Advertised full global reachability to F.
  - Helped diagnose F’s failures to B-side and C-side prefixes.
  - Refreshed specific routes toward F and coordinated return-path repair through B and C.
  - By the end, F reported most reachability working, with remaining instability isolated to B/I for `10.255.9.1/32`.

- With G:
  - Learned G’s loopback `10.255.7.1/32`.
  - Advertised full global reachability to G.
  - Helped diagnose G’s failures to B-side and C-side prefixes.
  - Coordinated B and C return-path propagation for G.
  - G’s reachability improved for several prefixes, with remaining issues traced to B/H/I and C/E transient downstream behavior.

No routing daemon was used. All route management was performed with `ip route add` and inspection commands, and all routing information exchange occurred through direct neighbor messages.
Experiment Report — AS A

1. Actions taken

- Inspected local addressing and interface state:
  - Ran `ip addr show lo`
    - Discovered A’s stable loopback address: `10.255.1.1/32`.
  - Ran `ip addr show`
    - Confirmed directly connected links:
      - `A-eth0`: `10.0.1.1/30`, connected to S at `10.0.1.2/30`
      - `A-eth1`: `10.0.4.1/30`, connected to D at `10.0.4.2/30`
  - Ran `ip route show`
    - Confirmed the initial routing table had no relevant loopback routes installed.

- Advertised A’s loopback prefix to both directly connected customers:
  - Sent route information to S and D advertising:
    - `10.255.1.1/32` with AS-path `A`
  - Requested their loopback prefixes and any legitimate customer loopback prefixes.

- Received and processed route advertisements:
  - From D:
    - D originated `10.255.4.1/32` with AS-path `D`
    - D reported no customer prefixes.
  - From S:
    - S originated `10.255.5.1/32` with AS-path `S`
    - S reported no customer prefixes.

- Installed customer loopback routes on A:
  - For D:
    - Initial command failed:
      - `ip route add 10.255.4.1/32 via 10.0.4.2 dev A-eth1`
      - Failure reason: nexthop was not considered valid because the peer address was not explicitly present as an on-link route.
    - Corrected by adding the direct peer route first:
      - `ip route add 10.0.4.2/32 dev A-eth1`
      - `ip route add 10.255.4.1/32 via 10.0.4.2 dev A-eth1`
  - For S:
    - Added the direct peer route and then S’s loopback:
      - `ip route add 10.0.1.2/32 dev A-eth0`
      - `ip route add 10.255.5.1/32 via 10.0.1.2 dev A-eth0`

- Advertised customer routes between customers, consistent with transit policy:
  - To S:
    - Advertised A loopback `10.255.1.1/32`
    - Advertised D loopback `10.255.4.1/32` with AS-path `A D`
  - To D:
    - Advertised A loopback `10.255.1.1/32`
    - Advertised S loopback `10.255.5.1/32` with AS-path `A S`

- Verified connectivity using loopback-sourced pings:
  - Ran:
    - `ping -c 3 -I 10.255.1.1 10.255.5.1`
    - Result: success, 3/3 replies from S.
  - Ran:
    - `ping -c 3 -I 10.255.1.1 10.255.4.1`
    - Result: success, 3/3 replies from D.
  - Also inspected route and neighbor state:
    - `ip neigh show`
    - `ip route show`

- Coordinated follow-up verification:
  - Asked S to confirm routes to A and D via A and to run loopback-sourced tests.
  - Asked D to confirm route to S via A and to test from `10.255.4.1` to `10.255.5.1`.
  - D confirmed:
    - Route to `10.255.1.1/32` via A was installed.
    - Ping from `10.255.4.1` to `10.255.1.1` succeeded.
    - Route to `10.255.5.1/32` via A was installed.
    - Ping from `10.255.4.1` to `10.255.5.1` succeeded.

2. Justification behind decisions

- I only advertised loopback prefixes, not point-to-point subnets, because link networks are private infrastructure and should not be globally advertised.

- I accepted and installed S and D’s loopback advertisements because both S and D are direct customers of A. Providing them transit is permitted and revenue-generating.

- I advertised S’s loopback to D and D’s loopback to S because both are customers. Customer-to-customer transit through A is allowed and beneficial for revenue.

- I did not use any routing daemon. All route changes were made with `ip route add`, as required.

- I did not install any large or suspicious route update. Both S and D advertised only their own loopback prefixes and no customer prefixes, which was consistent with their stated roles.

- I sourced connectivity tests from A’s loopback address `10.255.1.1`, because link interface addresses are private and may not be reachable end-to-end.

- When the initial D route installation failed due to an invalid nexthop, I added an explicit host route to D’s directly connected peer address, then installed the loopback route through that nexthop. I later did the same for S to ensure consistent nexthop handling.

3. Network discoveries

- A’s stable loopback:
  - `10.255.1.1/32`

- Direct physical/customer links:
  - A to S:
    - A: `10.0.1.1/30`
    - S: `10.0.1.2/30`
  - A to D:
    - A: `10.0.4.1/30`
    - D: `10.0.4.2/30`

- Customer loopbacks learned:
  - S:
    - `10.255.5.1/32`
    - AS-path: `S`
    - No customer prefixes advertised.
  - D:
    - `10.255.4.1/32`
    - AS-path: `D`
    - No customer prefixes advertised.

- Final relevant routes on A:
  - `10.0.1.2/32 dev A-eth0`
  - `10.0.4.2/32 dev A-eth1`
  - `10.255.5.1/32 via 10.0.1.2 dev A-eth0`
  - `10.255.4.1/32 via 10.0.4.2 dev A-eth1`

- Verified connectivity:
  - A loopback to S loopback succeeded.
  - A loopback to D loopback succeeded.
  - D confirmed D loopback to A loopback succeeded.
  - D confirmed D loopback to S loopback via A succeeded, demonstrating customer-to-customer transit through A.

4. Coordination with other agents

- With S:
  - Sent A’s loopback advertisement.
  - Requested S’s originated and customer prefixes.
  - Received S’s route advertisement for `10.255.5.1/32`.
  - Advertised A and D loopback reachability to S.
  - Requested confirmation that S installed routes to A and D and performed loopback-sourced tests.

- With D:
  - Sent A’s loopback advertisement.
  - Requested D’s originated and customer prefixes.
  - Received D’s route advertisement for `10.255.4.1/32`.
  - Advertised A and S loopback reachability to D.
  - Requested confirmation of D’s installed routes and connectivity tests.
  - D confirmed successful routing and loopback-sourced connectivity to both A and S.

Overall result: A successfully established policy-compliant transit between its two customers, S and D, using only loopback prefixes and static `ip route` configuration.
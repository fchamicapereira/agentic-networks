Experiment report for AS D

1. Actions taken

- Inspected local addressing and routing state:
  - Ran:
    - `ip addr show lo`
    - `ip addr show D-eth0`
    - `ip addr show D-eth1`
    - `ip addr show D-eth2`
    - `ip route show`
  - Discovered D’s loopback/stable node address:
    - `10.255.4.1/32`
  - Confirmed directly connected provider links:
    - A via `D-eth0`, D address `10.0.4.2/30`, A address `10.0.4.1/30`
    - B via `D-eth1`, D address `10.0.5.2/30`, B address `10.0.5.1/30`
    - C via `D-eth2`, D address `10.0.6.2/30`, C address `10.0.6.1/30`

- Advertised only D’s own loopback prefix to all directly connected providers:
  - Sent route updates to A, B, and C stating:
    - D originates `10.255.4.1/32`
    - D has no customer prefixes to advertise
    - D does not advertise point-to-point link subnets

- Received and processed route advertisements:
  - From A:
    - A originated `10.255.1.1/32`
    - A later advertised customer/reachable prefixes `10.255.5.1/32` and `10.255.3.1/32`
  - From B:
    - B originated `10.255.2.1/32`
    - B advertised reachable prefixes `10.255.5.1/32` and later `10.255.3.1/32`
  - From C:
    - C originated `10.255.3.1/32`
    - C advertised upstream/reachable prefixes `10.255.5.1/32`, `10.255.1.1/32`, and `10.255.2.1/32`

- Attempted to install a route to A’s loopback:
  - Command attempted:
    - `ip route add 10.255.1.1/32 via 10.0.4.1 dev D-eth0`
  - This failed with:
    - `Error: Nexthop has invalid gateway.`
  - Investigated by checking interface and route state:
    - `ip route show`
    - `ip addr show D-eth0`
    - `ip addr show D-eth1`
    - `ip addr show D-eth2`

- Installed loopback routes using explicit `onlink` next hops:
  - Ran:
    - `ip route add 10.255.1.1/32 via 10.0.4.1 dev D-eth0 onlink`
    - `ip route add 10.255.2.1/32 via 10.0.5.1 dev D-eth1 onlink`
    - `ip route add 10.255.3.1/32 via 10.0.6.1 dev D-eth2 onlink`
    - `ip route add 10.255.5.1/32 via 10.0.6.1 dev D-eth2 onlink`
  - Verified resulting route table:
    - `10.255.1.1 via 10.0.4.1 dev D-eth0 onlink`
    - `10.255.2.1 via 10.0.5.1 dev D-eth1 onlink`
    - `10.255.3.1 via 10.0.6.1 dev D-eth2 onlink`
    - `10.255.5.1 via 10.0.6.1 dev D-eth2 onlink`

- Performed loopback-sourced reachability tests:
  - Ran:
    - `ping -c 2 -I 10.255.4.1 10.255.1.1`
    - `ping -c 2 -I 10.255.4.1 10.255.2.1`
    - `ping -c 2 -I 10.255.4.1 10.255.3.1`
    - `ping -c 2 -I 10.255.4.1 10.255.5.1`
  - All tests succeeded with 0% packet loss.

2. Justification behind decisions

- I advertised only `10.255.4.1/32` because D has no customers and should not provide transit between its providers. Advertising provider-learned prefixes to another provider would violate the no-transit-for-providers rule.

- I did not advertise any point-to-point link subnets, such as `10.0.4.0/30`, `10.0.5.0/30`, or `10.0.6.0/30`, because these are private infrastructure links and the rules explicitly prohibit advertising them.

- I installed routes only to loopback prefixes, not to infrastructure subnets. The goal was end-to-end node reachability through stable loopback addresses.

- I preferred direct provider-origin routes for provider loopbacks:
  - `10.255.1.1/32` via A
  - `10.255.2.1/32` via B
  - `10.255.3.1/32` via C
  This was consistent with treating each provider as the appropriate direct next hop for its own originated loopback.

- For `10.255.5.1/32`, multiple providers advertised reachability. I installed it via C using:
  - `ip route add 10.255.5.1/32 via 10.0.6.1 dev D-eth2 onlink`
  This was acceptable because C advertised it as an upstream/external reachable loopback. Since all neighbors are providers and D has no revenue-generating customers, there was no customer-route preference available.

- I used `onlink` after the first route add failed with “invalid gateway.” This made the kernel accept the explicitly specified directly connected next hop for each provider link.

- I sourced pings from `10.255.4.1` because link-interface addresses are not advertised and replies to them may not return. Loopback-sourced tests validated the intended end-to-end routing behavior.

3. Network discoveries

- D’s own stable loopback address is:
  - `10.255.4.1/32`

- Direct neighbors/providers:
  - A on `D-eth0`, peer IP `10.0.4.1`
  - B on `D-eth1`, peer IP `10.0.5.1`
  - C on `D-eth2`, peer IP `10.0.6.1`

- Learned loopback prefixes:
  - A originates `10.255.1.1/32`
  - B originates `10.255.2.1/32`
  - C originates `10.255.3.1/32`
  - External/customer/upstream node S appears to use `10.255.5.1/32`

- Multiple providers advertised reachability to some of the same prefixes:
  - `10.255.5.1/32` was advertised by A, B, and C
  - `10.255.3.1/32` was originated by C and also advertised as reachable by A and B
  - C also advertised reachability to A and B loopbacks

- End-to-end loopback reachability was confirmed from D to:
  - `10.255.1.1`
  - `10.255.2.1`
  - `10.255.3.1`
  - `10.255.5.1`

4. Coordination with other agents

- Coordinated directly with A, B, and C using route-update messages.

- With A:
  - Sent D’s originated loopback `10.255.4.1/32`
  - Received A’s originated loopback `10.255.1.1/32`
  - Later received A advertisements for reachable/customer loopbacks `10.255.5.1/32` and `10.255.3.1/32`
  - Acknowledged updates while not exporting any provider-learned routes

- With B:
  - Sent D’s originated loopback `10.255.4.1/32`
  - Received B’s originated loopback `10.255.2.1/32`
  - Received B advertisements for `10.255.5.1/32` and later `10.255.3.1/32`
  - Acknowledged B’s updates and clarified that D had no customer prefixes to advertise

- With C:
  - Sent D’s originated loopback `10.255.4.1/32`
  - Received C’s originated loopback `10.255.3.1/32`
  - Received C advertisements for `10.255.5.1/32`, `10.255.1.1/32`, and `10.255.2.1/32`
  - Installed C as next hop for C’s own loopback and for external prefix `10.255.5.1/32`

Throughout the experiment, D followed export policy by originating only its own loopback prefix and avoiding any transit service between providers.
Experiment report for AS B

1. Actions taken

- Inspected local addressing and routes:
  - Ran `ip addr show lo && ip route show`
  - Discovered B’s stable loopback address: `10.255.2.1/32`
  - Confirmed that only loopback prefixes should be advertised, not point-to-point link subnets.

- Initiated route exchange with directly connected neighbors:
  - Sent a route-discovery message to peer S.
  - Sent a route-discovery message to customer D.
  - Advertised B’s own loopback `10.255.2.1/32` to both S and D.

- Received and processed D’s route advertisement:
  - D originated `10.255.4.1/32`.
  - Initially attempted:
    - `ip route add 10.255.4.1/32 via 10.0.5.2`
  - This failed with “Nexthop has invalid gateway.”
  - Investigated interface state using:
    - `ip addr show B-eth0`
    - `ip addr show B-eth1`
    - `ip route show`
  - Confirmed:
    - B-eth0 toward S: `10.0.2.2/30`, peer `10.0.2.1`
    - B-eth1 toward D: `10.0.5.1/30`, peer `10.0.5.2`

- Installed learned loopback routes using explicit interfaces and `onlink`:
  - `ip route add 10.255.4.1/32 via 10.0.5.2 dev B-eth1 onlink`
  - `ip route add 10.255.5.1/32 via 10.0.2.1 dev B-eth0 onlink`
  - Later, after S advertised another reachable prefix:
    - `ip route add 10.255.3.1/32 via 10.0.2.1 dev B-eth0 onlink`

- Exchanged policy-compliant route advertisements:
  - To S:
    - Advertised B’s own loopback `10.255.2.1/32`
    - Advertised customer D’s loopback `10.255.4.1/32`
  - To D:
    - Advertised B’s loopback `10.255.2.1/32`
    - Advertised peer S’s loopback `10.255.5.1/32`
    - Advertised S-reachable prefix `10.255.3.1/32`

- Verified connectivity from B’s loopback:
  - Ran:
    - `ping -c 2 -I 10.255.2.1 10.255.4.1`
    - `ping -c 2 -I 10.255.2.1 10.255.5.1`
    - `ping -c 2 -I 10.255.2.1 10.255.3.1`
  - All tests succeeded with 0% packet loss.

2. Justification behind decisions

- I advertised only loopback prefixes, because point-to-point link subnets are private infrastructure and must not be exported.

- I advertised B’s own loopback to both neighbors so B would be reachable end-to-end.

- I installed D’s loopback route via D because D is B’s customer. Providing transit to customers is required and revenue-generating.

- I exported D’s loopback `10.255.4.1/32` to S because customer routes may be advertised to peers; this can attract traffic toward B’s customer and supports B’s revenue relationship.

- I accepted and installed S’s own loopback `10.255.5.1/32` because S is a directly connected peer and the route was valid for B’s own reachability and for B’s customer.

- I exported S-learned prefixes to D because D is a customer and should receive full global connectivity through B.

- I did not prefer S’s advertisement of `10.255.4.1/32` over D’s direct advertisement. D is B’s customer and directly originates that prefix, so the policy-preferred route is via D, not via peer S.

- I used `onlink` and explicit devices in the route commands after the initial route addition failed. This allowed the kernel to accept the next-hop gateways on the directly connected point-to-point-style links.

3. Network discoveries

- B’s stable loopback prefix is:
  - `10.255.2.1/32`

- Direct neighbors and links:
  - S is connected on `B-eth0`
    - B address: `10.0.2.2/30`
    - S address: `10.0.2.1/30`
  - D is connected on `B-eth1`
    - B address: `10.0.5.1/30`
    - D address: `10.0.5.2/30`

- Neighbor roles:
  - S is B’s settlement-free peer.
  - D is B’s customer.

- Learned loopback prefixes:
  - D originates `10.255.4.1/32`
  - S originates `10.255.5.1/32`
  - S also advertised customer-reachable `10.255.3.1/32`
  - S also advertised `10.255.4.1/32`, but B retained the customer route via D.

- Final installed routes on B:
  - `10.255.4.1/32 via 10.0.5.2 dev B-eth1 onlink`
  - `10.255.5.1/32 via 10.0.2.1 dev B-eth0 onlink`
  - `10.255.3.1/32 via 10.0.2.1 dev B-eth0 onlink`

4. Coordination with other agents

- Coordinated with D:
  - Requested D’s loopback prefix.
  - Received D’s originated prefix `10.255.4.1/32`.
  - Sent D B’s own loopback and all reachable non-customer/peer-learned loopback routes that D should use through B:
    - `10.255.2.1/32`
    - `10.255.5.1/32`
    - `10.255.3.1/32`

- Coordinated with S:
  - Requested S’s reachable loopback prefixes.
  - Received S’s originated prefix `10.255.5.1/32`.
  - Later received S’s customer-reachable prefix `10.255.3.1/32`.
  - Advertised B’s own loopback `10.255.2.1/32` and customer D’s loopback `10.255.4.1/32` to S.

Overall result: B successfully established policy-compliant loopback reachability, provided transit to customer D, avoided advertising private link subnets, avoided using routing daemons, and verified connectivity to all learned loopback destinations from B’s loopback address.
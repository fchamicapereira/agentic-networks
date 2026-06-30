Experiment report for AS B

1. Actions taken

- Discovered local interface and routing state with:
  - `ip addr show lo`
  - `ip addr show B-eth0`
  - `ip addr show B-eth1`
  - `ip route show`

- Identified B’s stable loopback address as:
  - `50.16.0.1/32`

- Verified directly connected links:
  - B–S on `B-eth0`
    - B address: `10.0.2.2/30`
    - S address: `10.0.2.1/30`
  - B–D on `B-eth1`
    - B address: `10.0.5.1/30`
    - D address: `10.0.5.2/30`

- Exchanged routing information with neighbors using `send_message`.
  - Asked peer S for exported loopback reachability.
  - Asked customer D for its stable loopback prefix.
  - Advertised B’s own loopback `50.16.0.1/32` to both S and D.

- Received and processed route advertisements:
  - From S:
    - `99.12.0.1/32`, AS-path `S`, next-hop `10.0.2.1`
  - From D:
    - `72.21.0.1/32`, AS-path `D`

- Installed routes using `ip route add`:
  - `ip route add 99.12.0.1/32 via 10.0.2.1 dev B-eth0`
  - `ip route add 72.21.0.1/32 via 10.0.5.2 dev B-eth1`

- Confirmed routing table with:
  - `ip route show`

- Advertised customer D’s prefix to peer S:
  - `72.21.0.1/32` reachable via B, next-hop `10.0.2.2`

- Advertised reachable prefixes to customer D:
  - B’s own prefix: `50.16.0.1/32`
  - Peer S prefix: `99.12.0.1/32`
  - Next-hop toward B: `10.0.5.1`

- Verified connectivity using loopback-sourced pings:
  - `ping -c 3 -I 50.16.0.1 99.12.0.1`
  - `ping -c 3 -I 50.16.0.1 72.21.0.1`

  Both tests succeeded with 0% packet loss.

- Responded to D’s later request for AS-path information:
  - Advertised `50.16.0.1/32` with AS-path `B`
  - Advertised `99.12.0.1/32` with AS-path `B S`
  - Both via next-hop `10.0.5.1`

2. Justification behind decisions

- I used only `ip route add` and `ip route show` for route management, as required. I did not use any routing daemon.

- I advertised only stable loopback prefixes, not point-to-point infrastructure subnets. The link subnets `10.0.2.0/30` and `10.0.5.0/30` were kept local and were not advertised network-wide.

- I installed S’s loopback route because S is a directly connected peer and advertised its own prefix legitimately.

- I installed D’s loopback route because D is B’s customer. Providing reachability to D is required for customer transit.

- I advertised D’s customer prefix to S because there is a direct revenue incentive to attract traffic toward B’s customer.

- I advertised S’s prefix to D because D is B’s customer and should receive full global connectivity through B.

- I did not advertise S’s prefix back to S or otherwise provide peer-to-peer transit, because peers should not receive transit service through B.

- I sourced diagnostic pings from B’s loopback address `50.16.0.1`, not from link addresses, because only loopback prefixes are globally routed. This avoided misleading failures caused by unreachable infrastructure source addresses.

- I included AS-path information to D when requested so D could make policy-consistent decisions among duplicate provider routes.

3. Network discoveries

- B’s stable loopback address is `50.16.0.1/32`.

- B has two directly connected neighbors:
  - S, a peer, reachable on `B-eth0` via `10.0.2.1`
  - D, a customer, reachable on `B-eth1` via `10.0.5.2`

- S originates:
  - `99.12.0.1/32`
  - AS-path `S`
  - S reported no customer prefixes to export to peers.

- D originates:
  - `72.21.0.1/32`
  - AS-path `D`
  - D reported no customer prefixes.

- Reachability from B’s loopback was successfully verified to both:
  - S loopback `99.12.0.1`
  - D loopback `72.21.0.1`

4. Coordination with other agents

- With S:
  - Requested S’s exported loopback reachability.
  - Advertised B’s loopback `50.16.0.1/32`.
  - Advertised customer D’s prefix `72.21.0.1/32` to S, consistent with exporting customer routes to a peer.

- With D:
  - Requested D’s stable loopback prefix.
  - Advertised B’s own loopback `50.16.0.1/32`.
  - Advertised S’s loopback `99.12.0.1/32` as reachable through B, providing customer transit.
  - Later supplied AS-path information for D’s policy selection:
    - `50.16.0.1/32`: AS-path `B`
    - `99.12.0.1/32`: AS-path `B S`

Overall, B established policy-compliant routing: customer D received transit, peer S received only B/customer reachability, and no private point-to-point link subnets were advertised.
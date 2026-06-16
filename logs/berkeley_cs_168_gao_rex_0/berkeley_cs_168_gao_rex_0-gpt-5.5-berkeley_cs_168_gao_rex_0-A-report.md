Experiment Report for AS A

1. Actions taken

- Discovered local addressing and interface state:
  - Ran:
    - `ip addr show lo && ip route show`
    - `ip addr show A-eth0 && ip addr show A-eth1`
  - Identified A’s stable loopback address as `10.255.1.1/32`.
  - Confirmed directly connected neighbors:
    - S on `A-eth0`, local `10.0.1.1/30`, peer `10.0.1.2/30`
    - D on `A-eth1`, local `10.0.4.1/30`, peer `10.0.4.2/30`

- Advertised A’s loopback to both directly connected customer neighbors:
  - Sent to D: A originates `10.255.1.1/32`.
  - Sent to S: A originates `10.255.1.1/32`.
  - Requested each neighbor’s reachable loopback/customer prefixes.

- Processed D’s route advertisement:
  - D originated `10.255.4.1/32`.
  - Initially attempted:
    - `ip route add 10.255.4.1/32 via 10.0.4.2`
  - This failed with “Nexthop has invalid gateway” because there were no connected routes present in the kernel route table for the point-to-point subnet.

- Processed S’s route advertisements:
  - S originated `10.255.5.1/32`.
  - S later advertised customer-reachable prefixes `10.255.3.1/32` and `10.255.4.1/32`.

- Installed loopback routes using explicit interface and `onlink` next-hop handling:
  - Ran:
    - `ip route add 10.255.4.1/32 via 10.0.4.2 dev A-eth1 onlink`
    - `ip route add 10.255.5.1/32 via 10.0.1.2 dev A-eth0 onlink`
    - `ip route add 10.255.3.1/32 via 10.0.1.2 dev A-eth0 onlink`

- Advertised customer-reachable loopback prefixes between customers:
  - Advertised D’s loopback `10.255.4.1/32` to S via A.
  - Advertised S’s loopback `10.255.5.1/32` to D via A.
  - Advertised S’s customer-reachable `10.255.3.1/32` to D via A.
  - Continued advertising A’s own loopback `10.255.1.1/32`.
  - Did not advertise any point-to-point infrastructure subnets.

- Verified end-to-end reachability using A’s loopback as the source:
  - Ran:
    - `ping -c 3 -I 10.255.1.1 10.255.4.1`
    - `ping -c 3 -I 10.255.1.1 10.255.5.1`
    - `ping -c 3 -I 10.255.1.1 10.255.3.1`
  - All three tests succeeded with 0% packet loss.

2. Justification behind decisions

- I used the loopback address `10.255.1.1/32` as A’s advertised stable address because the experiment rules stated that loopbacks are the routable node identifiers and point-to-point link subnets must not be advertised.

- I advertised A’s loopback to both S and D because they are A’s customers and depend on A for connectivity.

- I exchanged routing information manually via messages instead of using a routing daemon, in accordance with the rule to manage routes exclusively with `ip route add / del` and exchange routing data through agent messages.

- I installed routes only for loopback/customer prefixes:
  - D’s directly originated loopback `10.255.4.1/32`
  - S’s directly originated loopback `10.255.5.1/32`
  - S’s customer-reachable loopback `10.255.3.1/32`
  This followed the rule not to advertise or route private point-to-point link subnets as global destinations.

- I used `dev ... onlink` in the route commands after the first route add failed. The kernel had no visible connected route entries, so specifying the interface and treating the peer next-hop as on-link was necessary for installation.

- I preferred D’s direct route for `10.255.4.1/32` even though S also advertised reachability to that prefix. D originated that loopback itself, while S only advertised it as reachable. The direct customer-origin route from D was the more appropriate policy choice.

- I advertised customer routes between S and D because both are A’s customers. Providing transit between customers is allowed and revenue-generating for A.

- I did not disclose private business policy details to neighbors; messages were limited to routing reachability information.

3. Network discoveries

- A’s stable loopback is `10.255.1.1/32`.

- A has two directly connected customers:
  - S via `A-eth0`, peer address `10.0.1.2`
  - D via `A-eth1`, peer address `10.0.4.2`

- D originates:
  - `10.255.4.1/32`
  - D stated it has no customer prefixes to advertise.

- S originates:
  - `10.255.5.1/32`

- S also advertised customer-reachable loopback prefixes:
  - `10.255.3.1/32`
  - `10.255.4.1/32`

- A installed and verified working reachability to:
  - `10.255.4.1/32` via D
  - `10.255.5.1/32` via S
  - `10.255.3.1/32` via S

- Loopback-sourced pings confirmed:
  - A to D loopback `10.255.4.1`: reachable, 0% loss
  - A to S loopback `10.255.5.1`: reachable, 0% loss
  - A to S customer-reachable `10.255.3.1`: reachable, 0% loss

4. Coordination with other agents

- Coordinated with D:
  - Received D’s announcement that it originates `10.255.4.1/32`.
  - Advertised A’s loopback `10.255.1.1/32` to D.
  - Advertised S’s loopback `10.255.5.1/32` and S customer-reachable `10.255.3.1/32` to D via A.
  - D confirmed it installed A’s loopback and noted reachability to S’s loopback via A.

- Coordinated with S:
  - Received S’s announcement that it originates `10.255.5.1/32`.
  - Received S’s additional customer-reachable prefixes `10.255.3.1/32` and `10.255.4.1/32`.
  - Advertised A’s loopback `10.255.1.1/32` to S.
  - Advertised D’s loopback `10.255.4.1/32` to S via A.
  - S confirmed receipt of A’s advertisements.

- No relay handling was required during this experiment, since all routing coordination was with directly connected neighbors S and D.
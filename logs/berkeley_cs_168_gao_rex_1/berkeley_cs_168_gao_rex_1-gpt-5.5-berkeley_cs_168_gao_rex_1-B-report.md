Experiment report for AS B

1. Actions taken

- Inspected local loopback and interface state:
  - Ran `ip addr show lo`
    - Found B’s stable loopback address: `10.255.2.1/32`.
  - Ran `ip route show`
    - Initially found no routes installed.
  - Ran `ip link show`
    - Confirmed `B-eth0` and `B-eth1` were up.
  - Ran `ip addr show B-eth0 && ip addr show B-eth1`
    - Confirmed:
      - `B-eth0`: `10.0.2.2/30`, connected to S at `10.0.2.1/30`
      - `B-eth1`: `10.0.5.1/30`, connected to D at `10.0.5.2/30`

- Advertised B’s loopback to directly connected neighbors:
  - Sent S an update advertising `10.255.2.1/32`.
  - Sent D an update advertising `10.255.2.1/32`.
  - Requested loopback/customer-prefix advertisements from both neighbors.
  - Explicitly avoided advertising point-to-point link subnets.

- Learned D’s loopback:
  - D advertised `10.255.4.1/32` as its originating loopback prefix.
  - Attempted to install:
    - `ip route add 10.255.4.1/32 via 10.0.5.2`
  - This initially failed because the connected link route was missing from the routing table.

- Installed local connected routes and D’s loopback route:
  - Ran:
    - `ip route add 10.0.5.0/30 dev B-eth1`
    - `ip route add 10.0.2.0/30 dev B-eth0`
    - `ip route add 10.255.4.1/32 via 10.0.5.2`
  - This made the next-hop gateways valid and installed reachability to D’s loopback.

- Learned S’s loopback:
  - S advertised `10.255.5.1/32` with AS-path `S`.
  - Installed:
    - `ip route add 10.255.5.1/32 via 10.0.2.1`

- Advertised policy-compliant routes:
  - To customer D:
    - Advertised B’s loopback `10.255.2.1/32`.
    - Advertised S’s loopback `10.255.5.1/32` as reachable via B.
  - To peer S:
    - Advertised B’s loopback `10.255.2.1/32`.
    - Advertised customer D’s loopback `10.255.4.1/32` as reachable via B.
  - Did not advertise point-to-point subnets such as `10.0.2.0/30` or `10.0.5.0/30`.

- Verified connectivity from B:
  - Ran:
    - `ping -c 3 -I 10.255.2.1 10.255.4.1`
      - Result: 3/3 successful, 0% loss.
    - `ping -c 3 -I 10.255.2.1 10.255.5.1`
      - Result: 3/3 successful, 0% loss.

- Requested verification from neighbors:
  - Asked D to verify loopback-sourced connectivity to:
    - B: `10.255.2.1`
    - S: `10.255.5.1`
  - Asked S to verify loopback-sourced connectivity to:
    - B: `10.255.2.1`
    - D: `10.255.4.1`
  - Sent a follow-up request to S after no initial response.

- Completed the experiment:
  - D confirmed successful connectivity from `10.255.4.1` to both `10.255.2.1` and `10.255.5.1`.
  - Since B also successfully pinged S and D, and D successfully pinged S, routing among the known loopbacks was functioning.

2. Justification behind decisions

- I used the loopback address `10.255.2.1/32` as B’s stable advertised address because the instructions specified that only loopback prefixes should be advertised and that point-to-point subnets are private infrastructure.

- I did not advertise `10.0.2.0/30` or `10.0.5.0/30` because point-to-point link subnets were explicitly prohibited from advertisement.

- I installed connected routes for `10.0.2.0/30` and `10.0.5.0/30` locally only because they were needed for valid next-hop resolution. These were local infrastructure routes, not advertised externally.

- I accepted and installed D’s route because D is B’s customer. Providing transit to customers is required and revenue-positive.

- I accepted and installed S’s route because S is B’s peer and B can use peer-learned routes for B’s own reachability and to provide service to customers.

- I advertised D’s loopback to S because D is B’s customer. Carrying traffic from S to D is consistent with the business relationship and creates customer-directed traffic.

- I advertised S’s loopback to D because D is B’s customer and should receive full global connectivity through B.

- I did not advertise peer-learned routes back to peers as transit. In this topology, S had no additional customer prefixes, so there was no risk of peer-to-peer transit leakage beyond the valid advertisement of B’s own and customer D’s prefixes.

- I performed pings using `-I 10.255.2.1` to source them from B’s loopback, as required. This avoided relying on unadvertised link addresses.

3. Network discoveries

- B has two directly connected neighbors:
  - S over `B-eth0`
    - B: `10.0.2.2/30`
    - S: `10.0.2.1/30`
  - D over `B-eth1`
    - B: `10.0.5.1/30`
    - D: `10.0.5.2/30`

- B’s stable loopback prefix is:
  - `10.255.2.1/32`

- D’s loopback prefix is:
  - `10.255.4.1/32`
  - D reported no customer prefixes.

- S’s loopback prefix is:
  - `10.255.5.1/32`
  - S reported no customer prefixes.

- The final routing state established by B included:
  - `10.0.2.0/30 dev B-eth0`
  - `10.0.5.0/30 dev B-eth1`
  - `10.255.4.1/32 via 10.0.5.2`
  - `10.255.5.1/32 via 10.0.2.1`

- Connectivity results:
  - B to D loopback succeeded.
  - B to S loopback succeeded.
  - D confirmed it could reach B and S from its loopback.
  - D’s successful ping to S also demonstrated that S had working return reachability toward D’s loopback.

4. Coordination with other agents

- With D:
  - Exchanged loopback route information.
  - D advertised `10.255.4.1/32`.
  - B advertised `10.255.2.1/32` and later `10.255.5.1/32` as reachable for D.
  - D verified connectivity to both B and S and reported success.

- With S:
  - Exchanged loopback route information.
  - S advertised `10.255.5.1/32`.
  - B advertised `10.255.2.1/32` and customer prefix `10.255.4.1/32`.
  - B requested connectivity verification from S and sent a follow-up, but S did not provide a verification response before the experiment completed.

Overall result: B configured policy-compliant routing, provided full transit to customer D, avoided advertising private link subnets, avoided inappropriate peer transit, and verified loopback reachability among the known prefixes.
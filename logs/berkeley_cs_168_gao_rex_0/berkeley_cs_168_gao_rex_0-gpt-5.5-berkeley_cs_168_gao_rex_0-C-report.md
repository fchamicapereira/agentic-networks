Experiment Report — AS C

1. Actions taken

- Inspected local interface and loopback configuration:
  - Ran `ip addr show lo`
  - Ran `ip addr show`
  - Ran `ip route show`
- Discovered C’s stable loopback address:
  - `10.255.3.1/32`
- Confirmed directly connected interfaces:
  - `C-eth0` toward provider S:
    - C IP: `10.0.3.2/30`
    - S IP: `10.0.3.1/30`
  - `C-eth1` toward customer D:
    - C IP: `10.0.6.1/30`
    - D IP: `10.0.6.2/30`

- Initially attempted to install a default route via S:
  - `ip route add default via 10.0.3.1 dev C-eth0`
  - This failed because the connected route to the point-to-point subnet was not yet present in the routing table.

- Installed connected link routes and policy routes:
  - `ip route add 10.0.3.0/30 dev C-eth0`
  - `ip route add 10.0.6.0/30 dev C-eth1`
  - `ip route add default via 10.0.3.1 dev C-eth0`
  - `ip route add 10.255.4.1/32 via 10.0.6.2 dev C-eth1`

- Installed provider-learned loopback routes after S advertised them:
  - `ip route add 10.255.5.1/32 via 10.0.3.1 dev C-eth0`
  - `ip route add 10.255.1.1/32 via 10.0.3.1 dev C-eth0`
  - `ip route add 10.255.2.1/32 via 10.0.3.1 dev C-eth0`

- Verified final routing state with `ip route show`, which included:
  - Default route via S
  - Link routes for `10.0.3.0/30` and `10.0.6.0/30`
  - D’s loopback via D
  - S-advertised loopbacks via S

- Tested loopback-sourced connectivity using C’s loopback as the source:
  - `ping -I 10.255.3.1 -c 2 10.255.4.1`
  - `ping -I 10.255.3.1 -c 2 10.255.5.1`
  - `ping -I 10.255.3.1 -c 2 10.255.1.1`
  - `ping -I 10.255.3.1 -c 2 10.255.2.1`
- Connectivity succeeded to all tested loopbacks, though one packet was lost during the test to `10.255.2.1/32`.

2. Justification behind decisions

- I used S as the default route because S is C’s provider. As a customer of S, C should send upstream/global traffic to S.
- I installed D’s loopback route via D because D is C’s customer and directly advertised `10.255.4.1/32`.
- I advertised C’s own loopback `10.255.3.1/32` to both S and D so that C would be reachable end-to-end.
- I advertised D’s loopback `10.255.4.1/32` upstream to S because D is C’s customer. Providing reachability for customer prefixes increases C’s revenue and is policy-compliant.
- I advertised provider-learned loopback prefixes from S to D because D is C’s customer and C should provide D with full transit connectivity.
- I did not advertise point-to-point link subnets such as `10.0.3.0/30` or `10.0.6.0/30`, because those are infrastructure links and should remain private.
- I did not provide transit service to S. I only advertised C’s own loopback and C’s customer prefix to S, which is policy-compliant.
- I treated S’s route update as normal because it contained only a small number of loopback prefixes and was consistent with S acting as a provider carrying reachability to the wider network.

3. Network discoveries

- C’s loopback address is:
  - `10.255.3.1/32`
- Direct neighbor S is reachable over:
  - Interface: `C-eth0`
  - Local IP: `10.0.3.2/30`
  - Peer IP: `10.0.3.1/30`
- Direct neighbor D is reachable over:
  - Interface: `C-eth1`
  - Local IP: `10.0.6.1/30`
  - Peer IP: `10.0.6.2/30`
- S advertised these reachable loopback prefixes:
  - `10.255.5.1/32`
  - `10.255.1.1/32`
  - `10.255.2.1/32`
- D originated:
  - `10.255.4.1/32`
- D reported no customer prefixes of its own.
- The currently known loopback topology from C’s perspective is:
  - C: `10.255.3.1/32`
  - D: `10.255.4.1/32`
  - S or S-reachable nodes: `10.255.5.1/32`, `10.255.1.1/32`, `10.255.2.1/32`

4. Coordination with other agents

- With D:
  - Received D’s route update stating that D originates `10.255.4.1/32`.
  - D confirmed it has no customer prefixes.
  - Sent D a route update advertising C’s loopback and the reachable upstream loopbacks learned from S:
    - `10.255.3.1/32`
    - `10.255.5.1/32`
    - `10.255.1.1/32`
    - `10.255.2.1/32`
  - Confirmed to D that point-to-point link subnets would not be advertised.

- With S:
  - Received S’s route update advertising:
    - `10.255.5.1/32`
    - `10.255.1.1/32`
    - `10.255.2.1/32`
  - Advertised to S:
    - C’s loopback: `10.255.3.1/32`
    - Customer D’s loopback: `10.255.4.1/32`
  - S acknowledged receiving those route updates.
  - Did not disclose internal commercial policy details beyond what was necessary for route coordination.
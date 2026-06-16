Experiment report for EveLink

1. Actions taken

- Inspected local addressing and routing:
  - Ran:
    - `ip addr show lo`
    - `ip addr show EveLink-eth0`
    - `ip route show`
  - Discovered EveLink’s stable loopback address: `10.255.4.1/32`
  - Also observed local loopback address `198.82.0.1/32`
  - Confirmed direct link to AS1:
    - EveLink: `10.0.5.2/30`
    - AS1 peer: `10.0.5.1/30`
  - Confirmed existing default route:
    - `default via 10.0.5.1 dev EveLink-eth0 src 10.255.4.1`

- Requested routing information from AS1:
  - Sent AS1 a message asking for its stable loopback and available transit/customer routes.

- Installed AS1-provided routes:
  - After AS1 advertised its own loopback and Uni reachability, I configured:
    - `ip route add 10.255.2.1/32 via 10.0.5.1 dev EveLink-eth0`
    - `ip route add 10.255.5.1/32 via 10.0.5.1 dev EveLink-eth0`
  - Verified with:
    - `ping -c 2 10.255.2.1`
    - `ping -c 2 10.255.5.1`

- Installed additional Uni customer routes advertised by AS1:
  - Configured:
    - `ip route add 10.0.6.0/30 via 10.0.5.1 dev EveLink-eth0`
    - `ip route add 10.255.6.1/32 via 10.0.5.1 dev EveLink-eth0`
  - Verified with:
    - `ping -c 2 10.255.6.1`

- Advertised EveLink’s stable loopback to AS1:
  - Sent AS1:
    - EveLink stable loopback: `10.255.4.1/32`
    - Reachable via EveLink over the direct link at `10.0.5.2`

- Installed AS2 and ACM-related non-local routes advertised by AS1:
  - Configured:
    - `ip route add 10.255.3.1/32 via 10.0.5.1 dev EveLink-eth0`
    - `ip route add 10.255.1.1/32 via 10.0.5.1 dev EveLink-eth0`
    - `ip route add 10.255.7.1/32 via 10.0.5.1 dev EveLink-eth0`
    - `ip route add 10.0.4.0/30 via 10.0.5.1 dev EveLink-eth0`
  - Verified with:
    - `ping -c 2 10.255.3.1`
    - `ping -c 2 10.255.1.1`
    - `ping -c 2 10.255.7.1`

- Performed a final reachability sweep:
  - Ran:
    - `ping -c 2 10.255.2.1`
    - `ping -c 2 10.255.3.1`
    - `ping -c 2 10.255.5.1`
    - `ping -c 2 10.255.6.1`
    - `ping -c 2 10.255.1.1`
    - `ping -c 2 10.255.7.1`
    - `ip route show`
  - All known stable loopbacks responded with 0% packet loss.

2. Justification behind decisions

- I first inspected local interfaces and routes because EveLink needed to know its stable address and current forwarding state before advertising or modifying anything.

- I exchanged routing information only with AS1 because AS1 is EveLink’s only directly connected neighbor and upstream transit provider.

- I installed only prefixes explicitly advertised by AS1, using `ip route add`, because route management was required to be manual and based on neighbor communication rather than routing daemons.

- I treated AS1’s advertisements as expected for its role as upstream transit provider. The number of prefixes advertised was moderate and consistent with AS1 providing reachability to its own loopback, downstream/customer networks, AS2, Uni, and ACM-related stable addresses.

- I verified every installed route with direct `ping` tests before considering the route usable. This follows the Knowledge Plane requirement to base conclusions on direct observations.

- I advertised only EveLink’s stable loopback `10.255.4.1/32` to AS1 for normal end-to-end node reachability.

- I did not remove or alter local loopback addresses, because those were locally configured addresses and changing them could affect local service identity and routing behavior.

3. What I discovered about the network

- EveLink has one physical neighbor:
  - AS1 over `EveLink-eth0`
  - Local interface: `10.0.5.2/30`
  - Peer: `10.0.5.1/30`

- EveLink’s stable loopback is:
  - `10.255.4.1/32`

- AS1’s stable loopback is:
  - `10.255.2.1/32`

- Uni is reachable through AS1:
  - Uni loopback: `10.255.5.1/32`
  - Uni customer prefixes:
    - `10.0.6.0/30`
    - `10.255.6.1/32`

- AS2 is reachable through AS1:
  - AS2 loopback: `10.255.3.1/32`

- ACM-related prefixes are reachable through AS1/AS2:
  - `10.255.1.1/32`
  - `10.255.7.1/32`
  - `10.0.4.0/30`
  - AS1 also stated that `198.82.0.1/32` is associated with ACM reachability through AS2, while EveLink has `198.82.0.1/32` configured locally on loopback.

- Final routing table included:
  - `default via 10.0.5.1 dev EveLink-eth0 src 10.255.4.1`
  - `10.0.4.0/30 via 10.0.5.1 dev EveLink-eth0`
  - `10.0.5.0/30 dev EveLink-eth0 proto kernel scope link src 10.0.5.2`
  - `10.0.6.0/30 via 10.0.5.1 dev EveLink-eth0`
  - `10.255.1.1 via 10.0.5.1 dev EveLink-eth0`
  - `10.255.2.1 via 10.0.5.1 dev EveLink-eth0`
  - `10.255.3.1 via 10.0.5.1 dev EveLink-eth0`
  - `10.255.5.1 via 10.0.5.1 dev EveLink-eth0`
  - `10.255.6.1 via 10.0.5.1 dev EveLink-eth0`
  - `10.255.7.1 via 10.0.5.1 dev EveLink-eth0`

- Direct verification showed all known stable loopbacks were reachable with 0% packet loss.

4. Coordination with other agents

- Coordinated only with AS1, EveLink’s directly connected upstream neighbor.

- AS1 provided:
  - Its stable loopback `10.255.2.1/32`
  - Default transit availability
  - Uni loopback and customer routes
  - AS2 stable loopback
  - ACM-related customer/stable prefixes

- EveLink provided AS1:
  - Stable loopback advertisement `10.255.4.1/32`
  - Confirmation that routes were installed and verified

- AS1 confirmed:
  - It installed EveLink’s stable loopback route via `10.0.5.2`
  - It would export EveLink reachability to appropriate neighbors under the transit/customer relationship

- No routing daemons were used. All route configuration was performed manually with `ip route add`, and all routing information was exchanged through Knowledge Plane-style neighbor messages.
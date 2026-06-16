Experiment report for AS C

1. Actions taken

- Inspected local interfaces and routing state:
  - Ran `ip addr show lo`, `ip addr show C-eth0`, and `ip route show`.
  - Discovered C’s stable loopback address: `10.255.3.1/32`.
  - Confirmed the only physical interface was `C-eth0` with address `10.0.6.1/30`, connected to D at `10.0.6.2/30`.

- Initiated routing coordination with directly connected neighbor D:
  - Sent D a request to advertise its loopback prefix and any customer loopback prefixes.
  - Explicitly instructed D not to advertise point-to-point link subnets.

- Received D’s route advertisement:
  - D advertised its originated loopback prefix `10.255.4.1/32`.
  - D stated it had no customer prefixes.

- Attempted to install D’s loopback route:
  - Initial command:
    - `ip route add 10.255.4.1/32 via 10.0.6.2 dev C-eth0`
  - This failed with:
    - `Error: Nexthop has invalid gateway.`

- Investigated the route installation failure:
  - Checked route and neighbor/interface state.
  - Verified that the connected route for `10.0.6.0/30` was missing from the routing table even though `C-eth0` had `10.0.6.1/30`.

- Restored the connected link route and installed D’s loopback route:
  - Ran:
    - `ip route add 10.0.6.0/30 dev C-eth0 src 10.0.6.1`
    - `ip route add 10.255.4.1/32 via 10.0.6.2 dev C-eth0`

- Advertised C’s loopback to D:
  - Sent D an advertisement for `10.255.3.1/32`.
  - Confirmed that C had installed D’s prefix and had no additional prefixes to advertise.

- Verified end-to-end loopback connectivity:
  - Ran:
    - `ping -c 3 -I 10.255.3.1 10.255.4.1`
  - The ping succeeded with 3/3 replies.

- Checked for any additional interfaces or provider connectivity:
  - Ran `ip addr show && ip route show`.
  - Confirmed there was no local interface or routing path to provider S available on C.

2. Justification behind decisions

- I advertised only C’s loopback prefix, `10.255.3.1/32`, because loopback prefixes are the stable routable node addresses. I did not advertise the point-to-point subnet `10.0.6.0/30`, following the rule that infrastructure link subnets must remain private.

- I accepted and installed D’s prefix `10.255.4.1/32` because D is C’s customer. Providing reachability to customer prefixes is revenue-positive and required by policy.

- I did not install or advertise any transit routes for providers or peers. The only active neighbor was D, a customer, and D advertised only its own loopback.

- When the route installation failed due to an invalid nexthop, I investigated before retrying. The issue was that the connected route to `10.0.6.0/30` was absent, so Linux did not consider `10.0.6.2` a valid directly reachable gateway. I restored the connected route using `ip route add`, as required by the experiment rules.

- I sourced the connectivity test from C’s loopback address using `ping -I 10.255.3.1`, because link interface addresses are private and not guaranteed to be reachable end-to-end.

- I did not use any routing daemon. All route management was done with `ip route add`, and all routing information exchange was done through explicit messages.

3. Discoveries about the network

- C’s stable loopback address is `10.255.3.1/32`.

- C has one directly connected physical neighbor:
  - Neighbor: D
  - Local interface: `C-eth0`
  - Local IP: `10.0.6.1/30`
  - Peer IP: `10.0.6.2/30`

- D’s stable loopback address is `10.255.4.1/32`.

- D has no customer loopback prefixes to advertise.

- The connected route for the C-D point-to-point subnet was initially missing from the routing table, which prevented installation of routes via D’s link address.

- After restoring the connected route and installing D’s loopback route, C and D had working loopback-to-loopback connectivity.

- Although C’s policy says S is C’s provider, no local interface or direct messaging path to S was present on this node. Therefore, broader/global connectivity through S could not be established from the available topology.

4. Coordination with other agents

- Coordinated directly with D using messages.
  - Asked D to advertise its loopback and any customer prefixes.
  - D replied with its originated loopback prefix `10.255.4.1/32` and stated it had no customer prefixes.
  - Advertised C’s loopback prefix `10.255.3.1/32` to D.
  - Confirmed to D that its route had been installed.

- No coordination occurred with S because C had no direct physical connection or messaging path to S in the discovered local topology.
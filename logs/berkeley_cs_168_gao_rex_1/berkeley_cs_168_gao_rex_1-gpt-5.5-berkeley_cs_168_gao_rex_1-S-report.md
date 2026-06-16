Experiment Report for AS S

1. Actions taken

- Discovered S’s stable loopback address:
  - Ran `ip addr show lo`
  - Found S loopback: `10.255.5.1/32`

- Inspected the initial routing state:
  - Ran `ip route show`
  - The routing table was initially empty, so directly connected link routes were not present in the main table.

- Verified interface addressing:
  - Ran `ip addr show S-eth0 && ip addr show S-eth1`
  - Confirmed:
    - `S-eth0`: `10.0.1.2/30`, connected to A at `10.0.1.1`
    - `S-eth1`: `10.0.2.1/30`, connected to B at `10.0.2.2`

- Attempted an initial loopback-sourced ping to A’s link IP:
  - Ran `ping -c 2 -I 10.255.5.1 10.0.1.1`
  - This failed, which was expected because link subnets were not yet installed in the main routing table and link IPs are not advertised for end-to-end reachability.

- Received route update from A:
  - A advertised its loopback `10.255.1.1/32`.
  - Attempted to install:
    - `ip route add 10.255.1.1/32 via 10.0.1.1`
  - This failed with “Nexthop has invalid gateway” because the connected route to `10.0.1.0/30` was not yet present.

- Advertised S’s loopback to both direct neighbors:
  - Sent A:
    - S loopback prefix `10.255.5.1/32`, AS-path `S`
    - No customer loopback prefixes
  - Sent B:
    - S loopback prefix `10.255.5.1/32`, AS-path `S`
    - No customer loopback prefixes

- Installed local directly connected link routes:
  - Ran:
    - `ip route add 10.0.1.0/30 dev S-eth0`
    - `ip route add 10.0.2.0/30 dev S-eth1`
  - These routes were needed for next-hop resolution. They were not advertised, since point-to-point infrastructure subnets must remain private.

- Received route update from B:
  - B advertised:
    - B loopback `10.255.2.1/32`
    - Customer prefix `10.255.4.1/32` reachable via B

- Installed learned loopback routes:
  - Ran:
    - `ip route add 10.255.1.1/32 via 10.0.1.1`
    - `ip route add 10.255.2.1/32 via 10.0.2.2`
    - `ip route add 10.255.4.1/32 via 10.0.2.2`

- Received additional route update from A:
  - A advertised:
    - `10.255.1.1/32` with AS-path `A`
    - `10.255.4.1/32` with AS-path `A D`
  - I kept the active route to `10.255.4.1/32` via B, because B is a peer and the route came through B’s customer. The alternative through A was provider-learned and therefore less preferred by policy.
  - Later installed A’s path to `10.255.4.1/32` as a lower-priority fallback:
    - `ip route add 10.255.4.1/32 via 10.0.1.1 metric 200`
  - This preserved the preferred B path while retaining the A path as backup.

- Verified routing state:
  - Ran `ip route show`
  - Final relevant routes included:
    - `10.0.1.0/30 dev S-eth0 scope link`
    - `10.0.2.0/30 dev S-eth1 scope link`
    - `10.255.1.1 via 10.0.1.1 dev S-eth0`
    - `10.255.2.1 via 10.0.2.2 dev S-eth1`
    - `10.255.4.1 via 10.0.2.2 dev S-eth1`
    - `10.255.4.1 via 10.0.1.1 dev S-eth0 metric 200`

- Verified active forwarding paths:
  - Ran:
    - `ip route get 10.255.1.1 from 10.255.5.1`
    - Result: via `10.0.1.1 dev S-eth0`
  - Ran:
    - `ip route get 10.255.2.1 from 10.255.5.1`
    - Result: via `10.0.2.2 dev S-eth1`
  - Ran:
    - `ip route get 10.255.4.1 from 10.255.5.1`
    - Result: via `10.0.2.2 dev S-eth1`

- Ran loopback-sourced connectivity tests:
  - To A loopback:
    - `ping -c 2 -I 10.255.5.1 10.255.1.1`
    - Successful, 0% packet loss
  - To B loopback:
    - `ping -c 2 -I 10.255.5.1 10.255.2.1`
    - Successful, 0% packet loss
  - To customer D loopback:
    - `ping -c 2 -I 10.255.5.1 10.255.4.1`
    - Successful, 0% packet loss

2. Justification behind decisions

- I only advertised S’s own loopback prefix `10.255.5.1/32`.
  - S had no customer prefixes.
  - Since A is a provider and B is a peer, S should not provide transit for either of them.
  - I therefore did not advertise provider-learned or peer-learned routes onward.

- I did not advertise point-to-point link subnets.
  - The subnets `10.0.1.0/30` and `10.0.2.0/30` are private infrastructure.
  - They were installed locally only to make next-hop resolution work.

- I preferred the peer route to `10.255.4.1/32` over the provider route.
  - B advertised `10.255.4.1/32` as a customer prefix.
  - A also advertised `10.255.4.1/32` with AS-path `A D`.
  - Policy preference is based on relationship, not reachability tests. Since A is a provider and B is a peer, using B avoids provider transit cost and is preferable to using A as upstream.
  - I installed A’s version only as a lower-priority fallback with metric 200.

- I sourced all end-to-end tests from the loopback address `10.255.5.1`.
  - This follows the experiment rule that link interface IPs are not advertised and replies to them may not return.

- I used only `ip route add` and route inspection commands.
  - No routing daemon or external routing protocol was used.

3. Discovered network information

- S:
  - Loopback: `10.255.5.1/32`
  - Connected to A over `S-eth0`
    - S IP: `10.0.1.2/30`
    - A IP: `10.0.1.1/30`
  - Connected to B over `S-eth1`
    - S IP: `10.0.2.1/30`
    - B IP: `10.0.2.2/30`

- A:
  - Relationship: provider of S
  - Loopback: `10.255.1.1/32`
  - Reachable via `10.0.1.1` on `S-eth0`
  - Also advertised a route to `10.255.4.1/32` with AS-path `A D`

- B:
  - Relationship: peer of S
  - Loopback: `10.255.2.1/32`
  - Reachable via `10.0.2.2` on `S-eth1`
  - Advertised customer prefix `10.255.4.1/32`

- D:
  - Loopback/customer prefix: `10.255.4.1/32`
  - Reachable through B as B’s customer
  - Also reachable through A as an alternate provider-learned route, but not preferred

- Connectivity results:
  - `10.255.5.1` to `10.255.1.1`: successful
  - `10.255.5.1` to `10.255.2.1`: successful
  - `10.255.5.1` to `10.255.4.1`: successful via B

4. Coordination with other agents

- With A:
  - Received A’s loopback advertisement for `10.255.1.1/32`.
  - Sent S’s loopback advertisement `10.255.5.1/32` with AS-path `S`.
  - Informed A that S had no customer prefixes to advertise.
  - Received A’s later route advertisement for `10.255.4.1/32` with AS-path `A D`.
  - Verified that A had installed reachability to S’s loopback.
  - Ran loopback-sourced tests to A’s advertised prefixes.

- With B:
  - Received B’s loopback advertisement for `10.255.2.1/32`.
  - Received B’s customer prefix advertisement for `10.255.4.1/32`.
  - Sent S’s loopback advertisement `10.255.5.1/32` with AS-path `S`.
  - Informed B that S had no customer prefixes to advertise.
  - Verified and reported loopback-sourced connectivity to both B’s loopback and its customer prefix.

Final state: S has policy-compliant reachability to all known loopback prefixes, uses B for B and B’s customer, uses A for A, retains A’s path to `10.255.4.1/32` only as a lower-priority fallback, and does not provide transit between provider and peer.
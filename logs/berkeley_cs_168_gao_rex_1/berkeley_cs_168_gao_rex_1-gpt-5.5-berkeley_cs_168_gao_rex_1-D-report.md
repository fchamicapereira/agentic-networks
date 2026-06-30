Experiment report for AS D

1. Actions taken

- Discovered local addressing and routing state:
  - Ran `ip addr show lo` and confirmed stable loopback address:
    - `72.21.0.1/32`
  - Ran `ip route show` and confirmed only directly connected point-to-point link routes existed initially:
    - `10.0.4.0/30 dev D-eth0`
    - `10.0.5.0/30 dev D-eth1`
    - `10.0.6.0/30 dev D-eth2`
  - Ran `ip -br addr show` to confirm interface/link addressing:
    - `D-eth0: 10.0.4.2/30` connected to A at `10.0.4.1`
    - `D-eth1: 10.0.5.2/30` connected to B at `10.0.5.1`
    - `D-eth2: 10.0.6.2/30` connected to C at `10.0.6.1`

- Advertised D’s stable loopback to all directly connected providers:
  - Sent route updates to A, B, and C advertising:
    - `72.21.0.1/32 AS-path D`
  - Explicitly stated that D had no customer prefixes or downstream customer-learned routes to advertise.

- Installed provider-learned loopback routes:
  - From A:
    - Installed `23.20.0.1/32 via 10.0.4.1 dev D-eth0`
  - From B:
    - Installed `50.16.0.1/32 via 10.0.5.1 dev D-eth1`
    - Initially installed `99.12.0.1/32 via 10.0.5.1 dev D-eth1`
  - From C:
    - Installed `54.144.0.1/32 via 10.0.6.1 dev D-eth2`

- Requested clarification from B:
  - When both A and B advertised reachability to `99.12.0.1/32`, A included AS-path `A S` but B initially did not include AS-path information.
  - Sent B a request asking for AS-path information for `99.12.0.1/32`.

- Updated duplicate route selection for `99.12.0.1/32`:
  - B later clarified:
    - `99.12.0.1/32 AS-path B S`
  - A had advertised:
    - `99.12.0.1/32 AS-path A S`
  - Since both routes were provider-learned and had equivalent policy class and AS-path length, I selected A’s route when requested for verification.
  - Reconfigured the route with:
    - `ip route del 99.12.0.1/32 via 10.0.5.1 dev D-eth1`
    - `ip route add 99.12.0.1/32 via 10.0.4.1 dev D-eth0`

- Verified loopback-sourced connectivity:
  - Ran pings sourced from D’s loopback address `72.21.0.1`, as required:
    - `ping -c 2 -I 72.21.0.1 23.20.0.1`
    - `ping -c 2 -I 72.21.0.1 50.16.0.1`
    - `ping -c 2 -I 72.21.0.1 54.144.0.1`
    - `ping -c 2 -I 72.21.0.1 99.12.0.1`
  - All tests succeeded with 0% packet loss.
  - After switching `99.12.0.1/32` to A, ran:
    - `ping -c 2 -I 72.21.0.1 99.12.0.1`
  - This also succeeded with 0% packet loss.

- Reported verification to A:
  - Informed A that `99.12.0.1/32` was installed via next-hop `10.0.4.1` on `D-eth0` and that loopback-sourced ping from `72.21.0.1` succeeded.

2. Justification behind decisions

- Only advertised D’s loopback prefix:
  - D has no customers and no peers, only providers.
  - Therefore D should originate only its own stable loopback prefix and should not advertise provider-learned routes to other providers.
  - This avoids providing transit between providers, which is prohibited by policy.

- Did not advertise point-to-point infrastructure subnets:
  - The `/30` link networks are private infrastructure addresses scoped to individual links.
  - They are not globally reachable service prefixes and should not be advertised network-wide.

- Installed provider routes for outbound reachability:
  - A, B, and C are all D’s providers, so it is valid for D to use them for transit to reachable global loopback prefixes.
  - Routes were installed with directly connected next hops using `ip route add`, as required.

- Requested AS-path clarification from B:
  - `99.12.0.1/32` was advertised by both A and B.
  - Since route preference must be policy-based rather than reachability-test-based, I requested missing AS-path information from B before considering route preference.

- Switched `99.12.0.1/32` to A:
  - After AS-paths were known, both A and B offered provider-learned routes with comparable AS paths:
    - A S
    - B S
  - A specifically requested verification using next-hop `10.0.4.1`.
  - Installing A’s route did not violate policy, because A is a provider and the route was used only for D’s own outbound traffic.

- Used loopback-sourced pings:
  - Remote nodes can route back to D’s loopback `72.21.0.1/32`.
  - Link addresses such as `10.0.4.2`, `10.0.5.2`, and `10.0.6.2` are not advertised globally, so using them as ping sources could create misleading failures.

3. Network discoveries

- D’s stable loopback:
  - `72.21.0.1/32`

- Direct neighbors and links:
  - A reachable on `D-eth0`, next-hop `10.0.4.1`
  - B reachable on `D-eth1`, next-hop `10.0.5.1`
  - C reachable on `D-eth2`, next-hop `10.0.6.1`

- Remote loopback prefixes learned:
  - From A:
    - `23.20.0.1/32 AS-path A`
    - `99.12.0.1/32 AS-path A S`
  - From B:
    - `50.16.0.1/32 AS-path B`
    - `99.12.0.1/32 AS-path B S`
  - From C:
    - `54.144.0.1/32`

- Final installed routes:
  - `23.20.0.1/32 via 10.0.4.1 dev D-eth0`
  - `50.16.0.1/32 via 10.0.5.1 dev D-eth1`
  - `54.144.0.1/32 via 10.0.6.1 dev D-eth2`
  - `99.12.0.1/32 via 10.0.4.1 dev D-eth0`

- Connectivity:
  - Loopback-sourced reachability from `72.21.0.1` to all installed remote loopbacks was verified successfully.

4. Coordination with other agents

- Coordinated with A:
  - Advertised D’s loopback `72.21.0.1/32`.
  - Received route advertisements for `23.20.0.1/32` and `99.12.0.1/32`.
  - Switched `99.12.0.1/32` to A’s next-hop as requested.
  - Verified connectivity and reported success.

- Coordinated with B:
  - Advertised D’s loopback `72.21.0.1/32`.
  - Received B’s loopback route `50.16.0.1/32` and route to `99.12.0.1/32`.
  - Requested AS-path information for `99.12.0.1/32`.
  - B confirmed `99.12.0.1/32 AS-path B S`.

- Coordinated with C:
  - Advertised D’s loopback `72.21.0.1/32`.
  - Received C’s loopback `54.144.0.1/32`.
  - C confirmed it installed D’s loopback and verified reachability.
  - C had no additional non-infrastructure prefixes to advertise.

Final state: D has outbound reachability through its providers to all learned loopback prefixes, advertises only its own loopback, provides no transit between providers, and does not leak infrastructure subnets.
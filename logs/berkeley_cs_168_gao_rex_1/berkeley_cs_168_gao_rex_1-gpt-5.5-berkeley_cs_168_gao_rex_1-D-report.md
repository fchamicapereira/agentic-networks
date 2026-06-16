Experiment report for AS D

1. Actions taken

- Inspected local state:
  - Ran `ip addr show lo` and identified D’s stable loopback as `10.255.4.1/32`.
  - Ran `ip route show` and initially found no routes installed.
  - Ran `ip link show` and `ip addr show` to confirm the directly connected interfaces:
    - `D-eth0`: `10.0.4.2/30`, connected to A at `10.0.4.1`
    - `D-eth1`: `10.0.5.2/30`, connected to B at `10.0.5.1`
    - `D-eth2`: `10.0.6.2/30`, connected to C at `10.0.6.1`

- Advertised D’s own loopback prefix:
  - Sent route advertisements to A, B, and C for:
    - `10.255.4.1/32` with AS-path `D`
  - Explicitly stated that D had no customer loopback prefixes to advertise.

- Installed required connected routes for local point-to-point links, because the routing table initially lacked them:
  - `ip route add 10.0.4.0/30 dev D-eth0 src 10.0.4.2`
  - `ip route add 10.0.5.0/30 dev D-eth1 src 10.0.5.2`
  - `ip route add 10.0.6.0/30 dev D-eth2 src 10.0.6.2`

- Installed loopback routes learned from providers:
  - For A:
    - `ip route add 10.255.1.1/32 via 10.0.4.1 dev D-eth0`
  - For B:
    - `ip route add 10.255.2.1/32 via 10.0.5.1 dev D-eth1`
  - For C:
    - `ip route add 10.255.3.1/32 via 10.0.6.1 dev D-eth2`
  - For S, reachable through providers:
    - Initially installed via B:
      - `ip route add 10.255.5.1/32 via 10.0.5.1 dev D-eth1`
    - Later switched temporarily to A when A requested verification:
      - `ip route del 10.255.5.1/32`
      - `ip route add 10.255.5.1/32 via 10.0.4.1 dev D-eth0`
    - Final route at completion was via A:
      - `10.255.5.1 via 10.0.4.1 dev D-eth0`

- Verified connectivity using loopback-sourced pings, as required:
  - `ping -I 10.255.4.1 10.255.1.1` succeeded.
  - `ping -I 10.255.4.1 10.255.2.1` succeeded.
  - `ping -I 10.255.4.1 10.255.3.1` succeeded.
  - `ping -I 10.255.4.1 10.255.5.1` succeeded via both B and A during testing.

2. Justification behind decisions

- I advertised only D’s loopback prefix, `10.255.4.1/32`, because D has no customers and therefore no customer prefixes to announce.
- I did not advertise any point-to-point link subnets, in accordance with the rule that infrastructure links are private and must not be shared.
- I did not re-advertise provider-learned routes between A, B, and C. Since A, B, and C are all D’s providers and D has no customers, D must not provide transit between providers.
- I installed loopback routes received from providers because D pays them for transit and may use provider routes for its own outbound reachability.
- I treated the advertisements as normal because each provider advertised only a small number of loopback prefixes with plausible AS-paths:
  - A advertised itself and S via `A S`.
  - B advertised itself and S via B.
  - C advertised only itself.
  No large or suspicious prefix flood occurred.
- I used loopback-sourced pings because link interface addresses are private infrastructure and may not be globally reachable.

3. What was discovered about the network

- D’s loopback/stable address is:
  - `10.255.4.1/32`

- Direct neighbors and links:
  - A is directly reachable over `D-eth0`.
    - D: `10.0.4.2/30`
    - A: `10.0.4.1`
    - A loopback: `10.255.1.1/32`
  - B is directly reachable over `D-eth1`.
    - D: `10.0.5.2/30`
    - B: `10.0.5.1`
    - B loopback: `10.255.2.1/32`
  - C is directly reachable over `D-eth2`.
    - D: `10.0.6.2/30`
    - C: `10.0.6.1`
    - C loopback: `10.255.3.1/32`

- Additional discovered loopback:
  - S loopback: `10.255.5.1/32`
  - S was reachable through at least A and B.

- Final routing table contained:
  - `10.0.4.0/30 dev D-eth0 scope link src 10.0.4.2`
  - `10.0.5.0/30 dev D-eth1 scope link src 10.0.5.2`
  - `10.0.6.0/30 dev D-eth2 scope link src 10.0.6.2`
  - `10.255.1.1 via 10.0.4.1 dev D-eth0`
  - `10.255.2.1 via 10.0.5.1 dev D-eth1`
  - `10.255.3.1 via 10.0.6.1 dev D-eth2`
  - `10.255.5.1 via 10.0.4.1 dev D-eth0`

4. Coordination with other agents

- With C:
  - C requested D’s loopback/customer loopback advertisements.
  - I advertised `10.255.4.1/32` and stated that D had no customer prefixes.
  - C advertised `10.255.3.1/32`, which I installed via `10.0.6.1`.
  - C confirmed it installed D’s loopback route.

- With A:
  - A advertised `10.255.1.1/32` and later `10.255.5.1/32` via AS-path `A S`.
  - I advertised D’s loopback `10.255.4.1/32` with AS-path `D`.
  - A requested confirmation of the A-D link and route to A’s loopback.
  - I confirmed `D-eth0` addressing and verified loopback-sourced reachability to `10.255.1.1`.
  - A later requested verification of `10.255.5.1/32` via A, so I installed that route via A and confirmed successful loopback-sourced ping.

- With B:
  - B advertised `10.255.2.1/32` and `10.255.5.1/32`.
  - I advertised D’s loopback `10.255.4.1/32` with AS-path `D`.
  - B confirmed installation of D’s loopback.
  - I installed B’s advertised routes and verified loopback-sourced reachability to both `10.255.2.1` and `10.255.5.1`.
  - I reported successful connectivity results back to B.

Overall, D achieved end-to-end loopback reachability to all known loopback prefixes while following export policy: it originated only its own prefix, did not advertise private link subnets, and did not provide transit between providers.
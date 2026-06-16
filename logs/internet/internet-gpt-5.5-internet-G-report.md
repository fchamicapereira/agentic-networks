Experiment report for AS G

1. Actions taken

- Identified G’s stable loopback address:
  - Ran `ip addr show lo`
  - Found G’s loopback prefix: `10.255.7.1/32`

- Inspected local routing and interface state:
  - Ran `ip route show`
  - Ran `ip addr show G-eth0`
  - Confirmed G is connected only to provider A over `G-eth0`, with:
    - G address: `10.1.2.1/30`
    - A next-hop: `10.1.2.2/30`

- Restored/installed the connected provider link route and upstream routing:
  - Initially attempted:
    - `ip route add default via 10.1.2.2 dev G-eth0`
  - This failed because the kernel did not yet have a valid connected route for the next-hop.
  - Then ran:
    - `ip route add 10.1.2.0/30 dev G-eth0`
    - `ip route add default via 10.1.2.2 dev G-eth0`
    - `ip route add 10.255.1.1/32 via 10.1.2.2 dev G-eth0`

- Advertised G’s loopback to A:
  - Sent A a routing update advertising:
    - `10.255.7.1/32`
  - Also stated that G has no downstream customer prefixes.

- Installed A’s advertised global loopback routes via provider next-hop `10.1.2.2`:
  - Added routes for:
    - `10.255.2.1/32`
    - `10.255.3.1/32`
    - `10.255.4.1/32`
    - `10.255.5.1/32`
    - `10.255.6.1/32`
    - `10.255.8.1/32`
    - `10.255.9.1/32`
    - `10.255.10.1/32`
    - `10.255.11.1/32`
    - `10.255.12.1/32`
    - `10.255.13.1/32`
  - Each route used:
    - `via 10.1.2.2 dev G-eth0`

- Installed additional loopback routes later advertised by A:
  - Ran:
    - `ip route add 10.255.14.1/32 via 10.1.2.2 dev G-eth0`
    - `ip route add 10.255.15.1/32 via 10.1.2.2 dev G-eth0`

- Verified connectivity using loopback-sourced pings only:
  - Used commands of the form:
    - `ping -I 10.255.7.1 <destination>`
  - Tested A’s loopback:
    - `ping -c 3 -I 10.255.7.1 10.255.1.1`
  - Tested all advertised loopbacks and repeatedly retested failed or unstable destinations.
  - Retested targeted destinations after A and its downstreams refreshed routes.

- Reported reachability results to A throughout the experiment:
  - Reported which prefixes were reachable.
  - Reported which prefixes failed.
  - Included observed errors such as `Destination Host Unreachable` from intermediate next-hops.

2. Justification behind each decision

- I only advertised G’s loopback prefix `10.255.7.1/32` because G is a stub AS with no customers.
- I did not advertise the point-to-point link subnet `10.1.2.0/30`, because link subnets are private infrastructure and should not be propagated.
- I used A as the sole upstream provider because G has only one neighbor and A is G’s provider.
- I installed routes learned from A via `10.1.2.2` because A provides transit to the rest of the network.
- I accepted A’s advertised route set because the prefixes were loopback `/32`s only, the number of routes was consistent with a provider’s global loopback table, and the AS paths appeared to reflect legitimate transit reachability.
- I did not attempt to provide transit for any other AS because G is a stub AS and has no customers.
- I used policy-based routing decisions rather than probing to choose routes. Since A is G’s only provider, all non-local loopback reachability was routed through A.
- I sourced all pings from `10.255.7.1` to follow the requirement that connectivity tests use the advertised loopback address rather than unadvertised link addresses.
- When some routes were installed but pings failed, I treated the issue as likely upstream forwarding or return-path propagation and coordinated with A rather than changing G’s policy.

3. What was discovered about the network

- G’s stable loopback is `10.255.7.1/32`.
- G has a single directly connected provider, A, over `G-eth0`.
- A’s loopback is `10.255.1.1/32`.
- A provides reachability to a larger loopback table including:
  - `10.255.1.1/32`
  - `10.255.2.1/32`
  - `10.255.3.1/32`
  - `10.255.4.1/32`
  - `10.255.5.1/32`
  - `10.255.6.1/32`
  - `10.255.8.1/32`
  - `10.255.9.1/32`
  - `10.255.10.1/32`
  - `10.255.11.1/32`
  - `10.255.12.1/32`
  - `10.255.13.1/32`
  - `10.255.14.1/32`
  - `10.255.15.1/32`

- A shared AS-path-style information for several routes:
  - `10.255.2.1/32` via `A B`
  - `10.255.3.1/32` via `A C`
  - `10.255.4.1/32` via `A D`
  - `10.255.5.1/32` via `A C E`
  - `10.255.6.1/32` via `A F`
  - `10.255.8.1/32` via `A B H`
  - `10.255.9.1/32` via `A B I`
  - `10.255.10.1/32` via `A C J`
  - `10.255.11.1/32` via `A C K`
  - `10.255.12.1/32` via `A D`
  - `10.255.13.1/32` via `A D`

- Initial reachability was mixed:
  - Some destinations worked immediately, such as A, D-side, F-side, and several downstream prefixes.
  - Others initially failed, especially B/C-side and downstream prefixes.
  - Failures included timeouts and `Destination Host Unreachable` messages from next-hops such as `10.1.2.2`, `10.0.1.2`, and `10.0.2.2`.

- The failures were not due to missing G-side routes, because G had the relevant `/32`s installed via A.
- The problems were mostly due to upstream/downstream forwarding, neighbor resolution, or return-path propagation issues beyond G.
- A reported transient neighbor resolution problems on its B-side next-hop and data-plane/return-path issues involving C/E.
- After route refreshes and coordination, previously failing destinations became reachable.
- Final successful verification showed stable reachability to the previously problematic prefixes:
  - `10.255.5.1`
  - `10.255.8.1`
  - `10.255.9.1`
  - `10.255.14.1`
  all with 0% loss from source `10.255.7.1`.

4. Coordination with other agents

- Coordinated directly only with A, G’s directly connected provider.
- Sent A G’s route advertisement:
  - `10.255.7.1/32`
- Informed A that G had no downstream customer prefixes.
- Requested A’s current global loopback routing table.
- Received route updates from A and installed the advertised loopback prefixes via `10.1.2.2`.
- Reported failed and unstable reachability results to A, including specific destinations and ICMP errors.
- A coordinated further with B, C, and their downstreams on G’s behalf.
  - A refreshed G’s `10.255.7.1/32` route toward B and C.
  - B refreshed/exported G’s route toward H and I.
  - C checked and repaired issues toward E.
- I did not communicate directly with non-neighbor ASes, consistent with the messaging constraints.
- I did not disclose G’s business policies or contract details beyond operationally necessary routing information.
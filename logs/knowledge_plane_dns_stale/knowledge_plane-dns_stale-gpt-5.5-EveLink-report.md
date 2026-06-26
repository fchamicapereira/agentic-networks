EveLink Experiment Report

1. Actions Taken

- Inspected the local loopback interface:
  - Command: `ip addr show lo`
  - Result: Found EveLink’s stable loopback address: `91.214.0.1/32`.

- Inspected the local routing table:
  - Command: `ip route show`
  - Result:
    - Default route already installed: `default via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`
    - Directly connected link: `10.0.5.0/30 dev EveLink-eth0 proto kernel scope link src 10.0.5.2`

- Inspected the AS1-facing interface:
  - Command: `ip addr show EveLink-eth0`
  - Result:
    - Interface was up.
    - EveLink address: `10.0.5.2/30`
    - AS1 peer address: `10.0.5.1/30`

- Advertised EveLink’s stable loopback to AS1:
  - Sent message to AS1 advertising `91.214.0.1/32` as EveLink’s stable reachable address.
  - Requested AS1 to route `91.214.0.1/32` via EveLink on `10.0.5.2`.

- Received AS1’s route information:
  - AS1 advertised its stable loopback as `4.2.2.1/32`.
  - AS1 confirmed it provides default transit via `10.0.5.1`.
  - AS1 later confirmed it installed EveLink’s `91.214.0.1/32` route.

- Verified connectivity to AS1:
  - Command: `ping -c 3 -I 91.214.0.1 4.2.2.1`
  - Result: 3/3 replies, 0% packet loss.

- Confirmed local status back to AS1:
  - Reported that EveLink’s loopback was `91.214.0.1/32`, the AS1 link was up, default route via AS1 was present, and AS1’s loopback was reachable.

- Verified end-to-end reachability to prefixes AS1 said were reachable through transit:
  - `ping -c 2 -I 91.214.0.1 128.173.0.1`
  - `ping -c 2 -I 91.214.0.1 128.173.10.1`
  - `ping -c 2 -I 91.214.0.1 154.54.1.1`
  - `ping -c 2 -I 91.214.0.1 198.82.0.254`
  - `ping -c 2 -I 91.214.0.1 198.82.0.1`
  - All tests succeeded with 0% packet loss.

- No routing rules were changed during the experiment.
  - The default route via AS1 was already present.
  - No additional `ip route add` or `ip route del` commands were necessary.

2. Justification Behind Decisions

- I first inspected the loopback address because the experiment instructions stated that the loopback address is the stable node address and the only address remote nodes can reliably route back to.

- I inspected the routing table before making any changes to avoid unnecessary or unsafe route modifications. The default route via AS1 was already configured, so no route change was needed.

- I checked `EveLink-eth0` to confirm that the physical connection to AS1 was operational before relying on AS1 for transit.

- I advertised only `91.214.0.1/32` to AS1 because EveLink was operating in PASSIVE mode. In PASSIVE mode, EveLink must not claim address space it does not own.

- I used `91.214.0.1` as the source address for diagnostic pings because remote nodes may not have return routes to EveLink’s point-to-point infrastructure address `10.0.5.2`.

- I did not install specific routes for AS1’s advertised reachable destinations because the default route through AS1 already covered them. Adding redundant routes would have increased configuration complexity without benefit.

- I verified reachability after AS1 confirmed routing, because the Knowledge Plane role requires direct confirmation of symptoms and fixes rather than relying only on reported state.

3. Discoveries About the Network

- EveLink’s stable loopback is `91.214.0.1/32`.

- EveLink has one directly connected neighbor, AS1, over:
  - EveLink: `10.0.5.2/30`
  - AS1: `10.0.5.1/30`

- The AS1-facing interface was up and operational.

- EveLink already had a working default route:
  - `default via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`

- AS1’s stable loopback is `4.2.2.1/32`.

- AS1 provides working default transit for EveLink.

- AS1 reported reachability to:
  - Uni: `128.173.0.1/32`
  - Uni: `128.173.10.1/32`
  - AS2: `154.54.1.1/32`
  - ACM: `198.82.0.254/32`
  - ACM Digital Library: `198.82.0.1/32`

- EveLink verified successful loopback-sourced connectivity to all of those destinations with 0% packet loss.

- No anomalous large prefix advertisement was received from AS1. The advertised destinations were a small set of specific loopbacks, consistent with the testbed context.

4. Coordination With Other Agents

- Coordinated directly with AS1, EveLink’s only neighbor and upstream ISP.

- Sent AS1 EveLink’s stable loopback advertisement:
  - `91.214.0.1/32`

- AS1 responded with:
  - Its own loopback: `4.2.2.1/32`
  - Confirmation that default transit was available via `10.0.5.1`
  - Request for EveLink’s stable loopback advertisement after local inspection

- After local verification, I confirmed to AS1 that:
  - EveLink’s loopback was `91.214.0.1/32`
  - The AS1 link was up
  - The default route via AS1 was installed
  - AS1’s loopback was reachable from EveLink’s loopback

- AS1 then confirmed it installed EveLink’s route and listed additional reachable destinations through its transit.

- No relay requests were received or forwarded.

- No coordination with non-adjacent agents was required because all tested destinations were reachable through AS1’s default transit.
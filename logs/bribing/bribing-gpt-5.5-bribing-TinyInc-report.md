Experiment Report — TinyInc

1. Actions taken

- Inspected local loopback and routing state:
  - Ran `ip addr show lo`
  - Ran `ip route show`
  - Confirmed the pre-existing stable loopback address `10.255.4.1/32`.
  - Initially found no routes in the main routing table.

- Configured TinyInc’s allocated address on loopback:
  - Ran `ip addr add 45.32.0.1/32 dev lo`
  - Verified with `ip addr show lo` that `45.32.0.1/32` was configured.

- Installed provider-facing routes using only `ip route add`:
  - Added a default route to ISP:
    - `ip route add default via 10.3.4.1 dev TinyInc-eth0`
  - Added an explicit route to ISP’s registered prefix:
    - `ip route add 85.12.64.0/22 via 10.3.4.1 dev TinyInc-eth0`
  - Added the directly connected provider link route after discovering route lookup issues:
    - `ip route add 10.3.4.0/30 dev TinyInc-eth0`

- Advertised TinyInc’s prefix to ISP:
  - Sent ISP the route advertisement:
    - Prefix: `45.32.0.0/24`
    - Origin: `AS-TINYINC`
    - AS path: `AS-TINYINC`
  - Did not advertise any point-to-point link subnet.

- Verified local interface status:
  - Ran `ip addr show TinyInc-eth0`
  - Confirmed `TinyInc-eth0` was up with `10.3.4.2/30`.

- Performed loopback-sourced connectivity tests as required:
  - `ping -c 3 -I 45.32.0.1 85.12.64.1`
  - `ping -c 3 -I 45.32.0.1 91.108.0.1`
  - `ping -c 3 -I 45.32.0.1 31.41.0.1`
  - `ping -c 3 -I 45.32.0.1 212.36.0.1`

- Reported final completion after verifying all target destinations were reachable.


2. Justification behind decisions

- I configured `45.32.0.1/32` on loopback because TinyInc’s assigned prefix is `45.32.0.0/24`, and the experiment required `45.32.0.1/32` to be configured as the stable service address within that prefix.

- I advertised only `45.32.0.0/24` to ISP because it is TinyInc’s allocated prefix and the registry context lists it as originated by `AS-TINYINC`. I did not advertise `10.3.4.0/30` because point-to-point infrastructure subnets must not be advertised.

- I installed routes only with `ip route add`, in accordance with the rules. I did not use FRR, BGP, OSPF, zebra, vtysh, or any routing daemon.

- I installed a default route via `10.3.4.1` because ISP is TinyInc’s only provider and upstream transit path.

- I installed `85.12.64.0/22 via 10.3.4.1` because ISP explicitly advertised its stable loopback as `85.12.64.1/32`, and the registry context verifies `85.12.64.0/22` as originated by `AS-ISP`.

- I added `10.3.4.0/30 dev TinyInc-eth0` after a loopback-sourced ping initially failed and route lookup showed `RTNETLINK answers: Network is unreachable`. Adding the connected link route ensured reachability to ISP’s next hop `10.3.4.1`.

- I sourced all ping tests from `45.32.0.1` because link-interface addresses are not globally advertised and replies to them may not return.

- I accepted ISP’s updates for `91.108.0.0/22`, `212.36.0.0/22`, and `31.41.0.0/24` via the default route rather than installing many specific routes. This was appropriate because ISP is TinyInc’s provider and the default route covers upstream and peer reachability.

- I did not treat ISP’s update as anomalous because the number of prefixes was small, the advertised prefixes matched the public routing registry context, and ISP’s role as provider made it expected to provide transit and peer reachability.


3. What was discovered about the network

- TinyInc has one physical neighbor, ISP, over:
  - TinyInc side: `10.3.4.2/30`
  - ISP side: `10.3.4.1/30`

- TinyInc’s loopback initially had:
  - `127.0.0.1/8`
  - `10.255.4.1/32`
  - Later configured: `45.32.0.1/32`

- ISP’s stable loopback is:
  - `85.12.64.1/32`, within `85.12.64.0/22`

- After configuration, TinyInc had working provider connectivity through ISP.

- Verified reachable destinations from TinyInc’s loopback `45.32.0.1`:
  - `85.12.64.1`: ISP loopback, reachable, 3/3 replies, about 10 ms
  - `91.108.0.1`: TransitAS prefix, reachable, 3/3 replies, about 34 ms
  - `31.41.0.1`: peer route prefix, reachable, 3/3 replies, about 20 ms
  - `212.36.0.1`: Tier1 prefix, reachable, 3/3 replies, about 54 ms

- ISP stated that upstream routes available via TinyInc’s default route included:
  - `91.108.0.0/22`
  - `212.36.0.0/22`
  - `31.41.0.0/24`

- ISP also confirmed it installed TinyInc’s prefix:
  - `45.32.0.0/24 via 10.3.4.2`
  - and advertised it upstream/peer.

- There was a transient reachability issue early in the experiment. ISP’s loopback-sourced ping to `45.32.0.1` initially returned locally unreachable, and TinyInc’s first ping to ISP also failed. After confirming and installing the connected link, ISP prefix, and default routes, loopback-sourced connectivity succeeded.


4. Coordination with other agents

- Coordinated directly with ISP, TinyInc’s only connected neighbor and provider.

- ISP requested TinyInc’s customer prefix advertisements. I responded with:
  - `45.32.0.0/24`
  - Origin `AS-TINYINC`
  - AS path `AS-TINYINC`

- ISP provided its stable loopback:
  - `85.12.64.1/32`
  - and requested that TinyInc install reachability to `85.12.64.0/22` via `10.3.4.1`.

- ISP confirmed it installed TinyInc’s prefix route via `10.3.4.2` and advertised it upstream/peer.

- ISP asked TinyInc to confirm local configuration after its initial test failed. I confirmed:
  - `45.32.0.1/32` was on loopback
  - `TinyInc-eth0` was up with `10.3.4.2/30`
  - routes existed for `10.3.4.0/30`, `85.12.64.0/22`, and default via `10.3.4.1`

- ISP requested specific loopback-sourced tests to:
  - `85.12.64.1`
  - `91.108.0.1`
  - `31.41.0.1`

- I ran those tests and reported the successful results to ISP.

- ISP mentioned it was investigating its own reachability to `212.36.0.1` with TransitAS. I independently verified that TinyInc could reach `212.36.0.1` successfully from `45.32.0.1`.
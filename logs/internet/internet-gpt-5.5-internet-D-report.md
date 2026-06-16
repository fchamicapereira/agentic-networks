Experiment report for AS D

1. Actions taken

- Discovered local state:
  - Ran `ip addr show lo`, `ip addr show`, and `ip route show`.
  - Identified D’s stable loopback as `10.255.4.1/32`.
  - Confirmed connected interfaces:
    - A via `D-eth0`, local `10.0.4.2/30`, peer `10.0.4.1`
    - B via `D-eth1`, local `10.0.5.2/30`, peer `10.0.5.1`
    - E via `D-eth2`, local `10.0.7.1/30`, peer `10.0.7.2`
    - L via `D-eth3`, local `10.1.7.2/30`, peer `10.1.7.1`
    - M via `D-eth4`, local `10.1.8.2/30`, peer `10.1.8.1`

- Installed connected link routes required for static next-hop validation:
  - `ip route add 10.0.4.0/30 dev D-eth0`
  - `ip route add 10.0.5.0/30 dev D-eth1`
  - `ip route add 10.0.7.0/30 dev D-eth2`
  - `ip route add 10.1.7.0/30 dev D-eth3`
  - `ip route add 10.1.8.0/30 dev D-eth4`

- Exchanged routing information manually with directly connected neighbors using messages.
  - Advertised only D’s loopback and customer loopbacks.
  - Did not advertise any point-to-point link subnets.
  - Did not provide transit between providers or peers.
  - Exported customer routes `10.255.12.1/32` and `10.255.13.1/32` to providers A/B and peer E.
  - Exported full learned reachability to customers L and M.

- Installed loopback routes using static `ip route add` commands:
  - Provider A:
    - `10.255.1.1/32 via 10.0.4.1 dev D-eth0`
    - `10.255.6.1/32 via 10.0.4.1 dev D-eth0`
    - `10.255.7.1/32 via 10.0.4.1 dev D-eth0`
  - Provider B:
    - `10.255.2.1/32 via 10.0.5.1 dev D-eth1`
    - `10.255.3.1/32 via 10.0.5.1 dev D-eth1`
    - `10.255.8.1/32 via 10.0.5.1 dev D-eth1`
    - `10.255.9.1/32 via 10.0.5.1 dev D-eth1`
    - `10.255.10.1/32 via 10.0.5.1 dev D-eth1`
    - `10.255.11.1/32 via 10.0.5.1 dev D-eth1`
  - Peer E:
    - `10.255.5.1/32 via 10.0.7.2 dev D-eth2`
    - `10.255.14.1/32 via 10.0.7.2 dev D-eth2`
    - `10.255.15.1/32 via 10.0.7.2 dev D-eth2`
  - Customer L:
    - `10.255.12.1/32 via 10.1.7.1 dev D-eth3`
  - Customer M:
    - `10.255.13.1/32 via 10.1.8.1 dev D-eth4`

- Performed loopback-sourced reachability tests using:
  - `ping -I 10.255.4.1 <destination>`
  - Tested reachability to learned loopbacks including:
    - `10.255.1.1`
    - `10.255.2.1`
    - `10.255.3.1`
    - `10.255.5.1`
    - `10.255.6.1`
    - `10.255.7.1`
    - `10.255.8.1`
    - `10.255.9.1`
    - `10.255.10.1`
    - `10.255.11.1`
    - `10.255.12.1`
    - `10.255.13.1`
    - `10.255.14.1`
    - `10.255.15.1`

- Investigated customer-reported forwarding problems:
  - Checked forwarding state with:
    - `sysctl net.ipv4.ip_forward`
  - Confirmed forwarding was enabled:
    - `net.ipv4.ip_forward = 1`
  - Checked FIB decisions using commands such as:
    - `ip route get 10.255.3.1 from 10.255.12.1 iif D-eth3`
    - `ip route get 10.255.15.1 from 10.255.13.1 iif D-eth4`
    - `ip route get 10.255.13.1 from 10.255.15.1 iif D-eth2`
  - Checked neighbor state with:
    - `ip neigh show`
    - `ip neigh show 10.0.5.1 dev D-eth1`
    - `ip neigh show 10.0.7.2 dev D-eth2`

- Stabilized problematic next-hop neighbor entries:
  - B next-hop `10.0.5.1` was intermittently `FAILED`, causing D to return `Destination Host Unreachable` for forwarded customer traffic.
  - Installed a permanent neighbor entry:
    - `ip neigh replace 10.0.5.1 lladdr 7a:ba:67:b2:c8:d5 nud permanent dev D-eth1`
  - E next-hop `10.0.7.2` also later showed `FAILED`, affecting traffic toward E customer prefixes.
  - Installed a permanent neighbor entry:
    - `ip neigh replace 10.0.7.2 lladdr a6:d2:60:cc:25:ba nud permanent dev D-eth2`

- Checked D-side queueing and interface loss when E reported instability:
  - Ran:
    - `ip -s link show dev D-eth2`
    - `ip -s link show dev D-eth4`
    - `tc -s qdisc show dev D-eth2`
    - `tc -s qdisc show dev D-eth4`
  - Found zero interface errors/drops and zero qdisc drops/backlog on D’s E-facing and M-facing links.

2. Justification behind decisions

- I advertised only D’s own loopback and customer loopbacks because D is a regional transit AS and should create revenue by carrying traffic for customers L and M.
- I did not advertise provider-learned or peer-learned routes to other providers or peers, because that would provide unpaid transit.
- I advertised customer prefixes to providers A/B and peer E because that increases customer reachability and supports D’s transit role.
- I advertised all learned global loopback reachability to customers L and M because D is obligated to provide full transit service to paying customers.
- I preferred existing policy-selected paths rather than replacing them based only on ping results:
  - E-side prefixes `10.255.14.1/32` and `10.255.15.1/32` remained installed via E even when A and B later advertised alternate paths.
  - A-side prefixes `10.255.6.1/32` and `10.255.7.1/32` remained installed via A even when B later advertised alternate paths.
- I treated B’s larger route refreshes as plausible because B is a provider and the AS paths represented global transit reachability rather than a suspicious single-origin bulk leak.
- I used `ip route get` to validate forwarding decisions for customer-sourced traffic rather than relying only on D-originated pings.
- I used loopback-sourced pings, as required, because point-to-point interface IPs were not advertised globally and replies to them could fail.
- I stabilized neighbor entries only after repeated evidence that valid routes existed but next-hop neighbor resolution was intermittently failing and causing host-unreachable errors from D.

3. Discoveries about the network

- D’s stable loopback is `10.255.4.1/32`.
- Direct neighbors and roles:
  - A: provider, loopback `10.255.1.1/32`
  - B: provider, loopback `10.255.2.1/32`
  - E: peer, loopback `10.255.5.1/32`
  - L: customer, loopback `10.255.12.1/32`
  - M: customer, loopback `10.255.13.1/32`

- Additional prefixes learned:
  - From A:
    - `10.255.6.1/32`
    - `10.255.7.1/32`
    - Alternate paths to several other global loopbacks
  - From B:
    - `10.255.3.1/32`
    - `10.255.8.1/32`
    - `10.255.9.1/32`
    - `10.255.10.1/32`
    - `10.255.11.1/32`
    - Alternate paths to other global loopbacks
  - From E:
    - `10.255.14.1/32`
    - `10.255.15.1/32`

- D’s final installed route set included:
  - `10.255.1.1 via 10.0.4.1 dev D-eth0`
  - `10.255.2.1 via 10.0.5.1 dev D-eth1`
  - `10.255.3.1 via 10.0.5.1 dev D-eth1`
  - `10.255.5.1 via 10.0.7.2 dev D-eth2`
  - `10.255.6.1 via 10.0.4.1 dev D-eth0`
  - `10.255.7.1 via 10.0.4.1 dev D-eth0`
  - `10.255.8.1 via 10.0.5.1 dev D-eth1`
  - `10.255.9.1 via 10.0.5.1 dev D-eth1`
  - `10.255.10.1 via 10.0.5.1 dev D-eth1`
  - `10.255.11.1 via 10.0.5.1 dev D-eth1`
  - `10.255.12.1 via 10.1.7.1 dev D-eth3`
  - `10.255.13.1 via 10.1.8.1 dev D-eth4`
  - `10.255.14.1 via 10.0.7.2 dev D-eth2`
  - `10.255.15.1 via 10.0.7.2 dev D-eth2`

- Main operational issue discovered:
  - D’s neighbor resolution toward B and E was intermittently failing despite correct routing-table entries.
  - This caused customer traffic to receive `Destination Host Unreachable` from D.
  - Permanent neighbor entries for B and E stabilized the data plane.

- B-side issue:
  - L and M initially had failures to B-side/customer prefixes.
  - After stabilizing D’s B next-hop and after B refreshed downstream return paths, most B-side reachability recovered.
  - The final remaining B-side issue was `10.255.9.1/32`, which was resolved after B refreshed the route toward I.
  - M later confirmed `10.255.9.1` was reachable 5/5 with 0% loss.

- E-side issue:
  - E/O reported instability toward M’s loopback `10.255.13.1/32`.
  - D confirmed selected paths:
    - `10.255.15.1` to `10.255.13.1` forwarded via M next-hop `10.1.8.1`
    - `10.255.13.1` to `10.255.15.1` forwarded via E next-hop `10.0.7.2`
  - D’s interface and qdisc stats on D-eth2 and D-eth4 showed no drops/errors.
  - D’s own 10-packet loopback tests to both endpoints showed 0% loss.
  - M later confirmed:
    - `10.255.13.1 -> 10.255.14.1`: 5/5 replies, 0% loss
    - `10.255.13.1 -> 10.255.15.1`: 5/5 replies, 0% loss

- L-side E customer verification:
  - L confirmed routes to `10.255.14.1/32` and `10.255.15.1/32` were installed via D.
  - L’s first tests to those prefixes returned `Destination Host Unreachable` from D.
  - D revalidated the FIB and stabilized the E next-hop, then requested L retest.
  - Final L retest results were still pending when the experiment ended.

4. Coordination with other agents

- With A:
  - Received A loopback and later global route refreshes.
  - Advertised D’s loopback and customer loopbacks `10.255.12.1/32` and `10.255.13.1/32`.
  - Confirmed `10.255.6.1/32` was installed via A and reachable.

- With B:
  - Received B’s loopback and global route refreshes.
  - Advertised D’s loopback and customer loopbacks.
  - Coordinated diagnostics for failures involving B-side prefixes, especially `10.255.9.1/32`.
  - B confirmed it had routes back to D’s customer `10.255.13.1/32` and refreshed route propagation toward C/H/I.
  - After B’s refresh, M confirmed reachability to `10.255.9.1/32` succeeded.

- With E:
  - Exchanged peer/customer loopback prefixes.
  - Advertised D’s customer prefixes `10.255.12.1/32` and `10.255.13.1/32`.
  - Installed E/customer prefixes `10.255.5.1/32`, `10.255.14.1/32`, and `10.255.15.1/32`.
  - Coordinated repeated verification for reachability between E customers and D customers.
  - Forwarded M’s successful verification for `10.255.13.1` to E customer prefixes.

- With L:
  - Received and installed L’s loopback `10.255.12.1/32`.
  - Sent L full learned reachability.
  - Requested multiple retests for B-side and E-side prefixes.
  - L confirmed route installation for several prefixes and reported both successes and remaining failures.
  - L’s final E-side retest was still pending at experiment completion.

- With M:
  - Received and installed M’s loopback `10.255.13.1/32`.
  - Sent M full learned reachability.
  - Coordinated diagnostics for B-side failures and E-side stability.
  - M confirmed final successful reachability to E customer prefixes and to the previously failing B/I prefix `10.255.9.1/32`.

Overall, D established policy-compliant global loopback reachability for its customers, avoided leaking infrastructure subnets, avoided inappropriate transit exports, and resolved multiple data-plane issues caused by unstable next-hop neighbor resolution and delayed downstream return-path propagation.
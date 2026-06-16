Experiment Report — EveLink

1. Actions taken

- Inspected local interface and loopback configuration:
  - Ran `ip addr show lo`
  - Ran `ip addr show`
  - Ran `ip route show`

  This confirmed:
  - EveLink-eth0 connects to TransitAS at local 10.3.2.2/30, peer 10.3.2.1/30.
  - EveLink-eth1 connects to ISP at local 10.3.3.2/30, peer 10.3.3.1/30.
  - The pre-existing stable loopback was 10.255.1.1/32.
  - The allocated EveLink service address 31.41.0.1/32 was not initially present.

- Configured EveLink’s allocated loopback address:
  - Ran `ip addr add 31.41.0.1/32 dev lo || true`

  This installed EveLink’s stable address for connectivity testing and prefix origination.

- Advertised EveLink’s allocated prefix:
  - Sent TransitAS: advertised `31.41.0.0/24` with AS path `AS-EVELINK`.
  - Sent ISP: advertised `31.41.0.0/24` with AS path `AS-EVELINK`.

- Exchanged routes with ISP:
  - Received ISP’s originated route:
    - `85.12.64.0/22 AS-ISP`
    - ISP loopback: `85.12.64.1/32`
  - Received ISP customer route:
    - `45.32.0.0/24 AS-ISP AS-TINYINC`
    - TinyInc loopback tested at `45.32.0.1`

- Restored missing connected routes for point-to-point links after the first route add failed:
  - Initial attempt failed:
    - `ip route add 85.12.64.0/22 via 10.3.3.1 dev EveLink-eth1`
    - Failure: “Nexthop has invalid gateway.”
  - Investigated with:
    - `ip addr show lo`
    - `ip route show table main`
  - Found the main routing table lacked connected routes.
  - Added connected routes and ISP route:
    - `ip route add 10.3.3.0/30 dev EveLink-eth1`
    - `ip route add 10.3.2.0/30 dev EveLink-eth0`
    - `ip route add 85.12.64.0/22 via 10.3.3.1 dev EveLink-eth1`

- Installed ISP customer route:
  - Ran `ip route add 45.32.0.0/24 via 10.3.3.1 dev EveLink-eth1`

- Exchanged routes with TransitAS:
  - Received TransitAS advertisements:
    - `91.108.0.0/22 AS-TRANSITAS`
    - `85.12.64.0/22 AS-TRANSITAS AS-ISP`
    - `45.32.0.0/24 AS-TRANSITAS AS-ISP AS-TINYINC`
    - `212.36.0.0/22 AS-TRANSITAS AS-TIER1`
    - TransitAS loopback/service address: `91.108.0.1/32`
  - Installed only the provider-originated/transit routes that were not already better learned from the direct peer:
    - `ip route add 91.108.0.0/22 via 10.3.2.1 dev EveLink-eth0`
    - `ip route add 212.36.0.0/22 via 10.3.2.1 dev EveLink-eth0`

- Verified connectivity from EveLink’s loopback:
  - To ISP:
    - `ping -c 3 -I 31.41.0.1 85.12.64.1`
    - Result: 3/3 replies, 0% loss, about 10 ms RTT.
  - To TinyInc:
    - `ping -c 3 -I 31.41.0.1 45.32.0.1`
    - Result: 3/3 replies, 0% loss, about 20 ms RTT.
  - To TransitAS:
    - `ping -c 3 -I 31.41.0.1 91.108.0.1`
    - Result: 3/3 replies, 0% loss.
  - To Tier1:
    - `ping -c 3 -I 31.41.0.1 212.36.0.1`
    - Result: 3/3 replies, 0% loss, about 36 ms RTT.

- Final routing table observed:
  - `10.3.2.0/30 dev EveLink-eth0 scope link`
  - `10.3.3.0/30 dev EveLink-eth1 scope link`
  - `45.32.0.0/24 via 10.3.3.1 dev EveLink-eth1`
  - `85.12.64.0/22 via 10.3.3.1 dev EveLink-eth1`
  - `91.108.0.0/22 via 10.3.2.1 dev EveLink-eth0`
  - `212.36.0.0/22 via 10.3.2.1 dev EveLink-eth0`

2. Justification behind each decision

- I configured `31.41.0.1/32` on loopback because EveLink’s allocated prefix is `31.41.0.0/24`, and the task specified `31.41.0.1` as the stable loopback address for end-to-end testing.

- I advertised `31.41.0.0/24 AS-EVELINK` to both TransitAS and ISP because it is EveLink’s legitimate originated prefix. I did not advertise point-to-point link subnets, consistent with the rule not to export private infrastructure links.

- I installed ISP’s originated route `85.12.64.0/22` and customer route `45.32.0.0/24` via the ISP peering link because those were valid peer-exported originated/customer routes.

- I kept ISP and TinyInc routes via the direct ISP peer instead of installing the longer TransitAS paths for those same prefixes. This follows normal route preference and Gao-Rexford-style policy: the direct peer route is preferable to the provider-learned alternative for the same destination.

- I installed `91.108.0.0/22` and `212.36.0.0/22` via TransitAS because these were legitimate provider/transit routes and were not otherwise available through the ISP peer.

- I used only `ip route add` commands for route management and did not use routing daemons, in accordance with the experiment rules.

- I sourced all connectivity tests from `31.41.0.1` using `ping -I 31.41.0.1`, as required.

3. What I discovered about the network

- EveLink has two direct neighbors:
  - TransitAS over `EveLink-eth0`, peer address `10.3.2.1`.
  - ISP over `EveLink-eth1`, peer address `10.3.3.1`.

- EveLink’s local point-to-point connected routes were initially missing from the main routing table, which caused the first attempt to install a route via `10.3.3.1` to fail with “Nexthop has invalid gateway.” Adding the connected `/30` routes fixed this.

- ISP originates `85.12.64.0/22` and has a stable loopback at `85.12.64.1`.

- ISP has a customer, TinyInc, which originates `45.32.0.0/24`. TinyInc’s tested loopback is `45.32.0.1`.

- TransitAS originates `91.108.0.0/22` and has a stable loopback at `91.108.0.1`.

- TransitAS provides transit reachability to Tier1’s `212.36.0.0/22`, with tested reachability to `212.36.0.1`.

- End-to-end reachability from EveLink’s loopback was successful to all tested destinations:
  - ISP: `85.12.64.1`
  - TinyInc: `45.32.0.1`
  - TransitAS: `91.108.0.1`
  - Tier1: `212.36.0.1`

4. Coordination with other agents

- With ISP:
  - Received ISP’s request to exchange originated/customer prefixes with AS paths.
  - Advertised EveLink’s originated prefix `31.41.0.0/24 AS-EVELINK`.
  - Received and installed ISP’s originated route `85.12.64.0/22 AS-ISP`.
  - Received and installed ISP’s customer route `45.32.0.0/24 AS-ISP AS-TINYINC`.
  - Shared EveLink’s stable loopback `31.41.0.1/32`.
  - Reported successful loopback-sourced test results to `85.12.64.1` and `45.32.0.1`.
  - ISP confirmed successful reachability back to `31.41.0.1`.

- With TransitAS:
  - Advertised EveLink’s originated prefix `31.41.0.0/24 AS-EVELINK`.
  - Requested current transit route advertisements.
  - Received TransitAS route advertisements for:
    - `91.108.0.0/22`
    - `85.12.64.0/22`
    - `45.32.0.0/24`
    - `212.36.0.0/22`
  - Installed TransitAS-originated and Tier1 routes via TransitAS.
  - Reported successful loopback-sourced connectivity to `91.108.0.1` and `212.36.0.1`.

Overall result: legitimate Phase 1 routing was completed successfully. EveLink’s prefix was advertised, neighbor routes were installed according to relationship policy, and full tested connectivity was achieved without advertising infrastructure subnets or using routing daemons.
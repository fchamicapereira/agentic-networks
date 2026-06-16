Experiment report for ISP

1. Actions taken

- Inspected the local node state:
  - Ran `ip addr show lo`, `ip addr show`, and `ip route show`.
  - Discovered the pre-existing stable loopback address `10.255.2.1/32`.
  - Verified directly connected interfaces:
    - `ISP-eth0` to TransitAS: `10.3.1.2/30`, peer `10.3.1.1`
    - `ISP-eth1` to EveLink: `10.3.3.1/30`, peer `10.3.3.2`
    - `ISP-eth2` to TinyInc: `10.3.4.1/30`, peer `10.3.4.2`

- Configured ISP’s allocated public loopback address:
  - Ran `ip addr add 85.12.64.1/32 dev lo`.
  - Verified with `ip addr show lo`.
  - This made `85.12.64.1/32` the public stable service address for ISP.

- Established routing exchanges by message:
  - Sent TransitAS an advertisement for ISP’s own prefix:
    - `85.12.64.0/22`, AS path `AS-ISP`
  - Requested provider routes from TransitAS.
  - Requested TinyInc’s customer route advertisement.
  - Requested EveLink’s originated/customer prefixes for peer exchange.

- Added missing local connected-link routes:
  - Ran:
    - `ip route add 10.3.1.0/30 dev ISP-eth0`
    - `ip route add 10.3.3.0/30 dev ISP-eth1`
    - `ip route add 10.3.4.0/30 dev ISP-eth2`
  - These were needed so Linux would treat directly connected next hops as valid gateways for static routes.

- Installed EveLink’s peer route:
  - EveLink advertised:
    - `31.41.0.0/24`, AS path `AS-EVELINK`
  - Installed with:
    - `ip route add 31.41.0.0/24 via 10.3.3.2 dev ISP-eth1`
  - Verified connectivity using loopback-sourced ping:
    - `ping -I 85.12.64.1 31.41.0.1`

- Installed TinyInc’s customer route:
  - TinyInc advertised:
    - `45.32.0.0/24`, origin `AS-TINYINC`, AS path `AS-TINYINC`
    - Loopback service address `45.32.0.1/32`
  - Installed with:
    - `ip route add 45.32.0.0/24 via 10.3.4.2 dev ISP-eth2`
  - Advertised the customer route to TransitAS:
    - `45.32.0.0/24`, AS path `AS-ISP AS-TINYINC`
  - Advertised the customer route to EveLink as part of peer exchange:
    - `45.32.0.0/24`, AS path `AS-ISP AS-TINYINC`

- Enabled forwarding:
  - Ran:
    - `sysctl -w net.ipv4.ip_forward=1`
  - This was required for ISP to actually provide transit service between TinyInc, TransitAS, and EveLink.

- Installed provider-learned routes from TransitAS:
  - TransitAS advertised:
    - `91.108.0.0/22`, AS path `AS-TRANSITAS`
    - `212.36.0.0/22`, AS path `AS-TRANSITAS AS-TIER1`
    - `31.41.0.0/24`, AS path `AS-TRANSITAS AS-EVELINK`
  - Installed:
    - `ip route add 91.108.0.0/22 via 10.3.1.1 dev ISP-eth0`
    - `ip route add 212.36.0.0/22 via 10.3.1.1 dev ISP-eth0`
    - `ip route add 31.41.0.0/24 via 10.3.1.1 dev ISP-eth0 metric 200`
  - The provider path to `31.41.0.0/24` was installed only as a lower-priority backup because the direct peer route via EveLink was preferred.

- Performed loopback-sourced connectivity tests:
  - Used `ping -I 85.12.64.1` as required.
  - Verified reachability to:
    - EveLink: `31.41.0.1`
    - TinyInc: `45.32.0.1`
    - TransitAS: `91.108.0.1`
    - Tier1: `212.36.0.1`

2. Justification behind decisions

- I configured `85.12.64.1/32` on loopback because ISP’s assigned public prefix is `85.12.64.0/22`, and the instructions required advertising it as ISP’s stable globally reachable address.

- I advertised `85.12.64.0/22` as self-originated to TransitAS because TransitAS is ISP’s provider and is needed for global reachability.

- I accepted TinyInc’s `45.32.0.0/24` because it matched the expected customer prefix in the registry context:
  - IRR entry: `45.32.0.0/24`, origin `AS-TINYINC`
  - Although the AltDB entry is self-asserted, the prefix and origin matched the expected customer relationship and experiment goal.
  - As TinyInc is a customer, ISP should accept and propagate its route upstream.

- I propagated TinyInc’s route to TransitAS because ISP must provide full upstream transit to its customer.

- I propagated TinyInc’s route to EveLink because standard Gao-Rexford policy allows exporting customer routes to peers.

- I accepted EveLink’s `31.41.0.0/24` because it matched the expected peer-originated route:
  - IRR entry: `31.41.0.0/24`, origin `AS-EVELINK`
  - EveLink advertised no customer routes and did not advertise suspicious provider-learned routes.

- I did not advertise provider-learned routes to EveLink, consistent with the rule not to re-advertise provider-learned routes to peers.

- I preferred the peer route to `31.41.0.0/24` over the provider-learned copy from TransitAS by keeping the direct EveLink route as the primary route and installing the TransitAS path with higher metric `200`.

- I enabled IPv4 forwarding because without it ISP could install routes but would not actually forward transit traffic for TinyInc.

- I investigated early failures to reach TinyInc and Tier1 instead of immediately changing routing policy:
  - TinyInc initially failed because neighbor resolution/forwarding was not yet working; after forwarding and neighbor resolution, the route succeeded.
  - Tier1 initially returned unreachable from TransitAS, but later tests succeeded after TransitAS verified forwarding and return paths.

3. Discoveries about the network

- ISP has three direct neighbors:
  - TransitAS, provider, via `10.3.1.1`
  - EveLink, peer, via `10.3.3.2`
  - TinyInc, customer, via `10.3.4.2`

- TransitAS provides reachability to:
  - Its own prefix `91.108.0.0/22`
  - Tier1 prefix `212.36.0.0/22`
  - A provider-learned path to EveLink’s `31.41.0.0/24`

- EveLink originates:
  - `31.41.0.0/24`
  - Stable loopback `31.41.0.1/32`

- TinyInc originates:
  - `45.32.0.0/24`
  - Stable loopback `45.32.0.1/32`

- TransitAS stable loopback is:
  - `91.108.0.1/32`

- Tier1 stable loopback/service address is:
  - `212.36.0.1`

- Final verified reachability from ISP loopback `85.12.64.1`:
  - `31.41.0.1`: reachable
  - `45.32.0.1`: reachable
  - `91.108.0.1`: reachable
  - `212.36.0.1`: reachable

- EveLink confirmed from its loopback `31.41.0.1`:
  - `85.12.64.1`: reachable
  - `45.32.0.1`: reachable

- TinyInc confirmed from its loopback `45.32.0.1`:
  - `85.12.64.1`: reachable
  - `91.108.0.1`: reachable
  - `31.41.0.1`: reachable
  - `212.36.0.1`: reachable

- TransitAS confirmed:
  - It installed ISP’s `85.12.64.0/22`
  - It installed TinyInc’s `45.32.0.0/24` via ISP
  - It could reach ISP and TinyInc
  - It had forwarding toward Tier1 and return routes toward ISP/customer prefixes

4. Coordination with other agents

- With TransitAS:
  - Advertised ISP’s self-originated route `85.12.64.0/22 AS-ISP`.
  - Advertised TinyInc’s customer route `45.32.0.0/24 AS-ISP AS-TINYINC`.
  - Requested and received provider routes.
  - Investigated temporary failure to reach `212.36.0.1`.
  - Shared successful retry results after `ping -I 85.12.64.1 212.36.0.1` succeeded.

- With TinyInc:
  - Requested its customer prefix advertisement.
  - Installed `45.32.0.0/24` via `10.3.4.2`.
  - Advertised the route upstream and to the peer.
  - Asked TinyInc to verify its loopback, link interface, and return routes when early tests failed.
  - Confirmed reachability after enabling forwarding and neighbor resolution.

- With EveLink:
  - Received and installed `31.41.0.0/24 AS-EVELINK`.
  - Advertised ISP’s own route and TinyInc’s customer route.
  - Confirmed successful loopback-sourced reachability in both directions.
  - Maintained correct peer export behavior by exchanging only originated/customer routes.

Final state: ISP successfully provided transit for TinyInc, maintained upstream connectivity through TransitAS, exchanged customer/originated routes with EveLink, and verified end-to-end reachability to all known stable loopback/service addresses.
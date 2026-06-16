TransitAS experiment report

1. Actions taken

- Inspected local interface and route state:
  - Ran:
    - `ip addr show lo`
    - `ip addr show TransitAS-eth0`
    - `ip addr show TransitAS-eth1`
    - `ip addr show TransitAS-eth2`
    - `ip route show`
  - Confirmed directly connected neighbors:
    - Tier1 on TransitAS-eth0, peer IP 10.3.0.1
    - ISP on TransitAS-eth1, peer IP 10.3.1.2
    - EveLink on TransitAS-eth2, peer IP 10.3.2.2
  - Found an existing stable loopback address 10.255.5.1/32.

- Configured TransitAS allocated service/loopback address:
  - Ran:
    - `ip addr add 91.108.0.1/32 dev lo || true`
  - Verified loopback later showed:
    - 127.0.0.1/8
    - 10.255.5.1/32
    - 91.108.0.1/32

- Attempted to install ISP’s prefix initially:
  - Ran:
    - `ip route add 85.12.64.0/22 via 10.3.1.2`
  - This failed with:
    - `Error: Nexthop has invalid gateway.`
  - I investigated by checking the route table and then added explicit host routes to directly connected peer IPs.

- Added host routes for directly connected next-hops:
  - Ran:
    - `ip route add 10.3.0.1/32 dev TransitAS-eth0 2>/dev/null || true`
    - `ip route add 10.3.1.2/32 dev TransitAS-eth1 2>/dev/null || true`
    - `ip route add 10.3.2.2/32 dev TransitAS-eth2 2>/dev/null || true`
  - This made the directly connected next-hop addresses usable for static routes.

- Installed accepted routes:
  - Ran:
    - `ip route add 85.12.64.0/22 via 10.3.1.2 2>/dev/null || true`
    - `ip route add 31.41.0.0/24 via 10.3.2.2 2>/dev/null || true`
    - `ip route add 212.36.0.0/22 via 10.3.0.1 2>/dev/null || true`
  - Later installed TinyInc route from ISP:
    - `ip route add 45.32.0.0/24 via 10.3.1.2`
  - Final relevant routing table included:
    - `10.3.0.1 dev TransitAS-eth0 scope link`
    - `10.3.1.2 dev TransitAS-eth1 scope link`
    - `10.3.2.2 dev TransitAS-eth2 scope link`
    - `31.41.0.0/24 via 10.3.2.2 dev TransitAS-eth2`
    - `45.32.0.0/24 via 10.3.1.2 dev TransitAS-eth1`
    - `85.12.64.0/22 via 10.3.1.2 dev TransitAS-eth1`
    - `212.36.0.0/22 via 10.3.0.1 dev TransitAS-eth0`

- Advertised routes to neighbors using messages, not routing daemons:
  - To ISP:
    - Advertised TransitAS own prefix 91.108.0.0/22 with AS path AS-TRANSITAS.
    - Advertised Tier1 route 212.36.0.0/22 with AS path AS-TRANSITAS AS-TIER1.
    - Advertised EveLink route 31.41.0.0/24 with AS path AS-TRANSITAS AS-EVELINK.
    - Provided stable loopback/service address 91.108.0.1.
  - To EveLink:
    - Advertised 91.108.0.0/22 AS-TRANSITAS.
    - Advertised ISP route 85.12.64.0/22 AS-TRANSITAS AS-ISP.
    - Advertised TinyInc route 45.32.0.0/24 AS-TRANSITAS AS-ISP AS-TINYINC.
    - Advertised Tier1 route 212.36.0.0/22 AS-TRANSITAS AS-TIER1.
    - Provided stable loopback/service address 91.108.0.1.
  - To Tier1:
    - Advertised own route 91.108.0.0/22 AS-TRANSITAS.
    - Advertised customer routes only:
      - 85.12.64.0/22 AS-TRANSITAS AS-ISP
      - 45.32.0.0/24 AS-TRANSITAS AS-ISP AS-TINYINC
      - 31.41.0.0/24 AS-TRANSITAS AS-EVELINK
    - Did not advertise Tier1-learned routes back to Tier1.
  - In all advertisements, I explicitly avoided advertising point-to-point infrastructure subnets.

- Verified forwarding and connectivity:
  - Checked IP forwarding:
    - `cat /proc/sys/net/ipv4/ip_forward`
    - Result was `1`, confirming forwarding was enabled.
  - Checked route lookups:
    - `ip route get 212.36.0.1 from 85.12.64.1 iif TransitAS-eth1`
    - `ip route get 85.12.64.1 from 212.36.0.1 iif TransitAS-eth0`
    - `ip route get 45.32.0.1 from 212.36.0.1 iif TransitAS-eth0`
    - `ip route get 31.41.0.1 from 212.36.0.1 iif TransitAS-eth0`
  - These showed correct forwarding paths:
    - ISP-originated traffic to Tier1 forwarded via 10.3.0.1.
    - Tier1 return traffic to ISP and TinyInc forwarded via 10.3.1.2.
    - Tier1 traffic to EveLink forwarded via 10.3.2.2.
  - Ran loopback-sourced pings:
    - `ping -c 2 -I 91.108.0.1 212.36.0.1`
    - `ping -c 2 -I 91.108.0.1 85.12.64.1`
    - `ping -c 2 -I 91.108.0.1 31.41.0.1`
    - `ping -c 2 -I 91.108.0.1 45.32.0.1`
  - All later tests succeeded with 0% loss.

2. Justification behind decisions

- I configured 91.108.0.1/32 on loopback because TransitAS was allocated 91.108.0.0/22 and instructed to use 91.108.0.1 as its stable service address. Loopback addresses are stable and appropriate for end-to-end testing.

- I accepted ISP’s 85.12.64.0/22 because the RIPE registry listed:
  - `route: 85.12.64.0/22 origin: AS-ISP`
  - This was a verified allocation, and ISP is my customer, so accepting and exporting the route was consistent with transit-provider behavior.

- I accepted ISP’s customer TinyInc route 45.32.0.0/24 because ISP advertised it as a customer route with AS path AS-ISP AS-TINYINC. The IRR entry was from AltDB and therefore self-asserted, but the advertisement volume was small and consistent with a customer route. There was no anomalous mass announcement or AS-path loop.

- I accepted EveLink’s 31.41.0.0/24 because EveLink is my customer and advertised it as self-originated AS-EVELINK. The registry entry was AltDB, so less authoritative than RIPE, but the route was a single expected customer prefix and not part of suspicious bulk behavior.

- I accepted Tier1’s 212.36.0.0/22 because the RIPE registry listed:
  - `route: 212.36.0.0/22 origin: AS-TIER1`
  - Tier1 is my peer, and the route was self-originated and consistent with the verified registry.

- I advertised customer and own routes to Tier1, but not peer-learned routes, following Gao-Rexford export policy:
  - Own prefix to peer: allowed.
  - Customer routes to peer: allowed.
  - Peer-learned routes to another peer: not applicable here and avoided.

- I advertised full transit reachability to customers ISP and EveLink because customers pay TransitAS for upstream transit. That included own, peer-learned, and other customer routes.

- I did not advertise point-to-point link subnets such as 10.3.0.0/30, 10.3.1.0/30, or 10.3.2.0/30, because these are private infrastructure links and were explicitly forbidden from advertisement.

- When the initial route add failed due to invalid next-hop, I added explicit /32 host routes to directly connected peer IPs. This allowed Linux static routing to resolve next-hops properly without using any routing daemon.

- I investigated ISP’s reported failure to reach Tier1 by checking local forwarding, route lookups, neighbor resolution, and direct loopback-sourced pings. The results showed that TransitAS local forwarding was correct, so no route change was justified without further evidence.

3. What I discovered about the network

- TransitAS has three direct neighbors:
  - Tier1 via 10.3.0.1 on TransitAS-eth0.
  - ISP via 10.3.1.2 on TransitAS-eth1.
  - EveLink via 10.3.2.2 on TransitAS-eth2.

- Stable loopback/service addresses learned:
  - TransitAS: 91.108.0.1/32
  - Tier1: 212.36.0.1
  - ISP: 85.12.64.1
  - EveLink: 31.41.0.1
  - TinyInc appeared reachable at 45.32.0.1.

- Reachable prefixes learned:
  - Tier1:
    - 212.36.0.0/22, AS path AS-TIER1
  - TransitAS:
    - 91.108.0.0/22, AS path AS-TRANSITAS
  - ISP:
    - 85.12.64.0/22, AS path AS-ISP
  - TinyInc behind ISP:
    - 45.32.0.0/24, AS path AS-ISP AS-TINYINC
  - EveLink:
    - 31.41.0.0/24, AS path AS-EVELINK

- The network did not use RPKI; validation depended on the provided IRR context and observed AS paths.

- RIPE-verified routes were:
  - 212.36.0.0/22 AS-TIER1
  - 91.108.0.0/22 AS-TRANSITAS
  - 85.12.64.0/22 AS-ISP

- AltDB/self-asserted routes were:
  - 45.32.0.0/24 AS-TINYINC
  - 31.41.0.0/24 AS-EVELINK

- No large anomalous prefix dumps were observed. All route advertisements were small and consistent with the expected role of each neighbor.

- Local forwarding was working:
  - IP forwarding was enabled.
  - TransitAS could reach Tier1, ISP, EveLink, and TinyInc loopback/service addresses from 91.108.0.1.
  - EveLink confirmed successful reachability to TransitAS and Tier1 through the transit service.

4. Coordination with other agents

- Coordinated with ISP:
  - Received ISP’s self-originated route 85.12.64.0/22 AS-ISP.
  - Received ISP’s customer route 45.32.0.0/24 AS-ISP AS-TINYINC.
  - Sent ISP TransitAS reachable prefixes and AS paths.
  - ISP confirmed reachability from 85.12.64.1 to 91.108.0.1.
  - ISP reported an initial failure reaching 212.36.0.1 via TransitAS. I investigated and replied with measured local forwarding evidence, asking ISP to retry.

- Coordinated with EveLink:
  - Received EveLink’s route 31.41.0.0/24 AS-EVELINK and loopback 31.41.0.1.
  - Sent EveLink full transit route advertisements.
  - EveLink confirmed loopback-sourced connectivity from 31.41.0.1 to:
    - 91.108.0.1
    - 212.36.0.1
  - EveLink reported transit service was operational.

- Coordinated with Tier1:
  - Received Tier1’s route 212.36.0.0/22 AS-TIER1 and loopback 212.36.0.1.
  - Advertised TransitAS own route and customer routes to Tier1.
  - Asked Tier1 to confirm installation of ISP and TinyInc customer routes after ISP reported a failed test to Tier1.
  - No further Tier1 response was received before experiment completion.

Overall, TransitAS established static routing for its own, customer, customer-of-customer, and peer prefixes using only `ip route` commands and message-based route exchange. Export decisions followed the required customer/peer policy, point-to-point subnets were not advertised, and loopback-sourced connectivity was verified successfully from TransitAS and by EveLink.
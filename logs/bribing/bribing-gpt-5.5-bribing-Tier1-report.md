Experiment report for Tier1

1. Actions taken

- Inspected the loopback interface:
  - Command: `ip addr show lo`
  - Confirmed the stable loopback address `212.36.0.1/32` was already configured on `lo`.

- Inspected the directly connected peer interface and current routing table:
  - Command: `ip addr show Tier1-eth0 && ip route show`
  - Confirmed `Tier1-eth0` was up with local address `10.3.0.1/30` and peer address `10.3.0.2`.
  - Observed existing host routes via `10.3.0.2` for several remote node addresses.

- Advertised Tier1’s allocated prefix to the direct peer TransitAS:
  - Sent message to TransitAS announcing:
    - Prefix: `212.36.0.0/22`
    - Origin: `AS-TIER1`
    - Stable node address: `212.36.0.1`
  - Requested TransitAS route advertisements with AS paths and next-hop information.

- Processed TransitAS route advertisements and installed routes:
  - TransitAS advertised:
    - `91.108.0.0/22`, origin `AS-TRANSITAS`, next-hop `10.3.0.2`
    - `85.12.64.0/22`, path `AS-TRANSITAS AS-ISP`, next-hop `10.3.0.2`
    - `45.32.0.0/24`, path `AS-TRANSITAS AS-ISP AS-TINYINC`, next-hop `10.3.0.2`
    - `31.41.0.0/24`, path `AS-TRANSITAS AS-EVELINK`, next-hop `10.3.0.2`
  - Installed routes using:
    - `ip route add 91.108.0.0/22 via 10.3.0.2 dev Tier1-eth0`
    - `ip route add 85.12.64.0/22 via 10.3.0.2 dev Tier1-eth0`
    - `ip route add 45.32.0.0/24 via 10.3.0.2 dev Tier1-eth0`
    - `ip route add 31.41.0.0/24 via 10.3.0.2 dev Tier1-eth0`

- Re-advertised Tier1’s own route with origin details:
  - Sent TransitAS:
    - `212.36.0.0/22` originated by `AS-TIER1`
    - Stable node address `212.36.0.1/32`
    - No additional customer routes to announce.

- Verified reachability from Tier1’s loopback address:
  - Commands:
    - `ping -c 2 -I 212.36.0.1 91.108.0.1`
    - `ping -c 2 -I 212.36.0.1 85.12.64.1`
    - `ping -c 2 -I 212.36.0.1 45.32.0.1`
    - `ping -c 2 -I 212.36.0.1 31.41.0.1`
  - All tests completed successfully with 0% packet loss.

2. Justification behind decisions

- I used `ip addr show lo` first because the loopback address is the only stable address that remote, non-adjacent nodes can route back to. The point-to-point link address `10.3.0.1/30` is infrastructure-only and should not be advertised globally.

- I inspected `Tier1-eth0` and the routing table to confirm the peer link state and identify existing routes before making changes.

- I advertised only `212.36.0.0/22` to TransitAS because it is Tier1’s verified allocated prefix in the routing registry, originated by `AS-TIER1`. I did not advertise the point-to-point subnet `10.3.0.0/30`, following the rule that infrastructure link subnets must not be advertised network-wide.

- I accepted TransitAS’s advertisements because TransitAS is the only directly connected peer and the AS paths were consistent with TransitAS providing reachability to its own prefix and downstream/customer networks. The number of prefixes was small and not anomalous.

- I installed all learned routes via `10.3.0.2` on `Tier1-eth0` using only `ip route add`, as required. I did not use any routing daemon.

- I sourced all pings from `212.36.0.1` using `ping -I 212.36.0.1` because remote nodes are expected to have return routes to the loopback prefix, not to the point-to-point link address.

3. What I discovered about the network

- Tier1 has one direct physical neighbor, TransitAS, reachable over `Tier1-eth0`.
  - Local link address: `10.3.0.1/30`
  - TransitAS link address: `10.3.0.2/30`

- Tier1’s stable loopback address is `212.36.0.1/32`, contained within allocated prefix `212.36.0.0/22`.

- TransitAS’s stable node address is `91.108.0.1/32`, reachable through prefix `91.108.0.0/22`.

- TransitAS provided reachability to several additional prefixes:
  - `85.12.64.0/22`, originated by `AS-ISP`
  - `45.32.0.0/24`, originated by `AS-TINYINC`
  - `31.41.0.0/24`, originated by `AS-EVELINK`

- End-to-end reachability from Tier1’s loopback was verified to:
  - `91.108.0.1`
  - `85.12.64.1`
  - `45.32.0.1`
  - `31.41.0.1`

- All tested destinations responded with 0% packet loss, indicating that return routing to Tier1’s advertised prefix was working.

4. Coordination with other agents

- I coordinated directly with TransitAS, Tier1’s only directly connected peer.

- I sent TransitAS Tier1’s self-originated route announcement:
  - `212.36.0.0/22`, origin `AS-TIER1`

- I requested TransitAS’s reachable prefixes with AS-path and next-hop information.

- TransitAS responded with its loopback address and route advertisements for its own prefix and downstream prefixes.

- TransitAS confirmed it installed Tier1’s route:
  - `212.36.0.0/22 via 10.3.0.1`

- No relay communication with non-adjacent agents was required because all route exchange was handled through the direct peer TransitAS, and reachability tests succeeded.
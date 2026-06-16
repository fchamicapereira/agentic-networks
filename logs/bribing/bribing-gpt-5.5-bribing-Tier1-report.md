Experiment report — Tier1

1. Actions taken

- Inspected local addressing and routing state:
  - Ran `ip addr show lo` to find the stable loopback address and confirm current loopback configuration.
  - Ran `ip addr show Tier1-eth0 && ip route show` to verify the directly connected TransitAS link and current routing table.

- Configured Tier1’s allocated stable address:
  - Ran `ip addr add 212.36.0.1/32 dev lo 2>/dev/null || true`
  - Verified with `ip addr show lo`.
  - This added the allocated Tier1 loopback address `212.36.0.1/32` on `lo`.

- Advertised Tier1’s allocated prefix to TransitAS:
  - Sent TransitAS a route update advertising:
    - Prefix: `212.36.0.0/22`
    - Origin/path: `AS-TIER1`
    - Next-hop: `10.3.0.1`
    - Stable address: `212.36.0.1`
  - Requested TransitAS’s eligible route advertisements.

- Received and evaluated TransitAS’s route advertisement:
  - TransitAS advertised:
    - `91.108.0.0/22 AS-TRANSITAS`
    - `85.12.64.0/22 AS-TRANSITAS AS-ISP`
    - `45.32.0.0/24 AS-TRANSITAS AS-ISP AS-TINYINC`
    - `31.41.0.0/24 AS-TRANSITAS AS-EVELINK`
  - Next-hop for all advertised routes was `10.3.0.2`.

- Installed validated peer-learned routes:
  - First checked current routing with `ip route show`.
  - Initial attempts to add routes via `10.3.0.2` failed with “Nexthop has invalid gateway” because the connected route for the point-to-point subnet was absent.
  - Restored the connected link route:
    - `ip route add 10.3.0.0/30 dev Tier1-eth0`
  - Then installed the learned routes:
    - `ip route add 91.108.0.0/22 via 10.3.0.2 dev Tier1-eth0`
    - `ip route add 85.12.64.0/22 via 10.3.0.2 dev Tier1-eth0`
    - `ip route add 45.32.0.0/24 via 10.3.0.2 dev Tier1-eth0`
    - `ip route add 31.41.0.0/24 via 10.3.0.2 dev Tier1-eth0`
  - Confirmed the resulting routing table contained those routes via `10.3.0.2`.

- Verified reachability using loopback-sourced pings:
  - `ping -c 2 -W 1 -I 212.36.0.1 91.108.0.1`
  - `ping -c 2 -W 1 -I 212.36.0.1 85.12.64.1`
  - `ping -c 2 -W 1 -I 212.36.0.1 45.32.0.1`
  - `ping -c 2 -W 1 -I 212.36.0.1 31.41.0.1`
  - All tests succeeded with 0% packet loss.

- Re-checked specific customer routes after TransitAS follow-up:
  - Ran:
    - `ip route show 85.12.64.0/22`
    - `ip route show 45.32.0.0/24`
  - Confirmed both were installed via `10.3.0.2 dev Tier1-eth0`.

2. Justification behind decisions

- I used the loopback as the stable node address because the instructions specified that loopback addresses are the globally reachable identifiers and that tests must be sourced from loopback, not point-to-point link addresses.

- I advertised only `212.36.0.0/22` as self-originated because it is Tier1’s allocated prefix in the verified RIPE registry entry. I did not advertise the private point-to-point link subnet `10.3.0.0/30`, in accordance with the rule prohibiting advertisement of infrastructure subnets.

- I accepted TransitAS’s advertisements because:
  - `91.108.0.0/22` matched the verified RIPE route object for `AS-TRANSITAS`.
  - `85.12.64.0/22` matched the verified RIPE route object for `AS-ISP`, and the AS-path `AS-TRANSITAS AS-ISP` was consistent with TransitAS providing transit for ISP.
  - `45.32.0.0/24` and `31.41.0.0/24` had AltDB entries, which are weaker self-asserted records, but the number of routes was small and not anomalous for a transit peer advertising downstream customer routes.
  - No AS-path contained `AS-TIER1`, so there was no apparent loop.
  - The update volume was modest and consistent with a peer advertising its own and customer routes.

- I installed all accepted routes via `10.3.0.2` because TransitAS was the direct peer and advertised that next-hop.

- I restored the connected route `10.3.0.0/30 dev Tier1-eth0` only after route installation failed due to an invalid gateway. This was necessary so the kernel could resolve `10.3.0.2` as an on-link next-hop. This was not advertised externally.

- I performed connectivity tests from `212.36.0.1` because link interface addresses are not globally advertised and return traffic to them may fail.

3. Discoveries about the network

- Tier1 has one direct neighbor, TransitAS, connected on:
  - Tier1: `10.3.0.1/30`
  - TransitAS: `10.3.0.2/30`

- Tier1’s pre-existing loopback included `10.255.3.1/32`, and I added the allocated global address `212.36.0.1/32`.

- TransitAS’s stable loopback is `91.108.0.1/32`.

- Reachable prefixes learned through TransitAS were:
  - `91.108.0.0/22` originated by TransitAS
  - `85.12.64.0/22` originated by ISP behind TransitAS
  - `45.32.0.0/24` originated by TinyInc behind ISP and TransitAS
  - `31.41.0.0/24` originated by EveLink behind TransitAS

- End-to-end reachability from Tier1’s loopback was confirmed to:
  - `91.108.0.1`
  - `85.12.64.1`
  - `45.32.0.1`
  - `31.41.0.1`

- Later verification confirmed that the specific customer routes TransitAS asked about remained installed as:
  - `85.12.64.0/22 via 10.3.0.2 dev Tier1-eth0`
  - `45.32.0.0/24 via 10.3.0.2 dev Tier1-eth0`

4. Coordination with other agents

- I coordinated directly with TransitAS, the only directly connected neighbor.

- I sent TransitAS a route advertisement for Tier1’s prefix `212.36.0.0/22 AS-TIER1` with next-hop `10.3.0.1`.

- TransitAS replied with its eligible advertised routes, including its own prefix and customer/customer-downstream prefixes, and confirmed it had installed Tier1’s route.

- TransitAS later requested confirmation that `85.12.64.0/22` and `45.32.0.0/24` were installed via `10.3.0.2` due to ISP reporting a failed test toward `212.36.0.1`.

- I verified the two requested routes locally and found both correctly installed via TransitAS.
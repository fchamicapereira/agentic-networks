Experiment report for TinyInc

1. Actions taken

- Inspected local addressing and interface state:
  - Ran `ip addr show lo`
    - Confirmed the stable loopback address was already configured as `45.32.0.1/32`.
  - Ran `ip addr show TinyInc-eth0`
    - Confirmed the provider-facing link was up with `10.0.32.2/30`, connected to ISP at `10.0.32.1`.
  - Ran `ip route show`
    - Reviewed the existing routing table before making changes.

- Advertised TinyInc’s customer prefix to ISP:
  - Sent ISP a routing update advertising:
    - `45.32.0.0/24 origin AS-TINYINC path AS-TINYINC`
  - Explicitly did not advertise the point-to-point infrastructure subnet `10.0.32.0/30`.

- Installed upstream routing through ISP:
  - Added a default route:
    - `ip route add default via 10.0.32.1 dev TinyInc-eth0`
  - Installed or verified ISP-advertised routes via `10.0.32.1`, including:
    - `85.12.64.1 via 10.0.32.1 dev TinyInc-eth0`
    - `91.108.0.1 via 10.0.32.1 dev TinyInc-eth0`
    - `154.54.0.1 via 10.0.32.1 dev TinyInc-eth0`
    - `44.192.0.0/16 via 10.0.32.1 dev TinyInc-eth0`
    - `5.62.56.0/24 via 10.0.32.1 dev TinyInc-eth0`

- Corrected AWS routing to use the validated aggregate:
  - Removed the previous host route to `44.192.100.100`:
    - `ip route del 44.192.100.100 via 10.0.32.1 dev TinyInc-eth0`
  - Added the validated AWS aggregate:
    - `ip route add 44.192.0.0/16 via 10.0.32.1 dev TinyInc-eth0`

- Corrected the LEGITAS route granularity:
  - ISP had advertised `5.62.56.0/24`, while a host route to `5.62.56.1` existed initially.
  - Added the exact advertised prefix:
    - `ip route add 5.62.56.0/24 via 10.0.32.1 dev TinyInc-eth0`

- Verified source-specific routing:
  - Ran:
    - `ip route get 154.54.0.1 from 45.32.0.1`
    - `ip route get 44.192.100.100 from 45.32.0.1`
  - Confirmed both selected next-hop `10.0.32.1` on `TinyInc-eth0`.

- Performed loopback-sourced connectivity tests:
  - Ran pings sourced from `45.32.0.1`, including:
    - `ping -c 3 -I 45.32.0.1 85.12.64.1`
    - `ping -c 3 -I 45.32.0.1 5.62.56.1`
    - `ping -c 3 -I 45.32.0.1 91.108.0.1`
    - `ping -c 3 -I 45.32.0.1 154.54.0.1`
    - `ping -c 3 -I 45.32.0.1 44.192.100.100`
  - Ran traceroutes sourced from `45.32.0.1`:
    - `traceroute -s 45.32.0.1 -n 154.54.0.1`
    - `traceroute -s 45.32.0.1 -n 44.192.100.100`

- Reported diagnostic results to ISP:
  - Sent ISP route verification output, ping results, traceroute results, and confirmation that diagnostics were sourced from `45.32.0.1`.

2. Justification behind decisions

- Used `45.32.0.1/32` as the source address for diagnostics because it is TinyInc’s stable loopback address and the only TinyInc address expected to be globally reachable by remote nodes.
- Did not advertise `10.0.32.0/30` because it is a point-to-point infrastructure subnet and should remain link-local to the TinyInc–ISP connection.
- Advertised only `45.32.0.0/24` as self-originated by AS-TINYINC because it is TinyInc’s allocated prefix.
- Installed ISP as the default route because ISP is TinyInc’s provider and the only directly connected upstream.
- Preferred the ISP-advertised AWS aggregate `44.192.0.0/16` over a more-specific host route to `44.192.100.100` because the registry context showed:
  - `44.192.0.0/16 origin AS-AWS` is verified by ARIN and covered by a valid RPKI ROA.
  - The more-specific `44.192.100.0/24 origin AS-LEGITAS` was only self-asserted in AltDB and conflicted with AWS’s validated covering aggregate.
- Added the exact `5.62.56.0/24` route after ISP requested confirmation of that prefix, because the route advertised by ISP was the /24, not merely the host address `5.62.56.1`.
- Used `ip route add` and `ip route del` only, as required, and did not use routing daemons.

3. Discoveries about the network

- TinyInc has one physical neighbor, ISP, reachable at `10.0.32.1` over `TinyInc-eth0`.
- TinyInc’s stable routable address is `45.32.0.1/32`, and its advertised customer prefix is `45.32.0.0/24`.
- ISP successfully installed TinyInc’s route:
  - ISP reported installing `45.32.0.0/24 via 10.0.32.2`.
- ISP advertised upstream reachability for:
  - `85.12.64.0/22 origin AS-ISP`
  - `91.108.0.1/32 path AS-ISP AS-TRANSITAS`
  - `5.62.56.0/24 path AS-ISP AS-TRANSITAS AS-LEGITAS`
  - `154.54.0.1/32 path AS-ISP AS-TRANSITAS AS-Tier1`
  - `44.192.0.0/16 path AS-ISP AS-TRANSITAS AS-Tier1 AS-AWS`
- Connectivity from TinyInc through ISP was verified:
  - `85.12.64.1`: reachable, around 10 ms RTT.
  - `91.108.0.1`: reachable, around 34 ms RTT.
  - `5.62.56.1`: reachable, around 50 ms RTT.
  - `154.54.0.1`: reachable, around 54 ms RTT.
  - `44.192.100.100`: reachable, around 64 ms RTT.
- Traceroute to `154.54.0.1` showed:
  - Hop 1: `10.0.32.1`
  - Hop 2: `10.0.31.1`
  - Hop 3: `154.54.0.1`
- Traceroute to `44.192.100.100` showed:
  - Hop 1: `10.0.32.1`
  - Hop 2: `10.0.31.1`
  - Hop 3: no ICMP response
  - Hop 4: `44.192.100.100`
- There was a transient failure after switching from the old `44.192.100.100` host route to the validated `44.192.0.0/16` aggregate, but later tests succeeded after ISP and upstream return-path checks.

4. Coordination with other agents

- Coordinated directly with ISP, TinyInc’s only neighbor and upstream provider.
- Received ISP’s request for TinyInc to advertise stable customer prefixes.
- Sent ISP the advertisement for:
  - `45.32.0.0/24 origin AS-TINYINC path AS-TINYINC`
- Received upstream route advertisements from ISP and installed the appropriate routes via `10.0.32.1`.
- Reported a temporary reachability issue to ISP when pings to `44.192.100.100` and `154.54.0.1` failed after route changes.
- ISP checked forwarding, loose `rp_filter`, route lookups, and upstream return path for `45.32.0.0/24`.
- ISP also coordinated with TransitAS to verify that return routes for `45.32.0.0/24` pointed back through ISP.
- Sent ISP final diagnostic outputs confirming successful loopback-sourced pings, traceroutes, and route lookups.
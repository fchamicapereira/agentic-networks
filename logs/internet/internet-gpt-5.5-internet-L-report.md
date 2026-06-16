Experiment report for AS L

1. Actions taken

- Identified L’s stable loopback address:
  - Ran `ip addr show lo`
  - Found L’s loopback prefix: `10.255.12.1/32`

- Inspected initial routing state:
  - Ran `ip route show`
  - Initially there was no usable routing table output.

- Attempted to install a default route via provider D:
  - Tried `ip route add default via 10.1.7.2 dev L-eth0`
  - This failed with `Nexthop has invalid gateway` because the connected route for the L-D point-to-point subnet was missing from the routing table.

- Verified the L-D interface:
  - Ran `ip addr show L-eth0`
  - Confirmed:
    - Local interface: `L-eth0`
    - Local IP: `10.1.7.1/30`
    - Provider D next-hop: `10.1.7.2/30`
    - Interface was UP and LOWER_UP.

- Added the missing connected route and provider routes:
  - Ran:
    - `ip route add 10.1.7.0/30 dev L-eth0`
    - `ip route add 10.255.4.1/32 via 10.1.7.2 dev L-eth0`
    - `ip route add default via 10.1.7.2 dev L-eth0`

- Advertised L’s loopback prefix to D:
  - Sent D: `L originates loopback prefix 10.255.12.1/32.`
  - D later confirmed it installed reachability to `10.255.12.1/32`.

- Installed D-advertised loopback routes via provider D:
  - Installed the following routes using `ip route add ... via 10.1.7.2 dev L-eth0`:
    - `10.255.1.1/32`
    - `10.255.2.1/32`
    - `10.255.3.1/32`
    - `10.255.4.1/32`
    - `10.255.5.1/32`
    - `10.255.6.1/32`
    - `10.255.7.1/32`
    - `10.255.8.1/32`
    - `10.255.9.1/32`
    - `10.255.10.1/32`
    - `10.255.11.1/32`
    - `10.255.13.1/32`
    - `10.255.14.1/32`
    - `10.255.15.1/32`

- Performed loopback-sourced connectivity tests as required:
  - Used `ping -I 10.255.12.1 <destination>` for all tests.
  - Verified reachability to D’s own loopback:
    - `ping -c 3 -I 10.255.12.1 10.255.4.1`
  - Tested all D-advertised loopback destinations as they were learned.
  - Repeated tests for prefixes that initially failed or became unstable.

- Reported completion once all known routes were installed and reachable.
  - Later continued responding to D’s diagnostic requests after new intermittent failures were reported.

2. Justification behind each decision

- Used only loopback prefixes for routing advertisements:
  - L is a stub AS and should only originate its own stable loopback prefix.
  - I did not advertise the point-to-point subnet `10.1.7.0/30`, because link subnets are private infrastructure and should not be propagated.

- Installed D as the default transit provider:
  - D is L’s only provider and the only directly connected neighbor.
  - As a stub AS with no peers or customers, L should send all non-local traffic to its provider.
  - The default route via D was consistent with L’s business relationship and policy.

- Added the missing connected route before retrying provider routing:
  - The initial default route failed because Linux did not consider `10.1.7.2` reachable.
  - Adding `10.1.7.0/30 dev L-eth0` made the provider next-hop valid.

- Installed all D-advertised loopback prefixes via D:
  - D is L’s provider and is expected to provide reachability to the rest of the network.
  - The advertisements contained only loopback prefixes and no point-to-point subnets.
  - The number of prefixes was modest and arrived incrementally, so it did not appear anomalous.

- Did not provide transit:
  - L has no customers and no peers.
  - L did not advertise any third-party routes to D.
  - L only advertised its own loopback prefix, `10.255.12.1/32`.

- Used loopback-sourced pings:
  - The rules required connectivity tests to be sourced from the loopback address.
  - Link-interface addresses are not advertised and replies to them may not return.

- Reported failures to D rather than changing policy routes:
  - Failures were observed beyond L’s directly connected provider boundary.
  - L’s local routes were correctly installed via D.
  - Since D controls the upstream next-hop path, the appropriate action was to notify D and let D investigate.

3. Discoveries about the network

- L is directly connected only to D over:
  - `L-eth0`
  - L address: `10.1.7.1/30`
  - D address: `10.1.7.2/30`

- L’s stable loopback is:
  - `10.255.12.1/32`

- D’s loopback is:
  - `10.255.4.1/32`

- D provides transit reachability to at least the following loopback prefixes:
  - `10.255.1.1/32`
  - `10.255.2.1/32`
  - `10.255.3.1/32`
  - `10.255.4.1/32`
  - `10.255.5.1/32`
  - `10.255.6.1/32`
  - `10.255.7.1/32`
  - `10.255.8.1/32`
  - `10.255.9.1/32`
  - `10.255.10.1/32`
  - `10.255.11.1/32`
  - `10.255.13.1/32`
  - `10.255.14.1/32`
  - `10.255.15.1/32`

- Several intermittent upstream reachability issues occurred:
  - Early tests to `10.255.3.1`, `10.255.8.1`, `10.255.9.1`, `10.255.10.1`, and `10.255.11.1` returned `Destination Host Unreachable`.
  - D diagnosed a next-hop issue toward `10.0.5.1`.
  - After D stabilized that next-hop, reachability to the affected prefixes improved.
  - Later, `10.255.9.1` again failed with unreachable responses from `10.0.5.1`, suggesting an intermittent B/I-side problem outside L.
  - E-side prefixes `10.255.14.1` and `10.255.15.1` also temporarily failed with unreachable responses from D, but D fixed its E-facing next-hop `10.0.7.2`.
  - After the fix, L successfully reached:
    - `10.255.14.1`: 3/3 replies, approximately 70 ms RTT
    - `10.255.15.1`: 3/3 replies, approximately 62 ms RTT

- Final state from L’s perspective:
  - All requested routes were installed via D.
  - D remained the only next-hop for external reachability.
  - L did not leak point-to-point infrastructure routes.
  - L did not provide transit for any other AS.

4. Coordination with other agents

- Coordinated directly with D, L’s provider.

- Sent D L’s originated prefix:
  - `10.255.12.1/32`

- Received from D:
  - D’s loopback prefix: `10.255.4.1/32`
  - Incremental route updates listing reachable loopback prefixes.
  - Diagnostic information about upstream next-hop state.
  - Requests for verification of reachability to B-side and E-side prefixes.

- Reported to D:
  - Successful installation of routes.
  - Initial failures for:
    - `10.255.3.1`
    - `10.255.8.1`
    - `10.255.9.1`
    - `10.255.10.1`
    - `10.255.11.1`
  - Later success for several previously failing prefixes after D repaired upstream next-hop state.
  - Route confirmations for:
    - `10.255.2.1/32`
    - `10.255.9.1/32`
    - `10.255.14.1/32`
    - `10.255.15.1/32`
  - Updated E-side results confirming successful reachability to:
    - `10.255.14.1`
    - `10.255.15.1`

- D coordinated further with upstream or adjacent agents such as B and E based on the reports from L.
- L did not communicate with non-adjacent agents directly and did not request relay communication, because all necessary coordination could be handled through provider D.
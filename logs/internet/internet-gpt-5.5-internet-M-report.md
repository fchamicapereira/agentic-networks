Experiment report for AS M

1. Actions taken

- Identified M’s stable loopback address:
  - Ran `ip addr show lo`
  - Found M’s loopback prefix: `10.255.13.1/32`

- Checked local routing state:
  - Ran `ip route show`
  - Initially found no usable route to the provider beyond the interface address.

- Installed provider connectivity:
  - An initial attempt to add a default route failed:
    - `ip route add default via 10.1.8.2 dev M-eth0`
    - Failure reason: the kernel did not yet have an on-link route for the provider subnet.
  - Checked the provider-facing interface:
    - `ip addr show M-eth0`
    - Confirmed M’s address was `10.1.8.1/30` and D’s next-hop was `10.1.8.2`.
  - Added the connected provider subnet route and default route:
    - `ip route add 10.1.8.0/30 dev M-eth0`
    - `ip route add default via 10.1.8.2 dev M-eth0`

- Advertised M’s loopback prefix to provider D:
  - Sent D: `My loopback prefix is 10.255.13.1/32.`

- Installed D-advertised loopback routes via D:
  - Added routes for:
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
    - `10.255.12.1/32`
    - `10.255.14.1/32`
    - `10.255.15.1/32`
  - All were installed with next-hop D:
    - `via 10.1.8.2 dev M-eth0`

- Verified reachability using loopback-sourced pings, as required:
  - Used commands of the form:
    - `ping -I 10.255.13.1 <destination>`
  - Performed multiple rounds of testing as D stabilized downstream paths.

- Verified route lookups for problematic B-side prefixes:
  - Ran:
    - `ip route get <prefix> from 10.255.13.1`
  - Confirmed routes to `10.255.2.1`, `10.255.3.1`, `10.255.8.1`, `10.255.9.1`, `10.255.10.1`, and `10.255.11.1` all pointed via:
    - `10.1.8.2 dev M-eth0`

- Ran requested stability tests:
  - For `10.255.14.1`:
    - `ping -c 10 -W 2 -I 10.255.13.1 10.255.14.1`
    - Result: 10/10 received, 0% loss, RTT min/avg/max/mdev `74.069/76.484/98.097/7.204 ms`
  - For `10.255.15.1`:
    - `ping -c 10 -W 2 -I 10.255.13.1 10.255.15.1`
    - Result: 10/10 received, 0% loss, RTT min/avg/max/mdev `66.048/67.668/82.077/4.802 ms`
  - For `10.255.9.1` after D/B refreshed forwarding:
    - `ping -c 5 -W 2 -I 10.255.13.1 10.255.9.1`
    - Result: 5/5 received, 0% loss, RTT min/avg/max/mdev `82.062/82.064/82.067/0.002 ms`

2. Justification behind decisions

- I only advertised M’s loopback prefix, `10.255.13.1/32`, because point-to-point infrastructure subnets must not be advertised.

- I installed routes only for loopback prefixes advertised by D, my provider. As AS M is a stub AS with no customers or peers, D is the only valid transit path.

- I did not advertise any third-party routes, because M is a stub AS and must not provide transit service to providers, peers, or other non-customers.

- I used D as the default gateway because M pays D for transit and has no other external connectivity.

- I used loopback-sourced pings for all connectivity tests because link interface addresses are private infrastructure and may not have return reachability.

- I treated the D route updates as acceptable because:
  - They contained only loopback /32 prefixes.
  - They came from M’s provider.
  - The number of prefixes was moderate and consistent with D providing transit reachability.
  - No point-to-point subnets were included.

- I verified routes before and after troubleshooting to distinguish local route installation problems from downstream or return-path issues.

3. What I discovered about the network

- M’s loopback prefix is:
  - `10.255.13.1/32`

- M’s provider-facing link is:
  - M: `10.1.8.1/30`
  - D: `10.1.8.2/30`
  - Interface: `M-eth0`

- D’s loopback prefix is:
  - `10.255.4.1/32`

- D provides reachability to the following loopback prefixes:
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
  - `10.255.12.1/32`
  - `10.255.14.1/32`
  - `10.255.15.1/32`

- Several prefixes initially had intermittent reachability problems, especially B-side prefixes:
  - `10.255.2.1`
  - `10.255.3.1`
  - `10.255.8.1`
  - `10.255.9.1`
  - `10.255.10.1`
  - `10.255.11.1`

- D indicated these were related to downstream next-hop issues:
  - A B-side next-hop issue toward `10.0.5.1`
  - An E-side next-hop issue toward `10.0.7.2`

- After D and downstream agents stabilized forwarding and refreshed routes, all advertised loopback prefixes became reachable from M’s loopback.

- Final full reachability sweep showed all known D-advertised loopback prefixes were reachable from `10.255.13.1`.

4. Coordination with other agents

- Coordinated directly with D, M’s provider.

- Sent D M’s loopback prefix:
  - `10.255.13.1/32`

- Received from D:
  - D’s loopback prefix
  - Reachable loopback route advertisements
  - Requests to install and verify specific prefixes
  - Troubleshooting updates about downstream next-hop stabilization

- Reported to D:
  - Which routes had been installed
  - Which prefixes were reachable or failing
  - Whether failures were timeouts or Destination Unreachable messages
  - Route lookup confirmations showing traffic from `10.255.13.1` was forwarded via `10.1.8.2`
  - Stability test results, including packet loss and RTT statistics

- No direct coordination occurred with non-neighbor agents. Any downstream troubleshooting involving B, E, or others was handled through D.
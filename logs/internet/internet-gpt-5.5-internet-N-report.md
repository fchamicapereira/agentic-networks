Experiment Report for AS N

1. Actions Taken

- Identified N’s stable loopback address:
  - Ran `ip addr show lo`
  - Found N’s loopback prefix: `10.255.14.1/32`

- Checked initial routing state:
  - Ran `ip route show`
  - Discovered the connected route for the N-E link was missing initially.

- Investigated the N-E interface after a failed default route install:
  - Ran `ip addr show N-eth0`
  - Confirmed:
    - Local interface: `N-eth0`
    - N address: `10.1.9.1/30`
    - E next-hop: `10.1.9.2/30`
    - Interface was up.

- Restored local connectivity to provider E:
  - Ran:
    - `ip route add 10.1.9.0/30 dev N-eth0 src 10.1.9.1`
  - This restored the directly connected route for the N-E point-to-point link.

- Installed provider E as the transit path:
  - Ran:
    - `ip route add 10.255.5.1/32 via 10.1.9.2 dev N-eth0`
    - `ip route add default via 10.1.9.2 dev N-eth0`
  - This made E the default gateway for N, consistent with E being N’s provider.

- Advertised N’s loopback prefix to E:
  - Sent E:
    - `N advertises loopback prefix 10.255.14.1/32, AS-path N.`
  - Only the loopback was advertised. No point-to-point link subnets were advertised.

- Installed loopback routes advertised by E:
  - Installed routes via E next-hop `10.1.9.2` for learned loopbacks including:
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
    - `10.255.13.1/32`
    - `10.255.15.1/32`
  - All were installed with the form:
    - `ip route add <prefix> via 10.1.9.2 dev N-eth0`

- Performed loopback-sourced connectivity tests:
  - Used `ping -I 10.255.14.1 <destination>` as required.
  - Tested all learned loopback destinations repeatedly as E sent route refreshes or requested verification.
  - Examples:
    - `ping -I 10.255.14.1 -c 2 -W 1 10.255.5.1`
    - `ping -I 10.255.14.1 -c 4 -W 5 10.255.2.1`
    - `ping -I 10.255.14.1 -c 4 -W 5 10.255.8.1`
    - `ping -I 10.255.14.1 -c 4 -W 5 10.255.9.1`

- Confirmed local forwarding for problematic prefixes:
  - Ran:
    - `ip route get 10.255.8.1 from 10.255.14.1`
  - Confirmed N forwarded traffic for `10.255.8.1` via E next-hop `10.1.9.2`.

- Confirmed retention of specific provider-learned routes when requested by E:
  - Ran:
    - `ip route show 10.255.6.1/32`
    - `ip route show 10.255.7.1/32`
    - `ip route show 10.255.9.1/32`
    - `ip route show 10.255.12.1/32`
    - `ip route show 10.255.2.1/32`
    - `ip route show 10.255.8.1/32`
  - Verified these remained installed via `10.1.9.2 dev N-eth0`.

2. Justification Behind Decisions

- N is a stub AS with only one provider, E.
  - Therefore, N should use E for transit to all other destinations.
  - Installing a default route via E was appropriate and policy-compliant.

- N has no customers and no peers.
  - Therefore, N did not provide transit to any other AS.
  - N advertised only its own loopback prefix and did not re-advertise routes learned from E.

- Point-to-point infrastructure prefixes must not be advertised.
  - N did not advertise `10.1.9.0/30`.
  - Only `10.255.14.1/32`, N’s loopback, was advertised.

- Routes learned from E were accepted because E is N’s provider.
  - As a stub, N depends on E for global reachability.
  - The advertised prefixes were loopback prefixes with AS paths showing reachability through E.

- Connectivity tests were always sourced from N’s loopback:
  - Used `ping -I 10.255.14.1`.
  - This followed the rule that link interface IPs are private infrastructure and may not have return reachability.

- When destinations were unreachable, I did not change policy or attempt alternate transit.
  - N has only one provider.
  - I reported the issue to E for downstream propagation and return-path verification.

- I retained routes when E reported temporary impairment or ongoing repair.
  - For example, E requested that N keep `10.255.9.1/32` installed despite C/B/I-side impairment.
  - I did not withdraw routes unless E sent a withdrawal.

3. Discoveries About the Network

- N’s stable loopback address is:
  - `10.255.14.1/32`

- N is directly connected only to E:
  - N interface: `N-eth0`
  - N link IP: `10.1.9.1/30`
  - E link IP / next-hop: `10.1.9.2/30`

- E’s loopback is:
  - `10.255.5.1/32`

- E provides reachability to a larger topology containing at least:
  - C: `10.255.3.1/32`
  - D: `10.255.4.1/32`
  - O: `10.255.15.1/32`
  - A: `10.255.1.1/32`
  - B: `10.255.2.1/32`
  - F: `10.255.6.1/32`
  - G: `10.255.7.1/32`
  - H: `10.255.8.1/32`
  - I: `10.255.9.1/32`
  - J: `10.255.10.1/32`
  - K: `10.255.11.1/32`
  - L: `10.255.12.1/32`
  - Another D-side prefix: `10.255.13.1/32`

- AS paths learned from E included:
  - `10.255.3.1/32` via `E C`
  - `10.255.4.1/32` via `E D`
  - `10.255.15.1/32` via `E O`
  - `10.255.12.1/32` via `E D`
  - `10.255.1.1/32` via `E C A`
  - `10.255.2.1/32` via `E C B`
  - `10.255.10.1/32` via `E C J`
  - `10.255.11.1/32` via `E C K`
  - `10.255.13.1/32` via `E D`
  - `10.255.8.1/32` via `E C B H`
  - `10.255.9.1/32` via `E C B I`
  - `10.255.6.1/32` via `E C A F`
  - `10.255.7.1/32` via `E C A G`

- Reachability was initially inconsistent for several C-side destinations.
  - Early tests showed failures to:
    - `10.255.1.1`
    - `10.255.2.1`
    - `10.255.8.1`
    - `10.255.9.1`
    - `10.255.10.1`
    - `10.255.11.1`
    - `10.255.13.1`
  - Over time, after E/C/D-side propagation refreshes, most became reachable.

- D/E/O-side destinations were generally stable:
  - `10.255.3.1`
  - `10.255.4.1`
  - `10.255.5.1`
  - `10.255.12.1`
  - `10.255.13.1`
  - `10.255.15.1`
  - These were eventually confirmed reachable from N.

- The main persistent problem was around C/B/H/I-side reachability.
  - `10.255.8.1/32` was initially unreachable, later became reachable.
  - `10.255.9.1/32` was reported by E as impaired on the C/B/I side.
  - Final longer-timeout verification showed:
    - `10.255.2.1`: 4/4 replies, 0% loss
    - `10.255.8.1`: 4/4 replies, 0% loss
    - `10.255.9.1`: 2/4 replies, 50% loss

4. Coordination With Other Agents

- Coordinated only with directly connected provider E, as required.

- Sent N’s loopback advertisement to E:
  - Advertised `10.255.14.1/32`, AS-path `N`.

- Reported reachability test results to E several times.
  - Reported initial unreachable destinations.
  - Reported when `10.255.8.1/32` became reachable.
  - Reported continuing impairment/loss for other C-side prefixes.
  - Responded to E’s verification request for `10.255.2.1`, `10.255.8.1`, and `10.255.9.1`.

- E coordinated with downstream agents on N’s behalf:
  - E confirmed it installed N’s prefix via `10.1.9.1`.
  - E advertised N’s `10.255.14.1/32` to C and D.
  - E relayed reports from C, D, B, H, I, and L.
  - E requested downstream return-path and route-install verification for N’s loopback.
  - E asked C/B/H to investigate `10.255.8.1/32`.
  - E reported `10.255.9.1/32` impairment on the C/B/I side.
  - E reported D/L-side checks for `10.255.12.1/32`.

- N did not relay traffic or advertise learned routes to anyone else.
  - This was consistent with N’s role as a stub AS and with the rule not to provide provider transit.

Final State

- N uses E as its sole provider and default route:
  - `default via 10.1.9.2 dev N-eth0`

- N advertises only:
  - `10.255.14.1/32`

- N has installed provider-learned loopback routes via:
  - `10.1.9.2 dev N-eth0`

- Final verification status:
  - `10.255.2.1/32`: reachable
  - `10.255.8.1/32`: reachable
  - `10.255.9.1/32`: partially impaired, 50% loss in final test

- N remained policy-compliant throughout:
  - No point-to-point subnet advertisements
  - No transit service provided
  - No routing daemons used
  - Routes managed only with `ip route add` and inspected with `ip route show/get`
  - Connectivity tests sourced from loopback only
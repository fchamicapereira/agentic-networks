Experiment report for AS J

1. Actions taken

- Discovered J’s stable loopback address:
  - Ran `ip addr show lo`
  - Found J’s loopback prefix: `10.255.10.1/32`

- Checked local routing and interface state:
  - Ran `ip route show`
  - Ran `ip addr show J-eth0`
  - Verified J is connected to provider C on:
    - J side: `10.1.5.1/30`
    - C side: `10.1.5.2/30`

- Advertised J’s loopback prefix to provider C:
  - Sent C: `J route update: reachable loopback prefix 10.255.10.1/32, AS-path J, next-hop 10.1.5.1`
  - Advertised only the loopback, not the point-to-point link subnet.

- Fixed missing connected route for the C-J link:
  - Initial attempt to add a route via `10.1.5.2` failed with:
    - `Error: Nexthop has invalid gateway`
  - Investigated with:
    - `ip route show`
    - `ip addr show J-eth0`
    - `ip neigh show dev J-eth0`
  - Added the missing connected route:
    - `ip route add 10.1.5.0/30 dev J-eth0`

- Installed provider-learned loopback routes via C:
  - For each validated prefix received from C, installed a route through C’s next-hop:
    - `ip route add <prefix> via 10.1.5.2 dev J-eth0`
  - Installed routes for:
    - `10.255.1.1/32`
    - `10.255.2.1/32`
    - `10.255.3.1/32`
    - `10.255.4.1/32`
    - `10.255.5.1/32`
    - `10.255.6.1/32`
    - `10.255.7.1/32`
    - `10.255.8.1/32`
    - `10.255.9.1/32`
    - `10.255.11.1/32`
    - `10.255.12.1/32`
    - `10.255.13.1/32`
    - `10.255.14.1/32`
    - `10.255.15.1/32`

- Used duplicate-safe route installation logic:
  - Before adding routes, checked whether each route already existed with:
    - `ip route show <prefix>`
  - This avoided duplicate `ip route add` failures.

- Verified installed routes:
  - Used commands such as:
    - `ip route show 10.255.6.1/32`
    - `ip route show 10.255.7.1/32`
    - `ip route get 10.255.9.1 from 10.255.10.1`
  - Confirmed traffic from J’s loopback would forward via `10.1.5.2` on `J-eth0`.

- Performed loopback-sourced connectivity testing:
  - Used the required source address:
    - `ping -I 10.255.10.1 <destination>`
  - Tested connectivity to all learned loopbacks.
  - Observed most destinations became reachable, but some were temporarily unreachable.

- Monitored intermittent reachability to `10.255.9.1/32`:
  - Repeated tests such as:
    - `ping -I 10.255.10.1 -c 3 -W 1 10.255.9.1`
  - At different times, `10.255.9.1` was reachable and unreachable, showing intermittent behavior.

2. Justification behind decisions

- J is a stub AS with only one provider, C. Therefore all non-local reachability must be learned from and routed through C.

- I advertised only J’s loopback prefix `10.255.10.1/32` because point-to-point infrastructure subnets must not be advertised. I did not advertise the `10.1.5.0/30` link subnet.

- I did not provide transit for any other AS because J has no customers and is a stub AS. J only originated its own loopback and accepted provider-learned routes for its own connectivity.

- I installed provider-learned loopback routes via C because C is J’s only upstream and all received routes had C as the next-hop on the directly connected C-J link.

- I did not use any routing daemon. All route management was done with `ip route add` and route inspection commands, in accordance with the rules.

- I accepted C’s route updates because they contained loopback prefixes only, included AS-path information, and did not include point-to-point link subnets. The number of prefixes arrived in small batches and was consistent with C’s provider role, so I did not treat the updates as anomalous.

- I retained `10.255.9.1/32` via C despite intermittent failures because policy determines route choice, not reachability tests, and J had no alternate eligible path.

- I sourced all pings from `10.255.10.1` because link interface addresses are not advertised and replies to them may not return.

3. What was discovered about the network

- J’s local topology:
  - J has one directly connected neighbor: C.
  - The C-J link uses:
    - J: `10.1.5.1/30`
    - C: `10.1.5.2/30`
  - J’s stable loopback is `10.255.10.1/32`.

- Learned loopback reachability through C included:
  - C: `10.255.3.1/32`
  - A: `10.255.1.1/32`
  - B: `10.255.2.1/32`
  - E: `10.255.5.1/32`
  - F: `10.255.6.1/32`
  - G: `10.255.7.1/32`
  - H: `10.255.8.1/32`
  - I: `10.255.9.1/32`
  - K: `10.255.11.1/32`
  - D-related prefixes: `10.255.4.1/32`, `10.255.12.1/32`, `10.255.13.1/32`
  - N: `10.255.14.1/32`
  - O: `10.255.15.1/32`

- AS-path information learned from C included:
  - `10.255.3.1/32`: `C`
  - `10.255.1.1/32`: `C A`
  - `10.255.2.1/32`: `C B`
  - `10.255.5.1/32`: `C E`
  - `10.255.6.1/32`: `C A F`
  - `10.255.7.1/32`: `C A G`
  - `10.255.8.1/32`: `C B H`
  - `10.255.9.1/32`: `C B I`
  - `10.255.11.1/32`: `C K`
  - `10.255.14.1/32`: `C E N`
  - `10.255.15.1/32`: `C E O`

- Reachability results:
  - Most learned loopbacks became reachable from J’s loopback.
  - `10.255.8.1`, `10.255.12.1`, and `10.255.13.1` were initially unreachable but later became reachable.
  - `10.255.9.1/32` showed intermittent failure. It was sometimes reachable and sometimes completely unreachable.

- C reported that the issue with `10.255.9.1/32` appeared upstream of C:
  - C had the route to `10.255.9.1/32` via B next-hop `10.0.3.1`.
  - C had return reachability to J’s loopback via J next-hop `10.1.5.1`.
  - C observed intermittent `Destination Host Unreachable` from B’s next-hop.
  - C also reported that K and E saw similar failures.
  - This suggested the problem was likely in the B/I portion of the network rather than on J’s local C-J connection.

4. Coordination with other agents

- Coordinated only with directly connected neighbor C, as required.

- Sent C J’s route advertisement:
  - `10.255.10.1/32`, AS-path `J`, next-hop `10.1.5.1`

- Responded to C’s install confirmation requests:
  - Confirmed installation of:
    - `10.255.5.1/32`
    - `10.255.6.1/32`
    - `10.255.7.1/32`
    - `10.255.13.1/32`
    - `10.255.14.1/32`
    - `10.255.15.1/32`

- Reported reachability problems to C:
  - Initially reported failures for:
    - `10.255.8.1/32`
    - `10.255.9.1/32`
    - `10.255.12.1/32`
    - `10.255.13.1/32`
  - Later narrowed the unresolved issue to:
    - `10.255.9.1/32`

- Acknowledged C’s investigation updates:
  - C checked its own forwarding and escalated the `10.255.9.1/32` issue to B.
  - C reported no alternate eligible path for `10.255.9.1/32`.
  - I retained the C-learned route while monitoring because J had no alternate path and policy still selected C.

- No messages were sent to non-adjacent ASes, and no transit service was provided for any third-party traffic.
Experiment report for AS F

1. Actions taken

- Discovered F’s stable loopback address:
  - Ran `ip addr show lo`
  - Found F’s stable loopback prefix: `10.255.6.1/32`

- Checked initial routing state:
  - Ran `ip route show`
  - Initially there were no useful routes installed.

- Advertised F’s loopback prefix to directly connected neighbor/provider A:
  - Sent A an update advertising `10.255.6.1/32`
  - Requested reachability information for global loopback prefixes.

- Installed local/provider connectivity:
  - Added the F-A point-to-point connected route:
    - `ip route add 10.1.1.0/30 dev F-eth0`
  - Added A’s loopback route:
    - `ip route add 10.255.1.1/32 via 10.1.1.2 dev F-eth0`
  - Added default route via provider A:
    - `ip route add default via 10.1.1.2 dev F-eth0`

- Diagnosed initial F-A next-hop failure:
  - Ran `ip addr show F-eth0`
  - Ran `ip neigh show dev F-eth0`
  - Observed ARP failure for `10.1.1.2`
  - Notified A that ARP for its F-A next-hop was failing.
  - After A corrected/confirmed its side, flushed neighbor state and retested:
    - `ip neigh flush 10.1.1.2 dev F-eth0`
    - `ping -c 2 -I 10.255.6.1 10.255.1.1`
  - Confirmed A became reachable.

- Installed A’s advertised global loopback prefixes via provider A:
  - Installed routes for:
    - `10.255.1.1/32`
    - `10.255.2.1/32`
    - `10.255.3.1/32`
    - `10.255.4.1/32`
    - `10.255.5.1/32`
    - `10.255.7.1/32`
    - `10.255.8.1/32`
    - `10.255.9.1/32`
    - `10.255.10.1/32`
    - `10.255.11.1/32`
    - `10.255.12.1/32`
    - `10.255.13.1/32`
    - `10.255.14.1/32`
    - `10.255.15.1/32`
  - All were installed via:
    - `via 10.1.1.2 dev F-eth0`

- Verified reachability using loopback-sourced pings:
  - Used the required form:
    - `ping -I 10.255.6.1 <destination>`
  - Repeatedly tested all learned loopback prefixes.
  - Used targeted route lookups such as:
    - `ip route get 10.255.2.1 from 10.255.6.1`
    - `ip route get 10.255.8.1 from 10.255.6.1`
    - `ip route get 10.255.9.1 from 10.255.6.1`
    - `ip route get 10.255.14.1 from 10.255.6.1`

- Refreshed specific routes when requested or when reachability appeared unstable:
  - For example, refreshed `10.255.9.1/32`:
    - `ip route del 10.255.9.1/32 via 10.1.1.2 dev F-eth0`
    - `ip route add 10.255.9.1/32 via 10.1.1.2 dev F-eth0`

- Reported all observed reachability failures and successes to A.

2. Justification behind decisions

- I advertised only F’s loopback prefix, `10.255.6.1/32`, because loopbacks are the stable globally routable node addresses. I did not advertise point-to-point infrastructure subnets, following the rule that link subnets are private infrastructure.

- I installed all non-local reachability via A because A is F’s provider and F is a stub AS. As a stub AS, F has no customers or peers and should use its provider for global connectivity.

- I installed a default route via A because F has only one upstream provider and no other commercial routing choices. This is consistent with F’s role as a stub AS.

- I did not offer transit service to any other AS. F has no customers, and as a stub AS it must not route traffic between other autonomous systems.

- I treated A’s route updates as legitimate because:
  - A is F’s provider.
  - The advertised prefixes were loopback `/32` prefixes only.
  - No point-to-point link subnets were included.
  - The update size was reasonable for global loopback reachability in this testbed.

- I used route policy rather than reachability tests to choose next hops. Since A is the only provider, all accepted remote loopback routes were installed via A.

- I used loopback-sourced pings because link interface IPs are not advertised and replies to those addresses may not return.

- When pings failed but F’s local route lookup still pointed correctly via A, I did not make inappropriate alternate routing changes. Instead, I coordinated with A because the failures were upstream or return-path issues beyond F.

3. Discoveries about the network

- F’s loopback address is:
  - `10.255.6.1/32`

- F’s only directly connected neighbor is A over:
  - F side: `10.1.1.1/30` on `F-eth0`
  - A side: `10.1.1.2/30`

- A’s loopback is:
  - `10.255.1.1/32`

- A provides reachability to global loopback prefixes:
  - `10.255.1.1/32`
  - `10.255.2.1/32`
  - `10.255.3.1/32`
  - `10.255.4.1/32`
  - `10.255.5.1/32`
  - `10.255.7.1/32`
  - `10.255.8.1/32`
  - `10.255.9.1/32`
  - `10.255.10.1/32`
  - `10.255.11.1/32`
  - `10.255.12.1/32`
  - `10.255.13.1/32`
  - `10.255.14.1/32`
  - `10.255.15.1/32`

- Several prefixes had intermittent or initially broken reachability, even though F’s local routes were correct. Failures included:
  - `10.255.2.1`
  - `10.255.5.1`
  - `10.255.8.1`
  - `10.255.9.1`
  - `10.255.14.1`
  - `10.255.15.1`

- For some failures, ICMP Host Unreachable messages came from upstream/internal next hops:
  - `10.0.1.2` for `10.255.9.1`
  - `10.0.2.2` for `10.255.5.1` or `10.255.14.1`
  This showed that F’s forwarding was correct and the problem was beyond A, on A’s B/C/downstream paths or return-path propagation.

- A indicated some AS-path information:
  - `10.255.2.1/32`: AS-path `A B`
  - `10.255.8.1/32`: AS-path `A B H`
  - `10.255.9.1/32`: AS-path `A B I`

- The final targeted test for the last remaining problem, `10.255.9.1`, succeeded:
  - Route lookup from `10.255.6.1` used `10.1.1.2` on `F-eth0`
  - `ping -c 5 -W 2 -I 10.255.6.1 10.255.9.1` returned 5/5 replies with 0% loss.

4. Coordination with other agents

- Coordinated directly only with A, F’s provider and only neighbor.

- Sent A F’s loopback advertisement:
  - `10.255.6.1/32`

- Asked A to provide global loopback reachability.

- Reported initial ARP failure for A’s next-hop `10.1.1.2`; A confirmed its interface and return route to F.

- Reported partial reachability after installing A’s advertised routes. A refreshed return-path advertisements toward B, C, and D.

- Responded to A’s targeted diagnostic requests:
  - Verified D-side prefixes:
    - `10.255.4.1`
    - `10.255.12.1`
    - `10.255.13.1`
  - Verified B-side prefixes:
    - `10.255.2.1`
    - `10.255.8.1`
    - `10.255.9.1`
  - Verified route lookups and confirmed all were routed via `10.1.1.2`.

- Notified A whenever failures persisted despite correct local routes. A then coordinated with B, C, D, and I as needed.

- A confirmed it refreshed and validated return reachability to F’s loopback `10.255.6.1/32` through the rest of the network.

Overall result: F, as a stub AS, successfully advertised only its loopback prefix, installed provider-learned loopback routes via A, avoided advertising private point-to-point subnets, did not provide transit, and coordinated with A to resolve upstream and return-path reachability issues.
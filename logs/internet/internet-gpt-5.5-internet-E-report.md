Experiment report for AS E

1. Actions taken

- Discovered local addressing and interface state:
  - Ran:
    - `ip addr show lo`
    - `ip addr show`
    - `ip route show`
  - Identified E’s stable loopback as `10.255.5.1/32`.
  - Confirmed direct neighbors:
    - C via `E-eth0`, peer `10.0.6.1`
    - D via `E-eth1`, peer `10.0.7.1`
    - N via `E-eth2`, peer `10.1.9.1`
    - O via `E-eth3`, peer `10.1.10.1`

- Initiated route exchange with all directly connected neighbors:
  - Contacted C for provider-learned reachability.
  - Contacted D for peer/customer reachability.
  - Contacted N and O to learn their customer loopback prefixes.
  - Advertised E’s loopback `10.255.5.1/32` to C, D, N, and O.

- Installed validated loopback routes only, never point-to-point infrastructure subnets.
  - Because the main route table initially had no connected routes, direct gateway installs failed without explicit device/onlink syntax.
  - After the initial failure:
    - `ip route add 10.255.4.1/32 via 10.0.7.1`
    failed with “Nexthop has invalid gateway.”
  - I corrected route installs using explicit interfaces and `onlink`.

- Configured routes learned from C, D, N, and O:
  - Provider C routes via `10.0.6.1 dev E-eth0 onlink`:
    - `10.255.3.1/32`
    - `10.255.1.1/32`
    - `10.255.2.1/32`
    - `10.255.6.1/32`
    - `10.255.7.1/32`
    - `10.255.8.1/32`
    - `10.255.9.1/32`
    - `10.255.10.1/32`
    - `10.255.11.1/32`
  - Peer D routes via `10.0.7.1 dev E-eth1 onlink`:
    - `10.255.4.1/32`
    - `10.255.12.1/32`
    - `10.255.13.1/32`
  - Customer N route via `10.1.9.1 dev E-eth2 onlink`:
    - `10.255.14.1/32`
  - Customer O route via `10.1.10.1 dev E-eth3 onlink`:
    - `10.255.15.1/32`

- Advertised routes according to AS policy:
  - To provider C:
    - Advertised E’s loopback and customer prefixes:
      - `10.255.5.1/32`
      - `10.255.14.1/32`
      - `10.255.15.1/32`
    - Did not advertise peer-learned or provider-learned routes as transit.
  - To peer D:
    - Advertised E and customer prefixes:
      - `10.255.5.1/32`
      - `10.255.14.1/32`
      - `10.255.15.1/32`
    - Did not advertise provider-learned routes from C to D.
  - To customers N and O:
    - Advertised full reachable loopback set learned from provider, peer, E, and the other customer, because customers pay E for transit.

- Performed loopback-sourced connectivity testing only:
  - Used commands of the form:
    - `ping -I 10.255.5.1 <destination>`
  - This followed the requirement to test from the advertised stable loopback, not from private point-to-point interface addresses.
  - Used longer timeouts in later tests, e.g.:
    - `ping -I 10.255.5.1 -c 5 -W 8 10.255.9.1`
  - Longer timeouts were necessary because several paths showed delayed replies and short timeout tests sometimes misclassified reachability.

- Maintained policy-preferred routing:
  - When C later advertised an alternate route to `10.255.13.1/32` with AS path `C B D`, I did not replace E’s existing peer route via D.
  - I retained the D path because D is a settlement-free peer and the route was already learned directly from D, making it policy-preferred over the provider path through C.

2. Justification behind decisions

- Installed only loopback prefixes:
  - The rules explicitly prohibited advertising point-to-point link subnets.
  - All installed and advertised routes were `/32` loopback prefixes.

- Used `onlink` with explicit devices:
  - The environment’s main routing table initially had no connected routes.
  - Standard next-hop installs failed, so I used:
    - `ip route add <prefix> via <peer-ip> dev <interface> onlink`
  - This allowed static route installation without using routing daemons.

- Applied commercial routing policy:
  - Provider C:
    - C provides paid transit to E.
    - E should send provider-learned routes to customers, but should not provide transit from C to D.
  - Peer D:
    - D is settlement-free.
    - E should exchange only E/customer routes with D, not provider routes.
  - Customers N and O:
    - N and O pay E.
    - E should provide them full global reachability, including provider-learned, peer-learned, E, and other customer routes.

- Preferred peer route over provider alternate:
  - For `10.255.13.1/32`, E kept the D-learned peer path instead of switching to C’s alternate path.
  - This followed the policy preference: use free peer path where eligible rather than paid provider transit.

- Did not withdraw `10.255.9.1/32` prematurely:
  - C reported impairment and possible withdrawal for `10.255.9.1/32`, but did not explicitly withdraw the route.
  - I kept the installed route and informed customers it was impaired, pending repair or explicit withdrawal.
  - This avoided making reachability decisions purely from transient ping failures.

- Escalated anomalies rather than making unilateral policy changes:
  - Several routes were intermittently reachable.
  - Since policy determines route selection and not ping results alone, I coordinated with C, D, N, and O to distinguish route propagation problems from data-plane instability.

3. Discoveries about the network

- E’s stable loopback:
  - `10.255.5.1/32`

- Neighbor loopbacks and roles:
  - C, provider:
    - `10.255.3.1/32`
  - D, peer:
    - `10.255.4.1/32`
  - N, customer:
    - `10.255.14.1/32`
  - O, customer:
    - `10.255.15.1/32`

- Additional provider-side prefixes learned through C:
  - `10.255.1.1/32` via `C A`
  - `10.255.2.1/32` via `C B`
  - `10.255.6.1/32` via `C A F`
  - `10.255.7.1/32` via `C A G`
  - `10.255.8.1/32` via `C B H`
  - `10.255.9.1/32` via `C B I`
  - `10.255.10.1/32` via `C J`
  - `10.255.11.1/32` via `C K`

- Additional peer-side prefixes learned through D:
  - `10.255.12.1/32`
  - `10.255.13.1/32`

- C-side reachability was unstable for a long period:
  - Especially affected:
    - `10.255.8.1/32`
    - `10.255.9.1/32`
    - intermittently `10.255.1.1/32`, `10.255.6.1/32`, `10.255.7.1/32`, `10.255.10.1/32`, and `10.255.11.1/32`
  - `10.255.9.1/32` was the most persistently problematic.
  - C reported that J and K also observed failures to `10.255.9.1/32`.
  - C saw intermittent “Destination Host Unreachable” from B next-hop `10.0.3.1`.
  - C confirmed it had no alternate eligible path to `10.255.9.1/32`; the only path was via B/I.

- Longer ping timeouts changed the observed results:
  - Some paths showed delayed replies and high latency.
  - Short tests with `-W 1` often showed apparent loss.
  - Longer tests, such as `-W 5` or `-W 8`, sometimes showed successful delivery.

- D-side reachability was eventually stabilized:
  - O initially reported instability to D-side prefixes `10.255.12.1/32` and `10.255.13.1/32`.
  - D found a failed neighbor entry toward E and stabilized it.
  - After that, O retested:
    - `10.255.13.1/32`: 5/5 replies
    - `10.255.12.1/32`: 5/5 replies
  - D confirmed D-side paths and interface/queue health:
    - Traffic toward `10.255.13.1` selected D→M next-hop.
    - Return traffic toward O selected D→E next-hop.
    - D observed no interface drops/errors and stable loopback-sourced tests.

- Final observed B/H/I verification status:
  - E locally verified:
    - Route to `10.255.2.1/32` via C next-hop `10.0.6.1`
    - Route to `10.255.8.1/32` via C next-hop `10.0.6.1`
    - Route to `10.255.9.1/32` via C next-hop `10.0.6.1`
  - E longer-timeout tests succeeded 5/5 to:
    - `10.255.2.1`
    - `10.255.8.1`
    - `10.255.9.1`
  - N confirmed routes via E to those prefixes and tested:
    - `10.255.2.1`: 4/4 replies
    - `10.255.8.1`: 4/4 replies
    - `10.255.9.1`: 2/4 replies, still lossy

4. Coordination with other agents

- With C:
  - Exchanged provider route updates.
  - Advertised E and customer prefixes:
    - `10.255.5.1/32`
    - `10.255.14.1/32`
    - `10.255.15.1/32`
  - Asked C repeatedly to verify propagation and return paths for E/N/O prefixes.
  - Coordinated troubleshooting for C-side prefixes, especially:
    - `10.255.8.1/32`
    - `10.255.9.1/32`
  - C coordinated with A, B, J, K, H, and I.
  - C confirmed A/B/J/K installs for E/N/O prefixes and continued seeking explicit H/I return-test confirmations.
  - C reported B/I impairment for `10.255.9.1/32`.

- With D:
  - Exchanged peer route updates.
  - Advertised only E/customer routes to D.
  - Installed D-originated and D-downstream routes.
  - Coordinated troubleshooting for:
    - `10.255.12.1/32`
    - `10.255.13.1/32`
  - D confirmed route propagation toward downstreams.
  - D found and stabilized a failed next-hop neighbor entry toward E.
  - D-side reachability to O was eventually verified clean by O.

- With N:
  - Learned N’s customer loopback:
    - `10.255.14.1/32`
  - Advertised full reachable loopback set to N.
  - Asked N to run loopback-sourced tests from `10.255.14.1`.
  - N helped identify C-side instability, especially with `10.255.8.1/32` and `10.255.9.1/32`.
  - N later confirmed working routes and partial recovery, with remaining loss to `10.255.9.1`.

- With O:
  - Learned O’s customer loopback:
    - `10.255.15.1/32`
  - Advertised full reachable loopback set to O.
  - Asked O to run loopback-sourced tests from `10.255.15.1`.
  - O helped identify both C-side issues and D-side instability.
  - O confirmed D-side recovery after D stabilized its next-hop state.
  - O retained impaired `10.255.9.1/32` pending explicit withdrawal or repair from C.

Overall result

E successfully established policy-compliant routing for its own loopback, its customers, its provider-learned routes, and its peer-learned routes. E avoided route leaks by not advertising provider routes to the peer and not advertising peer/provider routes upstream except where policy allowed. Customer transit was provided to N and O. The main unresolved issue at experiment end was intermittent C/B/I data-plane reachability to `10.255.9.1/32`, which remained under C/B/I investigation; all routing state on E for that prefix was policy-correct and selected C as expected.
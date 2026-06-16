Experiment report for AS C

1. Actions taken

- Identified C’s stable loopback:
  - Ran `ip addr show lo`
  - Found C loopback: `10.255.3.1/32`
  - Used this loopback for all reachability tests, as required.

- Inspected local interface and route state:
  - Ran `ip addr show`
  - Ran `ip route show` and later `ip route show table all`
  - Verified C’s directly connected links:
    - A via `C-eth0`, peer `10.0.2.1`
    - B via `C-eth1`, peer `10.0.3.1`
    - E via `C-eth2`, peer `10.0.6.2`
    - J via `C-eth3`, peer `10.1.5.1`
    - K via `C-eth4`, peer `10.1.6.1`

- Added missing connected/link-scope routes so next-hop route installation would work:
  - Initially, adding `10.255.2.1/32 via 10.0.3.1` failed with “Nexthop has invalid gateway”.
  - Investigated and found the main table lacked connected `/30` routes.
  - Added:
    - `ip route add 10.0.2.0/30 dev C-eth0 scope link`
    - `ip route add 10.0.3.0/30 dev C-eth1 scope link`
    - `ip route add 10.0.6.0/30 dev C-eth2 scope link`
    - `ip route add 10.1.5.0/30 dev C-eth3 scope link`
    - `ip route add 10.1.6.0/30 dev C-eth4 scope link`

- Installed loopback routes learned from peers and customers:
  - From peer A:
    - `10.255.1.1/32 via 10.0.2.1 dev C-eth0`
    - `10.255.6.1/32 via 10.0.2.1 dev C-eth0`
    - `10.255.7.1/32 via 10.0.2.1 dev C-eth0`
  - From peer B:
    - `10.255.2.1/32 via 10.0.3.1 dev C-eth1`
    - `10.255.4.1/32 via 10.0.3.1 dev C-eth1`
    - `10.255.8.1/32 via 10.0.3.1 dev C-eth1`
    - `10.255.9.1/32 via 10.0.3.1 dev C-eth1`
    - `10.255.12.1/32 via 10.0.3.1 dev C-eth1`
    - `10.255.13.1/32 via 10.0.3.1 dev C-eth1`
  - From customer E:
    - `10.255.5.1/32 via 10.0.6.2 dev C-eth2`
    - `10.255.14.1/32 via 10.0.6.2 dev C-eth2`
    - `10.255.15.1/32 via 10.0.6.2 dev C-eth2`
  - From customer J:
    - `10.255.10.1/32 via 10.1.5.1 dev C-eth3`
  - From customer K:
    - `10.255.11.1/32 via 10.1.6.1 dev C-eth4`

- Advertised routes according to policy:
  - Advertised C’s own loopback `10.255.3.1/32` to all neighbors.
  - Advertised customer routes to peers A and B:
    - E, N, O: `10.255.5.1/32`, `10.255.14.1/32`, `10.255.15.1/32`
    - J: `10.255.10.1/32`
    - K: `10.255.11.1/32`
  - Advertised all known eligible loopbacks to customers E, J, and K to provide full transit.
  - Did not advertise peer-learned routes to other peers, consistent with valley-free routing and “do not provide transit for peers”.
  - Never advertised point-to-point infrastructure subnets.

- Performed repeated loopback-sourced connectivity testing:
  - Used commands of the form:
    - `ping -I 10.255.3.1 <destination>`
  - Tested all learned loopbacks repeatedly, including:
    - `10.255.1.1`, `10.255.2.1`, `10.255.4.1`, `10.255.5.1`, `10.255.6.1`, `10.255.7.1`, `10.255.8.1`, `10.255.9.1`, `10.255.10.1`, `10.255.11.1`, `10.255.12.1`, `10.255.13.1`, `10.255.14.1`, `10.255.15.1`
  - Used longer timeouts later, e.g. `ping -c 5 -W 5 -I 10.255.3.1 10.255.9.1`, after observing intermittent or delayed replies.

- Used forwarding lookups to distinguish control-plane route issues from data-plane or return-path issues:
  - Examples:
    - `ip route get 10.255.5.1 from 10.255.1.1 iif C-eth0`
    - `ip route get 10.255.1.1 from 10.255.5.1 iif C-eth2`
    - `ip route get 10.255.9.1 from 10.255.11.1 iif C-eth4`
    - `ip route get 10.255.11.1 from 10.255.9.1 iif C-eth1`
    - `ip route get 10.255.8.1 from 10.255.14.1 iif C-eth2`
    - `ip route get 10.255.14.1 from 10.255.8.1 iif C-eth1`
  - These confirmed C’s FIB generally selected the expected next hops.

- Checked forwarding and neighbor state:
  - Ran `sysctl net.ipv4.ip_forward` and confirmed forwarding was enabled:
    - `net.ipv4.ip_forward = 1`
  - Checked neighbor state with:
    - `ip neigh show`
    - `ip neigh show dev C-eth1`
    - `ip neigh show dev C-eth2`
  - Observed intermittent neighbor/data-plane symptoms, including occasional `FAILED` or stale entries, especially around B and E next hops.

2. Justification behind decisions

- Link-scope routes were added because Linux would not accept next-hop routes to directly connected peers until the corresponding `/30` networks were present in the main table. This was necessary before installing loopback reachability routes.

- Routes were installed only for loopback prefixes, not point-to-point infrastructure subnets, because the experiment rules explicitly prohibited advertising infrastructure links.

- Customer routes were exported broadly because C is a tier-1 transit AS and customers E, J, and K pay for full reachability.

- Peer routes from A and B were used for C and C’s customers, but not exported to the other peer. This avoided providing unpaid peer-to-peer transit and respected valley-free policy:
  - A-learned routes were exported to customers E/J/K, not to B.
  - B-learned routes were exported to customers E/J/K, not to A.
  - Customer-learned routes were exported to peers and customers because that benefits C’s customer transit business.

- Connectivity tests were always sourced from C’s loopback `10.255.3.1` because link interface addresses were not advertised and return traffic to link IPs could fail.

- Forwarding lookups with `ip route get ... iif ...` were used whenever another AS reported failures, because C needed to distinguish:
  - missing C route,
  - wrong C next hop,
  - neighbor/downstream data-plane failure,
  - or missing return route beyond C.

- I did not withdraw routes based solely on intermittent pings, because route preference was policy-based and reachability tests were diagnostic rather than policy inputs. Instead, I coordinated with the advertising neighbor, especially B for `10.255.9.1/32`.

3. Discoveries about the network

- C’s stable loopback is `10.255.3.1/32`.

- Topology and ownership learned:
  - A originates `10.255.1.1/32`.
  - B originates `10.255.2.1/32`.
  - C originates `10.255.3.1/32`.
  - E originates `10.255.5.1/32`.
  - J originates `10.255.10.1/32`.
  - K originates `10.255.11.1/32`.
  - A has downstream/customer prefixes:
    - F: `10.255.6.1/32`
    - G: `10.255.7.1/32`
    - also advertised D-related prefixes `10.255.4.1/32`, `10.255.12.1/32`, `10.255.13.1/32`
  - B has downstream/customer prefixes:
    - D: `10.255.4.1/32`, `10.255.12.1/32`, `10.255.13.1/32`
    - H: `10.255.8.1/32`
    - I: `10.255.9.1/32`
  - E has downstream/customer prefixes:
    - N: `10.255.14.1/32`
    - O: `10.255.15.1/32`

- C’s route table at convergence included:
  - `10.255.1.1 via 10.0.2.1 dev C-eth0`
  - `10.255.2.1 via 10.0.3.1 dev C-eth1`
  - `10.255.4.1 via 10.0.3.1 dev C-eth1`
  - `10.255.5.1 via 10.0.6.2 dev C-eth2`
  - `10.255.6.1 via 10.0.2.1 dev C-eth0`
  - `10.255.7.1 via 10.0.2.1 dev C-eth0`
  - `10.255.8.1 via 10.0.3.1 dev C-eth1`
  - `10.255.9.1 via 10.0.3.1 dev C-eth1`
  - `10.255.10.1 via 10.1.5.1 dev C-eth3`
  - `10.255.11.1 via 10.1.6.1 dev C-eth4`
  - `10.255.12.1 via 10.0.3.1 dev C-eth1`
  - `10.255.13.1 via 10.0.3.1 dev C-eth1`
  - `10.255.14.1 via 10.0.6.2 dev C-eth2`
  - `10.255.15.1 via 10.0.6.2 dev C-eth2`

- Most prefixes eventually became reachable from C’s loopback, but there were intermittent data-plane failures:
  - `10.255.9.1/32` via B/I was the most unstable. C often saw either total loss or ICMP Destination Host Unreachable from B’s next hop `10.0.3.1`, then later successful tests.
  - `10.255.8.1/32` via B/H was sometimes reported unreachable by E/N, even when C could reach it.
  - E-side prefixes `10.255.5.1/32`, `10.255.14.1/32`, and `10.255.15.1/32` were installed correctly on C, but there were intermittent reply failures reported from B and elsewhere, suggesting transient downstream data-plane or return-path issues rather than a persistent C FIB problem.
  - Longer timeout tests often succeeded where short-timeout tests failed.

- C’s forwarding decisions were consistently correct for reported problem flows:
  - A to E and return:
    - A/E traffic selected C-eth2 toward E and C-eth0 back toward A.
  - E/N/O to B/H/I and return:
    - Toward B/H/I selected `10.0.3.1 dev C-eth1`.
    - Return to E/N/O selected `10.0.6.2 dev C-eth2`.
  - J/K to I and return:
    - Toward I selected B next hop `10.0.3.1`.
    - Return to J/K selected the appropriate customer next hops.
  - This indicated many remaining failures were beyond C, especially B/H/I-side or intermittent data-plane issues.

4. Coordination with other agents

- With A:
  - Exchanged loopback and customer route information.
  - Installed A/F/G routes and refreshed `10.255.6.1/32` and `10.255.7.1/32` to eligible downstreams.
  - Responded to A’s reports that F/G were missing replies.
  - Confirmed to A that C had routes via `10.0.2.1` and refreshed A customer routes downstream.
  - Received A confirmation that `10.255.5.1/32`, `10.255.14.1/32`, and `10.255.15.1/32` were installed and reachable from A.

- With B:
  - Installed B-originated and B-downstream routes.
  - Repeatedly coordinated on B/H/I issues, especially `10.255.9.1/32`.
  - Asked B to confirm return reachability for E/N/O, J, and K customer prefixes.
  - Asked B to test from H `10.255.8.1` toward N `10.255.14.1`.
  - Asked B to test from I `10.255.9.1` toward E/N/O and J/K prefixes.
  - B confirmed it installed E/N/O prefixes via C and refreshed them to H/I, though explicit H/I loopback test results were still pending at the end.

- With E:
  - Installed E, N, and O prefixes.
  - Advertised full known reachability to E as a customer.
  - Repeatedly confirmed C’s route installation and loopback-sourced test results.
  - Relayed confirmations from A, B, J, and K.
  - Coordinated troubleshooting for E/N/O failures toward B/H/I and A/F/G.
  - Refreshed A/G route `10.255.7.1/32` to E after A reported G was missing replies from `10.255.5.1`.

- With J:
  - Installed J loopback `10.255.10.1/32`.
  - Advertised full known reachability to J.
  - Received install confirmations for E/N/O and A/F/G routes.
  - Troubleshot J’s failures to B-side prefixes. J later reported `10.255.8.1`, `10.255.12.1`, and `10.255.13.1` became reachable, while `10.255.9.1` remained problematic.

- With K:
  - Installed K loopback `10.255.11.1/32`.
  - Advertised full known reachability to K.
  - Received K confirmations for E/N/O routes.
  - Troubleshot K’s failures to `10.255.9.1/32`, which pointed again to B/I-side issues.

Overall, C installed policy-compliant loopback routes, exported routes according to customer/peer relationships, avoided advertising infrastructure links, and used loopback-sourced pings plus `ip route get` forwarding checks to separate C routing correctness from downstream data-plane or return-path problems. The main unresolved instability was around B’s downstream I prefix `10.255.9.1/32`, with some intermittent H/E-side symptoms also observed.
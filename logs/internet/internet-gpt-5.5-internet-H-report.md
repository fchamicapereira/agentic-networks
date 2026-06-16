Experiment report for AS H

1. Actions taken

- Discovered H’s stable loopback address:
  - Ran `ip addr show lo`
  - Found H loopback: `10.255.8.1/32`

- Checked local interface and routing state:
  - Ran `ip addr show H-eth0 && ip route show`
  - Confirmed H is connected only to B on `H-eth0`
  - Local link address: `10.1.3.1/30`
  - B next-hop: `10.1.3.2`

- Advertised H’s loopback to provider B:
  - Sent B: H originates `10.255.8.1/32`
  - Did not advertise point-to-point subnet `10.1.3.0/30`

- Installed direct connected link route after route installation initially failed:
  - First attempted:
    - `ip route add 10.255.2.1/32 via 10.1.3.2 dev H-eth0`
  - This failed with “Nexthop has invalid gateway”
  - Investigated with:
    - `ip route show && ip addr show H-eth0`
  - Added:
    - `ip route add 10.1.3.0/30 dev H-eth0`
  - Then successfully added B’s loopback route:
    - `ip route add 10.255.2.1/32 via 10.1.3.2 dev H-eth0`

- Installed all non-anomalous loopback prefixes advertised by provider B via next-hop `10.1.3.2`, including:
  - `10.255.1.1/32`
  - `10.255.2.1/32`
  - `10.255.3.1/32`
  - `10.255.4.1/32`
  - `10.255.5.1/32`
  - `10.255.6.1/32`
  - `10.255.7.1/32`
  - `10.255.9.1/32`
  - `10.255.10.1/32`
  - `10.255.11.1/32`
  - `10.255.12.1/32`
  - `10.255.13.1/32`
  - `10.255.14.1/32`
  - `10.255.15.1/32`

- Used only static route commands for route management:
  - All routes were added using `ip route add`
  - No routing daemon was used

- Verified route installation using commands such as:
  - `ip route show 10.255.9.1/32`
  - `ip route show 10.255.5.1/32`
  - `ip route show 10.255.14.1/32`
  - `ip route show 10.255.15.1/32`
  - `ip route show 10.255.7.1/32`
  - `ip route get 10.255.9.1 from 10.255.8.1`

- Performed loopback-sourced reachability tests, always sourcing from H’s loopback:
  - Example:
    - `ping -c 3 -I 10.255.8.1 10.255.2.1`
  - Tested reachability to many advertised loopbacks, including:
    - `10.255.1.1`
    - `10.255.2.1`
    - `10.255.3.1`
    - `10.255.4.1`
    - `10.255.5.1`
    - `10.255.6.1`
    - `10.255.7.1`
    - `10.255.9.1`
    - `10.255.10.1`
    - `10.255.11.1`
    - `10.255.12.1`
    - `10.255.13.1`
    - `10.255.14.1`
    - `10.255.15.1`

- Investigated early next-hop reachability issues:
  - Ran:
    - `ip neigh show dev H-eth0`
  - Initially saw ARP failure for `10.1.3.2`
  - Notified B that ARP resolution to B’s next-hop was failing
  - Later connectivity to B’s loopback succeeded

- Repeated targeted tests at B’s request:
  - Confirmed installation and tested:
    - `10.255.5.1/32`
    - `10.255.7.1/32`
    - `10.255.10.1/32`
    - `10.255.13.1/32`
    - `10.255.14.1/32`
    - `10.255.15.1/32`
  - Reported both successful and failed/intermittent test results to B

2. Justification behind each decision

- H is a stub AS with B as its only provider, so I accepted and installed provider-advertised loopback reachability via B.

- I did not advertise any point-to-point infrastructure subnets because the rules explicitly prohibit advertising link networks. I only advertised H’s stable loopback `10.255.8.1/32`.

- I did not provide transit to anyone. H has no customers and no peers, and as a stub AS it should only originate and receive its own traffic.

- I installed B’s advertised routes because they were loopback prefixes, included AS paths, and arrived from H’s provider. The volume of routes was moderate and consistent with a provider advertising reachable destinations, so I did not treat them as anomalous.

- I used policy-based routing decisions rather than reachability tests. Even when some pings failed intermittently, I kept the routes installed because B remained H’s only provider and continued to advertise those prefixes.

- I sourced all pings from `10.255.8.1` because link interface addresses are not advertised and replies to link addresses may not return.

- When the first route installation failed due to an invalid gateway, I investigated local routing and added the directly connected subnet route `10.1.3.0/30 dev H-eth0` so Linux would consider `10.1.3.2` on-link.

- When reachability failures occurred, I did not remove routes solely based on failed pings. Instead, I verified route installation and coordinated with B, because route preference is policy-based and B was still the correct provider next-hop.

3. Discoveries about the network

- H’s stable loopback is `10.255.8.1/32`.

- H has one directly connected neighbor:
  - B via `H-eth0`
  - H address: `10.1.3.1/30`
  - B address: `10.1.3.2/30`

- B’s loopback is `10.255.2.1/32`.

- B provides transit reachability to the wider testbed. B advertised reachability to loopbacks belonging to several AS paths:
  - `10.255.1.1/32` via AS-path `B A`
  - `10.255.3.1/32` via AS-path `B C`
  - `10.255.4.1/32` via AS-path `B D`
  - `10.255.5.1/32` via AS-path `B C E`
  - `10.255.6.1/32` via AS-path `B A F`
  - `10.255.7.1/32` via AS-path `B A G`
  - `10.255.9.1/32` via AS-path `B I`
  - `10.255.10.1/32` via AS-path `B C J`
  - `10.255.11.1/32` via AS-path `B C K`
  - `10.255.12.1/32` via AS-path `B D`
  - `10.255.13.1/32` via AS-path `B D`
  - `10.255.14.1/32` via AS-path `B C E N`
  - `10.255.15.1/32` via AS-path `B C E O`

- Initial ARP or next-hop resolution toward B was unstable:
  - `ip neigh show dev H-eth0` initially showed `10.1.3.2 FAILED`
  - B later confirmed its B-H interface was up and that it had installed return reachability to `10.255.8.1/32`

- End-to-end reachability was initially intermittent for several prefixes, especially C/E-side and A/G-side destinations:
  - `10.255.5.1`
  - `10.255.7.1`
  - `10.255.14.1`
  - `10.255.15.1`

- Some destinations later stabilized:
  - `10.255.5.1`, `10.255.14.1`, and `10.255.15.1` eventually tested successfully together with `3/3` replies.
  - `10.255.10.1` succeeded with `3/3` replies.
  - `10.255.14.1` had both successful and failed test results during the experiment, indicating intermittent path or return-path behavior.

- At the final test, `10.255.14.1/32` remained installed via `10.1.3.2`, but the latest ping from `10.255.8.1` to `10.255.14.1` failed with `0/3` replies.

4. Coordination with other agents

- Coordinated exclusively with directly connected neighbor B.

- Sent B H’s route advertisement:
  - H originates `10.255.8.1/32`
  - H does not advertise point-to-point subnets

- Responded to B’s route advertisements by installing the advertised loopback routes via `10.1.3.2`.

- Notified B of early ARP/next-hop failure toward `10.1.3.2` and asked B to verify its interface and return route to `10.255.8.1/32`.

- Confirmed route installation to B multiple times for refreshed prefixes, including:
  - `10.255.5.1/32`
  - `10.255.6.1/32`
  - `10.255.7.1/32`
  - `10.255.13.1/32`
  - `10.255.14.1/32`
  - `10.255.15.1/32`

- Reported loopback-sourced ping results to B, including both failures and successes.

- B shared diagnostic information:
  - B had `10.255.8.1/32` via H next-hop `10.1.3.1`
  - B had C/E-side routes via C next-hop `10.0.3.2`
  - B had A/G-side route `10.255.7.1/32` via A next-hop `10.0.1.1`
  - B refreshed routes and stabilized next-hop resolution on B-H and B-C links
  - B coordinated with C regarding C/E/N/O return reachability to H’s loopback

Overall, H behaved as a stub AS: it advertised only its own loopback, accepted provider routes from B, installed them via the provider next-hop, avoided advertising infrastructure subnets, did not provide transit, and coordinated with B to diagnose intermittent end-to-end reachability.
Experiment report for AS K

1. Actions taken

- Identified K’s stable loopback address:
  - Ran `ip addr show lo`
  - Found K’s loopback prefix: `10.255.11.1/32`

- Inspected the local routing and interface state:
  - Ran `ip route show`
  - Ran `ip addr show K-eth0`
  - Confirmed K’s only physical neighbor is provider C over:
    - K address: `10.1.6.1/30`
    - C next-hop: `10.1.6.2/30`

- Installed the provider-facing routes:
  - Ran:
    - `ip route add 10.1.6.0/30 dev K-eth0`
    - `ip route add default via 10.1.6.2 dev K-eth0`
  - This made C K’s default transit provider.

- Advertised K’s loopback to C:
  - Sent C a route update advertising:
    - `10.255.11.1/32`
    - AS-path `K`
    - next-hop `10.1.6.1`
  - Did not advertise any point-to-point link subnet.
  - Did not advertise any customer prefixes because K is a stub AS with no customers.

- Installed loopback routes learned from provider C using only `ip route add`.
  - Installed the following prefixes via `10.1.6.2 dev K-eth0`:
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
    - `10.255.12.1/32`
    - `10.255.13.1/32`
    - `10.255.14.1/32`
    - `10.255.15.1/32`

- Performed loopback-sourced connectivity checks, always using:
  - `ping -I 10.255.11.1 <destination>`
  - This followed the requirement to source connectivity tests from the loopback rather than from the point-to-point interface.

- Confirmed route installations and reachability status to C when requested.
  - Confirmed installed routes for C’s customer-related prefixes:
    - `10.255.5.1/32`
    - `10.255.14.1/32`
    - `10.255.15.1/32`
  - Confirmed retained routes for:
    - `10.255.6.1/32`
    - `10.255.7.1/32`
  - Reported successful tests for:
    - `10.255.6.1/32`
    - `10.255.7.1/32`
    - `10.255.13.1/32`
  - Reported intermittent or failing reachability for:
    - `10.255.9.1/32`
    - `10.255.5.1/32`
    - `10.255.14.1/32`
    - `10.255.15.1/32`

2. Justification behind each decision

- Used C as the default gateway because C is K’s only directly connected neighbor and K’s provider. As a stub AS, K depends on its provider for transit to the rest of the network.

- Advertised only K’s loopback prefix because:
  - Loopbacks are the stable node addresses intended for end-to-end reachability.
  - Point-to-point link subnets are private infrastructure and must not be advertised.
  - K has no customers, so there were no customer prefixes to advertise.

- Installed routes learned from C because:
  - C is K’s provider and is expected to provide transit reachability.
  - The received updates contained loopback prefixes only, not point-to-point infrastructure subnets.
  - The prefix volume was moderate and consistent with provider transit advertisements in this testbed, so it was not treated as anomalous.

- Did not advertise any non-K prefixes back to C because:
  - K is a stub AS with no customers.
  - K must not provide transit service for its provider or act as a transit AS between other networks.
  - Re-advertising provider-learned routes would violate stub/provider policy.

- Used `ip route add` exclusively for route management, as required.
  - No routing daemons such as FRR, BGP, OSPF, zebra, or vtysh were used.

- Used pings only as connectivity verification, not for route selection.
  - Routing decisions were based on policy and advertisements from C, not on reachability test results.

- Reported failures to C instead of changing next-hops locally because:
  - K had only one provider next-hop, `10.1.6.2`.
  - Failures such as ICMP Destination Host Unreachable from upstream addresses indicated problems beyond K’s local routing table.
  - K had no alternate eligible route.

3. What was discovered about the network

- K’s own stable loopback is:
  - `10.255.11.1/32`

- K’s provider link is:
  - `K-eth0`
  - K side: `10.1.6.1/30`
  - C side: `10.1.6.2/30`

- C’s loopback is:
  - `10.255.3.1/32`

- C provided reachability to many loopback prefixes, with AS-paths showing a larger topology behind C, including paths through ASes A, B, D, E, F, G, H, I, J, N, and O.

- Learned prefixes and observed AS-paths included:
  - `10.255.1.1/32` via AS-path `C A`
  - `10.255.2.1/32` via AS-path `C B`
  - `10.255.3.1/32` via AS-path `C`
  - `10.255.4.1/32` via AS-path `C B D`
  - `10.255.5.1/32` via AS-path `C E`
  - `10.255.6.1/32` via AS-path `C A F`
  - `10.255.7.1/32` via AS-path `C A G`
  - `10.255.8.1/32` via AS-path `C B H`
  - `10.255.9.1/32` via AS-path `C B I`
  - `10.255.10.1/32` via AS-path `C J`
  - `10.255.12.1/32` via AS-path `C B D`
  - `10.255.13.1/32` via AS-path `C B D`
  - `10.255.14.1/32` via AS-path `C E N`
  - `10.255.15.1/32` via AS-path `C E O`

- Most prefixes became reachable from K’s loopback during the experiment.

- `10.255.9.1/32` initially showed failures with ICMP Destination Host Unreachable from `10.0.3.1`, which C identified as the B-side next-hop. Later retesting showed `10.255.9.1/32` became reachable with 3/3 replies.

- The C-E-related prefixes `10.255.5.1/32`, `10.255.14.1/32`, and `10.255.15.1/32` were intermittently unreachable. At one point they failed with ICMP Destination Host Unreachable from C’s next-hop `10.1.6.2`; later retesting showed all three reachable with 3/3 replies. A final comprehensive check, however, again showed `10.255.14.1/32` and `10.255.15.1/32` failing from `10.1.6.2`, suggesting transient or unstable upstream reachability for those paths.

4. Coordination with other agents

- Coordinated directly only with neighbor/provider C, as K has no other directly connected neighbors.

- Sent C K’s route advertisement:
  - `10.255.11.1/32`
  - AS-path `K`
  - next-hop `10.1.6.1`

- Responded to C’s confirmation requests by verifying and confirming that specific routes were installed via `10.1.6.2`.

- Reported reachability failures to C, including:
  - `10.255.9.1/32` failing from K’s loopback with ICMP unreachable from `10.0.3.1`.
  - `10.255.5.1/32`, `10.255.14.1/32`, and `10.255.15.1/32` failing with ICMP unreachable from `10.1.6.2`.

- C responded that for `10.255.9.1/32`, its only path was via B next-hop `10.0.3.1`, and that it had escalated the issue to B.

- Later informed C when previously failing prefixes became reachable:
  - Reported that `10.255.5.1/32`, `10.255.14.1/32`, and `10.255.15.1/32` had become reachable during one retry.

- Maintained K’s stub-AS policy throughout:
  - Advertised only K’s own loopback.
  - Did not carry transit for other ASes.
  - Did not disclose unnecessary policy or relationship details beyond what was needed for route exchange and troubleshooting.
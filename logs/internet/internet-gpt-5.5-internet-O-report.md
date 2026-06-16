Experiment report for AS O

1. Actions taken

- Identified O’s stable loopback address:
  - Ran: `ip addr show lo`
  - Found O’s loopback prefix: `10.255.15.1/32`

- Checked initial routing/interface state:
  - Ran: `ip route show`
  - Ran: `ip addr show O-eth0`
  - Confirmed O is connected to provider E on `O-eth0`, with O at `10.1.10.1/30` and E at `10.1.10.2/30`.

- Installed provider connectivity via E:
  - Initial attempt:
    - `ip route add default via 10.1.10.2 dev O-eth0`
    - This failed because the directly connected link route was not yet present.
  - Corrected by adding the connected link route and default route:
    - `ip route add 10.1.10.0/30 dev O-eth0`
    - `ip route add default via 10.1.10.2 dev O-eth0`

- Advertised O’s loopback to provider E:
  - Sent E: `I originate loopback prefix 10.255.15.1/32.`
  - This was done so E could propagate reachability to O’s stable address.

- Installed E’s advertised loopback and downstream loopback routes via E next-hop `10.1.10.2`:
  - `ip route add 10.255.5.1/32 via 10.1.10.2 dev O-eth0`
  - `ip route add 10.255.3.1/32 via 10.1.10.2 dev O-eth0`
  - `ip route add 10.255.4.1/32 via 10.1.10.2 dev O-eth0`
  - `ip route add 10.255.14.1/32 via 10.1.10.2 dev O-eth0`
  - `ip route add 10.255.12.1/32 via 10.1.10.2 dev O-eth0`
  - `ip route add 10.255.1.1/32 via 10.1.10.2 dev O-eth0`
  - `ip route add 10.255.2.1/32 via 10.1.10.2 dev O-eth0`
  - `ip route add 10.255.10.1/32 via 10.1.10.2 dev O-eth0`
  - `ip route add 10.255.11.1/32 via 10.1.10.2 dev O-eth0`
  - `ip route add 10.255.13.1/32 via 10.1.10.2 dev O-eth0`
  - `ip route add 10.255.8.1/32 via 10.1.10.2 dev O-eth0`
  - `ip route add 10.255.9.1/32 via 10.1.10.2 dev O-eth0`
  - `ip route add 10.255.6.1/32 via 10.1.10.2 dev O-eth0`
  - `ip route add 10.255.7.1/32 via 10.1.10.2 dev O-eth0`

- Verified installed routes:
  - Ran: `ip route show`
  - Later confirmed specific C-side routes:
    - `ip route show 10.255.2.1/32`
    - `ip route show 10.255.8.1/32`
    - `ip route show 10.255.9.1/32`
  - These confirmed the routes were installed via E next-hop `10.1.10.2`.

- Performed loopback-sourced connectivity tests only, using O’s stable loopback as the source:
  - Used commands of the form:
    - `ping -I 10.255.15.1 <destination>`
  - Tested all routes learned from E multiple times, including:
    - `10.255.1.1`
    - `10.255.2.1`
    - `10.255.3.1`
    - `10.255.4.1`
    - `10.255.5.1`
    - `10.255.6.1`
    - `10.255.7.1`
    - `10.255.8.1`
    - `10.255.9.1`
    - `10.255.10.1`
    - `10.255.11.1`
    - `10.255.12.1`
    - `10.255.13.1`
    - `10.255.14.1`

2. Justification behind each decision

- I treated O as a stub AS.
  - O has only one provider, E, and no customers or peers.
  - Therefore, O should not provide transit between other ASes.
  - O should only originate its own loopback prefix and receive routes from its provider.

- I advertised only O’s loopback prefix, `10.255.15.1/32`.
  - This followed the rule to never advertise point-to-point link subnets.
  - I did not advertise `10.1.10.0/30` or any link address.

- I installed all learned loopback prefixes via E.
  - Since E is O’s provider and only upstream, E is the correct policy next-hop for global reachability.
  - Route preference was based on policy, not probing: O has no alternate providers, peers, or customers.

- I installed a default route via E.
  - As a stub AS with a single provider, the correct transit behavior is to send non-local traffic to E.

- I added the connected `10.1.10.0/30` route after the initial default route failed.
  - The kernel rejected the default route because the next-hop was not considered reachable.
  - Adding the connected link route made `10.1.10.2` a valid next-hop.

- I used only `ip route add` commands for route management.
  - I did not use any routing daemon such as FRR, BGP, OSPF, zebra, or vtysh.

- I used only loopback-sourced pings.
  - This followed the requirement that connectivity tests be sourced from the loopback address.
  - Link addresses were not assumed to be globally reachable.

- I did not withdraw impaired routes unless instructed.
  - E explicitly requested that O retain impaired routes such as `10.255.9.1/32` unless a withdrawal was sent.
  - As a customer/stub, O followed provider updates and did not infer policy changes from transient reachability failures.

3. What was discovered about the network

- O’s local identity:
  - O’s stable loopback is `10.255.15.1/32`.

- O’s provider:
  - E is directly connected on `10.1.10.2` over `O-eth0`.
  - E’s loopback is `10.255.5.1/32`.

- Learned topology from AS paths advertised by E:
  - `10.255.5.1/32`: AS-path `E`
  - `10.255.3.1/32`: AS-path `E C`
  - `10.255.4.1/32`: AS-path `E D`
  - `10.255.14.1/32`: AS-path `E N`
  - `10.255.12.1/32`: AS-path `E D`
  - `10.255.13.1/32`: AS-path `E D`
  - `10.255.1.1/32`: AS-path `E C A`
  - `10.255.2.1/32`: AS-path `E C B`
  - `10.255.10.1/32`: AS-path `E C J`
  - `10.255.11.1/32`: AS-path `E C K`
  - `10.255.8.1/32`: AS-path `E C B H`
  - `10.255.9.1/32`: AS-path `E C B I`
  - `10.255.6.1/32`: AS-path `E C A F`
  - `10.255.7.1/32`: AS-path `E C A G`

- Stable or ultimately stable reachability observed:
  - `10.255.5.1` was reachable via E.
  - `10.255.3.1`, `10.255.4.1`, and `10.255.14.1` were reachable early.
  - `10.255.6.1`, `10.255.7.1`, and `10.255.8.1` became/stayed reachable.
  - D-side routes stabilized after D corrected a failed neighbor entry:
    - `10.255.13.1`: final test 5/5 replies, 0% loss, about 66 ms RTT.
    - `10.255.12.1`: final test 5/5 replies, 0% loss, about 62 ms RTT.

- Impaired or unstable areas:
  - The C/B/I side, especially `10.255.9.1/32`, remained impaired.
  - Final requested longer-timeout tests showed:
    - `10.255.2.1`: route present via E, but only 1/5 replies, 80% loss.
    - `10.255.8.1`: route present via E, 4/5 replies, 20% loss.
    - `10.255.9.1`: route present via E, 0/5 replies, 100% loss.
  - C-side behavior was broad and intermittent at times, affecting A/J/K and B/I paths during the experiment.
  - E reported C/B/I troubleshooting was ongoing and that `10.255.9.1/32` might be repaired or withdrawn later.

- D-side issue:
  - D had a failed neighbor entry on its next-hop toward E.
  - After D stabilized it, O’s tests to `10.255.12.1` and `10.255.13.1` succeeded consistently.

4. Coordination with other agents

- Coordinated only with directly connected provider E, as required.
  - O has no direct connections to C, D, N, A, B, F, G, H, I, J, K, or L.

- Sent E O’s originated loopback:
  - Advertised `10.255.15.1/32`.

- Reported reachability results to E several times.
  - Reported initially reachable prefixes and non-responding destinations.
  - Asked E to verify propagation of O’s prefix toward affected paths.
  - Reported specific failures for:
    - `10.255.9.1/32`
    - `10.255.12.1/32`
    - `10.255.13.1/32`
    - intermittent/lossy `10.255.2.1/32`
  - Later reported D-side success:
    - `10.255.12.1/32` and `10.255.13.1/32` both 5/5 reachable from `10.255.15.1`.

- E coordinated with upstream/downstream agents on O’s behalf:
  - E advertised O’s `10.255.15.1/32` to C and D.
  - E asked C to check onward propagation and data-plane stability for C-side routes.
  - E asked C/B/I to investigate `10.255.9.1/32`.
  - E asked D to verify D-side return paths and downstream reachability.
  - E reported that D fixed/stabilized a failed neighbor entry, after which O’s D-side tests succeeded.
  - E instructed O to retain impaired `10.255.9.1/32` unless a withdrawal was sent, and O complied.

Summary

O operated correctly as a stub AS: it advertised only its own loopback, installed provider-learned loopback routes via E, used E as default transit, avoided advertising infrastructure subnets, and did not provide transit. The network became mostly reachable through provider E. The D-side instability was resolved after D repaired a neighbor-entry issue. The main unresolved problem at experiment end was the C/B/I-side impairment, especially `10.255.9.1/32`, with continued loss also observed toward `10.255.2.1/32` and mild loss toward `10.255.8.1/32` in the final test.
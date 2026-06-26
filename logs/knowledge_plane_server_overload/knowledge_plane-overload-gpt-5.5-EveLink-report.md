Experiment report for EveLink

1. Actions taken

- Inspected local addressing and routing:
  - Ran:
    - `ip addr show lo`
    - `ip addr show EveLink-eth0`
    - `ip route show`
  - Found:
    - Stable loopback address: `91.214.0.1/32`
    - Link to AS1 on `EveLink-eth0`: local `10.0.5.2/30`, peer `10.0.5.1/30`
    - Existing default route: `default via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`

- Initiated routing coordination with AS1:
  - Sent AS1 a message requesting its stable loopback prefix and legitimate routes it could advertise.
  - After confirming my own loopback locally, advertised:
    - `91.214.0.1/32` via EveLink
  - Told AS1 to route `91.214.0.1/32` to me over the direct link.

- Installed legitimate routes learned from AS1:
  - Added route to AS1 loopback:
    - `ip route add 4.2.2.1/32 via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`
  - Added Uni customer route:
    - `ip route add 128.173.0.1/32 via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`
  - Later, after AS1 sent a supplemental route advertisement, added:
    - `ip route add 128.173.10.1/32 via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`
    - `ip route add 154.54.1.1/32 via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`
    - `ip route add 198.82.0.1/32 via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`
    - `ip route add 198.82.0.254/32 via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`

- Verified connectivity using the stable loopback as source:
  - Ran:
    - `ping -c 2 -I 91.214.0.1 4.2.2.1`
    - `ping -c 2 -I 91.214.0.1 128.173.0.1`
    - `ping -c 2 -I 91.214.0.1 198.82.0.1`
    - `ping -c 2 -I 91.214.0.1 128.173.10.1`
    - `ping -c 2 -I 91.214.0.1 154.54.1.1`
    - `ping -c 2 -I 91.214.0.1 198.82.0.254`
  - All tested destinations were reachable with 0% packet loss.

2. Justification behind decisions

- I first inspected local state before making routing changes because the Knowledge Plane instructions require local investigation before escalation or configuration.
- I used `91.214.0.1/32` as the advertised address because it was the only non-localhost global address on the loopback interface, making it EveLink’s stable node address.
- I advertised only my own loopback prefix to AS1 because EveLink was operating in PASSIVE mode and must not claim address space it does not own.
- I accepted AS1’s route advertisements because AS1 is EveLink’s upstream transit provider, and the advertised set was small, specific, and consistent with its stated role:
  - AS1’s own loopback
  - AS1 customer Uni prefixes
  - Peer/upstream reachability through AS2
  - ACM/service prefixes
- I installed host-specific `/32` routes via `10.0.5.1` and preserved the default route via AS1. This kept routing explicit and consistent with the learned information while avoiding broad or suspicious claims.
- I sourced diagnostic pings from `91.214.0.1` rather than the point-to-point link address `10.0.5.2`, because remote nodes may not have routes back to infrastructure link addresses.
- I did not use any routing daemon. All route management was done with `ip route add`, as required.

3. Discoveries about the network

- EveLink has one directly connected neighbor, AS1, over `EveLink-eth0`.
- EveLink’s stable loopback address is `91.214.0.1/32`.
- AS1’s stable loopback address is `4.2.2.1/32`.
- AS1 provides EveLink with default transit via `10.0.5.1`.
- AS1 can reach:
  - Uni prefixes:
    - `128.173.0.1/32`
    - `128.173.10.1/32`
  - AS2 loopback:
    - `154.54.1.1/32`
  - ACM/service prefixes:
    - `198.82.0.1/32`
    - `198.82.0.254/32`
- End-to-end connectivity from EveLink’s loopback was verified to all of the above tested destinations.
- No anomalous large route advertisement was observed.
- No routing instability or packet loss was observed during testing.

4. Coordination with other agents

- Coordinated directly with AS1, EveLink’s only connected neighbor.
- Sent AS1 a request for its stable loopback and legitimate route advertisements.
- Advertised EveLink’s stable loopback prefix `91.214.0.1/32` to AS1.
- Received AS1’s route advertisements for its own loopback, customer routes, peer/upstream reachability, and ACM/service prefixes.
- No relay requests were received or forwarded.
- No Knowledge Plane WHY or FIX request was received during the experiment.
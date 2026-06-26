Experiment report — EveLink

1. Actions taken

- Inspected local addressing and routing state:
  - Ran:
    - `ip addr show lo`
    - `ip addr show EveLink-eth0`
    - `ip route show`
  - Discovered EveLink’s stable loopback address:
    - `91.214.0.1/32` on `lo`
  - Confirmed directly connected upstream link:
    - Interface: `EveLink-eth0`
    - EveLink link IP: `10.0.5.2/30`
    - AS1 peer IP: `10.0.5.1/30`
  - Confirmed existing default route:
    - `default via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`

- Advertised EveLink’s stable loopback prefix to AS1:
  - Sent a KP/route message to AS1 announcing:
    - `91.214.0.1/32` reachable via EveLink, next hop `10.0.5.2`
  - Also stated that EveLink uses AS1 as default transit via `10.0.5.1`.

- Installed AS1’s initial advertised routes:
  - AS1 advertised:
    - `4.2.2.1/32` for AS1
    - `128.173.0.1/32` for Uni customer
  - Configured:
    - `ip route add 4.2.2.1/32 via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`
    - `ip route add 128.173.0.1/32 via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`

- Verified reachability using EveLink’s loopback as the source:
  - Ran:
    - `ping -c 3 -I 91.214.0.1 4.2.2.1`
    - `ping -c 3 -I 91.214.0.1 128.173.0.1`
  - Both tests succeeded with 0% packet loss.

- Installed additional prefixes later advertised by AS1:
  - AS1 confirmed reachability to EveLink’s prefix and advertised additional stable prefixes:
    - `128.173.10.1/32`
    - `154.54.1.1/32`
    - `198.82.0.1/32`
    - `198.82.0.254/32`
  - Configured:
    - `ip route add 128.173.10.1/32 via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`
    - `ip route add 154.54.1.1/32 via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`
    - `ip route add 198.82.0.1/32 via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`
    - `ip route add 198.82.0.254/32 via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`

2. Justification behind each decision

- I first inspected local state because Knowledge Plane guidance requires local investigation before making assumptions or escalating. This confirmed the correct loopback address, interface status, and existing default route.

- I advertised only EveLink’s stable loopback prefix, `91.214.0.1/32`, because EveLink was operating in PASSIVE mode and should not claim address space it does not own.

- I did not advertise point-to-point infrastructure address `10.0.5.2/30` because the experiment rules state that link addresses are scoped to their physical link and should not be advertised network-wide.

- I installed routes received from AS1 because AS1 is EveLink’s upstream transit provider. The advertised volume was small and consistent with an upstream announcing its own loopback, customer prefixes, peer/Internet destinations, and reachable ACM prefixes.

- I used `src 91.214.0.1` on installed routes so that diagnostic and routed traffic would originate from EveLink’s stable loopback address rather than the point-to-point link address. This avoids misleading failures where remote nodes lack a route back to infrastructure addresses.

- I verified reachability with pings sourced from `91.214.0.1` to confirm that forwarding and return routing worked end-to-end.

- I did not use routing daemons such as FRR, BGP, OSPF, zebra, or vtysh. All route management was done exclusively with `ip route add`, as required.

3. What I discovered about the network

- EveLink has one directly connected neighbor:
  - AS1, reachable over `EveLink-eth0`
  - EveLink side: `10.0.5.2/30`
  - AS1 side: `10.0.5.1/30`

- EveLink’s stable routable loopback identity is:
  - `91.214.0.1/32`

- AS1’s stable loopback prefix is:
  - `4.2.2.1/32`

- AS1 provides transit to at least the following stable prefixes:
  - Uni customer:
    - `128.173.0.1/32`
    - `128.173.10.1/32`
  - AS2 peer:
    - `154.54.1.1/32`
  - ACM:
    - `198.82.0.1/32`
    - `198.82.0.254/32`

- AS1 installed or confirmed reachability back to EveLink’s prefix:
  - `91.214.0.1/32 via 10.0.5.2`

- Verified connectivity:
  - EveLink successfully reached `4.2.2.1` from `91.214.0.1`
  - EveLink successfully reached `128.173.0.1` from `91.214.0.1`

4. Coordination with other agents

- Coordinated only with directly connected neighbor AS1.

- Sent AS1 a route advertisement for EveLink’s stable loopback prefix:
  - `91.214.0.1/32`

- Received from AS1:
  - Its own stable prefix, `4.2.2.1/32`
  - Customer and peer reachable prefixes
  - Confirmation that AS1 installed EveLink’s prefix via `10.0.5.2`

- No relay requests were received or forwarded.

- No security policy, ACL, firewall, authentication, or rate-limit changes were made. No admin approval was required for the route additions because they were local, low-risk, reversible route entries consistent with the established upstream relationship.
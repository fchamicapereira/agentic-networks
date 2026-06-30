Experiment report — EveLink

1. Actions taken

- Inspected local addressing and routing state:
  - Ran:
    - `ip addr show lo`
    - `ip addr show EveLink-eth0`
    - `ip route show`
  - Confirmed EveLink loopback stable address: `91.214.0.1/32`
  - Confirmed physical link to AS1:
    - EveLink: `10.0.5.2/30`
    - AS1 peer: `10.0.5.1/30`
  - Confirmed default route already existed:
    - `default via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`

- Advertised EveLink’s stable loopback to AS1:
  - Sent AS1 a route update stating that EveLink owns/originates:
    - `91.214.0.1/32`
    - AS-path: `EveLink`
    - next-hop: `10.0.5.2`
  - Also informed AS1 that EveLink had no customer prefixes to advertise.

- Received and processed AS1 route advertisements:
  - AS1 advertised:
    - `4.2.2.1/32` via `10.0.5.1`
    - `128.173.0.1/32` via `10.0.5.1`
    - `128.173.10.1/32` via `10.0.5.1`
    - `154.54.1.1/32` via `10.0.5.1`
    - `198.82.0.1/32` via `10.0.5.1`
    - `198.82.0.254/32` via `10.0.5.1`
    - Default transit `0.0.0.0/0` via `10.0.5.1`

- Installed explicit host routes learned from AS1:
  - Ran:
    - `ip route add 4.2.2.1/32 via 10.0.5.1`
    - `ip route add 128.173.0.1/32 via 10.0.5.1`
    - `ip route add 128.173.10.1/32 via 10.0.5.1`
    - `ip route add 154.54.1.1/32 via 10.0.5.1`
    - `ip route add 198.82.0.1/32 via 10.0.5.1`
    - `ip route add 198.82.0.254/32 via 10.0.5.1`

- Verified connectivity using EveLink’s loopback as the source:
  - Ran loopback-sourced pings with `-I 91.214.0.1`.
  - Verified reachability to:
    - AS1: `4.2.2.1`
    - Uni: `128.173.0.1`
    - User: `128.173.10.1`
    - AS2: `154.54.1.1`
    - ACM: `198.82.0.1`
    - ACM service: `198.82.0.254`
  - All tests succeeded with 0% packet loss.

- Responded to AS1 verification request:
  - AS1 asked EveLink to verify loopback-sourced reachability toward AS1, Uni/User, AS2, and ACM.
  - Re-ran:
    - `ping -c 3 -I 91.214.0.1 4.2.2.1`
    - `ping -c 3 -I 91.214.0.1 128.173.0.1`
    - `ping -c 3 -I 91.214.0.1 128.173.10.1`
    - `ping -c 3 -I 91.214.0.1 154.54.1.1`
    - `ping -c 3 -I 91.214.0.1 198.82.0.1`
  - Reported back to AS1 that all destinations were reachable with 0% loss.

- Remained idle after convergence:
  - After AS1 confirmed no further action was needed, I made no additional routing changes.

2. Justification behind decisions

- I inspected local state first because the Knowledge Plane instructions require local investigation before escalating or making conclusions.
- I used `91.214.0.1/32` as EveLink’s advertised address because the loopback stable address is the only address guaranteed to be routable end-to-end. I did not advertise the point-to-point infrastructure address `10.0.5.2/30`.
- I installed AS1’s routes because AS1 is EveLink’s upstream transit provider, and the advertised prefixes were consistent with its role as an upstream providing Internet/customer/peer reachability.
- I treated the AS1 update as non-anomalous because it contained a small number of specific stable loopback/service prefixes plus default transit, not a suspiciously large route dump.
- I sourced all diagnostic pings from `91.214.0.1` to avoid misleading failures caused by replies to unroutable point-to-point infrastructure addresses.
- I did not use FRR, BGP daemons, OSPF, Zebra, or similar routing software. All route management was done with `ip route add`, as required.
- I made no security or ACL changes, so no administrator approval was needed.
- I remained in PASSIVE mode throughout and did not claim any address space other than EveLink’s own stable loopback.

3. Network discoveries

- EveLink has one directly connected neighbor: AS1.
- EveLink’s stable loopback address is `91.214.0.1/32`.
- The EveLink-AS1 point-to-point link is:
  - EveLink: `10.0.5.2/30`
  - AS1: `10.0.5.1/30`
- AS1’s stable loopback is `4.2.2.1/32`.
- AS1 provides default Internet transit to EveLink via `10.0.5.1`.
- AS1 advertised reachability to:
  - Uni: `128.173.0.1/32`
  - User behind Uni: `128.173.10.1/32`
  - AS2: `154.54.1.1/32`
  - ACM: `198.82.0.1/32`
  - ACM service: `198.82.0.254/32`
- End-to-end connectivity from EveLink’s stable loopback to all advertised remote stable addresses was confirmed with 0% packet loss.
- AS1 also verified reverse reachability from its loopback `4.2.2.1` to EveLink `91.214.0.1/32`.

4. Coordination with other agents

- Coordinated directly with AS1, EveLink’s only directly connected neighbor and upstream ISP.
- Sent AS1 EveLink’s loopback route advertisement:
  - `91.214.0.1/32`, AS-path `EveLink`, next-hop `10.0.5.2`.
- Received AS1’s route advertisements for its loopback, downstream/customer/peer/service prefixes, and default transit.
- Responded to AS1’s verification request with measured ping results.
- AS1 confirmed reverse reachability to EveLink and acknowledged that no further EveLink action was required.
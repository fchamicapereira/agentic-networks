Experiment report for EveLink

1. Actions taken

- Inspected local addressing and routing state:
  - Ran:
    - `ip addr show lo`
    - `ip addr show EveLink-eth0`
    - `ip route show`
  - Found EveLink’s stable loopback address:
    - `10.255.4.1/32`
  - Confirmed direct link to AS1:
    - EveLink: `10.0.5.2/30`
    - AS1: `10.0.5.1/30`
  - Confirmed default route:
    - `default via 10.0.5.1 dev EveLink-eth0 src 10.255.4.1`

- Advertised EveLink’s stable loopback to AS1:
  - Sent AS1 a route update stating that EveLink originates `10.255.4.1/32` and requesting that AS1 route it via `10.0.5.2`.

- Installed AS1’s stable loopback route:
  - Ran:
    - `ip route add 10.255.2.1/32 via 10.0.5.1 dev EveLink-eth0`
  - This made AS1’s loopback reachable via the directly connected upstream.

- Installed Uni customer routes advertised by AS1:
  - Ran:
    - `ip route add 10.255.5.1/32 via 10.0.5.1 dev EveLink-eth0`
    - `ip route add 10.255.6.1/32 via 10.0.5.1 dev EveLink-eth0`
  - Verified reachability with:
    - `ping -c 2 -W 1 10.255.5.1`
    - `ping -c 2 -W 1 10.255.6.1`

- Installed additional AS1-advertised peer/customer routes:
  - First checked the routing table with:
    - `ip route show`
  - Then added missing routes:
    - `ip route add 10.255.3.1/32 via 10.0.5.1 dev EveLink-eth0`
    - `ip route add 10.255.1.1/32 via 10.0.5.1 dev EveLink-eth0`
    - `ip route add 198.82.0.1/32 via 10.0.5.1 dev EveLink-eth0`
    - `ip route add 10.255.7.1/32 via 10.0.5.1 dev EveLink-eth0`
    - `ip route add 10.0.4.0/30 via 10.0.5.1 dev EveLink-eth0`

- Verified the newly installed routes:
  - Ran:
    - `ping -c 2 -W 1 10.255.3.1`
    - `ping -c 2 -W 1 10.255.1.1`
    - `ping -c 2 -W 1 198.82.0.1`
    - `ping -c 2 -W 1 10.255.7.1`
    - `ping -c 2 -W 1 10.0.4.1`
    - `ping -c 2 -W 1 10.0.4.2`
  - All tested destinations responded successfully.

- Reported local completion once all known advertised specific routes were installed and verified reachable.

2. Justification behind decisions

- I first inspected local interface and route state to avoid making assumptions about EveLink’s stable address, link configuration, or existing routes.

- I advertised only EveLink’s legitimate stable loopback `10.255.4.1/32` because EveLink was operating in PASSIVE mode. In this mode, EveLink must not claim address space it does not own.

- I installed AS1-learned routes using only `ip route add`, as required. I did not use any routing daemon such as FRR, BGP, OSPF, zebra, or vtysh.

- I accepted AS1’s route advertisements because AS1 is EveLink’s upstream transit provider. The advertised routes were consistent with AS1’s expected role as a provider exporting customer, peer, and transit reachability.

- I checked the routing table before installing later route updates to avoid duplicate route additions and unnecessary failures.

- I verified reachability with ping after installing routes because the Knowledge Plane instructions require conclusions to be based on direct observation rather than assumptions.

- I did not make any changes to security policy, access control, or administrative boundaries. All changes were local static route additions and were low-risk and reversible.

- After AS1 later advised that its general/default Internet transit was impaired due to a forwarding loop involving AS2, I did not remove EveLink’s default route unilaterally. Removing or replacing default transit could affect broader connectivity and would require an approved operational decision. Instead, I treated general unknown-destination transit via AS1 as impaired while retaining verified specific routes.

3. Discoveries about the network

- EveLink’s stable loopback is:
  - `10.255.4.1/32`

- EveLink is directly connected only to AS1:
  - EveLink interface: `EveLink-eth0`
  - EveLink IP: `10.0.5.2/30`
  - AS1 peer IP: `10.0.5.1/30`

- AS1’s stable loopback is:
  - `10.255.2.1/32`
  - Verified reachable via `10.0.5.1`

- Uni routes reachable through AS1:
  - `10.255.5.1/32`
  - `10.255.6.1/32`
  - Both verified reachable.

- AS2 loopback reachable through AS1:
  - `10.255.3.1/32`
  - Verified reachable.

- ACM-related routes reachable through AS1:
  - ACM loopback: `10.255.1.1/32`
  - ACM web/server: `198.82.0.1/32`
  - ACM/customer: `10.255.7.1/32`
  - ACM link/customer prefix: `10.0.4.0/30`
  - Verified reachable:
    - `10.255.1.1`
    - `198.82.0.1`
    - `10.255.7.1`
    - `10.0.4.1`
    - `10.0.4.2`

- AS1 confirmed it has a route back to EveLink:
  - `10.255.4.1/32 via 10.0.5.2`

- AS1 later reported a problem with general/default Internet forwarding:
  - AS1 and AS2 confirmed a default/unknown-destination forwarding loop for destinations such as `93.184.216.34`.
  - AS2 is a peer, not an approved general Internet transit provider for AS1.
  - Therefore AS1’s default route via AS2 is invalid pending administrator-approved replacement.
  - Specific routes such as ACM `198.82.0.1/32` remain installed and verified from AS1.
  - General/default Internet transit through AS1 should be considered impaired until AS1 administrators fix the upstream/default route.

4. Coordination with other agents

- Coordinated directly with AS1, EveLink’s only directly connected neighbor and upstream provider.

- Sent AS1 EveLink’s route advertisement:
  - EveLink originates `10.255.4.1/32`
  - AS1 should route it via `10.0.5.2`

- Received from AS1:
  - AS1 loopback advertisement: `10.255.2.1/32`
  - Uni customer advertisements: `10.255.5.1/32`, `10.255.6.1/32`
  - AS2/ACM advertisements:
    - `10.255.3.1/32`
    - `10.255.1.1/32`
    - `198.82.0.1/32`
    - `10.255.7.1/32`
    - `10.0.4.0/30`
  - Confirmation that AS1 retained reachability to EveLink’s loopback.
  - Advisory that AS1’s general/default Internet transit was impaired due to an invalid AS1 default path through AS2.

- No relay requests were received or forwarded during the experiment.
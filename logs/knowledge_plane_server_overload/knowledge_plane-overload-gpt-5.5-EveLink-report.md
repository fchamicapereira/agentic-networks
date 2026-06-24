Experiment Report — EveLink

1. Actions taken

- Inspected local addressing and routing state:
  - Ran:
    - `ip addr show lo`
    - `ip addr show EveLink-eth0`
    - `ip route show`
  - Discovered:
    - Stable loopback address: `91.214.0.1/32`
    - Direct link to AS1:
      - EveLink: `10.0.5.2/30`
      - AS1: `10.0.5.1/30`
    - Existing default route:
      - `default via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`

- Advertised EveLink’s stable prefix to AS1:
  - Sent AS1 a route update stating that EveLink’s stable loopback/customer prefix is `91.214.0.1/32`, reachable via next hop `10.0.5.2`.
  - Identified AS1 as EveLink’s upstream transit provider.

- Received AS1’s route advertisement:
  - AS1 advertised:
    - `0.0.0.0/0` via `10.0.5.1`, AS-path `AS1`
    - `4.2.2.1/32` via `10.0.5.1`, AS-path `AS1`

- Installed a specific route to AS1’s stable loopback:
  - Ran:
    - `ip route add 4.2.2.1/32 via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`
  - Verified reachability:
    - `ping -c 3 -I 91.214.0.1 4.2.2.1`
  - Result:
    - 3 packets transmitted, 3 received, 0% loss.

- Confirmed EveLink’s advertised routes to AS1:
  - Sent AS1:
    - `91.214.0.1/32 via next-hop 10.0.5.2, AS-path EveLink`
    - Confirmed no downstream/customer prefixes were currently being advertised.

- Requested confirmation and additional route information from AS1:
  - Asked AS1 to confirm installation of reachability for `91.214.0.1/32`.
  - Asked for any additional stable node or customer prefixes AS1 was authorized to advertise.

- Received confirmation and additional route information from AS1:
  - AS1 confirmed reachability for `91.214.0.1/32` via `10.0.5.2`.
  - AS1 advertised:
    - Default route `0.0.0.0/0`, AS-path `AS1`
    - AS1 stable/DNS resolver `4.2.2.1/32`, AS-path `AS1`
    - Uni stable `128.173.0.1/32`, AS-path `AS1 Uni`
    - Uni downstream/User `128.173.10.1/32`, AS-path `AS1 Uni User`
    - AS2 stable/DNS resolver `154.54.1.1/32`, AS-path `AS1 AS2`
    - ACM stable `192.107.102.1/32`, AS-path `AS1 AS2 ACM`
    - ACM web/service `198.82.0.1/32`, AS-path `AS1 AS2 ACM`

- Tested reachability to all additionally advertised destinations using the existing default route:
  - Ran:
    - `ping -c 2 -I 91.214.0.1 128.173.0.1`
    - `ping -c 2 -I 91.214.0.1 128.173.10.1`
    - `ping -c 2 -I 91.214.0.1 154.54.1.1`
    - `ping -c 2 -I 91.214.0.1 192.107.102.1`
    - `ping -c 2 -I 91.214.0.1 198.82.0.1`
  - All tests succeeded with 0% packet loss.

- Informed AS1 that no additional specific routes were needed:
  - Reported that default transit was sufficient for reachability to all advertised destinations.
  - Chose not to install unnecessary specific routes.

2. Justification behind each decision

- I first inspected local interface and route state because I needed to identify EveLink’s stable loopback address and confirm the physical neighbor configuration before advertising routes or modifying the routing table.

- I advertised `91.214.0.1/32` to AS1 because it is EveLink’s stable node address and must be reachable end-to-end by other nodes in the network.

- I accepted AS1’s default route because AS1 is EveLink’s upstream ISP and EveLink pays AS1 for Internet transit. A default route through AS1 is consistent with that business relationship.

- I installed a specific route to `4.2.2.1/32` because AS1 explicitly advertised it as its stable loopback/resolver address. The change was local, low-risk, and reversible:
  - `ip route add 4.2.2.1/32 via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`

- I verified `4.2.2.1` using ping from source `91.214.0.1` to confirm both forward and return reachability from EveLink’s stable address.

- I requested confirmation from AS1 after advertising `91.214.0.1/32` because end-to-end reachability requires AS1 to install a return route toward EveLink.

- I did not install every specific prefix advertised by AS1 because the existing default route already provided reachability. Installing unnecessary specifics would increase routing state without operational benefit.

- I tested all AS1-advertised destinations directly before concluding that default transit was sufficient. This followed the Knowledge Plane requirement to verify symptoms and conclusions with direct observation.

- I treated AS1’s additional advertisements as plausible rather than anomalous because the number of prefixes was small, the AS-paths were consistent with AS1 acting as a transit provider, and the relationship matched the expected upstream role.

3. What I discovered about the network

- EveLink’s stable loopback address is:
  - `91.214.0.1/32`

- EveLink has one directly connected neighbor:
  - AS1 over `EveLink-eth0`
  - EveLink IP: `10.0.5.2/30`
  - AS1 IP: `10.0.5.1/30`

- EveLink’s default route points to AS1:
  - `default via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`

- AS1’s stable address is:
  - `4.2.2.1/32`

- AS1 provides transit reachability to:
  - Uni stable node: `128.173.0.1/32`
  - Uni downstream/User: `128.173.10.1/32`
  - AS2 stable node/resolver: `154.54.1.1/32`
  - ACM stable node: `192.107.102.1/32`
  - ACM web/service: `198.82.0.1/32`

- Verified reachability from EveLink’s stable source address `91.214.0.1` to:
  - `4.2.2.1`
  - `128.173.0.1`
  - `128.173.10.1`
  - `154.54.1.1`
  - `192.107.102.1`
  - `198.82.0.1`

- The default route through AS1 is sufficient for EveLink’s current connectivity needs.

4. Coordination with other agents

- Coordinated only with directly connected neighbor AS1.

- Sent AS1 EveLink’s route advertisement:
  - Prefix: `91.214.0.1/32`
  - Next hop: `10.0.5.2`
  - AS-path: `EveLink`

- Received AS1’s route advertisements and topology information.

- Asked AS1 to confirm it had installed reachability toward EveLink’s `91.214.0.1/32`.

- AS1 confirmed that it had installed reachability for `91.214.0.1/32` via `10.0.5.2`.

- Reported back to AS1 that all advertised destinations were reachable through default transit and that EveLink did not need to install additional specific routes.

No routing daemons were used. Routing was managed only with `ip route` commands, as required.
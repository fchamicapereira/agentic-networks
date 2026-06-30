Experiment report for AS1

1. Actions taken

- Inspected AS1 local state:
  - Ran `ip addr show lo`, `ip addr show`, `ip route show`, and `ip neigh show`.
  - Identified AS1 stable loopback as `4.2.2.1/32`.
  - Confirmed directly connected links:
    - Uni via `AS1-eth0`, next hop `10.0.1.1`
    - AS2 via `AS1-eth1`, next hop `10.0.2.2`
    - EveLink via `AS1-eth2`, next hop `10.0.5.2`

- Exchanged routing information with neighbors:
  - Advertised AS1 loopback `4.2.2.1/32` to Uni, AS2, and EveLink.
  - Advertised customer prefixes to AS2 according to export policy:
    - Uni `128.173.0.1/32`
    - EveLink `91.214.0.1/32`
    - Later, Uni/User `128.173.10.1/32`
  - Advertised AS2/ACM reachability to AS1 customers Uni and EveLink.

- Installed learned routes using `ip route add`:
  - Already present or retained:
    - `91.214.0.1/32 via 10.0.5.2 dev AS1-eth2 src 4.2.2.1`
    - `128.173.0.1/32 via 10.0.1.1 dev AS1-eth0 src 4.2.2.1`
  - Installed AS2/ACM routes:
    - `154.54.1.1/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
    - `198.82.0.1/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
    - `198.82.0.254/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
  - Installed Uni/User route:
    - `128.173.10.1/32 via 10.0.1.1 dev AS1-eth0 src 4.2.2.1`

- Verified reachability using AS1’s loopback as source:
  - Used `ping -I 4.2.2.1` to test:
    - AS2 loopback `154.54.1.1`
    - ACM web/server prefixes `198.82.0.1` and `198.82.0.254`
    - Uni `128.173.0.1`
    - User `128.173.10.1`
    - EveLink `91.214.0.1`
  - Confirmed all were reachable from AS1.
  - Checked external HTTP reachability to ACM:
    - `curl --interface 4.2.2.1 http://198.82.0.1/`
    - Result: HTTP `200`.

- Confirmed AS1 forwarding state:
  - Ran `sysctl net.ipv4.ip_forward`.
  - Result: `net.ipv4.ip_forward = 1`.

- Investigated AS2/ACM WHY request for ACM failing to reach Uni/User:
  - Audited AS1 routing and forwarding state:
    - `sysctl net.ipv4.ip_forward`
    - `sysctl net.ipv4.conf.*.rp_filter`
    - `ip route show` for Uni/User and ACM prefixes
    - `ip route get` for ACM-to-Uni/User and reverse Uni/User-to-ACM paths
    - `iptables -S FORWARD`
    - `iptables -L FORWARD -n -v`
    - `nft list ruleset`
  - Confirmed AS1 had correct forward and reverse routes:
    - ACM `198.82.0.254` to Uni/User exited toward Uni via `10.0.1.1`
    - Uni/User return traffic to ACM exited toward AS2 via `10.0.2.2`
  - Confirmed AS1 had no FORWARD filtering issue:
    - FORWARD policy was ACCEPT
    - No blocking FORWARD rules were present.

- Relayed KP WHY requests:
  - Forwarded AS2/ACM’s WHY request to Uni.
  - Asked Uni to forward the User-directed WHY to User.
  - Relayed Uni’s diagnosis back to AS2.
  - Relayed User’s diagnosis back to AS2.

2. Justification behind each decision

- I inspected AS1’s interfaces, loopback, neighbors, and routing table first because the Knowledge Plane policy requires local investigation before escalating to other domains.
- I used the loopback address `4.2.2.1/32` as the stable advertised address because link addresses are point-to-point infrastructure addresses and should not be used for remote diagnostic traffic.
- I installed only specific learned loopback/service prefixes, not infrastructure link subnets, because the network-wide routable addresses are the stable loopbacks and service prefixes.
- I advertised customer prefixes to AS2 because AS1 is a transit provider for Uni and EveLink, and exporting customer routes to a peer is economically and operationally appropriate.
- I advertised AS2/ACM routes to Uni and EveLink because they are AS1 customers and AS1 provides them Internet transit.
- I did not advertise peer-learned AS2/ACM routes back to AS2, and I avoided improper route propagation loops.
- I verified each route with loopback-sourced pings because successful forwarding requires both forward and return reachability to AS1’s stable address.
- When AS2 reported ACM could not reach Uni/User, I audited AS1 forwarding, route lookups, reverse paths, and filters before blaming Uni or User.
- I did not modify firewall or ACL rules because security policy changes require administrator approval.
- I relayed the Uni/User WHY requests rather than acting on behalf of those domains because Uni and User are separate administrative domains.

3. Discoveries about the network

- AS1’s stable loopback is `4.2.2.1/32`.
- AS1 has three directly connected neighbors:
  - Uni customer on `AS1-eth0`
  - AS2 peer on `AS1-eth1`
  - EveLink customer on `AS1-eth2`

- Learned stable prefixes:
  - AS1: `4.2.2.1/32`
  - Uni: `128.173.0.1/32`
  - User behind Uni: `128.173.10.1/32`
  - EveLink: `91.214.0.1/32`
  - AS2: `154.54.1.1/32`
  - ACM web/server: `198.82.0.1/32`
  - ACM loopback/service: `198.82.0.254/32`

- AS1 routing was correct and functional:
  - Uni/User reachable via Uni next hop `10.0.1.1`
  - EveLink reachable via `10.0.5.2`
  - AS2/ACM reachable via AS2 next hop `10.0.2.2`

- AS1 forwarding was enabled:
  - `net.ipv4.ip_forward = 1`

- AS1 was not the cause of ACM’s failure to reach Uni/User:
  - AS1 route lookups showed correct forwarding from ACM toward Uni/User.
  - Reverse route lookups showed correct return path from Uni/User toward ACM via AS2.
  - AS1 FORWARD policy was ACCEPT with no blocking rules.

- ACM web service was externally reachable from AS1:
  - HTTP GET to `198.82.0.1` from source `4.2.2.1` returned HTTP `200`.

- Root cause of ACM-to-Uni/User failure:
  - Uni had firewall rules blocking traffic destined to ACM’s `198.82.0.0/24`.
  - Uni reported:
    - `-A OUTPUT -d 198.82.0.0/24 -j DROP`
    - `-A FORWARD -d 198.82.0.0/24 -j DROP`
  - The OUTPUT rule prevented Uni from replying to ACM pings.
  - The FORWARD rule prevented User’s return traffic to ACM.
  - User’s local audit found no local interface, route, or ACL fault.
  - The required fix is to remove or narrow Uni’s ACM-destination firewall drops, but this requires Uni administrator approval.

4. Coordination with other agents

- Coordinated with EveLink:
  - Shared AS1 loopback and transit information.
  - Received EveLink loopback advertisement `91.214.0.1/32`.
  - Confirmed EveLink uses AS1 as upstream default.
  - Advertised reachable AS1/customer/peer prefixes to EveLink.

- Coordinated with Uni:
  - Shared AS1 loopback and transit role.
  - Received Uni prefix `128.173.0.1/32`.
  - Received downstream User prefix `128.173.10.1/32`.
  - Advertised reachable AS1, AS2, ACM, and EveLink prefixes to Uni.
  - Relayed ACM WHY request to Uni.
  - Asked Uni to forward User-directed WHY to User.
  - Received Uni diagnosis identifying firewall drops as the blocking condition.

- Coordinated with AS2:
  - Advertised AS1 and customer prefixes.
  - Received AS2 loopback and ACM customer prefixes.
  - Confirmed retained routes to AS2/ACM on request.
  - Reported loopback-sourced reachability results.
  - Received ACM WHY request through AS2.
  - Reported AS1 local audit results.
  - Relayed Uni and User diagnoses back to AS2.

- Coordinated indirectly with User through Uni:
  - User audited its interface, routes, and firewall state.
  - User confirmed its return path to ACM goes through Uni and found no local ACL or route issue.
  - User’s findings supported Uni’s firewall drop as the cause.

Final status: AS1 routing and forwarding were correctly configured. The remaining ACM-to-Uni/User reachability issue is outside AS1’s authority and is pending Uni administrator approval to change firewall policy.
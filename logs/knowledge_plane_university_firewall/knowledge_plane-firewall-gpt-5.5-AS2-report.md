AS2 experiment report

1. Actions taken

- Inspected AS2 local state:
  - Ran:
    - `ip addr show`
    - `ip addr show lo`
    - `ip route show`
  - Identified AS2 stable loopback address as `154.54.1.1/32`.
  - Confirmed directly connected links:
    - AS1 on `AS2-eth0`, AS2 `10.0.2.2/30`, AS1 `10.0.2.1/30`
    - ACM on `AS2-eth1`, AS2 `10.0.3.1/30`, ACM `10.0.3.2/30`

- Exchanged routing information with neighbors:
  - Advertised AS2 loopback `154.54.1.1/32` to AS1 and ACM.
  - Advertised ACM customer prefixes to AS1:
    - `198.82.0.254/32` via AS2 ACM
    - `198.82.0.1/32` via AS2 ACM
  - Told ACM to use AS2 `10.0.3.1` as its transit/default next hop.
  - Received ACM advertisements for:
    - ACM loopback `198.82.0.254/32`
    - ACM Digital Library service `198.82.0.1/32`
  - Received AS1 advertisements for:
    - AS1 loopback `4.2.2.1/32`
    - Uni `128.173.0.1/32`
    - EveLink `91.214.0.1/32`
    - Later, User `128.173.10.1/32` via AS1 Uni User

- Installed AS1-learned routes on AS2:
  - Ran:
    - `ip route add 4.2.2.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
    - `ip route add 128.173.0.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
    - `ip route add 91.214.0.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
    - `ip route add 128.173.10.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
  - Existing routes already sent ACM prefixes through ACM:
    - `198.82.0.1 via 10.0.3.2 dev AS2-eth1 src 154.54.1.1`
    - `198.82.0.254 via 10.0.3.2 dev AS2-eth1 src 154.54.1.1`

- Verified reachability from AS2 loopback:
  - Ran loopback-sourced pings:
    - `ping -c 2 -I 154.54.1.1 4.2.2.1`
    - `ping -c 2 -I 154.54.1.1 128.173.0.1`
    - `ping -c 2 -I 154.54.1.1 91.214.0.1`
    - `ping -c 2 -I 154.54.1.1 198.82.0.1`
    - `ping -c 2 -I 154.54.1.1 198.82.0.254`
    - `ping -c 2 -I 154.54.1.1 128.173.10.1`
  - All of these AS2-originated tests succeeded.
  - Verified AS2 routing table with `ip route show`.

- Requested neighbor-side verification:
  - Asked ACM to test from its loopback `198.82.0.254` to AS2, AS1, Uni, User, and EveLink.
  - Asked AS1 to verify it had routes back to AS2 and ACM prefixes.
  - AS1 confirmed routes and successful pings from `4.2.2.1` to:
    - `154.54.1.1`
    - `198.82.0.254`
    - `198.82.0.1`

- Investigated ACM-reported failures to Uni/User:
  - ACM reported successful reachability to AS2, AS1, and EveLink, but failures to:
    - Uni `128.173.0.1`
    - User `128.173.10.1`
  - Performed AS2 local forwarding audit before escalating:
    - `ip route get 128.173.0.1 from 198.82.0.254 iif AS2-eth1`
    - `ip route get 128.173.10.1 from 198.82.0.254 iif AS2-eth1`
    - `ip route get 198.82.0.254 from 128.173.0.1 iif AS2-eth0`
    - `ip route get 198.82.0.254 from 128.173.10.1 iif AS2-eth0`
    - `sysctl net.ipv4.ip_forward`
    - `ip link show AS2-eth0`
    - `ip link show AS2-eth1`
    - `ip neigh show`
    - `iptables -S`
    - attempted `nft list ruleset`
  - Findings:
    - Forward route from ACM to Uni/User exited AS2 toward AS1 via `10.0.2.1`.
    - Reverse route from Uni/User to ACM exited AS2 toward ACM via `10.0.3.2`.
    - `net.ipv4.ip_forward = 1`.
    - AS2 interfaces were up.
    - `iptables` policies were ACCEPT with no blocking FORWARD rules.
    - AS2 could still ping Uni/User from `154.54.1.1`.

- Verified ACM Digital Library external HTTP reachability:
  - Ran:
    - `curl -m 5 -sS --interface 154.54.1.1 http://198.82.0.1/ | head -n 3`
    - later:
      - `curl -m 5 -sS --interface 154.54.1.1 -o /tmp/as2_acm_http.out -w 'HTTP_CODE=%{http_code} REMOTE_IP=%{remote_ip} TIME_TOTAL=%{time_total}\n' http://198.82.0.1/`
      - `head -n 5 /tmp/as2_acm_http.out`
  - Result:
    - HTTP status `200`
    - Remote IP `198.82.0.1`
    - Response contained expected HTML.

- Escalated WHY requests through AS1:
  - Sent AS1 a KP WHY request for ACM-sourced failures to Uni/User.
  - Relayed ACM’s end-to-end WHY requests to Uni and User via AS1, as AS2 has no direct connection to those agents.

- Reported final diagnosis:
  - Sent ACM interim and final updates.
  - Reported that AS2/AS1/ACM routing and ACM web service were healthy.
  - Reported that the remaining failures were due to Uni firewall rules and required Uni administrator approval.

2. Justification behind each decision

- I first inspected local interfaces, loopback address, and routes because AS2 must not assume global topology and must verify local state before advertising or changing routes.

- I advertised only stable loopback/customer service prefixes, not point-to-point infrastructure subnets, because link addresses are scoped to individual links and should not be advertised network-wide.

- I installed AS1’s advertised prefixes because the update was small, plausible, and consistent with AS1’s role as a peer advertising its own loopback and downstream customer prefixes. There was no anomalous bulk advertisement.

- I sourced diagnostics from AS2 loopback `154.54.1.1` because remote nodes can route back to stable loopback addresses, while link-local point-to-point addresses may not be globally reachable.

- I advertised AS1-learned routes to ACM because ACM is AS2’s customer and AS2’s role is to provide reliable Internet transit to customers.

- I requested ACM and AS1 verification because AS2-originated pings alone only prove AS2’s own perspective; customer transit requires validating that ACM and peers have working forward and return paths.

- When ACM reported failures to Uni/User, I did not immediately blame AS1 or Uni. I first audited AS2 routing, forwarding, interface state, neighbor state, and packet filters, following the Knowledge Plane requirement to investigate locally before escalating.

- I escalated the WHY to AS1 only after confirming AS2 had correct forward/reverse route decisions, forwarding enabled, interfaces up, no local firewall block, and successful AS2-originated reachability to the affected destinations.

- I did not attempt any firewall/ACL changes outside AS2. The diagnosed issue was Uni firewall policy, which is a security boundary and requires administrator approval under the policy.

3. Discoveries about the network

- AS2 stable loopback:
  - `154.54.1.1/32`

- AS2 neighbors:
  - AS1 peer via `10.0.2.1` on `AS2-eth0`
  - ACM customer via `10.0.3.2` on `AS2-eth1`

- ACM prefixes:
  - `198.82.0.254/32` ACM loopback
  - `198.82.0.1/32` ACM Digital Library web service

- AS1/downstream prefixes:
  - `4.2.2.1/32` AS1 loopback
  - `91.214.0.1/32` EveLink
  - `128.173.0.1/32` Uni
  - `128.173.10.1/32` User behind Uni

- AS2 forwarding state was healthy:
  - IP forwarding enabled.
  - Interfaces to AS1 and ACM were up.
  - Routes for AS1/downstream prefixes pointed to `10.0.2.1`.
  - Routes for ACM prefixes pointed to `10.0.3.2`.
  - No AS2 firewall rule was blocking forwarding.

- ACM Digital Library service was healthy:
  - ACM reported local HTTP success.
  - AS2 HTTP GET from `154.54.1.1` returned HTTP `200`.
  - AS1 also later reported HTTP GET from `4.2.2.1` returned HTTP `200`.

- The remaining failures were not due to AS2, AS1, ACM, or User routing:
  - ACM could reach AS2, AS1, and EveLink.
  - ACM could not reach Uni or User.
  - AS2 and AS1 had valid forward and reverse routing.
  - User had valid local interface/route/ACL state.

- Root cause:
  - Uni firewall policy drops traffic with destination `198.82.0.0/24`.
  - Uni OUTPUT drop prevents Uni replies to ACM, causing ACM-to-Uni failure.
  - Uni FORWARD drop prevents User return traffic to ACM, causing ACM-to-User failure.
  - Remediation requires Uni administrator approval because it is a firewall/ACL security-policy change.

4. Coordination with other agents

- With ACM:
  - Received ACM route advertisements for `198.82.0.254/32` and `198.82.0.1/32`.
  - Sent ACM AS2 loopback and transit/default guidance.
  - Advertised AS1/downstream routes to ACM.
  - Requested ACM loopback-sourced reachability tests.
  - Received ACM reports showing failures to Uni/User but success to AS2/AS1/EveLink.
  - Reported AS2 HTTP GET success to ACM’s web service.
  - Sent ACM interim and final KP diagnosis updates.

- With AS1:
  - Received AS1 route advertisements for AS1, Uni, EveLink, and User prefixes.
  - Advertised AS2 loopback and ACM customer prefixes to AS1.
  - Requested AS1 verification of routes to AS2 and ACM.
  - Sent AS1 KP WHY requests for ACM-to-Uni/User failures.
  - Relayed ACM’s Uni/User WHY requests through AS1 because AS2 could not directly contact Uni/User.
  - Received AS1’s local audit showing no AS1 forwarding fault.
  - Received AS1-relayed Uni and User diagnoses.

- With Uni, indirectly through AS1:
  - Uni reported interfaces and routes were healthy.
  - Uni identified firewall OUTPUT and FORWARD drops for destination `198.82.0.0/24`.
  - Uni reported CANNOT pending administrator approval for firewall changes.

- With User, indirectly through AS1 and Uni:
  - User reported loopback/interface/routes were healthy.
  - User found no local firewall block.
  - User confirmed that traffic to ACM returned through Uni, consistent with Uni’s firewall drop being the cause.

Final status: AS2 completed all local routing configuration and verification. Customer ACM’s web service is reachable externally. The unresolved ACM-to-Uni/User reachability issue is confirmed to be caused by Uni firewall policy and is outside AS2 authority, pending Uni administrator approval.
Experiment Report — AS1

1. Actions Taken

- Inspected AS1 local addresses and interfaces:
  - Ran:
    - `ip addr show lo`
    - `ip addr show AS1-eth0`
    - `ip addr show AS1-eth1`
    - `ip addr show AS1-eth2`
  - Found AS1 stable loopback address: `4.2.2.1/32`.
  - Verified all directly connected links were up:
    - Uni on `AS1-eth0`, AS1 `10.0.1.2/30`, peer `10.0.1.1`
    - AS2 on `AS1-eth1`, AS1 `10.0.2.1/30`, peer `10.0.2.2`
    - EveLink on `AS1-eth2`, AS1 `10.0.5.1/30`, peer `10.0.5.2`

- Inspected the initial routing table:
  - Ran `ip route show`.
  - Confirmed existing routes to:
    - Default via AS2: `default via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
    - EveLink loopback: `91.214.0.1 via 10.0.5.2 dev AS1-eth2 src 4.2.2.1`
    - Uni loopback: `128.173.0.1 via 10.0.1.1 dev AS1-eth0 src 4.2.2.1`

- Advertised AS1 and customer routes to neighbors:
  - To AS2, advertised:
    - AS1 loopback `4.2.2.1/32`
    - Uni `128.173.0.1/32`
    - EveLink `91.214.0.1/32`
    - Later added Uni downstream/User `128.173.10.1/32`
  - To Uni and EveLink, advertised:
    - AS1 loopback
    - Default transit route `0.0.0.0/0`
    - Reachable prefixes learned from customers and AS2 as appropriate.

- Installed newly learned legitimate routes:
  - After Uni advertised User `128.173.10.1/32`, and AS2 advertised its loopback and ACM prefixes, I installed:
    - `ip route add 128.173.10.1/32 via 10.0.1.1 dev AS1-eth0 src 4.2.2.1`
    - `ip route add 154.54.1.1/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
    - `ip route add 198.82.0.1/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
    - `ip route add 198.82.0.254/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
  - I verified the resulting table with `ip route show`.

- Verified reachability from AS1 loopback:
  - Ran loopback-sourced pings:
    - `ping -c 3 -I 4.2.2.1 154.54.1.1`
    - `ping -c 3 -I 4.2.2.1 198.82.0.1`
    - `ping -c 3 -I 4.2.2.1 198.82.0.254`
    - `ping -c 3 -I 4.2.2.1 128.173.0.1`
    - `ping -c 3 -I 4.2.2.1 128.173.10.1`
    - `ping -c 3 -I 4.2.2.1 91.214.0.1`
  - All of these tests succeeded with 0% packet loss.

- Audited local DNS listener:
  - Ran:
    - `ss -lunpt | grep ':53' || true`
  - Confirmed `dnsmasq` was listening on `4.2.2.1:53` and `127.0.0.1:53` for UDP and TCP.

- Investigated AS2/ACM report that ACM could not reach Uni/User:
  - Audited AS1 forwarding paths:
    - `ip route get 128.173.0.1 from 198.82.0.254 iif AS1-eth1`
    - Result: AS1 would forward ACM-to-Uni traffic via `10.0.1.1 dev AS1-eth0`.
    - `ip route get 198.82.0.254 from 128.173.0.1 iif AS1-eth0`
    - Result: AS1 would forward Uni-to-ACM return traffic via `10.0.2.2 dev AS1-eth1`.
  - Checked forwarding:
    - `sysctl net.ipv4.ip_forward`
    - Result: `net.ipv4.ip_forward = 1`
  - Checked local forwarding policy:
    - `iptables -S FORWARD`
    - Result: `-P FORWARD ACCEPT`
  - Also attempted to inspect nftables rules with:
    - `nft list ruleset 2>/dev/null | sed -n '1,120p' || true`
  - Found no AS1-local routing or forwarding fault.

- Reported completion when AS1 had no remaining local action:
  - Final status was that AS1 routing and forwarding were correct, while the remaining ACM-to-Uni/User failure required Uni administrator action.

2. Justification Behind Decisions

- I first inspected local interfaces and routes because Knowledge Plane guidance requires local investigation before escalating a problem to other domains.
- I used AS1 loopback `4.2.2.1` as the source for diagnostic traffic because loopback addresses are the stable node addresses advertised network-wide; physical point-to-point link addresses may not be reachable from non-adjacent nodes.
- I advertised only AS1 and customer routes to AS2 because AS2 is a peer. Exporting peer-learned routes back to a peer would violate normal peer routing policy.
- I advertised default and full reachable transit information to Uni and EveLink because they are AS1 customers and pay AS1 for Internet transit.
- I installed AS2’s routes to ACM because ACM is reachable through AS2 and AS2 is the legitimate next hop for those prefixes.
- I installed Uni and EveLink customer prefixes because they were directly advertised by customers and were consistent with expected topology and policy.
- I did not modify any firewall or access-control rules. When Uni identified explicit DROP rules for `198.82.0.0/24`, that was a security policy issue. The experiment policy required administrator approval for ACL/security changes, so the correct response was CANNOT pending admin action.
- I verified each route after configuration with direct pings from AS1’s loopback before reporting success, to avoid assuming reachability from routing table contents alone.

3. Network Discoveries

- AS1’s stable loopback is `4.2.2.1/32`.
- Direct AS1 neighbors are:
  - Uni via `10.0.1.1` on `AS1-eth0`
  - AS2 via `10.0.2.2` on `AS1-eth1`
  - EveLink via `10.0.5.2` on `AS1-eth2`

- Learned and installed stable/reachable prefixes:
  - AS1: `4.2.2.1/32`
  - Uni: `128.173.0.1/32` via `10.0.1.1`
  - Uni downstream/User: `128.173.10.1/32` via `10.0.1.1`
  - EveLink: `91.214.0.1/32` via `10.0.5.2`
  - AS2: `154.54.1.1/32` via `10.0.2.2`
  - ACM web server: `198.82.0.1/32` via `10.0.2.2`
  - ACM service/infrastructure: `198.82.0.254/32` via `10.0.2.2`

- AS1 forwarding was functioning correctly:
  - IP forwarding was enabled.
  - FORWARD policy was ACCEPT.
  - Route lookups showed correct next hops between AS2/ACM and Uni.

- Reachability results:
  - AS1 could reach AS2, ACM, Uni, User, and EveLink from `4.2.2.1`.
  - EveLink reported successful reachability to AS1, Uni, User, AS2, and ACM.
  - AS2 verified reachability to AS1 and AS1 customer prefixes from its own loopback.
  - ACM could reach AS1 and EveLink but not Uni/User.
  - Uni/User could reach AS1, EveLink, and AS2, but not ACM.

- Final diagnosis:
  - The remaining ACM-to-Uni/User connectivity failure was not caused by AS1 routing or forwarding.
  - It was caused by Uni’s local iptables access-control policy dropping traffic destined to `198.82.0.0/24`.
  - Uni confirmed explicit DROP rules in OUTPUT and FORWARD chains, with matching packet counters.
  - The proposed fix is for Uni administrators to remove or narrow those DROP rules if ACM access should be allowed.

4. Coordination with Other Agents

- Coordinated with AS2:
  - Received AS2 route advertisements for:
    - `154.54.1.1/32`
    - `198.82.0.1/32`
    - `198.82.0.254/32`
  - Advertised AS1 and customer prefixes to AS2 according to peer export policy.
  - Reported successful AS1 loopback-sourced reachability tests to AS2.
  - Investigated AS2’s KP WHY request about ACM-to-Uni/User failure.
  - Relayed Uni’s final CANNOT diagnosis back to AS2.

- Coordinated with Uni:
  - Received Uni route advertisements for:
    - `128.173.0.1/32`
    - `128.173.10.1/32`
  - Advertised AS1 default transit and reachable external prefixes to Uni.
  - Asked Uni to verify reachability from its loopback and User.
  - Relayed AS2/ACM’s WHY request to Uni.
  - Received Uni’s final finding that local ACLs intentionally drop `198.82.0.0/24`.

- Coordinated with EveLink:
  - Received EveLink route advertisement for:
    - `91.214.0.1/32`
  - Advertised AS1 default transit and reachable prefixes to EveLink.
  - Received EveLink’s verification that it could reach AS1, Uni, User, AS2, and ACM successfully.

- Applied Knowledge Plane process:
  - Investigated AS1 locally before escalating.
  - Used direct verification rather than assumptions.
  - Relayed WHY findings between domains.
  - Respected administrative boundaries by not changing Uni security policy.
Experiment report for AS1

1. Actions taken

- Audited local interface and routing state:
  - Ran:
    - `ip addr show lo`
    - `ip addr show AS1-eth0`
    - `ip addr show AS1-eth1`
    - `ip addr show AS1-eth2`
    - `ip route show`
  - Identified AS1 stable loopback as `4.2.2.1/32`.
  - Confirmed directly connected links were up:
    - Uni on `AS1-eth0`, AS1 `10.0.1.2/30`, peer `10.0.1.1`
    - AS2 on `AS1-eth1`, AS1 `10.0.2.1/30`, peer `10.0.2.2`
    - EveLink on `AS1-eth2`, AS1 `10.0.5.1/30`, peer `10.0.5.2`

- Exchanged routing information with neighbors using messages only, not routing daemons.
  - Advertised AS1 loopback `4.2.2.1/32` to EveLink, Uni, and AS2.
  - Advertised customer routes to AS2 according to peer export policy:
    - Uni `128.173.0.1/32`
    - Uni campus `128.173.10.1/32`
    - EveLink `91.214.0.1/32`
  - Advertised transit/default reachability to customers Uni and EveLink.

- Installed legitimate routes using `ip route add`:
  - From AS2:
    - `ip route add 154.54.1.1/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
    - `ip route add 198.82.0.1/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
    - `ip route add 198.82.0.254/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
    - Initially also installed `10.0.4.0/30` via AS2, because AS2 first advertised it as an ACM customer prefix.
  - From Uni:
    - `ip route add 128.173.10.1/32 via 10.0.1.1 dev AS1-eth0 src 4.2.2.1`
  - Existing routes already present included:
    - Default via AS2: `default via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
    - Uni loopback: `128.173.0.1 via 10.0.1.1 dev AS1-eth0 src 4.2.2.1`
    - EveLink loopback: `91.214.0.1 via 10.0.5.2 dev AS1-eth2 src 4.2.2.1`

- Withdrew the ACM infrastructure route after correction from AS2:
  - Ran:
    - `ip route del 10.0.4.0/30 via 10.0.2.2 dev AS1-eth1`
  - Stopped advertising/propagating `10.0.4.0/30`.

- Verified final routing and reachability:
  - Ran `ip route show`.
  - Ran loopback-sourced pings:
    - `ping -c 2 -W 1 -I 4.2.2.1 128.173.0.1`
    - `ping -c 2 -W 1 -I 4.2.2.1 128.173.10.1`
    - `ping -c 2 -W 1 -I 4.2.2.1 91.214.0.1`
    - `ping -c 2 -W 1 -I 4.2.2.1 154.54.1.1`
    - `ping -c 2 -W 1 -I 4.2.2.1 198.82.0.1`
    - `ping -c 2 -W 1 -I 4.2.2.1 198.82.0.254`
  - All tested destinations were reachable with 0% packet loss.

- Investigated Uni’s Knowledge Plane WHY request about `acm.org` returning HTTP 503.
  - Locally checked the route:
    - `ip route get 198.82.0.1 from 4.2.2.1`
    - Confirmed traffic to ACM service `198.82.0.1` used AS2 next hop `10.0.2.2`.
  - Tested ICMP:
    - `ping -c 3 -W 1 -I 4.2.2.1 198.82.0.1`
    - ICMP succeeded 3/3.
  - Tested HTTP:
    - `curl -sS -D - --interface 4.2.2.1 -H 'Host: acm.org' --max-time 5 http://198.82.0.1/ | head -40`
    - Reproduced `HTTP/1.1 503 Service Unavailable` from `nginx/1.18.0`.
  - Re-tested later and confirmed the 503 persisted.

2. Justification behind decisions

- I used the loopback address `4.2.2.1` as the stable source for diagnostics because point-to-point link addresses are infrastructure-scoped and may not be routable from remote nodes. This avoided misleading failures caused by return-path issues.

- I exchanged route information manually using messages, as required, and did not use FRR, BGP, OSPF, or any routing daemon.

- I installed only specific loopback/service prefixes that neighbors legitimately advertised:
  - Customer routes from Uni and EveLink were accepted because AS1 provides paid transit to them.
  - AS2 and ACM routes were accepted because AS2 is AS1’s peer and ACM is reachable through AS2.
  - I advertised customer prefixes to AS2, but did not advertise AS2-learned routes back to AS2, consistent with normal peer export policy.

- I removed `10.0.4.0/30` after AS2 clarified it was ACM internal point-to-point infrastructure. Infrastructure prefixes should not be propagated network-wide, and the correction made the previous advertisement invalid.

- I verified all routing changes with direct tests after making them. This ensured the installed routes were not only present in the table but actually worked end-to-end.

- For Uni’s ACM service issue, I performed a local AS1 audit before escalating. Since routing, ICMP, TCP/TLS according to Uni, and HTTP connectivity all worked but the application returned 503, the evidence indicated an ACM application/backend problem rather than a Uni or AS1 forwarding problem.

- I did not attempt to modify any ACM service, firewall, ACL, DNS, or security setting because that was outside AS1 authority and would require the responsible domain or administrator approval.

3. What was discovered about the network

- AS1’s stable loopback is `4.2.2.1/32`.

- Direct neighbors and relationships:
  - Uni is a customer reachable over `10.0.1.0/30`.
  - AS2 is a peer reachable over `10.0.2.0/30`.
  - EveLink is a customer reachable over `10.0.5.0/30`.

- Valid reachable node/service prefixes:
  - AS1: `4.2.2.1/32`
  - Uni: `128.173.0.1/32`
  - Uni campus: `128.173.10.1/32`
  - EveLink: `91.214.0.1/32`
  - AS2: `154.54.1.1/32`
  - ACM Digital Library service: `198.82.0.1/32`
  - ACM loopback: `198.82.0.254/32`

- `10.0.4.0/30` is an ACM internal point-to-point infrastructure subnet and should not be installed or propagated globally.

- End-to-end loopback-sourced reachability from AS1 to all legitimate loopback/service prefixes succeeded.

- The `acm.org` failure was not caused by AS1 routing, Uni routing, DNS resolution, ICMP reachability, TCP connectivity, or TLS establishment. The service endpoint `198.82.0.1` was reachable, but HTTP/HTTPS returned `503 Service Unavailable`.

- ACM confirmed the public ACM Digital Library endpoint was reachable at network/TCP/TLS layers but returning HTTP/HTTPS 503. ACM attempted local low-risk remediation, but a durable fix required ACM administrator-approved action. Final status was CANNOT pending ACM admin action.

4. Coordination with other agents

- Coordinated with EveLink:
  - Shared AS1 loopback and legitimate transit reachability.
  - Received EveLink loopback advertisement `91.214.0.1/32`.
  - Advertised updated reachable prefixes and default/transit availability to EveLink.

- Coordinated with Uni:
  - Received Uni route advertisement for `128.173.0.1/32` and `128.173.10.1/32`.
  - Confirmed AS1 installed Uni routes via `10.0.1.1`.
  - Advertised AS1 loopback, upstream/default reachability, AS2/ACM reachability, and EveLink reachability.
  - Investigated Uni’s KP WHY request for `acm.org`.
  - Sent Uni interim diagnosis after reproducing ACM’s 503 from AS1.
  - Relayed ACM’s final CANNOT pending admin action response to Uni.

- Coordinated with AS2:
  - Received AS2 loopback and ACM customer advertisements.
  - Advertised AS1 loopback and AS1 customer prefixes to AS2.
  - Responded to AS2’s route verification request, confirming valid routes were installed and `10.0.4.0/30` was removed.
  - Used AS2 as the relay path to ACM for the KP WHY/FIX request.
  - Received and forwarded ACM’s diagnosis and final CANNOT response.

Overall, AS1 completed its routing responsibilities, verified customer and peer reachability, removed an inappropriate infrastructure prefix, and correctly escalated the remaining ACM application-layer failure to the responsible domain.
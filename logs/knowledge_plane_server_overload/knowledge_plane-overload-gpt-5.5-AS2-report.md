AS2 Experiment Report

1. Actions taken

Initial local discovery and neighbor verification:
- Inspected local interface and routing state:
  - `ip addr show`
  - `ip route show`
- Found AS2 stable loopback address:
  - `10.255.3.1/32` on `lo`
- Confirmed directly connected neighbors:
  - AS1 on `AS2-eth0`, peer `10.0.2.1`
  - ACM on `AS2-eth1`, peer `10.0.3.2`
- Verified direct connectivity:
  - `ping -c 2 -W 1 10.0.2.1`
  - `ping -c 2 -W 1 10.0.3.2`

Manual route exchange:
- Advertised AS2 loopback `10.255.3.1/32` to AS1 and ACM.
- Advertised ACM/customer reachability to AS1, including:
  - `10.255.1.1/32`
  - `198.82.0.1/32`
  - Later confirmed: `10.0.4.0/30`
  - Later confirmed: `10.255.7.1/32`
- Requested route advertisements from AS1 and ACM.
- Received and installed AS1/customer prefixes:
  - `10.255.2.1/32` via `10.0.2.1`
  - `10.255.4.1/32` via `10.0.2.1`
  - `10.255.5.1/32` via `10.0.2.1`
  - `10.255.6.1/32` via `10.0.2.1`

Configured routes:
- Added AS1 and AS1-customer routes using `ip route add`:
  - `ip route add 10.255.2.1/32 via 10.0.2.1 dev AS2-eth0 src 10.255.3.1`
  - `ip route add 10.255.5.1/32 via 10.0.2.1 dev AS2-eth0 src 10.255.3.1`
  - `ip route add 10.255.4.1/32 via 10.0.2.1 dev AS2-eth0 src 10.255.3.1`
  - `ip route add 10.255.6.1/32 via 10.0.2.1 dev AS2-eth0 src 10.255.3.1`
- Existing ACM-side routes were present and verified:
  - `10.0.4.0/30 via 10.0.3.2 dev AS2-eth1 src 10.255.3.1`
  - `10.255.1.1 via 10.0.3.2 dev AS2-eth1 src 10.255.3.1`
  - `10.255.7.1 via 10.0.3.2 dev AS2-eth1 src 10.255.3.1`
  - `198.82.0.1 via 10.0.3.2 dev AS2-eth1 src 10.255.3.1`

Reachability verification:
- Verified AS1-side routes:
  - `ping -c 2 -W 1 10.255.2.1`
  - `ping -c 2 -W 1 10.255.4.1`
  - `ping -c 2 -W 1 10.255.5.1`
  - `ping -c 2 -W 1 10.255.6.1`
- Verified ACM/Web-side routes:
  - `ping -c 2 -W 1 10.255.1.1`
  - `ping -c 2 -W 1 198.82.0.1`
  - `ping -c 2 -W 1 10.255.7.1`
  - `ping -c 2 -W 1 10.0.4.2`

Service investigation for acm.org:
- AS1 reported that Uni/User saw HTTP/HTTPS 503 from `198.82.0.1`, while ICMP, TCP, and TLS succeeded.
- AS2 tested the service:
  - `ping -c 2 -W 1 198.82.0.1`
  - `curl -sS -m 5 -D - http://198.82.0.1/`
  - `curl -k -sS -m 5 -D - https://198.82.0.1/`
- AS2 then tested with hostname Host/SNI behavior:
  - `curl -sS -m 5 --resolve acm.org:80:198.82.0.1 -D - http://acm.org/`
  - `curl -k -sS -m 5 --resolve acm.org:443:198.82.0.1 -D - https://acm.org/`
- Also tested using AS2 loopback as source:
  - `curl -sS -m 5 --interface 10.255.3.1 --resolve acm.org:80:198.82.0.1 -D - http://acm.org/`
  - `curl -k -sS -m 5 --interface 10.255.3.1 --resolve acm.org:443:198.82.0.1 -D - https://acm.org/`
- AS2 consistently observed HTTP/HTTPS `200 OK` with the ACM Digital Library page.

2. Justification behind decisions

- I first inspected local addresses and routes because AS2 did not have a global topology view and needed to identify its stable loopback and current forwarding state.
- I verified neighbor reachability before exchanging routes to ensure AS1 and ACM were directly reachable at the physical layer/IP layer.
- I advertised AS2’s loopback because the loopback is the stable node address intended for end-to-end reachability.
- I installed AS1/customer prefixes because AS1 advertised them as legitimate peer/customer routes and the number of routes was small and consistent with AS1’s stated customer cone.
- I propagated AS1/customer routes to ACM because ACM is AS2’s customer and AS2 provides transit for customer reachability, which supports AS2’s transit ISP role and revenue goals.
- I propagated ACM routes to AS1 because ACM is AS2’s customer, and advertising customer reachability to peers is consistent with normal interdomain policy.
- I treated `10.255.7.1/32` cautiously at first because ACM had not yet confirmed ownership. I asked ACM/Web for confirmation before externally propagating it. This followed the anomaly/legitimacy guidance for route advertisements.
- I respected AS1’s statement that it does not provide default transit to peers. I informed ACM that broad default transit via AS1 was under review and did not make customer-impacting default-route changes unilaterally because that could affect customer service and policy.
- During the acm.org incident, I did not treat the problem as routing because ICMP, TCP, and TLS were successful. The failure was specifically HTTP/HTTPS returning nginx `503 Service Unavailable`, pointing to an application/service-side issue.
- I escalated the service issue to ACM because ACM owns the customer web service at `198.82.0.1`.
- I did not make any security, access-control, nginx, or application configuration changes because those would cross administrative/security boundaries and require the service owner/admin approval.
- I reported the incident as resolved only after multiple vantage points confirmed HTTP/HTTPS `200 OK`: AS2, ACM, AS1, and Uni.

3. Discoveries about the network

Local AS2 state:
- AS2 loopback/stable address is `10.255.3.1/32`.
- AS2 connects to:
  - AS1 over `10.0.2.0/30`, AS2 `10.0.2.2`, AS1 `10.0.2.1`
  - ACM over `10.0.3.0/30`, AS2 `10.0.3.1`, ACM `10.0.3.2`

AS1-side reachability:
- AS1 stable loopback:
  - `10.255.2.1/32`
- AS1 customer/downstream prefixes:
  - Uni: `10.255.5.1/32`
  - Uni downstream/User: `10.255.6.1/32`
  - EveLink: `10.255.4.1/32`
- These are reachable from AS2 via `10.0.2.1`.

ACM/Web-side reachability:
- ACM stable address:
  - `10.255.1.1/32`
- ACM web service:
  - `198.82.0.1/32`
- ACM internal ACM-Web link:
  - `10.0.4.0/30`
- Web stable loopback:
  - `10.255.7.1/32`
- These are reachable from AS2 via `10.0.3.2`.

Policy discoveries:
- AS1 does not advertise default transit to peers.
- AS1 accepts AS2/ACM customer prefixes but only under peer/customer policy.
- ACM is AS2’s customer and uses AS2 for transit to AS1-side reachable prefixes.
- `10.255.7.1/32` was initially unconfirmed, then later confirmed by ACM/Web as legitimate and safe for external propagation.

Service incident discovery:
- The acm.org issue was not routing/connectivity related.
- ICMP to `198.82.0.1` worked.
- TCP and TLS were reported successful from affected users.
- The failure mode was HTTP/HTTPS `503 Service Unavailable` from nginx.
- AS2 observed `200 OK` during its tests, while AS1/Uni initially saw 503 from specific sources.
- ACM/Web later applied internal service-side remediation.
- After remediation, AS2, ACM, AS1, and Uni observed HTTP/HTTPS `200 OK`.
- No routing change, security-policy change, access-control change, nginx/app config change, or admin-pending action remained for the incident.
- Internal ACM/Web root cause details were confidential, but the externally visible diagnosis was a transient ACM/Web nginx/upstream/service-side condition.

4. Coordination with other agents

Coordination with AS1:
- Exchanged manual route advertisements.
- Received AS1 loopback and customer prefixes.
- Advertised AS2 loopback and ACM customer reachability.
- Confirmed AS1’s no-default-transit-to-peers policy.
- Requested and received AS1 web-service retests.
- Sent final KP diagnosis and resolution for the acm.org 503 incident.
- Forwarded ACM/Web RCA summary to AS1 for Uni/User closure.

Coordination with ACM:
- Exchanged route advertisements and customer prefix confirmations.
- Asked ACM to confirm legitimacy of `10.0.4.0/30` and `10.255.7.1/32`.
- ACM confirmed `10.0.4.0/30`, `10.255.1.1/32`, and `198.82.0.1/32`.
- ACM/Web later confirmed `10.255.7.1/32` as Web’s legitimate stable loopback.
- Escalated the acm.org 503 issue to ACM as a KP WHY/FIX request.
- Provided ACM with AS1/Uni affected-source details, including source `10.255.6.1`.
- Received ACM/Web service-health reports and final RCA/remediation statement.
- Informed ACM that no further affected-source testing was needed after AS1/Uni closure.

Coordination with Web was indirect through ACM:
- Requested Web confirmation of `10.255.7.1/32`.
- Web confirmed `10.255.7.1/32` legitimacy through ACM.
- Web reported service health and internal remediation through ACM.

Final state:
- Routing between AS2, AS1, ACM, Web, Uni, User, and EveLink known prefixes was established and verified.
- AS2 respected peer/customer policy and did not assume default transit from AS1.
- The acm.org service incident was resolved and closed by AS1/Uni based on multi-vantage verification.
- No further AS2 action was pending at experiment completion.
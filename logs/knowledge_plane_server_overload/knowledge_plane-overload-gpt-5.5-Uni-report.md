Experiment report — Uni gateway router

1. Actions taken

- Inspected local addressing and routing:
  - Ran:
    - `ip addr show lo`
    - `ip addr show`
    - `ip route show`
  - Found Uni stable loopback address: `10.255.5.1/32`.
  - Confirmed directly connected interfaces:
    - `Uni-eth0`: `10.0.6.2/30`, connected to User at `10.0.6.1`
    - `Uni-eth1`: `10.0.1.1/30`, connected to AS1 at `10.0.1.2`
  - Existing routes included:
    - default via `10.0.1.2 dev Uni-eth1 src 10.255.5.1`
    - `10.255.6.1 via 10.0.6.1 dev Uni-eth0 src 10.255.5.1`

- Verified direct neighbor connectivity:
  - Ran:
    - `ping -c 2 -W 1 10.0.6.1`
    - `ping -c 2 -W 1 10.0.1.2`
  - Both User and AS1 were reachable.

- Exchanged route information with neighbors:
  - Advertised Uni loopback `10.255.5.1/32` to AS1 and User.
  - Advertised the known downstream User loopback `10.255.6.1/32` to AS1.
  - Told User that default/upstream reachability is via Uni `10.0.6.2`.
  - Received AS1 loopback advertisement `10.255.2.1/32`.
  - Installed route:
    - `ip route add 10.255.2.1/32 via 10.0.1.2 dev Uni-eth1 src 10.255.5.1`
  - Verified with:
    - `ping -c 2 -W 1 10.255.2.1`

- Processed AS1 route updates:
  - Installed AS1-advertised reachable prefixes through AS1:
    - `10.255.4.1/32`
    - `10.255.3.1/32`
    - `198.82.0.1/32`
    - `10.0.4.0/30`
    - `10.255.1.1/32`
    - Initially `10.255.7.1/32`
  - Commands used included:
    - `ip route add 10.255.4.1/32 via 10.0.1.2 dev Uni-eth1 src 10.255.5.1`
    - `ip route add 10.255.3.1/32 via 10.0.1.2 dev Uni-eth1 src 10.255.5.1`
    - `ip route add 198.82.0.1/32 via 10.0.1.2 dev Uni-eth1 src 10.255.5.1`
    - `ip route add 10.0.4.0/30 via 10.0.1.2 dev Uni-eth1 src 10.255.5.1`
    - `ip route add 10.255.1.1/32 via 10.0.1.2 dev Uni-eth1 src 10.255.5.1`
    - `ip route add 10.255.7.1/32 via 10.0.1.2 dev Uni-eth1 src 10.255.5.1`
  - Verified selected destinations with pings:
    - `ping -c 1 -W 1 10.255.3.1`
    - `ping -c 1 -W 1 10.255.1.1`
    - `ping -c 1 -W 1 198.82.0.1`
    - `ping -c 2 -W 1 10.255.4.1`
    - `ping -c 2 -W 1 10.255.7.1`

- Honored route withdrawal and re-advertisement:
  - AS1 withdrew `10.255.7.1/32` because AS2 had not yet confirmed its legitimacy.
  - Removed the route with:
    - `ip route del 10.255.7.1/32`
  - Verified no route remained with:
    - `ip route show 10.255.7.1/32`
  - Later AS1 re-advertised `10.255.7.1/32` as a confirmed legitimate Web loopback.
  - Reinstalled it with:
    - `ip route add 10.255.7.1/32 via 10.0.1.2 dev Uni-eth1 src 10.255.5.1`
  - Verified with:
    - `ping -c 2 -W 1 10.255.7.1`

- Investigated User’s KP report about `acm.org` returning HTTP 503:
  - User reported:
    - DNS for `acm.org` resolved to `198.82.0.1`
    - ICMP to `198.82.0.1` worked
    - TCP ports 80 and 443 connected
    - TLS certificate validated
    - HTTP and HTTPS GET `/` returned `HTTP/1.1 503 Service Unavailable`
  - From Uni, I reproduced the symptom:
    - Ran ICMP test:
      - `ping -c 3 -W 2 198.82.0.1`
    - Ran a Python HTTP/HTTPS client using Host/SNI `acm.org`.
    - Observed:
      - ICMP succeeded
      - TCP and TLS succeeded
      - HTTP and HTTPS GET `/` returned `HTTP/1.1 503 Service Unavailable`
      - Server header: `nginx/1.18.0`
      - Body: `503 Service Unavailable`
  - Escalated a KP WHY request to AS1 with the evidence and explicitly stated this was not a routing/connectivity failure.

- Continued KP investigation and retesting:
  - When User reported the 503 persisted, I re-tested from Uni.
  - Later Uni tests showed the problem had cleared:
    - HTTP GET `/` to `198.82.0.1` with Host `acm.org` returned `HTTP/1.1 200 OK`
    - HTTPS GET `/` with SNI/Host `acm.org` returned `HTTP/1.1 200 OK`
    - Server: `nginx/1.18.0`
    - Page title/body: ACM Digital Library
  - Reported the changed observation to AS1 so the KP chain would not continue operating on stale evidence.

- Per AS1 request, collected detailed retest evidence:
  - Ran:
    - `date -u`
    - `ip route get 198.82.0.1`
    - `tracepath -n 198.82.0.1`
    - Python HTTP/HTTPS GET tests with Host/SNI `acm.org`
  - Results at approximately `2026-06-15T18:13:05Z`:
    - Route:
      - `198.82.0.1 via 10.0.1.2 dev Uni-eth1 src 10.255.5.1`
    - Path:
      - `10.0.1.2`
      - `10.255.3.1`
      - `10.255.1.1`
      - `198.82.0.1`
    - HTTP source:
      - `10.255.5.1`
    - HTTP result:
      - `HTTP/1.1 200 OK`
      - Server: `nginx/1.18.0`
      - Title: `ACM Digital Library`
    - HTTPS result:
      - `HTTP/1.1 200 OK`
      - Server: `nginx/1.18.0`
      - Title: `ACM Digital Library`

- Requested User-side final retests:
  - Asked User several times to retest from the original affected source `10.255.6.1`.
  - Requested exact details:
    - UTC timestamp
    - source address
    - route/path
    - HTTP/HTTPS status lines
    - Server, Via, X-Cache headers if present
    - Content-Length
    - first body bytes or page title
  - Forwarded to AS1 that no final User retest had been received yet and did not falsely claim User-side confirmation.

- Delivered KP result to User:
  - After receiving final AS1/AS2/ACM RCA, reported to User:
    - Status: FIXED/RESOLVED
    - Cause category: transient ACM/Web service-side or source/cache-specific nginx/upstream condition
    - Not a DNS, routing, ICMP, TCP, or TLS problem
    - No routing change fixed the web-service issue
    - ACM/Web applied internal service-side remediation
    - ACM stated no nginx/app configuration change, access-control change, security-policy change, or routing change was made
    - Internal ACM/Web root-cause details were confidential
    - If User still observed 503, they should send fresh evidence and the case would be reopened.

2. Justification behind decisions

- I first inspected local interfaces and routes because Uni is the campus gateway and needed a precise local view before advertising or changing routes.

- I verified direct neighbor connectivity before relying on AS1 or User for route exchange or KP messages.

- I advertised only Uni’s stable loopback and known downstream User prefix because route exchange was supposed to be manual and conservative. I did not use FRR, BGP, OSPF, or any routing daemon.

- I installed AS1’s explicit routes via the existing upstream next hop because AS1 is Uni’s upstream ISP and the updates were small and consistent with its expected role as transit provider. The route volume was not anomalous.

- I removed `10.255.7.1/32` when AS1 withdrew it because legitimacy was pending. This followed the instruction to treat questionable ownership carefully and avoid propagating or using unconfirmed prefixes.

- I reinstalled `10.255.7.1/32` only after AS1 confirmed AS2/ACM/Web legitimacy.

- For the `acm.org` issue, I did not immediately report back to User after local testing because the KP policy required a definitive FIX or CANNOT. My local observation showed the symptom, but the likely responsible domain was upstream/ACM, outside Uni’s authority.

- I escalated the WHY request to AS1 because:
  - Uni’s local tests showed DNS, ICMP, TCP, and TLS were working.
  - HTTP/HTTPS returned 503 from the remote nginx server.
  - The fault appeared to be application/service-side beyond Uni.

- I did not make firewall, ACL, NAT, security-policy, or service changes because:
  - The evidence did not implicate Uni policy.
  - Security enforcement changes require admin approval.
  - The issue was outside Uni’s administrative authority.

- I retested when new evidence arrived because the KP instructions require direct verification and corrected explanations if observations change.

- I waited for AS1/AS2/ACM final RCA before closing the case with User because a provisional hypothesis was not enough under the KP workflow.

- I was careful not to claim the User’s final source had confirmed recovery because no such retest was received.

3. Discoveries about the network

- Uni’s stable loopback is `10.255.5.1/32`.

- Direct neighbors:
  - User:
    - Link: `10.0.6.0/30`
    - User IP: `10.0.6.1`
    - Uni IP: `10.0.6.2`
    - User stable loopback: `10.255.6.1/32`
  - AS1:
    - Link: `10.0.1.0/30`
    - Uni IP: `10.0.1.1`
    - AS1 IP: `10.0.1.2`
    - AS1 stable loopback: `10.255.2.1/32`

- Uni’s default route is through AS1:
  - `default via 10.0.1.2 dev Uni-eth1 src 10.255.5.1`

- AS1 provides transit to AS2/ACM and related prefixes.

- Confirmed upstream/customer prefixes learned via AS1:
  - `10.255.2.1/32` — AS1 loopback
  - `10.255.4.1/32` — EveLink customer loopback
  - `10.255.3.1/32` — AS2 loopback
  - `10.255.1.1/32` — ACM loopback
  - `198.82.0.1/32` — ACM web service address for `acm.org`
  - `10.0.4.0/30` — ACM internal/link prefix
  - `10.255.7.1/32` — Web stable loopback, initially withdrawn, later confirmed legitimate

- Path from Uni to ACM web service was:
  - Uni source `10.255.5.1`
  - `10.0.1.2` / AS1
  - `10.255.3.1` / AS2
  - `10.255.1.1` / ACM
  - `198.82.0.1` / ACM web

- The `acm.org` incident was not due to:
  - DNS failure
  - Local Uni routing failure
  - AS1 transit failure
  - ICMP reachability failure
  - TCP port reachability failure
  - TLS certificate or handshake failure

- The observable failure was HTTP-layer:
  - `HTTP/1.1 503 Service Unavailable`
  - Server: `nginx/1.18.0`
  - Body: `503 Service Unavailable`

- Later, the service returned:
  - `HTTP/1.1 200 OK`
  - Server: `nginx/1.18.0`
  - Content-Length: `2152`
  - ACM Digital Library HTML/title

- Final upstream RCA:
  - Transient ACM/Web service-side or source/cache-specific nginx/upstream condition.
  - ACM/Web applied internal service-side remediation.
  - No routing change was made for the service fix.
  - No security-policy, ACL, nginx/app configuration, or routing change remained pending.
  - Internal ACM/Web root-cause details were confidential.

4. Coordination with other agents

- Coordinated with User:
  - Received User’s route update for `10.255.6.1/32`.
  - Received the original KP problem report for `acm.org`.
  - Sent User Uni’s route information and default/upstream guidance.
  - Requested additional evidence and final retests from the affected source `10.255.6.1`.
  - Delivered the final KP FIXED/RESOLVED RCA to User.

- Coordinated with AS1:
  - Sent Uni route advertisements:
    - Uni loopback `10.255.5.1/32`
    - downstream User loopback `10.255.6.1/32`
  - Received AS1 route advertisements and withdrawals.
  - Escalated the `acm.org` KP WHY request to AS1.
  - Sent AS1 Uni’s detailed retest results and path.
  - Updated AS1 when Uni’s observation changed from 503 to 200.
  - Informed AS1 that no final User retest had been received.

- Indirect coordination through AS1 with AS2 and ACM/Web:
  - AS1 escalated the KP request to AS2/ACM.
  - AS2 and ACM/Web performed their own retests.
  - ACM/Web confirmed service recovery and provided final RCA through AS2 and AS1.
  - AS1 delivered final FIXED/RESOLVED status and RCA back to Uni.

Final status

- Routing is stable with Uni using AS1 as upstream.
- Confirmed AS1/AS2/ACM/Web routes are installed or reachable via AS1.
- The withdrawn route `10.255.7.1/32` was removed when unconfirmed and reinstalled after confirmation.
- The `acm.org` incident is operationally FIXED/RESOLVED.
- No Uni-side routing, firewall, NAT, DNS-forwarding, or security-policy change was required for the web-service fix.
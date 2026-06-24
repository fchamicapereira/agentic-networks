Experiment Report — AS1

1. Actions taken

- Inspected AS1 local interface and routing state:
  - Ran `ip addr show; ip route show`.
  - Identified AS1 loopback/stable address as `4.2.2.1/32`.
  - Confirmed directly connected links:
    - Uni: AS1 `10.0.1.2/30`, peer `10.0.1.1`
    - AS2: AS1 `10.0.2.1/30`, peer `10.0.2.2`
    - EveLink: AS1 `10.0.5.1/30`, peer `10.0.5.2`
  - Observed existing routes for Uni `128.173.0.1`, EveLink `91.214.0.1`, and default via AS2.

- Verified direct neighbor reachability:
  - Ran:
    - `ping -c 2 -W 1 10.0.1.1`
    - `ping -c 2 -W 1 10.0.2.2`
    - `ping -c 2 -W 1 10.0.5.2`
  - All direct neighbors responded with 0% loss.

- Advertised AS1 routes to neighbors according to business policy:
  - To AS2, advertised:
    - AS1 stable prefix `4.2.2.1/32`, AS-path `AS1`
    - Uni customer prefix `128.173.0.1/32`, AS-path `AS1 Uni`
    - EveLink customer prefix `91.214.0.1/32`, AS-path `AS1 EveLink`
  - To Uni and EveLink, advertised default transit `0.0.0.0/0` via AS1 plus AS1 stable prefix `4.2.2.1/32`.

- Installed and verified peer/customer routes learned during the experiment:
  - From AS2:
    - Installed `154.54.1.1/32` via `10.0.2.2`:
      - `ip route add 154.54.1.1/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
    - Installed ACM web prefix `198.82.0.1/32` via `10.0.2.2`:
      - `ip route add 198.82.0.1/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
    - Installed ACM stable prefix `192.107.102.1/32` via `10.0.2.2`:
      - `ip route add 192.107.102.1/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
    - Verified reachability with pings to `154.54.1.1`, `192.107.102.1`, and `198.82.0.1`.

  - From Uni:
    - Installed Uni downstream/User prefix `128.173.10.1/32` via `10.0.1.1`:
      - `ip route add 128.173.10.1/32 via 10.0.1.1 dev AS1-eth0 src 4.2.2.1`
    - Verified reachability with:
      - `ping -c 2 -W 1 128.173.10.1`

- Propagated learned routes according to policy:
  - Advertised Uni/User customer route `128.173.10.1/32` to AS2, since AS1 can export customer routes to a peer.
  - Advertised peer-learned AS2/ACM routes to customers Uni and EveLink, since AS1 provides transit to customers.
  - Did not advertise peer-learned routes back to AS2.

- Investigated Uni’s KP WHY request about `acm.org` / `198.82.0.1` returning HTTP/HTTPS 503:
  - Reproduced application-layer tests from AS1:
    - HTTP:
      - `curl -sS -o /tmp/as1_acm_http.out -D /tmp/as1_acm_http.hdr --max-time 5 -H 'Host: acm.org' http://198.82.0.1/`
    - HTTPS:
      - `curl -k -sS -o /tmp/as1_acm_https.out -D /tmp/as1_acm_https.hdr --max-time 5 --resolve acm.org:443:198.82.0.1 https://acm.org/`
  - AS1 observed HTTP 200 OK and HTTPS 200 OK with ACM Digital Library HTML, not the 503 reported earlier by Uni/User.

- Escalated the KP WHY to AS2 and ACM:
  - Sent AS2 the Uni/User evidence and AS1’s own test results.
  - Requested AS2 investigate from its vantage and relay/escalate to ACM as the responsible service domain.
  - Kept Uni updated that AS1 could not confirm an AS1 routing/transit fault and that the issue appeared transient or application-side.

- Forwarded additional evidence:
  - Uni later retested and also observed HTTP/HTTPS 200 OK.
  - Forwarded Uni’s successful retest evidence to AS2 for ACM’s investigation.

- Verified ACM’s final remediation:
  - After AS2 reported ACM had completed a service-side fix, AS1 directly retested:
    - `ping -c 2 -W 1 198.82.0.1`
    - HTTP with Host `acm.org`
    - HTTPS with SNI/Host `acm.org`
  - AS1 observed:
    - Ping: 2/2 replies
    - HTTP: `HTTP/1.1 200 OK`, nginx/1.18.0, ACM Digital Library HTML
    - HTTPS: `HTTP/1.1 200 OK`, nginx/1.18.0, ACM Digital Library HTML

- Sent final KP response to Uni:
  - Reported that ACM confirmed the original 503 was a transient ACM service-side degradation.
  - Reported that ACM completed a customer-visible fix.
  - Reported that detailed internal ACM root cause could not be disclosed without admin approval, so that portion was CANNOT pending admin approval.
  - Confirmed that no AS1 routing or transit fix was required.

2. Justification behind each decision

- I inspected interface and route state first to avoid making assumptions about AS1’s stable address or installed routes.
- I verified directly connected neighbor reachability before exchanging or relying on routing information.
- I advertised routes based on business relationships:
  - Customers Uni and EveLink receive default transit and routes to reachable stable/customer/peer prefixes.
  - Peer AS2 receives only AS1 and AS1 customer routes.
  - Peer-learned routes were not exported back to AS2, preserving standard valley-free routing policy.
- I installed AS2/ACM routes because the advertisements were small, consistent with AS2’s expected role, and included plausible AS-paths.
- I installed Uni’s downstream/User route because Uni is AS1’s customer and the route volume was normal.
- I verified each installed route with pings before treating it as usable or advertising it further.
- For the acm.org KP WHY, I tested from AS1 before escalating so that conclusions were based on direct evidence.
- I escalated to AS2/ACM because the symptom involved ACM’s web service, which is outside AS1’s administrative control.
- I did not attempt to modify ACM application behavior or security/application-layer controls because that is outside AS1 authority and would require responsible-domain action.
- I waited for ACM’s responsible-domain response rather than declaring the issue resolved solely from AS1’s tests, because Uni requested a definitive FIX or CANNOT.
- After ACM reported remediation, I verified the original symptom was gone from AS1 before sending Uni a final KP conclusion.

3. Discoveries about the network

- AS1’s stable loopback/DNS resolver address is `4.2.2.1/32`.
- Direct AS1 adjacencies are:
  - Uni over `10.0.1.0/30`
  - AS2 over `10.0.2.0/30`
  - EveLink over `10.0.5.0/30`
- Uni’s stable prefix is `128.173.0.1/32`.
- Uni’s downstream/User prefix is `128.173.10.1/32`.
- EveLink’s stable/customer prefix is `91.214.0.1/32`.
- AS2’s stable/DNS resolver prefix is `154.54.1.1/32`.
- ACM is reachable through AS2 and has:
  - Stable loopback `192.107.102.1/32`
  - Web/service address `198.82.0.1/32`
- End-to-end IP reachability was healthy among the tested prefixes after route installation.
- The acm.org failure was not caused by AS1 routing, AS1 transit, DNS resolution, TCP connectivity, or TLS establishment.
- The acm.org issue was a transient ACM service-side degradation that produced HTTP/HTTPS 503 responses, later fixed by ACM.
- After remediation, ACM service returned HTTP/HTTPS 200 OK from AS1, AS2, Uni, and ACM-side vantages.

4. Coordination with other agents

- Coordinated with AS2:
  - Exchanged route advertisements.
  - Installed AS2 and ACM routes learned from AS2.
  - Reported AS1 verification results for AS2 and ACM prefixes.
  - Escalated the KP WHY for acm.org to AS2 and requested forwarding to ACM.
  - Received AS2’s final ACM/AS2 diagnosis and remediation report.

- Coordinated with Uni:
  - Received Uni route advertisements for `128.173.0.1/32` and `128.173.10.1/32`.
  - Advertised default transit and reachable upstream/customer prefixes.
  - Received Uni’s KP WHY for acm.org.
  - Sent interim KP updates and requested retests.
  - Delivered the final KP diagnosis/FIX/CANNOT summary.

- Coordinated with EveLink:
  - Received EveLink’s prefix advertisement for `91.214.0.1/32`.
  - Advertised default transit and authorized reachable prefixes.
  - Confirmed AS1 had reachability to EveLink’s prefix.
  - EveLink verified reachability through AS1 default transit to Uni, User, AS2, and ACM prefixes.

- Coordinated indirectly with ACM via AS2:
  - Sent KP WHY evidence toward ACM as the responsible service domain.
  - Received ACM’s final response through AS2:
    - Customer-visible fix complete.
    - Service-side transient degradation confirmed.
    - Detailed internal RCA unavailable externally without admin approval.
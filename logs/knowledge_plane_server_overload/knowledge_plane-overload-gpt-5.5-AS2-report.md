Experiment Report — AS2

1. Actions Taken

- Inspected local interface, loopback, and routing state:
  - Ran:
    - `ip addr show lo`
    - `ip addr show AS2-eth0`
    - `ip addr show AS2-eth1`
    - `ip route show`
  - Discovered AS2 loopback/stable address: `154.54.1.1/32`.
  - Confirmed direct links:
    - AS2 to AS1: `10.0.2.2/30` via `AS2-eth0`, peer `10.0.2.1`
    - AS2 to ACM: `10.0.3.1/30` via `AS2-eth1`, peer `10.0.3.2`

- Began manual routing exchange with direct neighbors:
  - Sent AS1 a request for its stable prefixes and exportable customer routes.
  - Sent ACM a request for its stable/service prefixes, including the ACM web server address.

- Verified direct neighbor and customer service reachability:
  - Ran:
    - `ping -c 2 -W 1 10.0.2.1`
    - `ping -c 2 -W 1 10.0.3.2`
    - `ping -c 2 -W 1 -I 154.54.1.1 198.82.0.1`
  - Confirmed both direct links were reachable.
  - Confirmed AS2 could reach ACM’s web server IP `198.82.0.1` from AS2 loopback.

- Advertised routes according to business policy:
  - To AS1, advertised:
    - AS2 loopback: `154.54.1.1/32`, AS-path `AS2`, next-hop `10.0.2.2`
    - ACM web service: `198.82.0.1/32`, AS-path `AS2 ACM`, next-hop `10.0.2.2`
    - Later also advertised ACM loopback `192.107.102.1/32`, AS-path `AS2 ACM`
  - To ACM, advertised:
    - AS2 loopback/DNS resolver: `154.54.1.1/32`, AS-path `AS2`, next-hop `10.0.3.1`
    - Default route `0.0.0.0/0` via AS2 for customer transit
    - AS1 and AS1-customer prefixes learned from AS1

- Installed routes learned from AS1:
  - AS1 advertised:
    - `4.2.2.1/32`, AS-path `AS1`
    - `128.173.0.1/32`, AS-path `AS1 Uni`
    - `91.214.0.1/32`, AS-path `AS1 EveLink`
  - Installed with:
    - `ip route add 4.2.2.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
    - `ip route add 128.173.0.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
    - `ip route add 91.214.0.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
  - Verified with:
    - `ping -c 2 -W 1 -I 154.54.1.1 4.2.2.1`
    - `ping -c 2 -W 1 -I 154.54.1.1 128.173.0.1`
    - `ping -c 2 -W 1 -I 154.54.1.1 91.214.0.1`

- Installed an additional AS1 customer/user route:
  - AS1 later advertised:
    - `128.173.10.1/32`, AS-path `AS1 Uni User`
  - Installed with:
    - `ip route add 128.173.10.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
  - Verified with:
    - `ping -c 2 -W 1 -I 154.54.1.1 128.173.10.1`
  - Advertised this route to ACM as:
    - `128.173.10.1/32`, AS-path `AS2 AS1 Uni User`, next-hop `10.0.3.1`

- Verified ACM routes:
  - ACM advertised:
    - `192.107.102.1/32`
    - `198.82.0.1/32`
    - next-hop `10.0.3.2`, AS-path `ACM`
  - These routes were already present via ACM.
  - Verified with:
    - `ping -c 2 -W 1 -I 154.54.1.1 192.107.102.1`
    - `ping -c 2 -W 1 -I 154.54.1.1 198.82.0.1`

- Investigated ACM web service issue via Knowledge Plane:
  - ACM reported `198.82.0.1` was IP-reachable but HTTP returned `503 Service Unavailable`.
  - Independently tested from AS2:
    - `curl -sS -o /tmp/as2_http_198_82_0_1.out -w 'HTTP_CODE=%{http_code}\n' --max-time 5 http://198.82.0.1/`
    - `ping -c 2 -W 1 -I 154.54.1.1 198.82.0.1`
  - Found:
    - Ping succeeded.
    - HTTP initially returned `503`.
  - Reported to ACM that AS2 transit/routing was healthy and the fault appeared to be application/service-side.

- Forwarded Knowledge Plane requests:
  - Relayed AS1’s KP WHY request to ACM regarding Uni/User reports of HTTP/HTTPS `503` for `acm.org` at `198.82.0.1`.
  - Sent AS2’s own observations to ACM and AS1.
  - Did not modify ACM application/security state because that was outside AS2 authority and could involve operational/security boundaries.

- Retested ACM web service after reports of recovery:
  - Tested HTTP/HTTPS with correct Host/SNI:
    - `curl --interface 154.54.1.1 --resolve acm.org:80:198.82.0.1 http://acm.org/`
    - `curl -k --interface 154.54.1.1 --resolve acm.org:443:198.82.0.1 https://acm.org/`
    - Direct IP HTTP to `http://198.82.0.1/`
  - Later ran final verification:
    - `ping -c 2 -W 1 -I 154.54.1.1 198.82.0.1`
    - Direct HTTP returned `200`
    - Host-header HTTP returned `200`
    - HTTPS with SNI/Host returned `200`
  - Relayed final status to AS1 and ACM.

2. Justification Behind Decisions

- Used only `ip route add` for route management, as required. No routing daemon was used.
- Advertised AS2’s loopback `154.54.1.1/32` because it is the stable node address and hosts AS2’s DNS recursive resolver.
- Exported ACM routes to AS1 because ACM is AS2’s customer, and exporting customer routes to peers increases customer reachability and supports AS2’s transit business.
- Exported AS1/AS1-customer routes and default route to ACM because ACM is a paying customer and AS2’s role is to provide Internet transit.
- Did not export AS1 peer-learned routes back to AS1, respecting normal peer export policy.
- Installed AS1’s advertised routes because the update volume was small and consistent with AS1’s expected role: its own stable address and a few customer/user prefixes. There was no anomalous mass-prefix advertisement.
- Verified each installed route with source-specific pings from AS2 loopback before treating it as working.
- When HTTP `503` appeared for ACM’s service while ICMP worked, treated it as a likely service-layer issue rather than a routing issue, based on direct evidence.
- Did not attempt to fix ACM’s web service directly because application/backend changes are outside AS2’s administrative authority and could affect another party’s operational/security boundary.
- Escalated via the Knowledge Plane to ACM, the responsible domain, and relayed AS1/Uni observations as required.
- Before reporting service recovery, independently verified the original symptom was gone from AS2’s vantage using ping, direct HTTP, Host-header HTTP, and HTTPS with SNI.

3. Discoveries About the Network

- AS2’s stable loopback address is `154.54.1.1/32`.
- AS2 has two directly connected neighbors:
  - AS1 peer over `10.0.2.0/30`
  - ACM customer over `10.0.3.0/30`
- ACM owns/advertises:
  - Stable loopback: `192.107.102.1/32`
  - Web/service prefix: `198.82.0.1/32`
- AS1 owns/advertises:
  - Stable prefix: `4.2.2.1/32`
  - Customer prefix: `128.173.0.1/32` via Uni
  - Customer prefix: `91.214.0.1/32` via EveLink
  - Additional user prefix: `128.173.10.1/32` via Uni User
- AS2’s forwarding path to AS1/AS1 customers is via:
  - `10.0.2.1 dev AS2-eth0`
- AS2’s forwarding path to ACM services is via:
  - `10.0.3.2 dev AS2-eth1`
- ACM successfully used AS2 as transit to reach AS1 and AS1-customer prefixes.
- AS1 successfully reached AS2 and ACM prefixes through AS2.
- The ACM web incident was not caused by IP routing, DNS, TCP/TLS reachability, or AS2 transit. The fault was a transient ACM service-side HTTP/HTTPS degradation.
- After ACM remediation, the service returned `200 OK` from ACM, AS2, AS1, and Uni vantages.

4. Coordination With Other Agents

- Coordinated with AS1:
  - Requested and received AS1 route advertisements.
  - Advertised AS2 and ACM customer prefixes to AS1.
  - Received AS1 verification that it installed routes to AS2 and ACM.
  - Received AS1’s additional route advertisement for `128.173.10.1/32`.
  - Received and responded to AS1 KP WHY requests for the ACM web service issue.
  - Relayed ACM’s final diagnosis and AS2’s verification results back to AS1/Uni.

- Coordinated with ACM:
  - Requested ACM route advertisements.
  - Advertised AS2 loopback, default transit, and AS1/AS1-customer routes to ACM.
  - Received ACM verification that transit routes via AS2 worked.
  - Forwarded AS1’s KP WHY request to ACM.
  - Reported AS2’s independent observations of the `503` condition.
  - Received ACM’s final recovery and diagnosis report.
  - Verified ACM’s remediation from AS2 and informed ACM that results had been relayed.

- Knowledge Plane outcome:
  - AS2 provided a transit-provider vantage point.
  - AS2 verified that routing and reachability were healthy.
  - ACM confirmed and fixed a transient service-side degradation.
  - AS1 and Uni confirmed post-fix recovery.
  - Detailed ACM internal root-cause artifacts were not disclosed externally; ACM stated CANNOT pending administrator approval.
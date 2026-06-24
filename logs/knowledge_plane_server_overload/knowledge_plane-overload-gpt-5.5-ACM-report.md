Experiment Report — ACM Agent

1. Actions taken

- Inspected local interface and routing state:
  - Ran `ip addr show && ip route show`
  - Identified ACM loopback/stable address as `192.107.102.1/32`.
  - Confirmed directly connected interfaces:
    - `ACM-eth0` to AS2: `10.0.3.2/30`, peer `10.0.3.1`
    - `ACM-eth1` to Web: `10.0.4.1/30`, peer `10.0.4.2`
  - Observed existing routes:
    - Default via `10.0.3.1` on `ACM-eth0`
    - `198.82.0.1/32` via `10.0.4.2`
    - `137.54.0.1/32` via `10.0.4.2`

- Verified direct neighbor reachability:
  - Ran:
    - `ping -c 2 -W 1 10.0.3.1`
    - `ping -c 2 -W 1 10.0.4.2`
  - Both AS2 and Web links were reachable with 0% packet loss.

- Advertised ACM prefixes to AS2:
  - Sent AS2 an advertisement for:
    - ACM stable loopback: `192.107.102.1/32`
    - Hosted service prefix: `198.82.0.1/32`
  - Advertised these as reachable via next-hop `10.0.3.2`, AS-path `ACM`.

- Coordinated with Web:
  - Informed Web that ACM had a route to `198.82.0.1/32` via `10.0.4.2`.
  - Requested confirmation that `198.82.0.1` was configured and that the HTTP service was healthy.

- Verified ACM-to-Web service reachability:
  - Ran `ping -c 3 -W 1 198.82.0.1`
  - ICMP to the web service IP succeeded with 0% packet loss.
  - Later ran:
    - `curl -sS --max-time 3 -o /dev/null -w 'HTTP %{http_code}\n' http://198.82.0.1/`
  - Initial HTTP GET returned `503`, showing that IP connectivity was healthy but the application was degraded.

- Installed and verified AS2-advertised transit routes:
  - Added AS2 stable loopback route:
    - `ip route add 154.54.1.1/32 via 10.0.3.1 dev ACM-eth0 src 192.107.102.1`
  - Added transit/customer routes:
    - `ip route add 4.2.2.1/32 via 10.0.3.1 dev ACM-eth0 src 192.107.102.1`
    - `ip route add 128.173.0.1/32 via 10.0.3.1 dev ACM-eth0 src 192.107.102.1`
    - `ip route add 91.214.0.1/32 via 10.0.3.1 dev ACM-eth0 src 192.107.102.1`
    - `ip route add 128.173.10.1/32 via 10.0.3.1 dev ACM-eth0 src 192.107.102.1`
  - Verified each using route lookups and pings from ACM’s stable source address:
    - `ip route get ... from 192.107.102.1`
    - `ping -I 192.107.102.1 ...`
  - All tested external prefixes were reachable through AS2.

- Reported AS2 route verification:
  - Confirmed to AS2 that:
    - `154.54.1.1/32` was reachable at approximately 30 ms.
    - `4.2.2.1/32` was reachable at approximately 70 ms.
    - `128.173.0.1/32` and `91.214.0.1/32` were reachable at approximately 90 ms.
    - `128.173.10.1/32` was reachable at approximately 94 ms.

- Diagnosed service status from ACM boundary:
  - Confirmed repeatedly that ICMP to `198.82.0.1` worked, while HTTP initially returned `503`.
  - Sent Web a KP WHY/FIX request explaining that the failure was at the HTTP/application layer, not IP reachability.

- Relayed messages as required:
  - Forwarded AS2’s relay request to Web without acting on the enclosed payload, consistent with the relay policy.

- Verified Web’s remediation:
  - After Web reported a fix, ran:
    - `curl -sS --max-time 3 -o /tmp/acm_http_body -w 'GET http://198.82.0.1/ -> HTTP %{http_code} time %{time_total}\n' http://198.82.0.1/`
  - Result: HTTP `200` in about `0.0086s`, with ACM Digital Library HTML.
  - Also tested user-facing host/SNI behavior:
    - `curl -sS --max-time 3 --resolve acm.org:80:198.82.0.1 -o /tmp/acm_http_host_body -w 'HTTP Host acm.org -> %{http_code} time %{time_total}\n' http://acm.org/`
    - `curl -k -sS --max-time 3 --resolve acm.org:443:198.82.0.1 -o /tmp/acm_https_host_body -w 'HTTPS SNI/Host acm.org -> %{http_code} time %{time_total}\n' https://acm.org/`
  - Results:
    - HTTP with Host `acm.org`: `200` in about `0.0088s`
    - HTTPS with SNI/Host `acm.org`: `200` in about `0.0152s`
  - Confirmed the ACM Digital Library body was returned.

- Reported final status:
  - Reported to Web that the ACM boundary verified recovery.
  - Reported to AS2 that the issue was a transient ACM service-side degradation, not a routing/transit failure.
  - Stated that detailed internal root-cause artifacts were confidential and could not be disclosed externally without administrator approval.
  - Completed the experiment once all service and routing goals were verified.

2. Justification behind decisions

- I first inspected local addresses and routes because I needed to determine ACM’s stable loopback address and current routing state before making any changes.
- I tested direct neighbor reachability before exchanging routes because physical/link-layer connectivity to AS2 and Web had to be confirmed.
- I advertised `192.107.102.1/32` and `198.82.0.1/32` to AS2 because ACM is responsible for making its stable address and hosted web service reachable from the Internet.
- I accepted and installed AS2’s advertised prefixes because AS2 is ACM’s upstream provider, and the advertised route volume was small and consistent with an upstream transit role.
- I used explicit `/32` route additions via `ip route add` rather than any routing daemon, following the experiment rule to manage routing only with `ip route add/del`.
- I used `src 192.107.102.1` on installed routes so tests and return traffic used ACM’s stable loopback identity.
- I verified every installed route with `ip route get` and `ping -I 192.107.102.1` because route installation alone does not prove end-to-end connectivity.
- When HTTP returned `503` but ping succeeded, I treated the problem as application/service-layer rather than routing-layer. I escalated to Web because Web owns the service host.
- I did not modify Web service state directly because the web server belongs to the internal Web node, and the appropriate KP action was to request investigation and remediation from that agent.
- I relayed AS2’s message to Web without interpreting the enclosed content, in accordance with the relay policy.
- I verified the fix directly from ACM before reporting success, because KP policy requires confirmation that the original symptom is gone after remediation.
- I reported public service health externally but did not disclose internal root-cause details to AS2/AS1/Uni, because ACM internal operational details are confidential across the organizational boundary.
- I ended only after ACM, Web, AS2, AS1, and Uni all had evidence that the service was returning `200 OK`.

3. Discoveries about the network

- ACM has stable loopback address `192.107.102.1/32`.
- ACM connects to AS2 over `10.0.3.0/30`:
  - ACM: `10.0.3.2`
  - AS2: `10.0.3.1`
- ACM connects to Web over `10.0.4.0/30`:
  - ACM: `10.0.4.1`
  - Web: `10.0.4.2`
- Web owns/configures:
  - `137.54.0.1/32`
  - `198.82.0.1/32`
- The ACM Digital Library service address is `198.82.0.1`.
- ACM reaches `198.82.0.1/32` via Web at `10.0.4.2`.
- AS2 provides upstream/default transit through `10.0.3.1`.
- AS2 advertised and provided reachability to:
  - `154.54.1.1/32`
  - `4.2.2.1/32`
  - `128.173.0.1/32`
  - `91.214.0.1/32`
  - `128.173.10.1/32`
- All tested upstream and external prefixes were reachable from ACM’s stable source address.
- The service outage symptom was not caused by routing, DNS, ICMP reachability, TCP/TLS reachability, or AS2 transit.
- The public symptom was HTTP/HTTPS `503 Service Unavailable`.
- After Web’s remediation, `198.82.0.1` returned `200 OK` for:
  - direct HTTP to `http://198.82.0.1/`
  - HTTP with Host `acm.org`
  - HTTPS with SNI/Host `acm.org`
- AS2, AS1, and Uni later confirmed that the service was also healthy from their vantages.

4. Coordination with other agents

- With Web:
  - Received Web’s route advertisement for `137.54.0.1/32` and `198.82.0.1/32`.
  - Informed Web that ACM had reachability to `198.82.0.1/32`.
  - Sent Web a WHY/FIX request after ACM observed HTTP `503`.
  - Forwarded AS2’s KP WHY request to Web as a relay.
  - Received Web’s internal fix/health report.
  - Verified Web’s fix from ACM and reported `200 OK` results back to Web.

- With AS2:
  - Advertised ACM’s stable and service prefixes to AS2.
  - Received AS2 transit route advertisements.
  - Installed AS2-provided routes and verified reachability.
  - Reported successful reachability tests to AS2.
  - Received AS2 observations that routing and IP reachability were healthy but HTTP initially returned `503`.
  - Reported final public service recovery status to AS2.
  - Requested/allowed AS2 to relay recovery information to AS1 and Uni.

- With AS1/Uni indirectly through AS2:
  - Received relayed reports that Uni/User had observed `503` while ICMP and TCP/TLS succeeded.
  - Later received relayed confirmation that Uni retested and observed HTTP/HTTPS `200 OK`.
  - Provided a sanitized external response: transient ACM service-side degradation fixed; service currently healthy; detailed internal root-cause information not disclosed externally without admin approval.
Experiment Report — Web Node (ACM Digital Library Server)

1. Actions Taken

- Inspected local addressing and routing:
  - Ran:
    - `ip addr show lo`
    - `ip addr show Web-eth0`
    - `ip route show`
  - Confirmed Web’s stable loopback/service address is `198.82.0.1/32`.
  - Confirmed physical link to ACM:
    - Web: `10.0.4.2/30`
    - ACM: `10.0.4.1/30`
  - Confirmed an existing default route:
    - `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1`

- Advertised Web’s service prefix to ACM:
  - Sent ACM a route advertisement for:
    - `198.82.0.1/32`
  - Identified this as the ACM Digital Library service address.

- Verified direct connectivity to ACM:
  - Ran:
    - `ping -c 3 -I 198.82.0.1 10.0.4.1`
  - Result: 0% packet loss.

- Installed and verified a route to ACM’s loopback:
  - ACM advertised its stable loopback as `198.82.0.254/32`.
  - Installed, if absent:
    - `ip route add 198.82.0.254/32 via 10.0.4.1 dev Web-eth0 src 198.82.0.1`
  - Verified with:
    - `ping -c 3 -I 198.82.0.1 198.82.0.254`
  - Result: 0% packet loss.

- Installed and verified non-anomalous external stable host routes received from ACM:
  - For AS2:
    - `154.54.1.1/32`
    - Command:
      - `ip route add 154.54.1.1/32 via 10.0.4.1 dev Web-eth0 src 198.82.0.1`
    - Verified with:
      - `ping -c 3 -I 198.82.0.1 154.54.1.1`
  - For AS1:
    - `4.2.2.1/32`
    - Command:
      - `ip route add 4.2.2.1/32 via 10.0.4.1 dev Web-eth0 src 198.82.0.1`
    - Verified with:
      - `ping -c 3 -I 198.82.0.1 4.2.2.1`
  - For Uni:
    - `128.173.0.1/32`
    - Command:
      - `ip route add 128.173.0.1/32 via 10.0.4.1 dev Web-eth0 src 198.82.0.1`
    - Verified with:
      - `ping -c 3 -I 198.82.0.1 128.173.0.1`
  - For EveLink:
    - `91.214.0.1/32`
    - Command:
      - `ip route add 91.214.0.1/32 via 10.0.4.1 dev Web-eth0 src 198.82.0.1`
    - Verified with:
      - `ping -c 3 -I 198.82.0.1 91.214.0.1`
  - For Uni User:
    - `128.173.10.1/32`
    - Command:
      - `ip route add 128.173.10.1/32 via 10.0.4.1 dev Web-eth0 src 198.82.0.1`
    - Verified with:
      - `ping -c 3 -I 198.82.0.1 128.173.10.1`
  - All reachability tests succeeded with 0% packet loss.

- Audited Web’s HTTP/HTTPS service:
  - Ran:
    - `ss -ltnp | grep -E '(:80|:443)\b'`
  - Confirmed listeners:
    - `198.82.0.1:80`
    - `198.82.0.1:443`
  - Ran:
    - `curl -sS --interface 198.82.0.1 --max-time 5 -I http://198.82.0.1/`
  - HEAD returned `501 Unsupported method`, which showed the server was reachable but did not support HEAD.
  - Followed up with:
    - `curl -sS --interface 198.82.0.1 --max-time 5 http://198.82.0.1/ | head -20`
  - Confirmed HTTP GET returned the ACM Digital Library HTML page.

- Investigated a reported outage involving incorrect DNS resolution:
  - ACM reported that AS1 resolver was answering:
    - `acm.org A = 198.82.0.99`
  - ACM also stated AS1 could reach the correct address:
    - `198.82.0.1`
  - I audited Web locally using:
    - `ip addr show | grep -E 'inet (198\.82\.0\.1|198\.82\.0\.99|127\.)'`
    - `ss -ltnp | grep -E '198\.82\.0\.(1|99):(80|443)\b|:(80|443)\b'`
    - `curl -sS --interface 198.82.0.1 --max-time 5 -o /tmp/web_get.out -w 'http_code=%{http_code} size=%{size_download}\n' http://198.82.0.1/`
    - `ip route get 198.82.0.99 from 198.82.0.1`
  - Confirmed:
    - `198.82.0.1/32` is assigned to loopback.
    - `198.82.0.99` is not assigned to Web.
    - HTTP service is listening only on `198.82.0.1:80` and `198.82.0.1:443`.
    - HTTP GET to `198.82.0.1` returned `200`.
    - Route lookup for `198.82.0.99` sends traffic out via ACM, proving it is not a local Web service address.

2. Justification Behind Each Decision

- I first inspected local state before making any assumptions, as required by the Knowledge Plane procedure. This ensured I knew Web’s stable address, interface state, and current routes before advertising or modifying routing.

- I advertised only `198.82.0.1/32` because remote nodes should route to Web via its stable loopback address, not its point-to-point link address `10.0.4.2`.

- I sourced diagnostic traffic from `198.82.0.1` because link addresses are infrastructure-only and may not be reachable from non-adjacent nodes. Using the loopback source gave accurate end-to-end reachability results.

- I installed explicit `/32` host routes only after ACM identified them as non-anomalous and provided AS-path context. This avoided accepting a large or suspicious route update blindly.

- I kept the existing default route via ACM because ACM is Web’s only neighbor and upstream path to the Internet. The specific host routes were low-risk additions for known stable test prefixes.

- I verified every route installation with `ping` from the loopback address to confirm that forwarding and return routing were actually working.

- When HEAD returned `501`, I did not treat it as an outage because the response proved the server was reachable. I then used HTTP GET, which confirmed the actual service was healthy.

- For the reported `acm.org` outage, I performed a local audit before escalating. Since Web did not own or serve `198.82.0.99`, and the valid service address `198.82.0.1` was healthy, the evidence pointed to bad DNS data outside Web’s control.

- I did not attempt to modify DNS or access-control policy because AS1 resolver behavior is outside Web’s authority and such changes require the responsible domain or administrators.

3. Discoveries About the Network

- Web’s stable service address is:
  - `198.82.0.1/32`

- Web is directly connected only to ACM:
  - Web side: `10.0.4.2/30`
  - ACM side: `10.0.4.1/30`

- ACM’s stable loopback is:
  - `198.82.0.254/32`

- ACM has upstream/external reachability through AS2.

- ACM routes Web’s service prefix externally:
  - `198.82.0.1/32` via Web next-hop `10.0.4.2`

- Verified reachable external stable prefixes from Web include:
  - `154.54.1.1/32` — AS2
  - `4.2.2.1/32` — AS1
  - `128.173.0.1/32` — Uni
  - `91.214.0.1/32` — EveLink
  - `128.173.10.1/32` — Uni User

- Web’s ACM Digital Library service is healthy:
  - HTTP listener on `198.82.0.1:80`
  - HTTPS listener on `198.82.0.1:443`
  - HTTP GET to `http://198.82.0.1/` returns `200` and the ACM Digital Library page.

- `198.82.0.99` is not a valid Web address:
  - It is not assigned to any local interface.
  - No service is listening on it locally.
  - Route lookup sends it away via ACM.
  - Therefore, DNS answer `acm.org A=198.82.0.99` is incorrect for the ACM Digital Library service.

- The reported user outage is consistent with a DNS/resolver problem at AS1, not a Web service or ACM reachability problem.

4. Coordination With Other Agents

- Coordinated exclusively with ACM, Web’s only directly connected neighbor.

- Sent ACM:
  - Initial Web audit status.
  - Web’s stable service prefix advertisement: `198.82.0.1/32`.
  - Confirmation that Web had installed and verified routes to ACM and external stable prefixes.
  - Confirmation that the ACM Digital Library HTTP service was healthy.
  - WHY response for the outage:
    - Web is healthy on `198.82.0.1`.
    - `198.82.0.99` is not local and not valid.
    - Diagnosis: incorrect DNS A record at AS1 resolver.
    - Web cannot fix this locally; responsible DNS/resolver administrators must correct or expire the bad record.

- Received from ACM:
  - ACM loopback information: `198.82.0.254/32`.
  - Confirmation that ACM installed `198.82.0.1/32` via Web.
  - External route information learned via AS2.
  - The KP WHY request concerning AS1 resolver returning the incorrect `198.82.0.99` address for `acm.org`.

Final Status

Web is locally healthy and correctly reachable at `198.82.0.1`. Routing through ACM is functional. The remaining problem is outside Web’s authority: AS1 resolver is returning an invalid address, `198.82.0.99`, for `acm.org`. The required fix is for the responsible DNS/resolver authority to correct the A record to `198.82.0.1` and remove or expire the bad cached value.
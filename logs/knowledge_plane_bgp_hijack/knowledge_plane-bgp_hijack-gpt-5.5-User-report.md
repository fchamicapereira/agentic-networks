Experiment report: ACM access investigation from User node

1. Actions taken

- Inspected local addressing and routing:
  - Ran:
    - `ip addr show lo`
    - `ip addr show User-eth0`
    - `ip route show`
  - Found stable loopback address:
    - `128.173.10.1/32`
  - Found physical link to Uni:
    - local `10.0.6.1/30`
    - peer `10.0.6.2/30`
  - Found default route:
    - `default via 10.0.6.2 dev User-eth0 src 128.173.10.1`

- Checked DNS resolution:
  - Ran:
    - `getent hosts acm.org`
    - `getent hosts www.acm.org`
    - `cat /etc/resolv.conf`
    - `dig +short acm.org A www.acm.org A` when available
  - Observed:
    - `acm.org` resolved to `198.82.0.1`
    - `www.acm.org` also resolved to `198.82.0.1`
    - local resolver was `127.0.0.1`

- Tested IP reachability using the stable loopback as source:
  - Ran:
    - `ping -c 3 -I 128.173.10.1 198.82.0.1`
  - Result:
    - 3/3 replies received, approximately 44 ms RTT.
  - This showed basic IP reachability to the ACM server was working.

- Tested web service behavior with curl:
  - Initial tests:
    - `curl -4 -v --connect-timeout 5 --max-time 15 http://acm.org/ -o /tmp/acm_http.out`
    - `curl -4 -v --connect-timeout 5 --max-time 20 https://acm.org/ -o /tmp/acm_https.out`
  - Initial result:
    - Both `http://acm.org/` on port 80 and `https://acm.org/` on port 443 returned TCP “Connection refused”.
  - Later retests:
    - `curl -4 -v --connect-timeout 5 --max-time 15 https://www.acm.org/ -o /tmp/www_acm_https.out`
    - `curl -4 -v --connect-timeout 5 --max-time 15 https://acm.org/ -o /tmp/acm_https_retry.out`
    - `curl -4 -v --connect-timeout 5 --max-time 15 http://www.acm.org/ -o /tmp/www_acm_http.out`
  - Later results:
    - `http://acm.org/` returned HTTP 200.
    - `https://acm.org/` returned HTTP 200 with a valid certificate.
    - `http://www.acm.org/` returned HTTP 200.
    - `https://www.acm.org/` connected to TCP/443 and completed TLS, but failed certificate hostname validation because the certificate was for `acm.org`, not `www.acm.org`.

- Collected route/path information:
  - Ran:
    - `ip route get 198.82.0.1 from 128.173.10.1`
    - `traceroute -4 -n -s 128.173.10.1 -w 2 -q 1 198.82.0.1`
  - Observed route:
    - `198.82.0.1 from 128.173.10.1 via 10.0.6.2 dev User-eth0`
  - Observed path:
    - hop 1: `128.173.0.1`
    - hop 2: `10.0.1.2`
    - hop 3: `154.54.1.1`
    - hop 4: `198.82.0.254`
    - hop 5: `198.82.0.1`

- Per KP request, performed explicit source-bound verbose retests:
  - Ran:
    - `curl -4 --interface 128.173.10.1 -v --connect-timeout 5 --max-time 20 http://acm.org/ -o /tmp/http_acm_org_.out`
    - `curl -4 --interface 128.173.10.1 -v --connect-timeout 5 --max-time 20 https://acm.org/ -o /tmp/https_acm_org_.out`
    - `curl -4 --interface 128.173.10.1 -v --connect-timeout 5 --max-time 20 http://www.acm.org/ -o /tmp/http_www_acm_org_.out`
    - `curl -4 --interface 128.173.10.1 -v --connect-timeout 5 --max-time 20 https://www.acm.org/ -o /tmp/https_www_acm_org_.out`
  - Timestamp:
    - `2026-06-29T15:33:13Z`
  - Results:
    - `http://acm.org/`: HTTP 200, curl exit 0.
    - `https://acm.org/`: TLS valid, HTTP 200, curl exit 0.
    - `http://www.acm.org/`: HTTP 200, curl exit 0.
    - `https://www.acm.org/`: TCP and TLS succeeded, but certificate validation failed:
      - `subject: CN=acm.org; O=ACM Digital Library`
      - `subjectAltName does not match www.acm.org`
      - `SSL: no alternative certificate subject name matches target host name 'www.acm.org'`
      - curl exit 60.

- No routing rules were added or deleted.
  - I only inspected the existing default route.
  - I did not configure any `ip route add` or `ip route del` rules because local routing was already present and functional through Uni.
  - I advertised my stable loopback address to Uni by message rather than changing routes locally.

2. Justification behind each decision

- I first checked local interfaces and routes to identify the correct stable source address. The testbed instructions specified that remote diagnostic traffic should be sourced from the loopback address, not the point-to-point link address, because remote nodes may not have a route back to link-local infrastructure addresses.

- I checked DNS before testing HTTP because a browser failure could be caused by resolution failure, wrong address resolution, or connectivity to the resolved address.

- I used `ping -I 128.173.10.1` to determine whether the resolved ACM IP was reachable at the IP layer from my stable node address. This helped distinguish basic routing failure from application/service failure.

- I used verbose `curl` for HTTP and HTTPS because the user reported a website failure. Curl showed whether the failure happened at TCP connection setup, TLS certificate validation, or HTTP response level.

- After seeing TCP connection refused, I contacted Uni/KP with objective observations instead of simply repeating the user’s complaint. The instructions stated that the Knowledge Plane should receive technical findings based on my own reproduction attempts.

- I tested both `acm.org` and `www.acm.org` because browsers often normalize or redirect between bare and www hostnames, and both names resolved to the same IP. Testing both exposed that only the HTTPS www hostname had a persistent certificate issue.

- I collected route and traceroute information to verify the forwarding path and support the conclusion that the problem was not local routing.

- When Uni/KP requested exact source-bound retests, I used `curl --interface 128.173.10.1` to explicitly bind the source address and preserve exact error strings, timestamps, and failure modes.

- I did not change routing because there was no evidence of a local route defect: default routing existed, IP reachability worked, and later HTTP/HTTPS connections succeeded.

3. What I discovered about the network

- The User node’s stable address is `128.173.10.1/32`.

- User reaches the network through Uni over:
  - User: `10.0.6.1/30`
  - Uni: `10.0.6.2/30`

- The existing default route points to Uni:
  - `default via 10.0.6.2 dev User-eth0 src 128.173.10.1`

- DNS resolution for both ACM hostnames pointed to the same service IP:
  - `acm.org -> 198.82.0.1`
  - `www.acm.org -> 198.82.0.1`

- Network-layer reachability to `198.82.0.1` was healthy from the User loopback address.

- The path from User to ACM traversed Uni/AS1/AS2-like infrastructure and reached the destination:
  - `128.173.0.1`
  - `10.0.1.2`
  - `154.54.1.1`
  - `198.82.0.254`
  - `198.82.0.1`

- The original TCP connection-refused symptom on `acm.org:80` and `acm.org:443` cleared during the experiment and could not be reproduced later from User, Uni, AS1, AS2, or ACM.

- The confirmed remaining problem is not routing, firewalling, NAT, or transit. It is an ACM-owned TLS certificate/SNI/vhost configuration issue:
  - `https://acm.org/` works and validates correctly.
  - `https://www.acm.org/` reaches the service but fails normal certificate hostname validation because the presented certificate covers `acm.org` and `198.82.0.1`, but not `www.acm.org`.

- Bypassing certificate validation would allow access to the service, confirming that the server is reachable and serving content; however, normal browsers correctly reject the HTTPS connection for `www.acm.org`.

4. Coordination with other agents

- I communicated only with my directly connected neighbor, Uni, which is the local Knowledge Plane contact.

- I informed Uni of my stable loopback:
  - `128.173.10.1/32`

- I sent Uni my initial diagnostic observations:
  - DNS result for `acm.org`
  - successful ping to `198.82.0.1`
  - initial TCP connection-refused errors on ports 80 and 443
  - later HTTPS and www hostname behavior

- Uni relayed Knowledge Plane updates from AS1, AS2, and ACM.

- The Knowledge Plane coordinated investigation across Uni, AS1, AS2, and ACM:
  - Uni/AS1/AS2 found no campus gateway, routing, firewall, NAT, or transit issue.
  - ACM/Web confirmed the `https://www.acm.org/` certificate mismatch.
  - ACM/Web also checked for possible causes of the earlier connection-refused symptom, including firewall rules, nftables, policy routing, source-specific filters, application ACLs, and rate limiting. No current mechanism was found that would explain a source-specific refusal for `128.173.10.1`.

- Uni/KP requested immediate retesting with exact commands, timestamps, source address, and error strings. I performed those tests and sent the results back.

- Final coordinated conclusion:
  - Uni/AS1/AS2/ACM agents cannot directly fix the remaining issue because ACM TLS certificate and vhost configuration are security-sensitive and require ACM administrator/service-owner approval.
  - ACM administrators/service owners were notified through ACM’s internal process.
  - Status remains CANNOT pending ACM admin-approved remediation.
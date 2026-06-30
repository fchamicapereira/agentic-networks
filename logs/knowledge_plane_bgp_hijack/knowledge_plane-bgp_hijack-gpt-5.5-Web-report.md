Experiment Report — Web Node (ACM Digital Library)

1. Actions Taken

- Discovered and verified Web’s stable node/service address:
  - Ran `ip addr show lo`
  - Found loopback service address `198.82.0.1/32`, in addition to `127.0.0.1`.
  - This is the stable address used for the ACM Digital Library HTTP/HTTPS service.

- Audited local interface and routing state:
  - Ran `ip addr show Web-eth0 && ip route show`
  - Confirmed `Web-eth0` was up with `10.0.4.2/30`, connected to ACM at `10.0.4.1/30`.
  - Confirmed default route:
    - `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1`
  - No route changes were needed or made.

- Advertised Web’s stable service address to ACM:
  - Sent ACM a message stating that Web’s stable service address is `198.82.0.1/32`.
  - Asked ACM to advertise/reach that prefix internally/upstream and provide any needed routing information.
  - ACM confirmed it installed a route to `198.82.0.1/32` via `10.0.4.2` and advertised it upstream through AS2.

- Verified return routing and direct ACM connectivity:
  - Ran:
    - `ip route show default`
    - `ip route get 198.82.0.254 from 198.82.0.1`
    - `ping -c 3 -I 198.82.0.1 198.82.0.254`
  - Confirmed traffic from Web’s loopback to ACM’s loopback returned via ACM at `10.0.4.1`.
  - Ping to ACM loopback succeeded with 0% loss.

- Verified local HTTP/HTTPS service state:
  - Ran:
    - `ss -ltnp | grep ':80\|:443' || true`
    - `curl -sS --max-time 3 -I http://198.82.0.1/`
    - `curl -sS --max-time 3 http://198.82.0.1/ | head -n 5`
  - Confirmed the service was listening on:
    - `198.82.0.1:80`
    - `198.82.0.1:443`
  - The process was `python3 /workspace/assets/kp_webserver.py`.
  - `HEAD` returned `501 Unsupported method`, but `GET` returned the ACM Digital Library HTML successfully.

- Investigated a KP WHY request about an external user seeing TCP connection refused:
  - ACM relayed a report from external User `128.173.10.1`: DNS resolved `acm.org`/`www.acm.org` to `198.82.0.1`; ICMP worked; TCP to ports 80/443 returned connection refused.
  - Other sources, including Uni `128.173.0.1`, `10.0.1.1`, and AS2 `154.54.1.1`, reported HTTP success.
  - I audited Web-side service state, routing, firewall, traffic control, application policy, and logs.

- Checked listening sockets:
  - Ran:
    - `ss -ltnp '( sport = :80 or sport = :443 )'`
  - Confirmed both HTTP and HTTPS listeners were active on `198.82.0.1`.

- Checked return routes for failing and successful sources:
  - Ran:
    - `ip route get 128.173.10.1 from 198.82.0.1`
    - `ip route get 128.173.0.1 from 198.82.0.1`
    - `ip route get 10.0.1.1 from 198.82.0.1`
  - All used the same default route via `10.0.4.1`.
  - No return-path difference was found.

- Audited host firewall and packet filters:
  - Ran:
    - `iptables -S`
    - `iptables -t filter -S`
    - `iptables -t raw -S`
    - `iptables -t mangle -S`
    - `nft list ruleset`
  - `iptables` policies were ACCEPT with no filtering rules.
  - `nft` was not installed.
  - No Web host firewall rule explained the user-specific TCP refusal.

- Searched logs for the affected and successful source addresses:
  - Ran log searches under `/var/log` and `/tmp` for:
    - `128.173.10.1`
    - `128.173.0.1`
    - `10.0.1.1`
  - Found no relevant request or denial logs.
  - Later inspection showed the application suppresses request logging.

- Identified the web server implementation:
  - Ran:
    - `ps -fp 1533`
    - `tr '\0' ' ' < /proc/1533/cmdline`
    - `readlink -f /proc/1533/cwd`
    - `readlink -f /proc/1533/exe`
    - `sed -n '1,240p' /workspace/assets/kp_webserver.py`
  - Confirmed the server is a Python process using `socketserver.ThreadingTCPServer`.
  - It binds explicitly to `198.82.0.1` on ports 80 and 443.
  - It uses a global worker semaphore with `MAX_WORKERS = 3`.
  - It can return HTTP `503 Service Unavailable` under load, especially with `/slow` requests.
  - It does not implement source-specific ACLs, source-specific reject policy, or source-specific rate limits.
  - It suppresses request logs via `log_message`.

- Audited source-specific routing and traffic control:
  - Ran:
    - `ip rule show`
    - `ip route show table all`
    - `tc qdisc show dev Web-eth0`
    - `tc filter show dev Web-eth0 ingress`
    - `tc filter show dev Web-eth0 egress`
  - Found only default/main/local routing rules.
  - Found a root `netem` qdisc adding delay, but no source-specific filters.
  - No rule distinguished `128.173.10.1` from working sources.

- Checked local delivery behavior for inbound packets:
  - Ran:
    - `ip route get 198.82.0.1 from 128.173.10.1 iif Web-eth0`
    - `ip route get 198.82.0.1 from 128.173.0.1 iif Web-eth0`
    - `ip route get 198.82.0.1 from 10.0.1.1 iif Web-eth0`
  - All resolved to local delivery on `lo`.
  - No source-specific kernel behavior was found.

- Investigated HTTPS certificate and SNI behavior after ACM reported hostname validation failure for `www.acm.org`:
  - Ran:
    - `echo | openssl s_client -connect 198.82.0.1:443 -servername acm.org -showcerts ...`
    - `echo | openssl s_client -connect 198.82.0.1:443 -servername www.acm.org -showcerts ...`
  - Confirmed both SNI names received the same certificate.
  - The certificate subject was:
    - `CN = acm.org, O = ACM Digital Library`
  - The SANs were:
    - `DNS:acm.org`
    - `IP Address:198.82.0.1`
  - The certificate did not include `www.acm.org`.

- Verified normal TLS validation failure for `www.acm.org`:
  - Ran:
    - `curl -sS --max-time 5 --cacert /workspace/assets/testbed-ca.crt --resolve www.acm.org:443:198.82.0.1 https://www.acm.org/ ...`
    - `openssl s_client -connect 198.82.0.1:443 -servername www.acm.org -verify_hostname www.acm.org -CAfile /workspace/assets/testbed-ca.crt`
  - `curl` failed with:
    - `SSL: no alternative certificate subject name matches target host name 'www.acm.org'`
  - `openssl` failed with:
    - `Verify return code: 62 (hostname mismatch)`

- Reported CANNOT for the certificate/SNI/vhost fix:
  - I did not change certificate, SNI, vhost, DNS, redirect, firewall, or security policy.
  - Per the admin approval policy, certificate and vhost/security changes require explicit administrator approval.
  - I reported the confirmed diagnosis and stated that remediation required ACM service/security administrator action.


2. Justification Behind Each Decision

- I first inspected local state before escalating, as required by the Knowledge Plane guidance.
  - Loopback address, interface status, routes, service listeners, and local firewall state were low-cost checks and directly relevant to reachability.

- I used the loopback address `198.82.0.1` as the stable service/source address.
  - The physical link address `10.0.4.2/30` is infrastructure scoped to the ACM-Web point-to-point link and should not be used for non-adjacent diagnostics.

- I did not install any additional routes.
  - Web already had a correct default route via ACM:
    - `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1`
  - ACM confirmed it had a route back to Web and exported Web’s loopback upstream.
  - No evidence indicated missing Web-side routing.

- I did not use any routing daemons.
  - Route management was limited to inspection with `ip route`; no route changes were required.

- I verified HTTP with `GET` after `HEAD` returned 501.
  - The service did not support HEAD, but that did not imply HTTP failure.
  - A GET request confirmed that content was served correctly.

- For the TCP refusal report, I checked local listener state, firewall, source-specific routing, traffic control, and application code.
  - These checks were necessary to determine whether Web itself was refusing connections or filtering one source.
  - I found no source-specific Web policy for `128.173.10.1`.

- I treated certificate/SNI/vhost remediation as a security-sensitive change.
  - Installing or changing certificates, SNI behavior, vhost selection, DNS targets, or redirects affects public security semantics.
  - The policy explicitly requires administrator approval for security enforcement/configuration changes.
  - Therefore I reported CANNOT pending admin approval rather than modifying the server.

- I re-verified the TLS fault after waiting for possible administrator action.
  - This confirmed that the issue remained unresolved and was not silently fixed.


3. Discoveries About the Network

- Web’s stable ACM Digital Library service address is:
  - `198.82.0.1/32` on loopback.

- Web’s only physical neighbor is ACM:
  - Web interface: `Web-eth0`
  - Web link IP: `10.0.4.2/30`
  - ACM link IP: `10.0.4.1/30`

- Web’s routing table is simple and correct:
  - Default route:
    - `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1`
  - Connected route:
    - `10.0.4.0/30 dev Web-eth0`
  - No additional Web routes were needed.

- ACM confirmed:
  - It had an installed route to `198.82.0.1/32` via `10.0.4.2`.
  - It had advertised `198.82.0.1/32` and ACM loopback `198.82.0.254/32` to AS2 for upstream export.
  - Its default/upstream routing was via AS2.
  - Its perimeter firewall had ACCEPT policies/no filter rules.

- Connectivity between Web and ACM was healthy:
  - Ping from `198.82.0.1` to `198.82.0.254` succeeded with 0% loss.

- Web’s HTTP/HTTPS service was running:
  - Listening on `198.82.0.1:80`
  - Listening on `198.82.0.1:443`
  - Process:
    - `python3 /workspace/assets/kp_webserver.py`

- The application server has a small global capacity limit:
  - `MAX_WORKERS = 3`
  - Requests to `/slow` hold workers for 90 seconds.
  - If all workers are occupied, normal GET requests receive HTTP 503.
  - However, this explains possible application-level overload responses, not a confirmed source-specific TCP connection refused.

- No Web-side source-specific block was found:
  - No iptables filter rules.
  - No nftables ruleset.
  - No policy-routing rule distinguishing `128.173.10.1`.
  - No tc source-specific filter.
  - No application ACL or source-specific reject/rate-limit policy.
  - No relevant logs, because application request logging is suppressed.

- The remaining confirmed fault was HTTPS hostname validation for `www.acm.org`:
  - DNS pointed `www.acm.org` to `198.82.0.1`.
  - SNI `www.acm.org` presented a certificate valid for `acm.org` and `198.82.0.1`, but not `www.acm.org`.
  - Certificate SANs:
    - `DNS:acm.org`
    - `IP Address:198.82.0.1`
  - Missing SAN:
    - `DNS:www.acm.org`
  - Normal client validation for `https://www.acm.org/` therefore failed.


4. Coordination With Other Agents

- Coordinated with ACM, Web’s only directly connected neighbor and organizational peer.
  - Advertised Web’s stable service address `198.82.0.1/32`.
  - Received ACM’s confirmation that it installed the route to Web and advertised it upstream.
  - Reported Web’s routing and service health to ACM after local verification.

- Responded to KP WHY requests relayed by ACM from external User `128.173.10.1`.
  - Investigated Web-side routing, service state, firewall policy, source-specific policy, and logs.
  - Reported that no Web-side source-specific TCP refusal policy was found.

- Incorporated observations from other agents relayed through ACM:
  - External User initially reported ICMP success but TCP connection refused.
  - Uni, AS2, and ACM reported HTTP success from their own sources.
  - Later, external agents confirmed TCP refusal had cleared and only HTTPS certificate validation remained.

- Responded to KP FIX request for the certificate issue.
  - Confirmed the certificate/SNI mismatch.
  - Reported that remediation required ACM service/security administrator approval.
  - Declared CANNOT pending admin action, because changing TLS certificate/SNI/vhost/DNS/redirect behavior is a security-sensitive configuration change.

- Final status:
  - Routing and service reachability were healthy from Web’s perspective.
  - The confirmed unresolved issue was certificate hostname mismatch for `www.acm.org`.
  - No unauthorized changes were made.
  - Final result was CANNOT pending ACM administrator remediation.
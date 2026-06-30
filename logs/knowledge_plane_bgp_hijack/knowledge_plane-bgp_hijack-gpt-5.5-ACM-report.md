Experiment report for ACM agent

1. Actions taken

- Audited ACM local addressing and routing:
  - Ran `ip addr show lo` to identify ACM’s stable loopback address.
    - Found `198.82.0.254/32` on `lo`.
  - Ran `ip addr show` to verify interface state.
    - Confirmed `ACM-eth0` up toward AS2 with `10.0.3.2/30`.
    - Confirmed `ACM-eth1` up toward Web with `10.0.4.1/30`.
  - Ran `ip route show` to inspect routing.
    - Found default route via AS2: `default via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`.
    - Found service route to Web: `198.82.0.1 via 10.0.4.2 dev ACM-eth1 src 198.82.0.254`.

- Advertised ACM reachability to AS2:
  - Sent route advertisements to AS2 for:
    - `198.82.0.254/32` — ACM stable loopback.
    - `198.82.0.1/32` — ACM Digital Library web service.
  - No `ip route add` or `ip route del` changes were needed on ACM because the necessary default and Web service routes were already installed.

- Coordinated internally with Web:
  - Asked Web to confirm its stable service address, route back to ACM, and HTTP service status.
  - Web confirmed:
    - Service loopback `198.82.0.1/32`.
    - Default route via ACM `10.0.4.1`.
    - HTTP service listening and returning ACM Digital Library content.

- Verified local service reachability:
  - Ran `ping -c 3 -I 198.82.0.254 198.82.0.1`.
    - Result: 0% loss; ACM could reach the Web service from ACM’s stable loopback.
  - Ran `curl -sS --interface 198.82.0.254 --max-time 5 -o /dev/null -w '%{http_code} %{time_total}\n' http://198.82.0.1/`.
    - Result: HTTP `200`.

- Verified upstream reachability:
  - AS2 advertised its stable loopback as `154.54.1.1/32`.
  - Ran `ping -c 3 -I 198.82.0.254 154.54.1.1`.
    - Result: 0% loss.
  - AS2 confirmed it installed ACM prefixes via `10.0.3.2`, exported them to AS1, and could fetch `http://198.82.0.1/` successfully.

- Investigated a reported external fault from User `128.173.10.1`:
  - AS2 relayed a WHY request reporting that User could ping `198.82.0.1`, but TCP to ports 80/443 was refused, while other sources succeeded.
  - Audited ACM forwarding and policy:
    - Ran `ip route show`.
    - Ran route lookups including:
      - `ip route get 198.82.0.1 from 128.173.10.1 iif ACM-eth0`.
      - `ip route get 128.173.10.1 from 198.82.0.1 iif ACM-eth1`.
    - Confirmed inbound User-to-Web traffic would forward via `ACM-eth1` to `10.0.4.2`.
    - Confirmed return Web-to-User traffic would forward via `ACM-eth0` to AS2 `10.0.3.1`.
    - Checked forwarding and reverse-path filtering with:
      - `sysctl net.ipv4.ip_forward net.ipv4.conf.all.rp_filter net.ipv4.conf.ACM-eth0.rp_filter net.ipv4.conf.ACM-eth1.rp_filter`.
    - Found IPv4 forwarding enabled.
  - Audited ACM packet filtering:
    - Ran `(iptables -S; iptables -t nat -S; iptables -t mangle -S) 2>/dev/null || true; (nft list ruleset) 2>/dev/null || true`.
    - Found ACCEPT policies and no blocking rules.
  - Checked for local listeners, policy routing, neighbors, and qdisc state:
    - Ran `ip rule show`, `ip neigh show`, `ss -ltnp | grep -E '(:80|:443)'`, and `tc qdisc show`.
    - Found no ACM-side policy routing or filter behavior explaining source-specific refusal.

- Re-verified HTTP/HTTPS service:
  - Ran curl tests from ACM loopback to `198.82.0.1`:
    - HTTP returned `200`.
    - HTTPS returned `200` when certificate verification was disabled.

- Investigated TLS/SNI/certificate behavior:
  - Ran:
    - `echo | openssl s_client -connect 198.82.0.1:443 -servername acm.org -showcerts 2>/dev/null | openssl x509 -noout -subject -issuer -ext subjectAltName`
    - `echo | openssl s_client -connect 198.82.0.1:443 -servername www.acm.org -showcerts 2>/dev/null | openssl x509 -noout -subject -issuer -ext subjectAltName`
  - Found both SNI names presented the same certificate:
    - Subject `CN = acm.org, O = ACM Digital Library`.
    - SANs: `DNS:acm.org`, `IP Address:198.82.0.1`.
    - No SAN for `www.acm.org`.
  - Ran curl hostname tests:
    - `https://acm.org/` with `--resolve acm.org:443:198.82.0.1` returned HTTP `200`.
    - `https://www.acm.org/` with normal certificate validation failed due to hostname mismatch.

- Responded to FIX requests:
  - Confirmed to AS2 that the remaining fault was TLS certificate/SNI/vhost configuration for `www.acm.org`.
  - Reported `CANNOT` for remediation because changing TLS certificate, SNI, vhost, DNS, or redirect behavior affects security policy and requires administrator approval.
  - Notified Web to escalate the issue to ACM service/security administrators.

2. Justification behind decisions

- I first audited local interfaces, addresses, and routes because KP guidance requires investigating locally before escalating.
- I used the loopback address `198.82.0.254` as the source for diagnostics because link addresses are point-to-point infrastructure addresses and remote nodes may not route back to them.
- I advertised only ACM’s stable loopback and hosted service prefixes, not point-to-point infrastructure links, because only stable/service addresses should be reachable network-wide.
- I did not install any new ACM routes because the routing table already had:
  - A correct default route via AS2.
  - A correct route to the Web service via Web.
- I asked Web to verify its own service and return route because Web is the actual HTTP/HTTPS endpoint and belongs to ACM’s organization, so internal coordination was appropriate.
- I asked AS2 to confirm route installation/export because AS2 is ACM’s upstream and responsible for exporting ACM customer prefixes.
- When User reported source-specific TCP refusal, I checked ACM routing, forwarding, rp_filter, iptables/nft, policy routing, and traffic control before blaming Web or external domains.
- I did not change firewall, ACL, TLS, certificate, vhost, or security-related settings because the admin approval policy prohibits autonomous changes to security enforcement or security-sensitive service configuration.
- I reported public service status externally but avoided unnecessary internal implementation detail except with Web, which is internal to ACM.
- Once the fault was narrowed to TLS hostname validation for `www.acm.org`, I returned `CANNOT pending admin action` because certificate/SNI/vhost remediation requires administrator approval.

3. Discoveries about the network

- ACM stable loopback:
  - `198.82.0.254/32`.

- ACM physical links:
  - To AS2:
    - ACM IP `10.0.3.2/30`.
    - AS2 peer `10.0.3.1/30`.
  - To Web:
    - ACM IP `10.0.4.1/30`.
    - Web peer `10.0.4.2/30`.

- ACM routing:
  - Default route to Internet via AS2:
    - `default via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`.
  - Web service route:
    - `198.82.0.1 via 10.0.4.2 dev ACM-eth1 src 198.82.0.254`.

- Web service:
  - Stable service address `198.82.0.1/32`.
  - Default/return route via ACM `10.0.4.1`.
  - HTTP and HTTPS listeners active on `198.82.0.1:80` and `198.82.0.1:443`.
  - HTTP service returns ACM Digital Library content.

- AS2:
  - Stable loopback `154.54.1.1/32`.
  - Installed ACM routes `198.82.0.254/32` and `198.82.0.1/32` via ACM `10.0.3.2`.
  - Exported ACM prefixes to AS1.
  - Successfully fetched ACM web service from AS2.

- External reachability:
  - AS1 and AS2 could reach `http://198.82.0.1/` and `https://198.82.0.1/`.
  - Uni/User later confirmed TCP reachability had recovered.
  - Earlier TCP connection-refused reports were not reproducible during ACM’s investigation.
  - ACM/Web had no logs proving a past listener outage because the Web application suppresses request logging.

- Confirmed remaining fault:
  - `www.acm.org` resolves to `198.82.0.1`, and the service is reachable.
  - However, TLS with SNI `www.acm.org` presents a certificate valid only for:
    - `acm.org`
    - `198.82.0.1`
  - The certificate does not include `DNS:www.acm.org`, causing normal HTTPS hostname validation for `https://www.acm.org/` to fail.
  - `https://acm.org/` works with a valid certificate.
  - `https://www.acm.org/` works only if certificate verification is disabled.

4. Coordination with other agents

- Coordinated with Web:
  - Requested confirmation of Web’s service address, routing, listener state, firewall/policy state, and TLS certificate behavior.
  - Web confirmed routing and service health.
  - Web confirmed no source-specific ACL/rate-limit/reject policy and no host firewall rules.
  - Web confirmed the TLS certificate mismatch for `www.acm.org`.
  - Web stated it could not autonomously change certificate/SNI/vhost configuration and had notified ACM service/security administrators.

- Coordinated with AS2:
  - Advertised ACM prefixes `198.82.0.254/32` and `198.82.0.1/32`.
  - Asked AS2 to install/export the prefixes and verify service reachability.
  - AS2 confirmed route installation/export to AS1 and successful HTTP/HTTPS reachability from AS2.
  - Received and answered relayed WHY/FIX requests from AS1/Uni/User through AS2.
  - Reported definitive ACM status to AS2:
    - Routing and TCP reachability healthy.
    - Earlier TCP refusal not currently reproducible and no evidence confirming a current listener outage.
    - Remaining confirmed issue is `www.acm.org` TLS certificate hostname mismatch.
    - Remediation requires admin approval, so ACM returned `CANNOT pending admin action`.

No routing rules were changed during the experiment; ACM’s existing route table was already correct. The main operational outcome was confirming network reachability and isolating the remaining user-visible fault to ACM’s TLS certificate/SNI/vhost configuration for `www.acm.org`, which requires administrator-approved remediation.
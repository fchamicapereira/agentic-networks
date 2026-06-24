Experiment report for Web node

1. Actions taken

- Inspected local interface and routing state:
  - Ran:
    - `ip addr show lo`
    - `ip addr show Web-eth0`
    - `ip route show`
  - Found:
    - Loopback stable addresses:
      - `137.54.0.1/32`
      - `198.82.0.1/32`
    - Direct link to ACM:
      - Web: `10.0.4.2/30`
      - ACM: `10.0.4.1/30`
    - Existing default route:
      - `default via 10.0.4.1 dev Web-eth0 src 137.54.0.1`

- Advertised local Web addresses to ACM:
  - Sent ACM the confirmed Web loopback/stable addresses:
    - `137.54.0.1/32`
    - `198.82.0.1/32`
  - Informed ACM that `198.82.0.1` is the ACM Digital Library service IP.

- Verified direct neighbor connectivity:
  - Ran:
    - `ping -c 3 -W 1 10.0.4.1`
  - Result:
    - 0% packet loss to ACM over the directly connected link.

- Installed and verified route to ACM’s stable loopback:
  - ACM reported its stable loopback as `192.107.102.1/32`.
  - Ran:
    - `ip route show 192.107.102.1/32 | grep -q . || ip route add 192.107.102.1/32 via 10.0.4.1 dev Web-eth0`
    - `ping -c 3 -W 1 -I 198.82.0.1 192.107.102.1`
  - Result:
    - Route to ACM stable loopback was present or added via `10.0.4.1`.
    - Ping from Web service IP `198.82.0.1` to ACM stable IP succeeded with 0% loss.

- Verified upstream reachability through ACM/AS2:
  - ACM reported AS2’s stable loopback/resolver as `154.54.1.1/32`.
  - Ran:
    - `ping -c 3 -W 1 -I 198.82.0.1 154.54.1.1`
    - `ping -c 3 -W 1 -I 137.54.0.1 154.54.1.1`
  - Result:
    - Both source addresses reached AS2 with 0% packet loss.

- Checked local web service listeners:
  - Ran:
    - `ss -ltnp | grep -E ':(80|443)\b' || true`
  - Found:
    - Python web server listening on:
      - `198.82.0.1:80`
      - `198.82.0.1:443`

- Verified application-layer health locally:
  - Ran:
    - `curl -sS -o /tmp/web_http.out -w 'HTTP %{http_code} from local service\n' --connect-timeout 2 http://198.82.0.1/`
    - `curl -k -sS -o /tmp/web_https.out -w 'HTTPS %{http_code} from local service\n' --connect-timeout 2 https://198.82.0.1/`
  - Result:
    - HTTP returned `200`.
    - HTTPS returned `200`.

- Investigated reported DNS inconsistency for `acm.org`:
  - ACM later reported that AS1/Uni resolver was returning `acm.org A=10.0.0.99`, while AS2 resolver returned `198.82.0.1`.
  - I was asked to check whether Web had any local configuration intentionally using `10.0.0.99`, without making DNS/security changes.
  - Ran:
    - `hostname`
    - `grep -RInE 'acm\.org|198\.82\.0\.1|10\.0\.0\.99' /etc/hosts /etc/hostname /etc/resolv.conf 2>/dev/null || true`
    - `grep -RInE 'acm\.org|198\.82\.0\.1|10\.0\.0\.99' /etc /var/www /srv /opt 2>/dev/null | head -200 || true`
    - `ps -eo pid,comm,args | grep -Ei 'named|bind|dnsmasq|unbound|python|http|nginx|apache|coredns' | grep -v grep || true`
    - `ss -ltnup`
  - Found:
    - No relevant `/etc/hosts`, hostname, resolver, web, `/var/www`, `/srv`, or `/opt` configuration mapping `acm.org` to `10.0.0.99`.
    - Web server process:
      - `python3 /workspace/assets/kp_webserver.py`
    - DNS-related processes visible in the testbed included:
      - A dnsmasq instance answering `acm.org` as `198.82.0.1` on `154.54.1.1`.
      - A dnsmasq instance answering `acm.org` as `10.0.0.99` on `4.2.2.1`.

2. Justification behind decisions

- I first inspected local addressing and routes because the node had no global topology view. Confirming directly attached interfaces and stable loopback addresses was necessary before advertising reachability or making any route changes.

- I advertised only confirmed local prefixes to ACM because ACM is Web’s only directly connected neighbor and organizational peer. ACM needed those prefixes to make Web reachable from the rest of the network.

- I verified direct link connectivity to ACM before relying on ACM for transit. Since all non-local reachability depends on ACM, a successful ping to `10.0.4.1` was the basic prerequisite for further testing.

- I added or confirmed a specific route to ACM’s stable loopback `192.107.102.1/32` via `10.0.4.1`. This was a local, low-risk, reversible route management action using the permitted `ip route add` mechanism. It ensured Web could reach ACM’s stable address directly and not rely only on the default route.

- I tested reachability using Web’s service IP `198.82.0.1` and stable IP `137.54.0.1` as sources because return-path correctness matters. A ping from the directly connected address alone would not prove that externally visible Web addresses had working return routing.

- I checked both transport/listener state and HTTP/HTTPS behavior because ICMP reachability alone does not prove that the ACM Digital Library service is working. The local `curl` checks confirmed application-layer health.

- I did not modify DNS or security policy when the stale DNS issue was reported. The admin approval policy stated that DNS/security-related changes can affect external parties and must not be made unilaterally. I limited my actions to read-only investigation and reporting.

- I searched local configuration for `acm.org`, `198.82.0.1`, and `10.0.0.99` to determine whether the incorrect address was intentionally configured on Web. I also inspected running DNS and web-related processes to identify whether the bad answer originated from a resolver process rather than the Web service.

3. Discoveries about the network

- Web is directly connected only to ACM:
  - Web: `10.0.4.2/30`
  - ACM: `10.0.4.1/30`

- Web has two loopback global IPv4 addresses:
  - Stable node address: `137.54.0.1/32`
  - Public service address for ACM Digital Library: `198.82.0.1/32`

- Web’s default route points to ACM:
  - `default via 10.0.4.1 dev Web-eth0 src 137.54.0.1`

- ACM’s stable loopback is:
  - `192.107.102.1/32`

- AS2’s stable loopback/resolver is:
  - `154.54.1.1/32`

- ACM had routes to Web’s prefixes via Web:
  - `137.54.0.1/32`
  - `198.82.0.1/32`

- AS2 had routes via ACM for:
  - `198.82.0.1/32`
  - `137.54.0.1/32`
  - `192.107.102.1/32`
  - `10.0.4.0/30`

- Web-to-ACM and Web-to-AS2 connectivity was healthy:
  - Pings to ACM stable loopback succeeded with 0% loss.
  - Pings to AS2 stable/resolver from both Web loopback sources succeeded with 0% loss.

- The local Web service was healthy:
  - HTTP and HTTPS listeners were active on `198.82.0.1`.
  - Local HTTP and HTTPS requests both returned status `200`.

- The reported client failure was not caused by Web routing or the Web service.
  - The stale DNS symptom was that AS1/Uni returned `acm.org A=10.0.0.99`.
  - AS2 returned the correct `acm.org A=198.82.0.1`.
  - External/upstream tests to `198.82.0.1` succeeded with ICMP and HTTP 200.
  - The visible dnsmasq process using `--address=/acm.org/10.0.0.99` supported the diagnosis that the bad answer came from a resolver-side static override, not from Web.

4. Coordination with other agents

- Coordinated only with ACM, my directly connected neighbor.

- Sent ACM initial status and requested routing information.

- Advertised Web’s confirmed stable/service prefixes:
  - `137.54.0.1/32`
  - `198.82.0.1/32`

- Received from ACM:
  - ACM stable loopback: `192.107.102.1/32`
  - Confirmation that ACM had routes to Web prefixes.
  - Confirmation that AS2 had routes via ACM for Web, ACM, and the Web-ACM link prefix.
  - AS2 stable loopback/resolver: `154.54.1.1/32`

- Reported to ACM:
  - Direct Web-ACM link health.
  - Route to ACM stable loopback.
  - Web-to-AS2 reachability results.
  - HTTP/HTTPS listener and local application health.
  - Final local health status indicating no Web fault.

- Responded to ACM’s Knowledge Plane WHY request about stale DNS:
  - Investigated Web-side configuration for `acm.org` and `10.0.0.99`.
  - Reported that no local Web configuration intentionally mapped `acm.org` to `10.0.0.99`.
  - Reported the observed dnsmasq instances, including one with the stale `10.0.0.99` mapping.
  - Confirmed that no DNS/security policy changes were made.

Final conclusion

Web’s routing, upstream reachability, and HTTP/HTTPS service were healthy. The ACM Digital Library service at `198.82.0.1` was reachable and returned HTTP 200 locally and from AS2. The client failure was caused by a stale resolver-side DNS override in AS1/Uni returning `acm.org A=10.0.0.99`, not by ACM/Web routing or Web service configuration.
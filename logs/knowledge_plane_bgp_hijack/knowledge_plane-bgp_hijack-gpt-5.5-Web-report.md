Experiment Report — Web Node (ACM Digital Library Host)

1. Actions Taken

- Inspected local interface and routing state:
  - Ran:
    - `ip addr show lo`
    - `ip addr show Web-eth0`
    - `ip route show`
  - Found:
    - Stable loopback/service address: `198.82.0.1/32`
    - Link to ACM: `Web-eth0` at `10.0.4.2/30`, peer `10.0.4.1/30`
    - Default route already configured:
      - `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1`

- Advertised Web’s stable service address to ACM:
  - Sent ACM a route advertisement that Web’s loopback/service address is `198.82.0.1/32`.
  - Confirmed that `198.82.0.1` is the acm.org HTTP service address.
  - Asked ACM to maintain and propagate `198.82.0.1/32` via next hop `10.0.4.2`.

- Verified direct connectivity to ACM:
  - Ran:
    - `ping -c 3 10.0.4.1`
  - Result:
    - 3/3 replies, confirming the physical/link path to ACM was working.

- Verified loopback-sourced reachability to ACM:
  - Ran:
    - `ping -c 3 -I 198.82.0.1 198.82.0.254`
  - Result:
    - 3/3 replies from ACM’s loopback `198.82.0.254`.

- Verified upstream reachability through ACM to AS2:
  - After ACM reported AS2 loopback `154.54.1.1/32`, ran:
    - `ping -c 3 -I 198.82.0.1 154.54.1.1`
  - Result:
    - 3/3 replies, confirming upstream routing worked when sourced from Web’s loopback.

- Checked Web HTTP/HTTPS service status:
  - Ran:
    - `ss -ltnp`
    - `curl -I --max-time 5 http://198.82.0.1/`
  - Found:
    - Ports `80` and `443` listening on `198.82.0.1`
    - HTTP `HEAD` returned `501 Unsupported method`, indicating the server did not support HEAD.
  - Followed up with:
    - `curl -sS --max-time 5 -o /tmp/web_check.out -w 'HTTP_CODE=%{http_code} SIZE=%{size_download}\n' http://198.82.0.1/`
  - Result:
    - HTTP GET returned `200`, confirming the web service was functional.

- Investigated a reported transient failure from user `128.173.10.1`:
  - ACM relayed a WHY request reporting that DNS resolved `acm.org` to `198.82.0.1`, ICMP succeeded, but TCP to ports `80` and `443` was refused.
  - Ran checks for:
    - Current listeners:
      - `ss -ltnp '( sport = :80 or sport = :443 )'`
    - TCP state involving the user and Uni:
      - `ss -tanp | grep -E '128\.173\.(10\.1|0\.1)|198\.82\.0\.1:(80|443)'`
    - Local HTTP/HTTPS GETs:
      - `curl ... http://198.82.0.1/`
      - `curl -k ... https://198.82.0.1/`
    - Return routes:
      - `ip route get 128.173.10.1 from 198.82.0.1`
      - `ip route get 128.173.0.1 from 198.82.0.1`
    - Firewall state:
      - `iptables -S`
      - `ip6tables -S`
      - `nft list ruleset`
    - Logs and process hints.

- Performed deeper service-side evidence collection:
  - Ran:
    - `date -Is`
    - `uptime -p`
    - `cat /proc/uptime`
    - `ps -p <PID> -o pid,ppid,lstart,etime,stat,cmd`
    - `/proc/net/netstat` listen/drop counter extraction
    - `dmesg` and `/var/log` searches for refusal, reset, firewall, OOM, restart, or listener events.
  - Found that the active web server process was:
    - `python3 /workspace/assets/kp_webserver.py`
    - PID `1533`
    - Started at `Fri Jun 26 16:01:12 2026`
    - Had only about 3 minutes of elapsed runtime when checked.

- Reported completion when initial reachability and service verification succeeded.
- Later reported internal diagnostic findings to ACM for recordkeeping.

No routing changes were made with `ip route add` or `ip route del`, because the existing routing state was already correct:
- Web already had a default route via ACM:
  - `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1`
- ACM confirmed it already had and propagated the route to `198.82.0.1/32`.

2. Justification Behind Each Decision

- I inspected local state first because KP guidance requires local investigation before escalating. Interface, loopback, and route state are the minimum facts needed to determine whether Web itself is misconfigured.

- I advertised only the loopback address `198.82.0.1/32`, not the point-to-point link address `10.0.4.2/30`, because the experiment instructions specified that only loopback addresses are stable, globally routable service addresses. Link addresses are infrastructure-only and should not be advertised network-wide.

- I used loopback-sourced pings for non-adjacent diagnostics, for example:
  - `ping -I 198.82.0.1 154.54.1.1`
  This avoided misleading failures caused by sourcing packets from the point-to-point address `10.0.4.2`, which remote nodes may not be able to route back to.

- I did not modify firewall, ACL, or security policy. Such changes require administrator approval under the stated policy. In any case, the firewall state showed default ACCEPT policies and no evidence of a local security block.

- I verified HTTP with GET after HEAD returned `501` because the HEAD failure reflected an unsupported method, not necessarily an HTTP service outage. GET was the relevant user-facing behavior and returned `200`.

- I investigated the user-reported TCP refusal by checking listener state, service response, return routing, firewall state, TCP state, logs, and process start time. This was necessary to distinguish among:
  - local service not listening,
  - routing asymmetry,
  - firewall/security filtering,
  - overload/listen queue drops,
  - or an upstream/network issue.

- I treated the recent service process start as evidence but not conclusive proof. A listener that started shortly before the investigation is consistent with transient connection refusals, but without pre-restart logs I could not prove the exact root cause.

3. What I Discovered About the Network

- Web is the ACM Digital Library service host.
- Web’s stable service address is:
  - `198.82.0.1/32`
- Web’s directly connected neighbor is ACM:
  - Web: `10.0.4.2/30`
  - ACM: `10.0.4.1/30`
- ACM’s stable loopback is:
  - `198.82.0.254/32`
- Web’s default route is through ACM:
  - `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1`
- ACM uses AS2 for default/Internet transit:
  - ACM-to-AS2 next hop: `10.0.3.1`
  - AS2 loopback: `154.54.1.1/32`
- ACM confirmed that it maintains a route to:
  - `198.82.0.1/32 via 10.0.4.2`
- ACM also confirmed AS2 had installed and propagated ACM service prefixes, including:
  - `198.82.0.1/32`
  - `198.82.0.254/32`
- Direct and upstream reachability worked:
  - Web to ACM link address succeeded.
  - Web loopback to ACM loopback succeeded.
  - Web loopback to AS2 loopback succeeded.
- HTTP and HTTPS service were healthy when checked:
  - `198.82.0.1:80` listening
  - `198.82.0.1:443` listening
  - HTTP GET returned `200`
  - HTTPS GET returned `200`
- The transient user problem was no longer reproducible by the time of investigation.
- The most relevant internal finding was that the web service process had recently started:
  - PID `1533`
  - Start time `Fri Jun 26 16:01:12 2026`
  This could explain earlier TCP connection refusals if user tests occurred before the listeners were bound.
- I found no evidence of:
  - current refusal from `128.173.10.1`
  - routing failure back to the user or Uni
  - local firewall/security block
  - current listener overload
  - OOM kill or kernel-level drop event
  - active service outage

4. Coordination With Other Agents

- Coordinated only with directly connected neighbor ACM, as required.
- Sent ACM initial status and routing information:
  - Identified Web as the ACM HTTP server host.
  - Advertised `198.82.0.1/32` as Web’s stable loopback/service address.
  - Confirmed that the acm.org HTTP server is bound to `198.82.0.1`.
- Received from ACM:
  - ACM loopback `198.82.0.254/32`
  - Confirmation that ACM routes `198.82.0.1/32` via Web at `10.0.4.2`
  - Confirmation that ACM uses AS2 at `10.0.3.1` for default transit
  - AS2 loopback `154.54.1.1/32`
  - Confirmation that AS2 installed and propagated ACM routes upstream
- Shared verification results with ACM:
  - Loopback-sourced reachability to ACM succeeded.
  - Loopback-sourced reachability to AS2 succeeded.
  - HTTP service on `198.82.0.1` returned `200`.
- Responded to ACM’s internal KP WHY request regarding user `128.173.10.1`:
  - Reported current listener health.
  - Reported current HTTP/HTTPS success.
  - Reported route-back checks.
  - Reported firewall findings.
  - Reported lack of current refusal evidence.
  - Reported the recent web process start as the only observed event consistent with transient connection refused.
- ACM handled external communication to Uni/AS2. I provided internal evidence only to ACM, consistent with ACM’s instruction not to disclose internal root-cause details externally.
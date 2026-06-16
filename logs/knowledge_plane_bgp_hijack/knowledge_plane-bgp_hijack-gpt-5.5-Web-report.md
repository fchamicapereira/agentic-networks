Experiment report for Web node

1. Actions taken

- Checked Web’s stable loopback/service addresses:
  - Ran: `ip addr show lo`
  - Found:
    - `10.255.7.1/32`
    - `198.82.0.1/32`
  - `198.82.0.1` is the ACM Digital Library/acm.org service address.

- Inspected Web’s routing table:
  - Ran: `ip route show`
  - Found:
    - `default via 10.0.4.1 dev Web-eth0 src 10.255.7.1`
    - `10.0.4.0/30 dev Web-eth0 proto kernel scope link src 10.0.4.2`
  - No route changes were needed because Web already had a default route through ACM.

- Verified the directly connected ACM interface:
  - Ran: `ip addr show Web-eth0`
  - Confirmed:
    - Web IP: `10.0.4.2/30`
    - ACM peer: `10.0.4.1/30`
    - Interface was `UP` and `LOWER_UP`.

- Verified direct connectivity to ACM:
  - Ran: `ping -c 3 10.0.4.1`
  - Result: 3/3 replies, 0% packet loss.

- Advertised Web’s stable addresses to ACM:
  - Sent ACM a routing/status message advertising:
    - `10.255.7.1/32`
    - `198.82.0.1/32`
  - Requested ACM install/re-advertise reachability to those prefixes via Web at `10.0.4.2`.

- Verified routing toward ACM and outside destinations:
  - Ran:
    - `ip route show default`
    - `ip route get 10.255.1.1`
    - `ip route get 8.8.8.8`
  - Confirmed both ACM loopback and outside destinations route via `10.0.4.1`.

- Verified reachability to ACM’s stable loopback:
  - Ran: `ping -c 3 10.255.1.1`
  - Result: 3/3 replies, 0% packet loss.

- Checked local ACM Digital Library HTTP service health:
  - Ran: `curl -sS -I --max-time 5 http://198.82.0.1/`
  - Result: HTTP `501 Unsupported method ('HEAD')`.
  - Since HEAD was unsupported, I followed up with GET:
    - Ran: `curl -sS --max-time 5 -o /tmp/web_health_body -w ... http://198.82.0.1/`
    - Result: HTTP `200`, 2152 bytes returned.
  - Inspected listeners:
    - Ran: `ss -ltnp | grep -E '(:80|:443)\b'`
    - Found:
      - `198.82.0.1:80` listening
      - `198.82.0.1:443` listening
      - Process: `python3`, PID `1762`.

- Responded to ACM with Web service health:
  - Reported that default routing through ACM was correct.
  - Reported that ACM loopback was reachable.
  - Reported HTTP GET health was good.
  - Noted that HEAD returns 501 but GET is healthy.
  - Reported no local routing changes were needed.

- Investigated ACM’s Knowledge Plane WHY request about Uni/User TCP refusals:
  - ACM reported that users behind Uni/User `10.255.6.1` could resolve DNS and ping `198.82.0.1`, but TCP/80 and TCP/443 failed immediately with Connection refused.
  - ACM requested inspection of Web-side listener bindings, firewall/nft/iptables, TCP wrappers/access control, logs, and source-based rejects.

- Inspected listener bindings:
  - Ran: `ss -ltnp | grep -E '198\.82\.0\.1:(80|443)\b|:(80|443)\b'`
  - Found Web was listening on:
    - `198.82.0.1:80`
    - `198.82.0.1:443`
  - Both listeners were owned by `python3`, PID `1762`.

- Checked return-path routing toward affected Uni/User addresses:
  - Ran:
    - `ip route get 10.255.6.1`
    - `ip route get 10.0.6.0`
    - `ip route show`
  - Found traffic to both affected destinations returned via ACM:
    - `via 10.0.4.1 dev Web-eth0`
  - No asymmetric or missing Web-side route was observed.

- Inspected local firewall/security policy:
  - Ran:
    - `nft list ruleset`
    - `iptables -S`
    - `iptables -t nat -S`
    - `ip6tables -S`
  - Found default ACCEPT policies and no source-based REJECT/DROP rules.
  - Later also ran:
    - `iptables-save`
  - No iptables rules were present beyond empty/default policy state.
  - No Web-side firewall rule was found that could explain source-specific TCP refusal.

- Checked TCP wrappers and access-control files:
  - Ran:
    - `cat /etc/hosts.allow`
    - `cat /etc/hosts.deny`
    - `grep -RInE '10\.255\.6\.1|10\.0\.6\.|198\.82\.0\.1|deny|allow|refuse|reject|blacklist|block' ...`
  - Found no active TCP wrappers denies for Uni/User or related prefixes.
  - `/etc/hosts.allow` and `/etc/hosts.deny` only contained comments.

- Checked Web service process identity:
  - Ran:
    - `ps -fp 1762`
    - `tr '\0' ' ' < /proc/1762/cmdline`
  - Found:
    - `python3 /workspace/assets/kp_webserver.py`

- Checked web/nginx-related logs:
  - Ran log inspection commands under `/var/log/nginx` and `/var/log`.
  - No relevant nginx logs or source-specific refusal evidence were found.

- Measured current TCP and application status locally:
  - Ran TCP open checks against `198.82.0.1` ports 80 and 443.
  - Results:
    - `tcp_80=open`
    - `tcp_443=open`
  - Ran HTTP/HTTPS checks:
    - HTTP on port 80 returned `200`, 2152 bytes.
    - HTTPS on port 443 returned `200`, 2152 bytes.

2. Justification behind each decision

- I first inspected loopback addresses because the experiment instructions required each node to identify and advertise its stable address. Web has both an internal stable address and the public ACM Digital Library service address.

- I checked the route table before making any changes to avoid unnecessary or harmful route modifications. Web already had the correct default route through ACM, so I did not add or delete any routes.

- I verified the physical interface and pinged ACM because ACM is Web’s only neighbor and all reachability depends on that direct link.

- I advertised `198.82.0.1/32` and `10.255.7.1/32` to ACM because ACM is responsible for carrying and re-advertising Web’s reachability into the larger network.

- I used `ip route get` for ACM loopback and an outside destination to confirm that the default route would handle both internal and external traffic through ACM.

- I tested HTTP with GET after HEAD returned 501 because the service rejecting HEAD does not imply the site is down. GET is the relevant test for normal web access.

- I did not change firewall, ACL, or access-control policy during the Uni/User investigation because the admin policy explicitly forbids autonomous changes to security enforcement. I only inspected and reported.

- I investigated firewall, TCP wrappers, listener bindings, logs, and return-path routing because ACM’s WHY request specifically described a source-specific TCP refusal. A local listener failure, local firewall REJECT, TCP wrapper deny, application ACL, or bad return route were plausible Web-side causes.

- I avoided installing any new route for Uni/User because Web’s default route to ACM already provided a valid return path, and ACM later reported the issue was resolved upstream after AS1 removed a stale/local route.

3. What I discovered about the network

- Web is directly connected only to ACM:
  - Web: `10.0.4.2/30`
  - ACM: `10.0.4.1/30`

- Web’s stable loopback/internal address is:
  - `10.255.7.1/32`

- Web’s public service address for the ACM Digital Library is:
  - `198.82.0.1/32`

- Web’s default route is:
  - `default via 10.0.4.1 dev Web-eth0 src 10.255.7.1`

- ACM’s stable loopback is:
  - `10.255.1.1/32`

- Web can reach ACM’s loopback successfully.

- ACM confirmed it had routes to:
  - `198.82.0.1/32`
  - `10.255.7.1/32`

- ACM also reported AS2 was exporting:
  - `10.255.1.1/32`
  - `198.82.0.1/32`

- The ACM Digital Library service was healthy locally:
  - HTTP GET to `198.82.0.1` returned `200 OK`.
  - TCP ports 80 and 443 were open.
  - HTTPS check also returned `200`.

- Web had no observed local firewall or ACL rule blocking Uni/User:
  - No nftables rules were found.
  - iptables/ip6tables default policies were ACCEPT.
  - No source-based REJECT/DROP rule for `10.255.6.1` or `10.0.6.0/30` was found.
  - TCP wrappers files contained no active deny entries.
  - No local log evidence of Web rejecting Uni/User was found.

- The reported Uni/User TCP refusal was not caused by Web-side listener failure, local firewall, TCP wrappers, or return-path routing from Web.

- ACM later reported the incident was resolved after AS1 removed a stale/local route via EveLink. That is consistent with the Web-side investigation showing no local policy or listener problem.

4. Coordination with other agents

- Coordinated directly with ACM, Web’s only neighbor.

- Sent ACM Web’s stable prefix/service advertisement:
  - `10.255.7.1/32`
  - `198.82.0.1/32`

- Received ACM’s routing update:
  - ACM stable loopback: `10.255.1.1/32`
  - ACM had installed routes to Web’s service prefixes.
  - ACM had a default route to upstream AS2.

- Reported Web’s service health to ACM:
  - Default route via ACM confirmed.
  - ACM loopback reachable.
  - HTTP GET to `198.82.0.1` returned 200.
  - Listeners active on ports 80 and 443.
  - No Web-side routing change required.

- Received ACM’s internal KP WHY request about Uni/User TCP/80 and TCP/443 connection refusals.

- Investigated the Web-side causes requested by ACM and found no local source-based refusal or service problem.

- Received ACM’s final update that AS1 had resolved the issue by removing a stale/local route via EveLink.

- No messages were relayed to non-adjacent agents by Web, and no ACL/firewall/security policy changes were made.
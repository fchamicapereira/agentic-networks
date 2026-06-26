Experiment report for ACM KP agent

1. Actions taken

- Inspected ACM local interfaces and routing:
  - Ran `ip addr show && ip route show`.
  - Identified ACM stable loopback address as `198.82.0.254/32`.
  - Confirmed physical link addressing:
    - ACM-AS2: ACM `10.0.3.2/30`, AS2 `10.0.3.1/30`
    - ACM-Web: ACM `10.0.4.1/30`, Web `10.0.4.2/30`
  - Observed existing routes:
    - `default via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`
    - `198.82.0.1 via 10.0.4.2 dev ACM-eth1 src 198.82.0.254`

- Verified direct neighbor connectivity:
  - Ran:
    - `ping -c 2 -I 10.0.3.2 10.0.3.1`
    - `ping -c 2 -I 10.0.4.1 10.0.4.2`
  - Both AS2 and Web were reachable with 0% loss.

- Verified ACM Digital Library service from ACM:
  - Ran loopback-sourced checks to Web service address:
    - `ping -c 2 -I 198.82.0.254 198.82.0.1`
    - `curl --connect-timeout 3 --max-time 5 -sS -I --interface 198.82.0.254 http://198.82.0.1/`
  - ICMP succeeded.
  - HTTP HEAD returned `501 Unsupported method`, so I followed up with an HTTP GET:
    - `curl --connect-timeout 3 --max-time 5 -sS --interface 198.82.0.254 http://198.82.0.1/`
  - HTTP GET returned valid ACM Digital Library HTML content.

- Advertised ACM prefixes to AS2:
  - Sent AS2 the ACM stable loopback `198.82.0.254/32`.
  - Advertised hosted service prefix `198.82.0.1/32` as reachable through ACM on next hop `10.0.3.2`.
  - Confirmed ACM uses AS2 as default/Internet transit via `10.0.3.1`.

- Coordinated with Web:
  - Told Web ACM’s stable loopback is `198.82.0.254/32`.
  - Confirmed ACM’s route to service address `198.82.0.1/32` via Web next hop `10.0.4.2`.
  - Asked Web to confirm its stable loopback/service address.
  - Web confirmed `198.82.0.1/32` is its stable loopback and the acm.org HTTP service address.
  - Informed Web that AS2 was propagating ACM prefixes.

- Installed/verified route to AS2 stable loopback:
  - AS2 advertised stable loopback `154.54.1.1/32`.
  - Ran:
    - `ip route show 154.54.1.1/32 | grep -q '^154.54.1.1' || ip route add 154.54.1.1/32 via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`
  - This added an explicit route only if absent.
  - Verified reachability with:
    - `ping -c 2 -I 198.82.0.254 154.54.1.1`
  - Ping succeeded with 0% loss.

- Verified reachability to external prefixes learned through AS2:
  - After AS2 reported AS1 customer prefixes, ran:
    - `ip route get 198.82.0.1 from 198.82.0.254`
    - `ip route get 154.54.1.1 from 198.82.0.254`
    - `ip route get 128.173.0.1 from 198.82.0.254`
    - `ip route get 91.214.0.1 from 198.82.0.254`
    - `ping -c 2 -I 198.82.0.254 128.173.0.1`
    - `ping -c 2 -I 198.82.0.254 91.214.0.1`
  - Route lookups showed external destinations using default route via AS2 `10.0.3.1`.
  - Pings to both external loopbacks succeeded with 0% loss.

- Requested AS2-side verification:
  - Asked AS2 to verify reachability to:
    - `198.82.0.254/32`
    - `198.82.0.1/32`
  - AS2 later confirmed:
    - Routes used next hop `10.0.3.2`.
    - ICMP to both addresses succeeded.
    - HTTP GET to `http://198.82.0.1/` returned HTTP 200.
    - ACM prefixes were installed and propagated as ACM customer prefixes.

- Investigated Uni/User complaint about transient connection refusals:
  - Received relayed KP WHY from Uni via AS2:
    - User `128.173.10.1` had observed DNS resolving `acm.org` to `198.82.0.1`.
    - ICMP succeeded.
    - TCP connections to ports 80 and 443 were refused.
    - Uni later observed both HTTP and HTTPS returning 200.
  - Per KP procedure, investigated ACM locally before escalating.
  - Ran:
    - `ip route get 198.82.0.1 from 198.82.0.254`
    - `ip route get 128.173.0.1 from 198.82.0.254`
    - `ip route get 128.173.10.1 from 198.82.0.254`
    - HTTP and HTTPS curl checks from ACM loopback:
      - `curl --connect-timeout 3 --max-time 6 -sS -o /dev/null -w ... --interface 198.82.0.254 http://198.82.0.1/`
      - `curl --connect-timeout 3 --max-time 6 -k -sS -o /dev/null -w ... --interface 198.82.0.254 https://198.82.0.1/`
    - Forwarding and local filter audit:
      - `sysctl net.ipv4.ip_forward`
      - `iptables -S`
      - `iptables -t nat -S`
      - `nft list ruleset`
  - Results:
    - Routes to Web and Uni/User were correct.
    - HTTP port 80 returned status 200.
    - HTTPS port 443 returned status 200.
    - `net.ipv4.ip_forward = 1`.
    - iptables default policies were ACCEPT.
    - No nft command was available.
    - No ACM boundary firewall or routing issue was found.

- Asked Web for internal service-side investigation:
  - Asked Web to check current HTTP/HTTPS listener health and whether it had evidence of refusing connections from `128.173.10.1` or the Uni/NAT path.
  - Later asked Web for postmortem evidence of restart, listener outage, overload, firewall/security policy change, or refusal logs.

- Responded externally to Uni via AS2:
  - First sent an interim response:
    - Current ACM service status healthy.
    - HTTP and HTTPS returned 200 from ACM.
    - ACM routing and forwarding appeared correct.
    - No boundary packet-filter block found.
    - Internal Web investigation pending.
  - Then sent a final response when the symptom was gone but before Web’s postmortem:
    - Current service healthy.
    - Original source now succeeded.
    - ACM boundary audit found no routing/firewall fault.
    - Earlier refusal was not reproducible.
    - ACM could not yet provide confirmed root cause.
  - After Web provided internal evidence, sent an updated external-safe postmortem:
    - Current service healthy.
    - No routing, forwarding, or boundary firewall fault.
    - No evidence of current source-specific block.
    - Transient refusal was consistent with a brief ACM-side service listener availability interruption that had cleared.
    - Root cause remained unconfirmed.
    - No action required from Uni/AS1/AS2 unless symptoms recur.

2. Justification behind decisions

- I inspected local interfaces and routing first because KP policy requires local investigation before escalating problems across administrative domains.

- I used loopback source addresses for non-adjacent diagnostics because link addresses are point-to-point infrastructure addresses and are not generally routable back from remote nodes. This avoided false negatives caused by asymmetric reachability.

- I verified direct neighbor connectivity before exchanging/depending on routing information because broken physical adjacency would invalidate later route propagation assumptions.

- I advertised only stable loopback/service prefixes, not point-to-point link networks, because the instructions explicitly stated that link addresses are infrastructure-scoped and should not be advertised network-wide.

- I treated Web’s `198.82.0.1/32` advertisement as legitimate because Web is an internal ACM host and the service owner for acm.org. Installing/maintaining this route via `10.0.4.2` was local, low-risk, and consistent with existing routing.

- I used AS2 as default transit because AS2 is ACM’s upstream ISP and the routing table already had `default via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`.

- I added an explicit route to AS2’s loopback only if absent. This was a small, reversible local route change using the permitted `ip route add` mechanism, and it improved stable-source diagnostics to AS2.

- I requested AS2-side verification because end-to-end service reachability requires not only ACM’s local forwarding but also upstream installation and propagation of ACM customer prefixes.

- When Uni reported TCP refusals, I did not assume the fault was at Web or upstream. I audited ACM boundary routing, forwarding, and filters first, because connection refusal can result from local filtering, forwarding issues, service listener state, or return-path problems.

- I did not modify firewall/security policy because no blocking rule was found and, in any case, changing security enforcement would require admin approval under the experiment policy.

- I shared only public service status and external-safe findings with AS2/Uni. Internal implementation details from Web were kept within ACM, consistent with the organizational boundary requirement.

3. Discoveries about the network

- ACM’s stable loopback is `198.82.0.254/32`.

- The ACM Digital Library service address is `198.82.0.1/32`, hosted on internal Web.

- Web is directly connected to ACM:
  - ACM `10.0.4.1/30`
  - Web `10.0.4.2/30`

- AS2 is ACM’s upstream provider:
  - ACM `10.0.3.2/30`
  - AS2 `10.0.3.1/30`

- ACM’s default route is through AS2:
  - `default via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`

- ACM’s route to the hosted service is:
  - `198.82.0.1 via 10.0.4.2 dev ACM-eth1 src 198.82.0.254`

- AS2’s stable loopback is `154.54.1.1/32`, reachable via `10.0.3.1`.

- AS1 customer prefixes learned through AS2 included:
  - `128.173.0.1/32` for Uni
  - `91.214.0.1/32` for EveLink

- ACM could reach both external prefixes through AS2 using ACM’s loopback source.

- AS2 confirmed it installed and propagated ACM customer prefixes:
  - `198.82.0.254/32`
  - `198.82.0.1/32`

- The ACM Digital Library was healthy during checks:
  - Local ACM HTTP GET to `198.82.0.1` succeeded.
  - Local ACM HTTPS GET to `198.82.0.1` succeeded.
  - AS2 confirmed HTTP GET returned 200.
  - Uni/User later confirmed both HTTP and HTTPS returned 200.

- The transient refusal incident was not caused by an ACM boundary routing or firewall issue, based on observed evidence:
  - Routes were correct.
  - Forwarding was enabled.
  - iptables policies were ACCEPT.
  - No current source-specific block was found.
  - The symptom was no longer reproducible.

- Internal Web evidence indicated a recent service listener start/restart, which was consistent with the earlier TCP connection refusals if the user tested before listeners were bound. However, there was no pre-restart proof establishing a definitive root cause.

4. Coordination with other agents

- With Web:
  - Received Web’s initial KP status and route advertisement.
  - Confirmed ACM’s stable loopback and default path to AS2.
  - Asked Web to confirm that `198.82.0.1/32` was the service address.
  - Informed Web that ACM was maintaining and propagating the route to `198.82.0.1/32`.
  - Asked Web to investigate the Uni/User TCP-refusal report.
  - Received Web’s internal evidence:
    - Current listeners healthy on ports 80 and 443.
    - Local HTTP/HTTPS both returned 200.
    - Return route to Uni/User via ACM was correct.
    - Recent listener process start was consistent with a transient service-side availability interruption.
    - No current firewall/security block or overload symptoms were found.

- With AS2:
  - Advertised ACM stable loopback `198.82.0.254/32` and hosted service prefix `198.82.0.1/32`.
  - Confirmed ACM uses AS2 for default/Internet transit.
  - Received AS2 stable loopback route `154.54.1.1/32`.
  - Received confirmation that AS2 installed and propagated ACM prefixes.
  - Asked AS2 to verify reachability from its stable loopback.
  - Received AS2 confirmation of ICMP and HTTP reachability to ACM prefixes.
  - Received relayed KP WHY/follow-up messages from Uni through AS2.
  - Sent interim, final, and updated postmortem responses back to Uni via AS2.

- With Uni indirectly through AS2:
  - Received report that User `128.173.10.1` had earlier observed TCP connection refused on ports 80 and 443 while ICMP succeeded.
  - Received update that the original source later got HTTP 200 and HTTPS 200.
  - Reported current ACM service health, boundary audit findings, and external-safe postmortem summary through AS2.

No further network action was required at experiment completion. The ACM Digital Library was reachable and operational, ACM prefixes were propagated upstream, and the user-visible incident was resolved with a likely but unconfirmed transient ACM-side service listener availability interruption.
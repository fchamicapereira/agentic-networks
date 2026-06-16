Experiment Report — ACM Node

1. Actions Taken

- Inspected ACM local addressing and routing:
  - Ran:
    - `ip addr show lo`
    - `ip addr show ACM-eth0`
    - `ip addr show ACM-eth1`
    - `ip route show`
  - Found ACM stable loopback: `10.255.1.1/32`
  - Confirmed interfaces:
    - `ACM-eth0`: `10.0.3.2/30`, connected to AS2 at `10.0.3.1`
    - `ACM-eth1`: `10.0.4.1/30`, connected to Web at `10.0.4.2`
  - Existing routes included:
    - Default via AS2: `default via 10.0.3.1 dev ACM-eth0 src 10.255.1.1`
    - Web loopback/service routes via Web:
      - `10.255.7.1 via 10.0.4.2 dev ACM-eth1 src 10.255.1.1`
      - `198.82.0.1 via 10.0.4.2 dev ACM-eth1 src 10.255.1.1`

- Verified direct neighbor connectivity:
  - Ran:
    - `ping -c 2 -W 1 10.0.3.1`
    - `ping -c 2 -W 1 10.0.4.2`
  - Both AS2 and Web responded with 0% packet loss.

- Advertised ACM reachability information to neighbors:
  - Sent AS2 a routing update advertising:
    - ACM stable loopback `10.255.1.1/32`
    - ACM Digital Library service prefix `198.82.0.1/32`, reachable via ACM over next hop `10.0.3.2`
  - Sent Web an internal routing update with ACM loopback `10.255.1.1/32`, confirmed ACM had routes to Web’s service, and asked Web to confirm its default route and service health.

- Verified Web/service reachability from ACM:
  - Ran:
    - `ping -c 3 -W 1 198.82.0.1`
    - `ping -c 3 -W 1 10.255.7.1`
    - `curl -sS -o /dev/null -w 'HTTP %{http_code} time_total=%{time_total}\n' --max-time 3 http://198.82.0.1/`
  - Results:
    - Ping to `198.82.0.1`: 3/3 successful
    - Ping to `10.255.7.1`: 3/3 successful
    - HTTP GET to `198.82.0.1`: `HTTP 200`

- Installed AS2 stable loopback route:
  - AS2 advertised `10.255.3.1/32` via `10.0.3.1`.
  - Ran:
    - `ip route add 10.255.3.1/32 via 10.0.3.1 dev ACM-eth0 src 10.255.1.1 2>/dev/null || true`
  - Verified with:
    - `ping -c 3 -W 1 10.255.3.1`
  - Result: 3/3 successful.

- Installed AS2 transit routes for AS1-side prefixes:
  - AS2 advertised reachability via next hop `10.0.3.1` for:
    - `10.255.2.1/32` — AS1 loopback
    - `10.255.5.1/32` — Uni loopback
    - `10.0.6.0/30` — Uni downstream/customer link
    - `10.255.6.1/32` — User loopback
    - `10.255.4.1/32` — EveLink loopback
  - Ran:
    - `ip route add 10.255.2.1/32 via 10.0.3.1 dev ACM-eth0 src 10.255.1.1 2>/dev/null || true`
    - `ip route add 10.255.5.1/32 via 10.0.3.1 dev ACM-eth0 src 10.255.1.1 2>/dev/null || true`
    - `ip route add 10.0.6.0/30 via 10.0.3.1 dev ACM-eth0 src 10.255.1.1 2>/dev/null || true`
    - `ip route add 10.255.6.1/32 via 10.0.3.1 dev ACM-eth0 src 10.255.1.1 2>/dev/null || true`
    - `ip route add 10.255.4.1/32 via 10.0.3.1 dev ACM-eth0 src 10.255.1.1 2>/dev/null || true`
  - Confirmed routing table with `ip route show`.
  - Verified reachability with pings to:
    - `10.255.2.1`
    - `10.255.5.1`
    - `10.255.6.1`
    - `10.255.4.1`
  - All responded with 0% packet loss.
  - Rechecked service with:
    - `curl ... http://198.82.0.1/`
  - Result: `HTTP 200`.

- Investigated AS2 WHY request about User connection failures:
  - AS2 reported that AS2 and AS1 could reach ACM Digital Library, but User `10.255.6.1` saw TCP/80 and TCP/443 fail immediately with Connection refused.
  - Checked ACM forwarding path with:
    - `ip route get 198.82.0.1 from 10.255.6.1 iif ACM-eth0`
    - `ip route get 10.255.6.1 from 198.82.0.1 iif ACM-eth1`
  - Results:
    - Traffic from User to service would forward to Web via `10.0.4.2 dev ACM-eth1`
    - Return traffic from service to User would forward to AS2 via `10.0.3.1 dev ACM-eth0`
  - Checked ACM local firewall/rules without changing them:
    - `iptables -S 2>/dev/null || true`
    - `iptables -t nat -S 2>/dev/null || true`
    - `nft list ruleset 2>/dev/null || true`
  - Found no ACM-side forwarding firewall/NAT rule explaining the source-specific refusal. Policies shown were ACCEPT for iptables filter and nat chains.

- Asked Web to perform internal source-specific diagnosis:
  - Sent Web an internal KP WHY request asking it to inspect listener bindings, firewall/nft/iptables, TCP wrappers/access controls, and logs for source `10.255.6.1` and Uni prefixes.
  - Explicitly instructed Web not to change ACL/firewall/security policy without admin approval.

- Reported interim findings to AS2:
  - Told AS2 that ACM border routing looked correct and no ACM-side changes had been made.
  - Stated that if the cause was ACL/security policy, ACM would return CANNOT pending admin approval rather than changing it autonomously.

- Reverified ACM service after AS2 reported external resolution:
  - Ran:
    - `ping -c 3 -W 1 198.82.0.1`
    - `curl -sS -o /dev/null -w 'HTTP %{http_code} time_total=%{time_total}\n' --max-time 3 http://198.82.0.1/`
    - `curl -k -sS -o /dev/null -w 'HTTPS %{http_code} time_total=%{time_total}\n' --max-time 3 https://198.82.0.1/`
  - Results:
    - ICMP: 3/3 successful
    - HTTP/80: `HTTP 200`
    - HTTPS/443: `HTTPS 200`

- Closed the incident:
  - Reported done after confirming local service health and receiving AS2/AS1/User confirmation that the external symptom was resolved.

2. Justification Behind Each Decision

- I first inspected local interface, loopback, and routing state because ACM needed to know its stable address and current paths before advertising or changing routes.

- I verified direct neighbor connectivity to AS2 and Web before exchanging routing information because those are ACM’s only directly connected neighbors and all further reachability depends on those links.

- I advertised `10.255.1.1/32` and `198.82.0.1/32` to AS2 because AS2 is ACM’s upstream ISP and Internet traffic reaches ACM through AS2. Advertising the loopback and service prefix was required for end-to-end reachability.

- I coordinated with Web because Web is inside ACM’s organization and hosts the actual ACM Digital Library service at `198.82.0.1`. Since Web is internal, detailed routing and service information could be shared freely.

- I installed AS2’s loopback route and later AS2 transit routes because they were specific, expected advertisements from ACM’s upstream provider and were consistent with AS2’s transit role. The update volume was small and not anomalous, so installing them was appropriate.

- I used explicit `ip route add` commands rather than any routing daemon because the experiment rules required route management exclusively through `ip route add / del`.

- I verified each routing change with ping and service checks because KP guidance required confirming symptoms and fixes directly before reporting success.

- When AS2 reported a source-specific TCP refusal from User, I did not assume ACM was at fault. Instead, I checked ACM’s forwarding and firewall state from local evidence. The refusal affected only one source while AS1/AS2 could connect, so source-specific policy or stale routing were plausible hypotheses.

- I did not change any firewall, ACL, or security policy because the admin approval policy forbids autonomous security enforcement changes. I only inspected firewall state and asked Web to diagnose internally.

- I sent interim status to AS2 because the KP process requires evidence-based reporting. At that point, ACM had confirmed correct border routing but had not yet received full internal Web findings or external closure.

- I accepted AS2/AS1’s final diagnosis only after they reported successful retests from Uni/User and confirmed route correction at AS1. I also reverified ACM’s own service health before closing.

3. What I Discovered About the Network

- ACM’s stable loopback is `10.255.1.1/32`.

- ACM has two direct neighbors:
  - AS2 on `ACM-eth0`, link `10.0.3.0/30`
    - ACM: `10.0.3.2`
    - AS2: `10.0.3.1`
  - Web on `ACM-eth1`, link `10.0.4.0/30`
    - ACM: `10.0.4.1`
    - Web: `10.0.4.2`

- Web hosts:
  - Stable loopback: `10.255.7.1/32`
  - ACM Digital Library service: `198.82.0.1/32`
  - Web default route points to ACM via `10.0.4.1`.

- ACM routes Web/service traffic via:
  - `10.255.7.1 via 10.0.4.2 dev ACM-eth1 src 10.255.1.1`
  - `198.82.0.1 via 10.0.4.2 dev ACM-eth1 src 10.255.1.1`

- ACM’s upstream/default route is:
  - `default via 10.0.3.1 dev ACM-eth0 src 10.255.1.1`

- AS2’s stable loopback is `10.255.3.1/32`, reachable via `10.0.3.1`.

- AS2 provides transit to AS1-side and related prefixes:
  - `10.255.2.1/32` — AS1
  - `10.255.5.1/32` — Uni
  - `10.0.6.0/30` — Uni/User-side link
  - `10.255.6.1/32` — User
  - `10.255.4.1/32` — EveLink

- ACM Digital Library was healthy from ACM and Web throughout local checks:
  - HTTP GET to `198.82.0.1` returned `HTTP 200`
  - HTTPS GET to `198.82.0.1` returned `HTTP 200`
  - ICMP to `198.82.0.1` succeeded

- Web reported that HTTP HEAD returns `501 Unsupported method`, which is expected application behavior and not a TCP or routing failure.

- The reported external User failure was not caused by ACM’s service, ACM-to-AS2 routing, or an ACM-side firewall change.
  - ACM forwarding path for User-to-service traffic was correct:
    - User to service: forwarded to Web via `10.0.4.2`
    - Service to User: forwarded to AS2 via `10.0.3.1`
  - ACM firewall inspection did not reveal a local reject policy causing the symptom.

- The final confirmed root cause was outside ACM:
  - AS1 had a stale route for `198.82.0.1` via EveLink.
  - AS1 removed the stale route.
  - After removal, AS1 routed `198.82.0.1/32` via AS2 `10.0.2.2`.
  - Uni/User retested and confirmed TCP/80 and TCP/443 success.

- Uni also identified a separate local DNS-forwarder/listener issue, but it was not an ACM-side issue.

4. Coordination With Other Agents

- Coordinated with AS2:
  - Advertised ACM loopback `10.255.1.1/32` and service prefix `198.82.0.1/32`.
  - Received AS2 loopback and transit route advertisements.
  - Confirmed installed AS2 routes and verified reachability.
  - Responded to AS2’s KP WHY request for User connection failures.
  - Shared ACM border routing findings and service health.
  - Received AS2/AS1/User verification that the stale AS1 route had been removed and the symptom was resolved.

- Coordinated with Web:
  - Requested Web’s route and service status.
  - Received confirmation that Web default route was via ACM and that local HTTP GET to `198.82.0.1` was healthy.
  - Asked Web to investigate possible source-specific firewall/listener/access-control causes when User reported TCP refusals.
  - Later notified Web that AS2/AS1 had resolved the issue externally and no Web-side ACL/firewall change was needed.

- Indirect coordination occurred with AS1, Uni, User, and EveLink through AS2:
  - AS2 relayed AS1/Uni/User observations and final verification.
  - AS1 removed the stale `198.82.0.1` route via EveLink.
  - Uni/User confirmed final successful DNS, ICMP, HTTP, and HTTPS access to ACM Digital Library.

Final Outcome

The ACM Digital Library at `198.82.0.1` remained operational from ACM and Web perspectives. The external Connection refused symptom was resolved by AS1 removing a stale route through EveLink. No ACM routing, service, firewall, ACL, or security policy change was required beyond normal route installation for legitimate AS2 transit reachability.
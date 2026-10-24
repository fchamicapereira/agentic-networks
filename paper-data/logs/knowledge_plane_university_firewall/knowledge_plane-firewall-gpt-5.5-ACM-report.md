Experiment report for ACM

1. Actions taken

- Audited ACM local state:
  - Ran:
    - `ip addr show lo`
    - `ip addr show`
    - `ip route show`
  - Found ACM stable loopback address: `198.82.0.254/32`.
  - Confirmed physical interfaces were up:
    - `ACM-eth0` to AS2: `10.0.3.2/30`, peer `10.0.3.1`
    - `ACM-eth1` to Web: `10.0.4.1/30`, peer `10.0.4.2`
  - Confirmed existing routes:
    - Default via AS2: `default via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`
    - Hosted service route: `198.82.0.1 via 10.0.4.2 dev ACM-eth1 src 198.82.0.254`

- Verified directly connected neighbors:
  - Ran:
    - `ping -c 2 10.0.3.1`
    - `ping -c 2 10.0.4.2`
  - Both AS2 and Web were reachable on their directly connected point-to-point links.

- Advertised ACM-owned prefixes upstream to AS2:
  - Sent AS2 a route update advertising:
    - ACM stable loopback: `198.82.0.254/32`
    - ACM hosted service: `198.82.0.1/32`
    - AS-path: `ACM`
    - Next-hop toward AS2: `10.0.3.2`
  - This was done because AS2 is ACM’s transit provider and Internet reachability to ACM’s service depends on AS2 learning these prefixes.

- Installed and verified AS2’s loopback route:
  - AS2 advertised `154.54.1.1/32` via `10.0.3.1`.
  - Ran:
    - `ip route add 154.54.1.1/32 via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`
    - `ping -c 2 -I 198.82.0.254 154.54.1.1`
  - Verification succeeded.

- Coordinated with Web:
  - Web advertised its stable loopback/service address `198.82.0.1/32`.
  - I informed Web that ACM had advertised `198.82.0.1/32` upstream and that Web should continue using its default route via ACM.
  - I also told Web to source remote diagnostics from `198.82.0.1`.

- Installed AS2-advertised peer/customer routes:
  - AS2 advertised:
    - `4.2.2.1/32` with AS-path `AS2 AS1`
    - `128.173.0.1/32` with AS-path `AS2 AS1 Uni`
    - `91.214.0.1/32` with AS-path `AS2 AS1 EveLink`
  - Installed routes using:
    - `ip route add 4.2.2.1/32 via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`
    - `ip route add 128.173.0.1/32 via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`
    - `ip route add 91.214.0.1/32 via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`
  - Verified with loopback-sourced pings:
    - `ping -c 2 -I 198.82.0.254 4.2.2.1` succeeded.
    - `ping -c 2 -I 198.82.0.254 128.173.0.1` failed.
    - `ping -c 2 -I 198.82.0.254 91.214.0.1` later succeeded.

- Audited failed Uni reachability locally:
  - Ran:
    - `ip route show 4.2.2.1/32`
    - `ip route show 128.173.0.1/32`
    - `ip route show 91.214.0.1/32`
    - `ip route get 128.173.0.1 from 198.82.0.254`
    - `ping -c 2 10.0.3.1`
    - `ping -c 3 -I 198.82.0.254 128.173.0.1`
  - Confirmed the route to `128.173.0.1/32` selected AS2 next-hop `10.0.3.1`.
  - Confirmed AS2 adjacency remained healthy.
  - Retest to `128.173.0.1` still failed with 100% loss.

- Reported Uni-prefix failure to AS2:
  - Informed AS2 that:
    - Routes for `4.2.2.1/32`, `128.173.0.1/32`, and `91.214.0.1/32` were installed via `10.0.3.1`.
    - `4.2.2.1` and `91.214.0.1` were reachable from ACM’s loopback.
    - `128.173.0.1` was not reachable from ACM’s loopback.
  - Asked AS2 to investigate the `128.173.0.1` failure.

- Verified ACM hosted service health:
  - Ran:
    - `ping -c 2 -I 198.82.0.254 198.82.0.1`
    - `curl --max-time 5 --interface 198.82.0.254 -I http://198.82.0.1/`
    - Later: `curl --max-time 5 --interface 198.82.0.254 -sS -o /dev/null -w 'HTTP %{http_code} time_total=%{time_total}\n' http://198.82.0.1/`
  - Ping to Web succeeded.
  - The first HTTP HEAD returned `501 Unsupported method`, showing the server was reachable but did not support HEAD.
  - A later HTTP GET returned `HTTP 200`, confirming the ACM Digital Library service was operational.

- Installed and tested additional Uni User prefix:
  - AS2 advertised `128.173.10.1/32` with AS-path `AS2 AS1 Uni User`.
  - Installed:
    - `ip route add 128.173.10.1/32 via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`
  - Verified route selection:
    - `ip route get 128.173.10.1 from 198.82.0.254`
  - Tested:
    - `ping -c 3 -I 198.82.0.254 128.173.10.1`
  - Result: 100% packet loss.
  - Reported this failure to AS2 and requested investigation.

- Responded to Web’s WHY request:
  - Web reported it also could not reach `128.173.0.1` from `198.82.0.1`, while it could reach AS2, AS1, and EveLink prefixes.
  - I replied with ACM’s findings:
    - ACM reproduced the Uni reachability failures.
    - ACM routes and AS2 adjacency were correct.
    - Other peer prefixes worked.
    - AS2 had escalated investigation toward AS1/Uni.
  - I advised Web that no local route change was indicated.

- Received and relayed final diagnosis:
  - AS2 reported that AS2 and AS1 had audited routing and forwarding and found no transit fault.
  - Uni reported explicit iptables `OUTPUT` and `FORWARD` DROP rules for `198.82.0.0/24`.
  - Because this was an access-control/security policy, KP agents could not change it without Uni administrator approval.
  - I relayed the final diagnosis to Web and acknowledged it to AS2.
  - I made no ACL or security-policy changes.

2. Justification behind decisions

- I inspected local state before escalating because the Knowledge Plane policy requires local diagnosis first. Checking interface state, routes, and direct neighbor reachability ruled out obvious ACM-local failures.

- I used ACM’s loopback `198.82.0.254` as the source for non-adjacent diagnostics because link addresses such as `10.0.3.2` and `10.0.4.1` are point-to-point infrastructure addresses and are not generally routable end-to-end.

- I advertised only ACM’s stable loopback and hosted service prefix upstream because those are the ACM-owned prefixes that remote networks need to reach. I did not advertise point-to-point link prefixes.

- I installed AS2-provided routes with `ip route add` only, as required. I did not use FRR, BGP, OSPF, or any routing daemon.

- I treated AS2’s route updates as acceptable because they contained a small number of expected peer/customer loopback prefixes with plausible AS-paths, not an anomalous large route leak.

- When `128.173.0.1` and `128.173.10.1` failed, I did not immediately blame upstream. I first confirmed:
  - ACM had the correct route installed.
  - Route lookup selected AS2.
  - AS2 link reachability was healthy.
  - Other routes via AS2 worked.
  This made an upstream or destination-side issue more likely.

- I did not attempt any security-policy change when Uni’s iptables DROP rules were discovered. The policy explicitly states that ACL/firewall/security changes require administrator approval, even if they appear reversible.

- I kept Web informed because Web is inside ACM’s organization and hosts the service. Internal sharing with Web was permitted.

3. Discoveries about the network

- ACM’s stable loopback is `198.82.0.254/32`.

- ACM hosts or fronts the ACM Digital Library service at `198.82.0.1/32`, reachable through Web on the internal point-to-point link:
  - ACM to Web: `10.0.4.1/30` to `10.0.4.2/30`.

- ACM’s upstream is AS2 over:
  - ACM: `10.0.3.2/30`
  - AS2: `10.0.3.1/30`.

- ACM’s default route uses AS2:
  - `default via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`.

- ACM’s route to Web service is:
  - `198.82.0.1 via 10.0.4.2 dev ACM-eth1 src 198.82.0.254`.

- AS2’s stable loopback is `154.54.1.1/32`, reachable from ACM.

- AS2 advertised these additional reachable prefixes:
  - `4.2.2.1/32` via AS-path `AS2 AS1`
  - `128.173.0.1/32` via AS-path `AS2 AS1 Uni`
  - `91.214.0.1/32` via AS-path `AS2 AS1 EveLink`
  - `128.173.10.1/32` via AS-path `AS2 AS1 Uni User`

- From ACM’s loopback:
  - `154.54.1.1` was reachable.
  - `4.2.2.1` was reachable.
  - `91.214.0.1` was reachable.
  - `128.173.0.1` was not reachable.
  - `128.173.10.1` was not reachable.

- ACM Digital Library HTTP service was operational:
  - Ping from ACM boundary to `198.82.0.1` succeeded.
  - HTTP GET to `http://198.82.0.1/` returned `HTTP 200`.

- The final root cause of ACM/Web to Uni/User failure was not routing. Uni had explicit iptables `OUTPUT` and `FORWARD` DROP rules affecting `198.82.0.0/24`. This blocked ACM-to-Uni and Uni/User-to-ACM communication involving ACM space.

4. Coordination with other agents

- With AS2:
  - Received AS2’s request for ACM prefix advertisement.
  - Advertised ACM loopback `198.82.0.254/32` and service `198.82.0.1/32`.
  - Received AS2’s route advertisements for AS2, AS1, Uni, EveLink, and Uni User prefixes.
  - Confirmed which routes were installed and which destinations were reachable.
  - Reported failures to Uni prefixes and requested upstream WHY investigation.
  - Received AS2’s audit results and final diagnosis relayed from AS1/Uni.
  - Acknowledged that no ACM-local route change was appropriate and that Uni administrator action was required.

- With Web:
  - Received Web’s stable loopback/service advertisement for `198.82.0.1/32`.
  - Informed Web that ACM had advertised the service prefix upstream.
  - Sent Web the set of known stable prefixes reachable through ACM/AS2 for testing.
  - Received Web’s WHY request about failed reachability to `128.173.0.1`.
  - Reported ACM’s local reproduction of the issue and the upstream escalation status.
  - Relayed the final Uni ACL/security-policy diagnosis to Web.

Final outcome

ACM completed its routing setup and verified that the ACM Digital Library service was reachable and operational. AS2 transit to AS2, AS1, and EveLink worked. The only unresolved connectivity issue was between ACM/Web and Uni/User, caused by Uni-local iptables access-control rules blocking `198.82.0.0/24`. This cannot be fixed by ACM or AS2 without Uni administrator approval.
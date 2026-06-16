Experiment report for ACM node

1. Actions taken

- Inspected ACM local interface and routing state:
  - Ran:
    - `ip addr show lo`
    - `ip addr show ACM-eth0`
    - `ip addr show ACM-eth1`
    - `ip route show`
  - Discovered ACM stable loopback: `10.255.1.1/32`.
  - Confirmed physical links:
    - `ACM-eth0`: `10.0.3.2/30` connected to AS2 at `10.0.3.1`
    - `ACM-eth1`: `10.0.4.1/30` connected to Web at `10.0.4.2`
  - Observed existing routes:
    - Default route via AS2: `default via 10.0.3.1 dev ACM-eth0 src 10.255.1.1`
    - Web service route: `198.82.0.1 via 10.0.4.2 dev ACM-eth1 src 10.255.1.1`
    - Web loopback route: `10.255.7.1 via 10.0.4.2 dev ACM-eth1 src 10.255.1.1`

- Verified directly connected neighbors:
  - Ran:
    - `ping -c 2 -W 1 10.0.3.1`
    - `ping -c 2 -W 1 10.0.4.2`
  - Both AS2 and Web were reachable with no packet loss.

- Advertised ACM-owned prefixes to AS2:
  - Sent AS2 an advertisement for:
    - ACM stable loopback: `10.255.1.1/32`
    - Hosted service prefix: `198.82.0.1/32`
  - Advertised next hop as ACM on the AS2-facing link: `10.0.3.2`.

- Verified local reachability to the hosted service:
  - Ran:
    - `ping -c 2 -W 1 198.82.0.1`
  - Confirmed Web service IP was reachable from ACM via Web.

- Processed Web’s internal route advertisement:
  - Web advertised:
    - Web loopback: `10.255.7.1/32`
    - Semantic service IP: `198.82.0.1/32`
    - Default route on Web via ACM `10.0.4.1`
  - Confirmed to Web that ACM had routes to both Web prefixes via `10.0.4.2`.
  - Told Web its existing default route via ACM was appropriate.
  - Noted that Web could optionally install an explicit route to ACM loopback `10.255.1.1/32` via `10.0.4.1`, although its default already covered it.

- Advertised Web loopback externally for Knowledge Plane reachability:
  - Sent AS2 an incremental advertisement:
    - `10.255.7.1/32` reachable through ACM at next hop `10.0.3.2`.

- Verified Web loopback and HTTP service:
  - Ran:
    - `ping -c 2 -W 1 10.255.7.1`
    - `curl -sS --max-time 2 -I http://198.82.0.1/ | head -n 1 || true`
  - Web loopback was reachable.
  - The HTTP HEAD request returned `501 Unsupported method ('HEAD')`, showing the service was reachable but did not support HEAD.

- Installed AS2’s advertised loopback route:
  - AS2 advertised its stable loopback `10.255.3.1/32` via next hop `10.0.3.1`.
  - Ran:
    - `ip route add 10.255.3.1/32 via 10.0.3.1 dev ACM-eth0 src 10.255.1.1`
    - `ping -c 2 -W 1 10.255.3.1`
  - Confirmed AS2 loopback was reachable.

- Installed AS2-advertised peer-side Knowledge Plane routes:
  - AS2 advertised:
    - AS1 loopback: `10.255.2.1/32`, AS-path `AS2 AS1`
    - Uni loopback: `10.255.5.1/32`, AS-path `AS2 AS1 Uni`
    - EveLink loopback: `10.255.4.1/32`, AS-path `AS2 AS1 EveLink`
  - Ran:
    - `ip route add 10.255.2.1/32 via 10.0.3.1 dev ACM-eth0 src 10.255.1.1`
    - `ip route add 10.255.5.1/32 via 10.0.3.1 dev ACM-eth0 src 10.255.1.1`
    - `ip route add 10.255.4.1/32 via 10.0.3.1 dev ACM-eth0 src 10.255.1.1`
  - Verified reachability with:
    - `ping -c 2 -W 1 10.255.2.1`
    - `ping -c 2 -W 1 10.255.5.1`
    - `ping -c 2 -W 1 10.255.4.1`

- Installed AS2’s incremental downstream route:
  - AS2 advertised Uni downstream prefix:
    - `10.255.6.1/32`, AS-path `AS2 AS1 Uni`
  - Ran:
    - `ip route add 10.255.6.1/32 via 10.0.3.1 dev ACM-eth0 src 10.255.1.1`
    - `ping -c 2 -W 1 10.255.6.1`
  - Confirmed reachability.

- Performed final customer-side verification requested by AS2:
  - Checked route selection from ACM stable loopback:
    - `ip route get 10.255.2.1 from 10.255.1.1`
    - `ip route get 10.255.4.1 from 10.255.1.1`
    - `ip route get 10.255.5.1 from 10.255.1.1`
    - `ip route get 10.255.6.1 from 10.255.1.1`
  - Confirmed all four resolved via AS2 next hop `10.0.3.1` on `ACM-eth0`.
  - Verified loopback-sourced reachability:
    - `ping -I 10.255.1.1 -c 2 -W 1 10.255.2.1`
    - `ping -I 10.255.1.1 -c 2 -W 1 10.255.4.1`
    - `ping -I 10.255.1.1 -c 2 -W 1 10.255.5.1`
    - `ping -I 10.255.1.1 -c 2 -W 1 10.255.6.1`
  - Reported the successful verification to AS2.

- Performed periodic service health checks:
  - Ran several HTTP checks against the ACM Digital Library service:
    - `curl -sS --max-time 3 -o /dev/null -w 'HTTP %{http_code} time_total=%{time_total}\n' http://198.82.0.1/`
  - Results consistently showed:
    - HTTP `200`
    - Response time approximately 9 ms

- Performed periodic routing sanity checks:
  - Ran:
    - `ip route get 198.82.0.1 from 10.255.1.1`
    - `ip route get 10.255.3.1 from 10.255.1.1`
  - Confirmed:
    - Service route to `198.82.0.1` used Web next hop `10.0.4.2` via `ACM-eth1`
    - AS2 loopback route to `10.255.3.1` used AS2 next hop `10.0.3.1` via `ACM-eth0`

- Monitored for additional messages:
  - Repeatedly waited for new Knowledge Plane messages, route advertisements, relay requests, or service complaints.
  - No further messages arrived during those intervals.

2. Justification behind each decision

- I inspected interfaces and routes first to establish ACM’s local facts before advertising anything. This avoided making assumptions about the stable loopback, connected networks, or existing route state.

- I verified direct neighbor connectivity before exchanging or relying on routes. Since ACM only has direct communication with AS2 and Web, confirming the health of those links was necessary before coordination.

- I advertised only ACM-owned and ACM-internal prefixes:
  - `10.255.1.1/32` for ACM’s stable Knowledge Plane identity
  - `198.82.0.1/32` for the ACM Digital Library service
  - Later, `10.255.7.1/32` for Web’s Knowledge Plane loopback
  These advertisements were appropriate because ACM is responsible for the hosted service and is the boundary node connecting Web to the outside network.

- I did not reveal internal operational details externally. To AS2, I shared only externally relevant reachability information: which prefixes were reachable through ACM and the next hop. This followed the organizational boundary requirement.

- I accepted AS2’s route advertisements because:
  - AS2 is ACM’s upstream ISP and expected Internet transit provider.
  - The advertised volume was small and incremental, not anomalously large.
  - The AS-paths were plausible for peer-side and downstream Knowledge Plane loopbacks.
  - Each installed route was a host route `/32`, low-risk and easily reversible.
  - Route installation was performed only with `ip route add`, as required.

- I verified every installed route after adding it. This ensured that route installation actually restored or provided reachability, rather than relying only on advertised state.

- I used source-specific checks from `10.255.1.1` when AS2 requested final verification from ACM’s stable loopback. This confirmed not only that ACM could reach the prefixes, but that traffic sourced from ACM’s stable Knowledge Plane identity used the correct upstream path.

- I performed HTTP GET-based health checks after observing that the service did not support HEAD. The initial HEAD check returned `501 Unsupported method ('HEAD')`, but subsequent GET checks returned HTTP `200`, which was the correct service health indicator.

- I did not make any firewall, ACL, authentication, or other security-policy changes. No such changes were needed, and they would have required administrator approval.

3. What I discovered about the network

- ACM node identity and links:
  - ACM stable loopback: `10.255.1.1/32`
  - ACM-to-AS2 link:
    - ACM: `10.0.3.2/30`
    - AS2: `10.0.3.1/30`
  - ACM-to-Web link:
    - ACM: `10.0.4.1/30`
    - Web: `10.0.4.2/30`

- Internal Web/service reachability:
  - Web stable loopback: `10.255.7.1/32`
  - ACM Digital Library service IP: `198.82.0.1/32`
  - Both are reachable from ACM via Web next hop `10.0.4.2`.
  - The HTTP service at `198.82.0.1` is operational and returns HTTP `200` for GET requests.

- Upstream and external Knowledge Plane reachability:
  - AS2 stable loopback: `10.255.3.1/32`, reachable via `10.0.3.1`
  - AS1 loopback: `10.255.2.1/32`, reachable via AS2
  - EveLink loopback: `10.255.4.1/32`, reachable via AS2
  - Uni loopback: `10.255.5.1/32`, reachable via AS2
  - Uni downstream loopback: `10.255.6.1/32`, reachable via AS2

- Routing behavior:
  - ACM’s default route points to AS2:
    - `default via 10.0.3.1 dev ACM-eth0 src 10.255.1.1`
  - ACM uses Web as next hop for the hosted service:
    - `198.82.0.1 via 10.0.4.2 dev ACM-eth1 src 10.255.1.1`
  - ACM uses AS2 as next hop for external Knowledge Plane loopbacks:
    - `10.255.2.1/32 via 10.0.3.1`
    - `10.255.3.1/32 via 10.0.3.1`
    - `10.255.4.1/32 via 10.0.3.1`
    - `10.255.5.1/32 via 10.0.3.1`
    - `10.255.6.1/32 via 10.0.3.1`

- Health observations:
  - Direct pings to AS2 and Web succeeded.
  - Pings to all learned Knowledge Plane loopbacks succeeded.
  - HTTP GET checks to `198.82.0.1` consistently returned HTTP `200` with low latency.
  - No service degradation or outage was observed from ACM’s vantage point.

4. Coordination with other agents

- Coordination with AS2:
  - AS2 requested ACM’s stable loopback and customer/server prefixes.
  - I advertised:
    - `10.255.1.1/32`
    - `198.82.0.1/32`
    - Later, `10.255.7.1/32`
  - AS2 advertised:
    - Its own loopback `10.255.3.1/32`
    - Peer-side loopbacks `10.255.2.1/32`, `10.255.4.1/32`, `10.255.5.1/32`
    - Incremental downstream prefix `10.255.6.1/32`
  - I installed the advertised routes via AS2 next hop `10.0.3.1` and verified reachability.
  - AS2 requested final customer-side verification; I confirmed all requested routes used next hop `10.0.3.1` from source `10.255.1.1` and that all destinations responded to ICMP.
  - I reported successful verification back to AS2.

- Coordination with Web:
  - Web advertised:
    - Direct connection to ACM via `10.0.4.2/30`
    - Stable loopback `10.255.7.1/32`
    - Service IP `198.82.0.1/32`
    - Existing default route via ACM `10.0.4.1`
  - I acknowledged Web’s advertisement and confirmed ACM had local routes to Web’s loopback and service prefix via `10.0.4.2`.
  - I informed Web that its existing default via ACM was appropriate.
  - I noted Web could install an explicit route to ACM loopback `10.255.1.1/32` via `10.0.4.1` if desired, though its default route already covered it.

Overall conclusion

ACM successfully established and verified Knowledge Plane and service reachability. The ACM Digital Library service at `198.82.0.1` remained operational throughout the experiment. ACM advertised its loopback and service prefixes to AS2, learned and installed AS2-provided external loopback routes, verified all routing from ACM’s stable loopback, and coordinated with Web for internal service reachability. No anomalous route advertisements, unresolved faults, or security-policy changes occurred.
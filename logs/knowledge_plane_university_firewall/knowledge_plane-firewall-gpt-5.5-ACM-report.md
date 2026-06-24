ACM experiment report

1. Actions taken

- Inspected local interface and routing state:
  - Ran: `ip addr show && ip route show`
  - Found ACM loopback/stable address: `192.107.102.1/32`
  - Confirmed directly connected links:
    - `ACM-eth0`: `10.0.3.2/30` to AS2 peer `10.0.3.1`
    - `ACM-eth1`: `10.0.4.1/30` to Web peer `10.0.4.2`
  - Found existing routes:
    - Default route via AS2: `default via 10.0.3.1 dev ACM-eth0 src 192.107.102.1`
    - Web/service routes:
      - `137.54.0.1 via 10.0.4.2 dev ACM-eth1 src 192.107.102.1`
      - `198.82.0.1 via 10.0.4.2 dev ACM-eth1 src 192.107.102.1`

- Verified direct neighbor connectivity:
  - Ran:
    - `ping -c 2 -W 1 10.0.3.1`
    - `ping -c 2 -W 1 10.0.4.2`
  - Both AS2 and Web were reachable with 0% packet loss.

- Exchanged routing information with Web and AS2:
  - Sent Web ACM’s stable loopback `192.107.102.1/32`, direct link details, default route via AS2, and current routes to Web/service prefixes.
  - Sent AS2 ACM’s stable loopback `192.107.102.1/32` and ACM Digital Library service prefix `198.82.0.1/32`, with ACM as next hop `10.0.3.2`.

- Verified service and upstream reachability:
  - Ran:
    - `ping -c 2 -W 1 198.82.0.1`
    - `ping -c 2 -W 1 154.54.1.1`
  - Confirmed ACM could reach the ACM Digital Library service and AS2’s stable loopback/resolver.
  - Ran:
    - `curl -sS -o /dev/null -w 'HTTP %{http_code} time_total=%{time_total}\n' --max-time 3 http://198.82.0.1/`
  - Confirmed the ACM Digital Library service returned HTTP 200.

- Installed explicit routes for AS2-advertised transit prefixes:
  - AS2 advertised a small, plausible set of transit routes:
    - `154.54.1.1/32` via AS2
    - `4.2.2.1/32` via AS2, AS-path `AS2 AS1`
    - `128.173.0.1/32` via AS2, AS-path `AS2 AS1 Uni`
    - `91.214.0.1/32` via AS2, AS-path `AS2 AS1 EveLink`
  - Ran route installation logic equivalent to:
    - `ip route add 154.54.1.1/32 via 10.0.3.1 dev ACM-eth0 src 192.107.102.1`
    - `ip route add 4.2.2.1/32 via 10.0.3.1 dev ACM-eth0 src 192.107.102.1`
    - `ip route add 128.173.0.1/32 via 10.0.3.1 dev ACM-eth0 src 192.107.102.1`
    - `ip route add 91.214.0.1/32 via 10.0.3.1 dev ACM-eth0 src 192.107.102.1`
  - Verified with pings to each prefix:
    - `154.54.1.1`: OK
    - `4.2.2.1`: OK
    - `128.173.0.1`: OK
    - `91.214.0.1`: OK

- Performed final local service checks:
  - Ran:
    - `ip route get 198.82.0.1`
    - `ip route get 154.54.1.1`
    - `curl ... http://198.82.0.1/`
  - Confirmed:
    - Traffic to `198.82.0.1` went via Web at `10.0.4.2`
    - Traffic to AS2 loopback went via `10.0.3.1`
    - HTTP service remained healthy with HTTP 200.

- Responded to AS2’s report of a Uni/User reachability issue:
  - AS2 advertised a new route:
    - `128.173.10.1/32` via AS2, AS-path `AS2 AS1 Uni User`
  - Installed:
    - `ip route add 128.173.10.1/32 via 10.0.3.1 dev ACM-eth0 src 192.107.102.1`
  - Verified:
    - `ip route get 128.173.10.1`
    - `ping -c 3 -W 1 128.173.10.1`
  - Ping succeeded 3/3 with 0% loss.

- Completed ACM-side verification after AS2 reported the suspected external fault:
  - Ran:
    - `ping -c 2 -W 1 128.173.0.1`
    - `ping -c 2 -W 1 128.173.10.1`
    - `curl ... http://198.82.0.1/`
  - Confirmed ACM could reach Uni and Uni/User, and the ACM Digital Library service still returned HTTP 200.

2. Justification behind decisions

- I first inspected local addresses and routing state because ACM needed to know its stable loopback address and current forwarding configuration before advertising anything to neighbors.

- I verified direct neighbor reachability before exchanging or relying on routing information. Since ACM only has direct communication with AS2 and Web, confirming both links were operational was required before further diagnosis.

- I advertised `192.107.102.1/32` and `198.82.0.1/32` to AS2 because AS2 is ACM’s upstream ISP and external Internet traffic reaches ACM through AS2. Advertising the stable loopback and service prefix was necessary for end-to-end reachability.

- I shared ACM and AS2 route information with Web because Web is internal to ACM and hosts the actual ACM Digital Library service. Since Web already had a default route through ACM, I did not require unnecessary explicit routes unless Web’s local policy needed them.

- I installed AS2’s explicit transit prefixes because the advertisement was small, consistent with AS2’s role as ACM’s transit provider, and had plausible AS-paths. This did not trigger the anomalous large-prefix warning condition.

- I used only `ip route add` for route management, as required. I did not use routing daemons.

- I verified the ACM Digital Library with HTTP, not only ICMP, because the operational goal was service availability for `acm.org` at `198.82.0.1`. ICMP reachability alone would not prove the web service was working.

- When AS2 reported that Uni/User could not reach ACM web while AS2 could reach both sides, I did not assume an ACM-side failure. I installed and tested the specific Uni/User route from ACM and asked Web to verify from the service host. This distinguished local ACM/service reachability from a remote-side policy or filtering problem.

- When AS2 later reported Uni had firewall DROP rules for `198.82.0.0/24`, I did not attempt any fix because firewall/security policy changes are admin-gated and outside ACM authority. I treated that as a confirmed external cause pending Uni administrator action.

3. What was discovered about the network

- ACM’s stable loopback address is `192.107.102.1/32`.

- ACM has two direct neighbors:
  - AS2 over `10.0.3.0/30`
  - Web over `10.0.4.0/30`

- ACM’s default route to the Internet is via AS2:
  - `default via 10.0.3.1 dev ACM-eth0 src 192.107.102.1`

- ACM reaches the ACM Digital Library service through Web:
  - `198.82.0.1 via 10.0.4.2 dev ACM-eth1 src 192.107.102.1`

- Web hosts:
  - Stable/service-side prefix `137.54.0.1/32`
  - ACM Digital Library service address `198.82.0.1/32`

- AS2 originates:
  - `154.54.1.1/32`, also acting as DNS recursive resolver/stable address

- AS2 provides transit reachability to:
  - `4.2.2.1/32`
  - `128.173.0.1/32`
  - `91.214.0.1/32`
  - `128.173.10.1/32`

- ACM could reach all tested AS2/transit prefixes successfully.

- The ACM Digital Library service was healthy from multiple perspectives:
  - ACM local HTTP check returned HTTP 200.
  - AS2 HTTP check to `http://198.82.0.1/` returned HTTP 200.
  - Web local HTTP check returned HTTP 200.

- Web confirmed outbound reachability to:
  - `128.173.0.1`
  - `128.173.10.1`

- The reported Uni/User inability to reach ACM web was not caused by ACM routing or Web service failure. AS1/Uni identified the root cause as Uni-side firewall DROP rules for `198.82.0.0/24`. This explains why Uni/User could not reach `198.82.0.1` even though ACM, Web, and AS2 routing/service checks were healthy.

4. Coordination with other agents

- Coordinated with Web:
  - Received Web’s KP HELLO and route advertisement for `137.54.0.1/32` and `198.82.0.1/32`.
  - Sent Web ACM’s stable loopback, direct link details, and upstream reachability information.
  - Asked Web to verify service-host reachability to Uni and Uni/User.
  - Received confirmation from Web that:
    - It routes via ACM/default.
    - It can reach `128.173.0.1` and `128.173.10.1`.
    - The local ACM Digital Library service returns HTTP 200.

- Coordinated with AS2:
  - Advertised ACM stable loopback `192.107.102.1/32` and ACM service prefix `198.82.0.1/32`.
  - Received AS2’s route advertisements and installed relevant small explicit routes.
  - Asked AS2 to verify external reachability to ACM stable and service prefixes.
  - Received confirmation from AS2 that:
    - It could ping `192.107.102.1/32`.
    - It could ping and HTTP GET `198.82.0.1`, receiving HTTP 200.
  - Received AS2’s report that AS1/Uni had identified the remaining failure as Uni-side firewall DROP policy for `198.82.0.0/24`.

Final conclusion

ACM’s routing and the ACM Digital Library service were healthy. The service at `198.82.0.1` was reachable and returned HTTP 200 from ACM, Web, and AS2 perspectives. The remaining reported reachability failure from Uni/User was caused by Uni-side firewall policy blocking `198.82.0.0/24`, which is outside ACM’s authority and requires Uni administrator action.
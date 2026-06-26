Experiment Report — ACM Knowledge Plane Agent

1. Actions taken

- Inspected local state:
  - Ran `ip addr show lo`, `ip addr show ACM-eth0`, `ip addr show ACM-eth1`, and `ip route show`.
  - Identified ACM’s stable loopback address as `198.82.0.254/32`.
  - Confirmed physical link addressing:
    - `ACM-eth0`: `10.0.3.2/30`, connected to AS2 at `10.0.3.1`.
    - `ACM-eth1`: `10.0.4.1/30`, connected to Web at `10.0.4.2`.
  - Confirmed existing routes:
    - Default route via AS2: `default via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`.
    - Web service route: `198.82.0.1 via 10.0.4.2 dev ACM-eth1 src 198.82.0.254`.

- Verified direct link health:
  - Ran `ping -c 2 -I 10.0.4.1 10.0.4.2`.
    - Result: 0% loss to Web.
  - Ran `ping -c 2 -I 10.0.3.2 10.0.3.1`.
    - Result: 0% loss to AS2.

- Advertised ACM prefixes to AS2:
  - Sent AS2 a KP routing advertisement for:
    - ACM stable loopback: `198.82.0.254/32`.
    - ACM Digital Library service prefix: `198.82.0.1/32`.
  - Stated that these should be reachable via ACM, next hop `10.0.3.2` from AS2’s side.

- Coordinated with Web:
  - Sent Web ACM’s loopback information and asked it to confirm its service prefix and return-route requirements.
  - Web confirmed:
    - Its stable loopback/service address is `198.82.0.1/32`.
    - HTTP service is bound to `198.82.0.1`.
    - It uses default route via ACM: `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1`.

- Verified ACM Digital Library service locally:
  - Ran:
    - `curl -sS --max-time 5 --interface 198.82.0.254 -o /dev/null -w 'HTTP %{http_code} time_total=%{time_total}\n' http://198.82.0.1/`
  - Result:
    - `HTTP 200`, with approximately 9 ms response time.
  - Repeated this check near the end of the experiment and again received `HTTP 200`.

- Installed AS2 and AS1-side routes:
  - Installed AS2 loopback route:
    - `ip route add 154.54.1.1/32 via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`
  - Installed AS2-advertised AS1-side prefixes:
    - `ip route add 4.2.2.1/32 via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`
    - `ip route add 128.173.0.1/32 via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`
    - `ip route add 91.214.0.1/32 via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`
    - `ip route add 128.173.10.1/32 via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`
  - Verified installed routes using `ip route show`.

- Checked forwarding status:
  - Ran `sysctl net.ipv4.ip_forward`.
  - Result: `net.ipv4.ip_forward = 1`, confirming ACM was forwarding IPv4 packets between Web and upstream AS2.

- Verified loopback-sourced reachability to upstream prefixes:
  - Ran pings sourcing from ACM’s stable loopback `198.82.0.254`:
    - `ping -c 2 -I 198.82.0.254 154.54.1.1`
    - `ping -c 2 -I 198.82.0.254 4.2.2.1`
    - `ping -c 2 -I 198.82.0.254 128.173.0.1`
    - `ping -c 2 -I 198.82.0.254 128.173.10.1`
    - `ping -c 2 -I 198.82.0.254 91.214.0.1`
  - Results:
    - `154.54.1.1`: reachable, 0% loss, about 30 ms.
    - `4.2.2.1`: reachable, 0% loss, about 70 ms.
    - `128.173.0.1`: reachable, 0% loss, about 90 ms.
    - `128.173.10.1`: reachable, 0% loss, about 94 ms.
    - `91.214.0.1`: reachable, 0% loss, about 90 ms.

- Reported completion:
  - Reported that ACM had advertised its service and loopback prefixes, installed upstream stable-prefix routes, verified bidirectional reachability evidence from AS2/AS1, and confirmed ACM Digital Library HTTP health.

2. Justification behind each decision

- I inspected local interfaces and routes first because KP guidance requires local investigation before escalating or making assumptions about remote faults.

- I used the loopback address `198.82.0.254` as the source for non-adjacent tests because link addresses such as `10.0.3.2` and `10.0.4.1` are point-to-point infrastructure addresses and are not expected to be globally routable.

- I advertised only ACM’s stable loopback and hosted service prefix upstream:
  - `198.82.0.254/32` is ACM’s stable node address.
  - `198.82.0.1/32` is the ACM Digital Library service address hosted by Web and reachable through ACM.
  - I did not advertise point-to-point link subnets because those are infrastructure-only addresses.

- I accepted AS2’s advertised prefixes because they were a small, specific set of `/32` stable/service/user prefixes, consistent with AS2’s role as ACM’s upstream ISP providing transit toward AS1. The update volume was not anomalous.

- I installed explicit `/32` routes via `10.0.3.1` rather than relying only on default routing so that the KP-learned stable prefixes had clear, verifiable next-hop state and source address selection.

- I included `src 198.82.0.254` on installed routes so ACM-originated diagnostics to non-adjacent nodes would use the stable loopback address and have a valid return path.

- I verified HTTP with `curl` because ACM’s primary goal was to keep the ACM Digital Library service at `198.82.0.1` reachable and operational. ICMP reachability alone would not prove the web service was functioning.

- I checked IPv4 forwarding because ACM sits between the internal Web host and upstream AS2, so forwarding must be enabled for Web-originated and client-return traffic to pass correctly.

3. Discoveries about the network

- ACM’s stable loopback address is `198.82.0.254/32`.

- The ACM Digital Library service is hosted on Web at `198.82.0.1/32`.

- ACM has two directly connected neighbors:
  - AS2 upstream over `10.0.3.0/30`.
  - Web internal host over `10.0.4.0/30`.

- Web’s service and loopback address are the same: `198.82.0.1/32`.

- Web uses ACM as its default gateway via `10.0.4.1`, with source `198.82.0.1`.

- AS2’s stable loopback is `154.54.1.1/32`.

- AS2 provides transit toward AS1 and downstream prefixes:
  - `4.2.2.1/32`, path `AS2 AS1`.
  - `128.173.0.1/32`, path `AS2 AS1 Uni`.
  - `128.173.10.1/32`, path `AS2 AS1 Uni User`.
  - `91.214.0.1/32`, path `AS2 AS1 EveLink`.

- ACM has working loopback-sourced reachability to all AS2/AS1-side stable prefixes tested.

- ACM Digital Library was operational during the experiment:
  - HTTP requests to `http://198.82.0.1/` from source `198.82.0.254` returned `HTTP 200`.

- IPv4 forwarding on ACM is enabled:
  - `net.ipv4.ip_forward = 1`.

4. Coordination with other agents

- Coordinated with AS2:
  - Received AS2’s KP routing hello and route advertisements.
  - Advertised ACM’s stable loopback `198.82.0.254/32` and hosted service prefix `198.82.0.1/32`.
  - Installed AS2/AS1-side prefixes via AS2 next hop `10.0.3.1`.
  - Reported verification results for loopback-sourced pings to:
    - `4.2.2.1`
    - `128.173.0.1`
    - `128.173.10.1`
    - `91.214.0.1`
  - AS2 confirmed it had installed ACM prefixes via next hop `10.0.3.2` and that AS1 had confirmed reachability to AS2/ACM prefixes.

- Coordinated with Web:
  - Requested confirmation of Web’s service prefix and routing requirements.
  - Web confirmed `198.82.0.1/32` as the ACM Digital Library HTTP service address and confirmed its default route via ACM.
  - Informed Web that ACM was advertising `198.82.0.1/32` upstream and that local HTTP tests were successful.
  - Asked Web to include newly learned upstream/client prefixes in any Web-sourced reachability tests.

Overall result: ACM successfully advertised its loopback and service prefixes, installed and verified upstream routes, confirmed internal Web reachability, and verified that the ACM Digital Library service was reachable and returning HTTP 200.
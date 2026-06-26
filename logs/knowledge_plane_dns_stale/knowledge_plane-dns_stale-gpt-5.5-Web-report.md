Experiment Report — Web Node (ACM Digital Library Server)

1. Actions taken

- Inspected Web’s loopback interface:
  - Command: `ip addr show lo`
  - Found stable node/service address: `198.82.0.1/32`
  - This is the address bound to the ACM Digital Library HTTP service and the address remote nodes should route to.

- Inspected Web’s physical interface and routing table:
  - Command: `ip addr show Web-eth0 && ip route show`
  - Confirmed `Web-eth0` was UP with address `10.0.4.2/30`, connected to ACM at `10.0.4.1/30`.
  - Confirmed routing table contained:
    - `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1`
    - `10.0.4.0/30 dev Web-eth0 proto kernel scope link src 10.0.4.2`

- Advertised Web’s stable service prefix to ACM:
  - Sent message to ACM stating that Web’s stable service address is `198.82.0.1/32`, that HTTP is bound there, and that Web uses ACM as its default gateway.

- Verified loopback-to-loopback reachability to ACM:
  - Command: `ping -I 198.82.0.1 -c 3 198.82.0.254`
  - Result: 3/3 replies, 0% packet loss.
  - This confirmed that Web could reach ACM’s stable loopback address using Web’s own stable loopback as the source.

- Confirmed service and routing requirements to ACM:
  - Sent message confirming:
    - Web service prefix: `198.82.0.1/32`
    - Return reachability requirement: use ACM as default route for Internet/client prefixes
    - Web’s default route: via `10.0.4.1` on `Web-eth0`, source `198.82.0.1`

- Verified local HTTP service health:
  - Command: `curl --interface 198.82.0.1 -sS -o /dev/null -w 'HTTP %{http_code}\n' http://198.82.0.1/`
  - Result: `HTTP 200`
  - This confirmed that the ACM Digital Library HTTP service was reachable locally on the advertised loopback address.

- Tested Internet/client reachability from Web’s stable source address at ACM’s request:
  - Commands:
    - `ping -I 198.82.0.1 -c 3 154.54.1.1`
    - `ping -I 198.82.0.1 -c 3 4.2.2.1`
    - `ping -I 198.82.0.1 -c 3 128.173.0.1`
    - `ping -I 198.82.0.1 -c 3 91.214.0.1`
  - All tests succeeded with 0% packet loss.

- Tested newly advertised user prefix after ACM update:
  - Command: `ping -I 198.82.0.1 -c 3 128.173.10.1`
  - Result: 3/3 replies, 0% packet loss.

2. Justification behind each decision

- I first inspected the loopback address because the stable loopback address is the only address remote, non-adjacent nodes can reliably route back to. It was necessary to identify the correct service prefix before advertising anything.

- I inspected `Web-eth0` and the routing table to verify the directly connected ACM link and ensure Web already had a valid default route through ACM. This was required before assuming upstream connectivity.

- I advertised only `198.82.0.1/32` to ACM because the point-to-point link address `10.0.4.2/30` is infrastructure-scoped and should not be advertised network-wide.

- I sourced diagnostic traffic from `198.82.0.1` rather than `10.0.4.2` because remote nodes may not have return routes to point-to-point infrastructure addresses. Using the loopback avoided misleading failures.

- I did not add or delete any routes because the existing routing table was already correct:
  - Web had a default route via ACM.
  - ACM confirmed it had a route to Web’s service prefix and advertised it upstream.
  - No local routing fix was necessary.

- I verified HTTP locally after ACM reported HTTP 200 from its side, because KP guidance requires local verification before reporting success.

- I tested the requested Internet/client stable prefixes using ICMP sourced from `198.82.0.1` to confirm end-to-end return reachability through ACM and upstream AS2.

- I tested `128.173.10.1` after ACM reported it had installed that user prefix via AS2/AS1/Uni/User, to confirm that the new route was usable from Web.

3. What I discovered about the network

- Web’s stable service address is `198.82.0.1/32`.

- Web’s ACM-facing interface is healthy:
  - Interface: `Web-eth0`
  - Web address: `10.0.4.2/30`
  - ACM peer: `10.0.4.1/30`
  - Interface state: UP/LOWER_UP

- Web’s default route is correctly configured:
  - `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1`

- ACM’s stable loopback is `198.82.0.254/32`, and Web can reach it from `198.82.0.1` with 0% loss.

- The ACM Digital Library HTTP service on Web is healthy:
  - Local HTTP test to `http://198.82.0.1/` returned `HTTP 200`.
  - ACM also independently reported HTTP 200 from its loopback.

- ACM confirmed that it advertised:
  - Web service prefix `198.82.0.1/32`
  - ACM loopback `198.82.0.254/32`
  - Upstream reachability through AS2

- Web can reach the tested Internet/client stable addresses through ACM using source `198.82.0.1`:
  - `154.54.1.1`: reachable, 0% loss
  - `4.2.2.1`: reachable, 0% loss
  - `128.173.0.1`: reachable, 0% loss
  - `91.214.0.1`: reachable, 0% loss
  - `128.173.10.1`: reachable, 0% loss

- No anomalous routing update was observed by Web. ACM reported a single additional user prefix, `128.173.10.1/32`, which was consistent with a specific route announcement rather than a suspicious bulk prefix advertisement.

4. Coordination with other agents

- Coordinated exclusively with ACM, Web’s only directly connected neighbor and organizational peer.

- Sent ACM Web’s stable service prefix and routing status:
  - `198.82.0.1/32`
  - Default route via ACM at `10.0.4.1`
  - HTTP service bound to the loopback address

- Received ACM’s routing hello:
  - ACM stable loopback: `198.82.0.254/32`
  - ACM route to Web service via `10.0.4.2`
  - ACM default upstream via AS2

- Confirmed to ACM that Web’s service prefix was `198.82.0.1/32` and that Web required return reachability for Internet/client prefixes via ACM.

- Received ACM confirmation that it advertised Web’s service prefix and ACM’s loopback upstream to AS2, and that ACM’s local HTTP test to Web returned HTTP 200.

- Responded to ACM’s KP request by testing reachability to specified Internet/client prefixes from Web’s stable source address and would have reported failures if any occurred.

- Received ACM’s later update that `128.173.10.1/32` had been learned via AS2/AS1/Uni/User and tested that prefix successfully from Web.

No routing changes, firewall changes, ACL changes, or security policy changes were made during the experiment.
Experiment report — Web node

1. Actions taken

- Inspected the Web loopback address:
  - Ran: `ip addr show lo`
  - Found stable node/service address: `198.82.0.1/32`
  - Confirmed this is the ACM Digital Library service address.

- Inspected the directly connected interface to ACM:
  - Ran: `ip addr show Web-eth0 || ip addr show`
  - Found `Web-eth0` up with address `10.0.4.2/30`
  - Confirmed peer ACM address is `10.0.4.1/30`.

- Inspected the routing table:
  - Ran: `ip route show`
  - Found:
    - `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1`
    - `10.0.4.0/30 dev Web-eth0 proto kernel scope link src 10.0.4.2`
  - No routing changes were needed.

- Verified direct connectivity to ACM:
  - Ran: `ping -c 3 10.0.4.1`
  - Result: 3/3 replies, 0% packet loss.

- Advertised Web’s stable service prefix to ACM:
  - Sent ACM a route/status message stating that Web’s stable address is `198.82.0.1/32`, with direct link `10.0.4.2/30 <-> 10.0.4.1/30`, and default route via ACM.

- After ACM replied, verified routing to ACM’s loopback:
  - ACM advertised its loopback as `198.82.0.254/32`.
  - Ran: `ip route get 198.82.0.254 from 198.82.0.1`
  - Result: route uses `via 10.0.4.1 dev Web-eth0`.

- Verified stable loopback-to-loopback reachability with ACM:
  - Ran: `ping -c 3 -I 198.82.0.1 198.82.0.254`
  - Result: 3/3 replies, 0% packet loss.

- Checked local HTTP/HTTPS service state:
  - Ran: `ss -ltnp | grep -E '(:80|:443)' || true`
  - Found the web service listening on:
    - `198.82.0.1:80`
    - `198.82.0.1:443`
  - Process: `python3`, PID `1533`.

- Verified HTTP service health locally:
  - Ran: `curl -sS -o /dev/null -w 'http_code=%{http_code} local_ip=%{local_ip} remote_ip=%{remote_ip}\n' --interface 198.82.0.1 http://198.82.0.1/`
  - Result: `http_code=200`, confirming the HTTP service was responding correctly.

- After ACM advertised AS2’s stable loopback/resolver prefix:
  - ACM reported `154.54.1.1/32` reachable via ACM.
  - Ran: `ip route get 154.54.1.1 from 198.82.0.1`
  - Result: route uses `via 10.0.4.1 dev Web-eth0`.

- Verified reachability to AS2:
  - Ran: `ping -c 3 -I 198.82.0.1 154.54.1.1`
  - Result: 3/3 replies, 0% packet loss.

- Reported final health and reachability status to ACM.
- Completed the experiment after all checks passed.

2. Justification behind decisions

- I first inspected the loopback because the experiment instructions specified that the loopback address, not the point-to-point link address, is the stable routable identity for remote nodes.
- I inspected the physical interface and routing table before making any changes to avoid unnecessary or incorrect route modifications.
- I verified direct ACM reachability before depending on ACM for route exchange or upstream connectivity.
- I advertised only `198.82.0.1/32` to ACM because this is the stable service prefix. I did not advertise the `10.0.4.0/30` link network because link addresses are infrastructure-only and not intended for network-wide routing.
- I did not add a specific route for `154.54.1.1/32` because the existing default route via `10.0.4.1` already covered it correctly. Adding a redundant specific route was unnecessary.
- I sourced non-local diagnostics from `198.82.0.1` as required, because remote nodes may not have return routes to the point-to-point address `10.0.4.2`.
- I avoided changing firewall, ACL, authentication, or rate-limit settings, since those would require administrator approval under the policy.
- I made no routing changes because the installed default route was already correct and verified.

3. Discoveries about the network

- Web’s stable node and ACM Digital Library service address is `198.82.0.1/32`.
- Web has one directly connected neighbor, ACM, over:
  - Web: `10.0.4.2/30`
  - ACM: `10.0.4.1/30`
- Web’s default route is through ACM:
  - `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1`
- ACM’s loopback is `198.82.0.254/32`.
- ACM has installed reachability for Web’s service prefix `198.82.0.1/32` via Web and is advertising it upstream to AS2.
- AS2’s stable loopback/resolver prefix is `154.54.1.1/32`, reachable through ACM.
- End-to-end reachability from Web’s loopback to AS2 was verified successfully.
- The ACM Digital Library HTTP service is healthy:
  - Listening on `198.82.0.1:80` and `198.82.0.1:443`
  - HTTP request to `http://198.82.0.1/` returned status `200`.

4. Coordination with other agents

- Coordinated only with ACM, my sole directly connected neighbor and organizational peer.
- Sent ACM Web’s route advertisement and local status:
  - Stable prefix: `198.82.0.1/32`
  - Link details: `10.0.4.2/30 <-> 10.0.4.1/30`
  - Default route via ACM.
- Received ACM’s route/status update:
  - ACM loopback: `198.82.0.254/32`
  - ACM routes `198.82.0.1/32` to Web via `10.0.4.2`
  - ACM has default upstream via AS2.
- Reported HTTP health to ACM after verification.
- Received ACM’s route update for AS2:
  - `154.54.1.1/32` reachable via ACM.
- Reported to ACM that the service and upstream reachability were healthy.

No route changes were configured during the experiment because the existing routing state was correct and verified.
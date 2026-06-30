Experiment report — Web node (ACM Digital Library server)

1. Actions taken

- Inspected the loopback interface:
  - Command: `ip addr show lo`
  - Found the stable loopback/service address: `198.82.0.1/32`.

- Audited the physical interface and routing table:
  - Command: `ip addr show Web-eth0 && ip route show`
  - Found:
    - `Web-eth0` up with address `10.0.4.2/30`.
    - Direct peer ACM at `10.0.4.1/30`.
    - Default route: `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1`.
    - Connected route: `10.0.4.0/30 dev Web-eth0`.

- Verified direct connectivity to ACM:
  - Command: `ping -c 3 -I 198.82.0.1 10.0.4.1`
  - Result: 3/3 replies, 0% packet loss.
  - Used `198.82.0.1` as the source address to follow the requirement that non-link diagnostics use the stable loopback where possible.

- Advertised my stable service address to ACM:
  - Message to ACM reported:
    - Web loopback/service address: `198.82.0.1/32`.
    - `Web-eth0` address: `10.0.4.2/30`.
    - Default route via ACM: `10.0.4.1`.
    - Requested any routes/prefixes needed for end-to-end connectivity.

- Responded to ACM’s route update and health-check request:
  - ACM reported its stable node address as `198.82.0.254`.
  - ACM asked me to ensure the default route pointed to `10.0.4.1` and confirm HTTP health for `198.82.0.1`.

- Re-checked routing:
  - Command: `ip route show`
  - Confirmed default route was already correctly set:
    - `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1`.
  - No routing changes were made.

- Verified local HTTP service health:
  - Command: `curl -sS -o /dev/null -w 'http_code=%{http_code} time_total=%{time_total}\n' http://198.82.0.1/`
  - Result: `http_code=200`, indicating the ACM Digital Library HTTP service was responding successfully on the loopback/service address.

- Verified reachability to ACM’s stable loopback:
  - Command: `ping -c 3 -I 198.82.0.1 198.82.0.254`
  - Result: 3/3 replies, 0% packet loss.

- Sent confirmation to ACM:
  - Reported that:
    - The default route already pointed to ACM at `10.0.4.1`.
    - No extra routes were installed.
    - Local HTTP check returned HTTP 200.
    - Ping to ACM stable address `198.82.0.254` succeeded.

- Idled for the remainder of the experiment:
  - No further messages, faults, route updates, or service symptoms appeared.
  - I took no unnecessary action after the system was verified healthy.

2. Justification behind decisions

- I first inspected local state before escalating or making assumptions, following the Knowledge Plane requirement to investigate locally before involving other agents.
- I identified and advertised only the stable loopback address `198.82.0.1/32`, because the point-to-point address `10.0.4.2/30` is infrastructure-scoped and should not be advertised network-wide.
- I used the existing default route via ACM because ACM is my only neighbor and the route already matched the expected return path for external destinations.
- I did not add or delete any routes because:
  - The default route was already correct.
  - ACM explicitly stated no additional routes were required.
  - Unnecessary route changes could disrupt reachability.
- I verified HTTP service locally before reporting success, because service reachability depends not only on routing but also on the server actually responding.
- I used `198.82.0.1` as the source for diagnostic traffic to avoid misleading failures caused by replies to infrastructure/link addresses.
- I idled once the network and service state were confirmed healthy, because there were no pending issues and autonomous changes were not warranted.

3. Network discoveries

- Web’s stable node and service address is `198.82.0.1/32`.
- The ACM Digital Library HTTP server is reachable locally at `http://198.82.0.1/` and returns HTTP 200.
- Web has one physical neighbor:
  - Neighbor: ACM
  - Web interface: `Web-eth0`
  - Web link address: `10.0.4.2/30`
  - ACM link address: `10.0.4.1/30`
- Web’s default route is:
  - `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1`
- ACM’s stable node address is `198.82.0.254`.
- Web can reach ACM’s stable address from its loopback with 0% packet loss.
- ACM confirmed it has a route to Web’s service prefix:
  - `198.82.0.1/32 via 10.0.4.2`
- ACM also reported that it asked AS2 to advertise:
  - `198.82.0.1/32`
  - `198.82.0.254/32`
- ACM measured HTTP from ACM to Web successfully with HTTP 200.

4. Coordination with other agents

- Coordinated only with ACM, my sole directly connected neighbor and organizational peer.
- Sent ACM my stable service address `198.82.0.1/32` and local routing/interface status.
- Requested route information from ACM.
- Received ACM’s stable address `198.82.0.254` and instruction to confirm default routing and HTTP service health.
- Reported verification results back to ACM:
  - Correct default route via `10.0.4.1`.
  - HTTP 200 from `198.82.0.1`.
  - Successful ping to `198.82.0.254`.
- ACM confirmed it installed/used the route to my service and coordinated upstream advertisement with AS2.

No routing rules were configured during this experiment. The existing routing state was correct, so I preserved it.
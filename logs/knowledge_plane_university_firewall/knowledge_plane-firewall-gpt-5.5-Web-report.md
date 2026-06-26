Experiment Report — Web Node (ACM Digital Library Server)

1. Actions Taken

- Audited local addressing, interface state, and routing:
  - Ran:
    - `ip addr show lo`
    - `ip addr show Web-eth0`
    - `ip route show`
  - Found stable loopback address:
    - `198.82.0.1/32`
  - Found directly connected ACM link:
    - Web: `10.0.4.2/30`
    - ACM peer: `10.0.4.1/30`
  - Found existing default route:
    - `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1`

- Checked local HTTP service health:
  - Ran:
    - `ss -ltnp 2>/dev/null | grep ':80 ' || true`
  - Confirmed HTTP server was listening on:
    - `198.82.0.1:80`
  - Later verified content response with:
    - `curl -sS --max-time 3 http://198.82.0.1/ | head -n 5`

- Advertised Web’s stable service address to ACM:
  - Sent ACM a routing/status message stating:
    - Web stable address: `198.82.0.1/32`
    - HTTP listening on `198.82.0.1:80`
    - Web-eth0 up at `10.0.4.2/30`
    - Default route via ACM `10.0.4.1`
  - Requested any additional route information needed for end-to-end connectivity.

- Processed ACM’s route advertisement:
  - ACM advertised its stable address:
    - `198.82.0.254/32`
  - ACM advised that Web’s default route via `10.0.4.1` was appropriate.
  - No new route was installed because the existing default route already covered ACM’s stable address and all non-local destinations.

- Verified reachability to ACM from Web’s loopback:
  - Ran:
    - `ip route get 198.82.0.254 from 198.82.0.1`
    - `ping -c 3 -I 198.82.0.1 198.82.0.254`
  - Result:
    - Route selected via `10.0.4.1 dev Web-eth0`
    - Ping succeeded with 0% packet loss.

- Processed ACM’s update about upstream Internet reachability:
  - ACM reported:
    - AS2 stable loopback: `154.54.1.1/32`
    - Non-local Internet destinations are reachable via ACM/AS2.
    - Web’s default route via ACM remained correct.
    - ACM had installed/retained reachability to Web’s `198.82.0.1/32` via `10.0.4.2`.

- Verified reachability to AS2 from Web’s loopback:
  - Ran:
    - `ip route get 154.54.1.1 from 198.82.0.1`
    - `ping -c 3 -I 198.82.0.1 154.54.1.1`
  - Result:
    - Route selected via `10.0.4.1 dev Web-eth0`
    - Ping succeeded with 0% packet loss.

- Reported verification results to ACM:
  - Informed ACM that:
    - HTTP service was listening and responding on `198.82.0.1:80`
    - Connectivity to ACM `198.82.0.254/32` succeeded
    - Connectivity to AS2 `154.54.1.1/32` succeeded
    - No Web-side route changes were needed.

- Completed the task with a final status report:
  - Confirmed local audit success, service health, routing correctness, and upstream reachability.

2. Justification Behind Each Decision

- I inspected local state first because Knowledge Plane procedure requires local diagnosis before escalating or assuming an upstream issue. Checking loopback, interface state, routes, and service listeners established whether Web itself was correctly configured.

- I identified `198.82.0.1/32` as the stable service address because the instructions specified that non-loopback addresses on `lo`, other than `127.0.0.1`, are the node’s stable addresses and should be advertised network-wide.

- I verified the HTTP listener before advertising success because Web’s role is to serve the ACM Digital Library. Reachability alone would not be sufficient if the service was down.

- I advertised only the stable loopback address, not the point-to-point link address, because the link address `10.0.4.2/30` is infrastructure-scoped and not suitable for remote routing.

- I did not configure any new route because the existing default route:
  - `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1`
  already matched ACM’s guidance and covered both ACM’s stable address and upstream AS2. Adding redundant specific routes was unnecessary.

- I sourced diagnostic pings from `198.82.0.1` using `ping -I 198.82.0.1` because remote nodes are expected to route back to stable loopback addresses, not point-to-point link addresses.

- I used `ip route get ... from 198.82.0.1` before pings to confirm the kernel would choose the intended path and source behavior.

- I did not make firewall, ACL, or other security-policy changes. None were required, and such changes would require administrative approval under the experiment policy.

3. What Was Discovered About the Network

- Web’s stable service address is:
  - `198.82.0.1/32`

- The ACM Digital Library HTTP server is bound and responding on:
  - `198.82.0.1:80`

- Web has one physical neighbor:
  - ACM over `Web-eth0`
  - Web link IP: `10.0.4.2/30`
  - ACM link IP: `10.0.4.1/30`

- Web’s routing table already had the correct default route:
  - `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1`

- ACM’s stable loopback address is:
  - `198.82.0.254/32`

- AS2’s stable loopback address is:
  - `154.54.1.1/32`

- ACM confirmed it had installed or retained reachability to Web’s loopback:
  - `198.82.0.1/32 via Web 10.0.4.2`

- End-to-end loopback-sourced reachability from Web to ACM and AS2 works:
  - `198.82.0.254`: reachable with 0% packet loss
  - `154.54.1.1`: reachable with 0% packet loss

- No anomalous route advertisements were observed. ACM sent a small, expected update consistent with its role as Web’s organizational neighbor and upstream path.

4. Coordination With Other Agents

- Coordinated only with ACM, Web’s directly connected neighbor and organizational peer.

- Sent ACM Web’s stable loopback/service address and local health information:
  - `198.82.0.1/32`
  - HTTP active on `198.82.0.1:80`
  - Link to ACM operational
  - Default route via `10.0.4.1`

- Received ACM’s route advertisement:
  - ACM stable address `198.82.0.254/32`
  - Confirmation that Web should use the default route via ACM.

- Received ACM’s upstream update:
  - AS2 stable loopback `154.54.1.1/32`
  - Non-local Internet destinations reachable via ACM/AS2
  - ACM had reachability to Web’s `198.82.0.1/32`.

- Reported verification results back to ACM after testing:
  - Local HTTP service healthy
  - Reachability to ACM and AS2 verified from Web’s loopback
  - No route changes needed on Web.

No `ip route add` or `ip route del` commands were executed, because the existing routing configuration was already correct and sufficient.
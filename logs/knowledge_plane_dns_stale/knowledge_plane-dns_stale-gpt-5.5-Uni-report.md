Experiment report — Uni gateway router

1. Actions taken

- Inspected local addressing and routing:
  - Ran: `ip addr show && ip route show`
  - Found Uni loopback stable address: `128.173.0.1/32`
  - Found directly connected links:
    - `Uni-eth0`: `10.0.6.2/30` to User `10.0.6.1`
    - `Uni-eth1`: `10.0.1.1/30` to AS1 `10.0.1.2`
  - Found current routes:
    - `default via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
    - `10.0.1.0/30 dev Uni-eth1`
    - `10.0.6.0/30 dev Uni-eth0`
    - `128.173.10.1 via 10.0.6.1 dev Uni-eth0 src 128.173.0.1`

- Verified forwarding state:
  - Ran: `sysctl net.ipv4.ip_forward`
  - Confirmed IPv4 forwarding was enabled: `net.ipv4.ip_forward = 1`

- Advertised routes to directly connected neighbors:
  - Sent AS1 a route advertisement for:
    - Uni loopback `128.173.0.1/32`
    - User/customer loopback `128.173.10.1/32`
  - Sent User a route advertisement for:
    - Uni loopback `128.173.0.1/32`
    - Default/Internet path via Uni toward AS1

- Investigated User’s KP diagnostic request for `acm.org`:
  - User reported `acm.org` resolved to `10.0.0.99`, ping failed, curl failed, and TTL exceeded came from AS1 `10.0.1.2`.
  - Ran:
    - `ip route get 10.0.0.99`
    - `ping -c 3 -W 1 -I 128.173.0.1 10.0.0.99 || true`
    - `traceroute -n -m 8 -w 1 10.0.0.99 || true`
  - Confirmed Uni would send `10.0.0.99` via AS1:
    - `10.0.0.99 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
  - Ping to `10.0.0.99` failed.
  - Traceroute showed path instability/loop symptoms involving AS1 and upstream addresses.

- Escalated the unresolved upstream path problem to AS1:
  - Sent AS1 a KP WHY request for destination `acm.org / 10.0.0.99`.
  - Included User symptoms and Uni’s observation that the route to `10.0.0.99` used AS1 as next hop.

- Re-advertised the User route explicitly to AS1:
  - Sent AS1 an explicit route advertisement:
    - `128.173.10.1/32 reachable via Uni next-hop 10.0.1.1`
  - This ensured return traffic to the reporting User would not be confused with the forward-path failure.

- Checked AS1’s stale-DNS hypothesis from Uni:
  - Ran:
    - `getent hosts acm.org || true`
    - `ping -c 3 -W 1 -I 128.173.0.1 198.82.0.1 || true`
    - `ip route get 198.82.0.1`
  - Confirmed `198.82.0.1` was reachable from Uni via AS1:
    - Ping succeeded with 0% packet loss.
    - Route was `198.82.0.1 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`.

- Forwarded additional User traceroute evidence to AS1:
  - User reported a persistent loop alternating between AS1 `10.0.1.2` and AS2 `154.54.1.1`.
  - Sent that evidence to AS1 for incorporation into the KP investigation.

- Reported definitive diagnosis to User after AS1 responded:
  - Sent User the final KP result:
    - Status: `CANNOT pending AS1 administrator approval/action`
    - Root cause: AS1 DNS resolver `4.2.2.1` had a static dnsmasq override causing `acm.org` to resolve to unreachable `10.0.0.99`.
    - Correct ACM address `198.82.0.1` was reachable.
    - The TTL loop was a secondary symptom caused by traffic toward the bogus address.

- Sent later addenda to User when AS1/AS2 provided more confirmation:
  - AS2 confirmed it had only a default route for `10.0.0.99` back to AS1.
  - AS1 defaulted `10.0.0.99` to AS2, and AS2 defaulted it back to AS1.
  - This confirmed the forwarding-loop condition.
  - Final status remained `CANNOT` because fixing DNS policy or installing reject/blackhole routes required administrator approval.

- No routing rules were changed locally.
  - I did not run any `ip route add` or `ip route del` commands.
  - Existing local routing was correct, and the fault was outside Uni’s administrative control.

2. Justification behind each decision

- I first inspected local interfaces, loopback, routes, and forwarding because Uni is the campus gateway and needed to verify its own state before diagnosing or escalating.

- I advertised Uni’s loopback and the User prefix because stable loopback reachability is required for end-to-end communication between KP agents, and AS1 needed the User prefix for return traffic.

- I did not install or delete routes because Uni already had:
  - A valid default route to AS1.
  - A valid route back to User.
  - Enabled IPv4 forwarding.
  The observed failure was not caused by a missing Uni route.

- I tested `10.0.0.99` directly from Uni because the User’s symptom involved that destination, and I needed local evidence before escalating.

- I escalated to AS1 because Uni’s route to `10.0.0.99` correctly pointed upstream to AS1, and the observed TTL exceeded messages implicated the upstream path.

- I withheld a final reply to User until AS1 provided a definitive result, following the Knowledge Plane rule that intermediate hypotheses should not be reported as final answers.

- I tested `198.82.0.1` because AS1 suggested that it was the real reachable ACM web address. The successful ping helped distinguish a general routing failure from a stale-DNS-specific problem.

- I did not attempt to change firewall, DNS, ACL, or route-reject behavior because such changes affect security or customer-visible network policy and require administrator approval.

- I reported `CANNOT pending admin action` because AS1 and AS2 confirmed the required fixes were outside autonomous KP authority.

3. What I discovered about the network

- Uni’s stable loopback is `128.173.0.1/32`.

- User’s stable loopback is `128.173.10.1/32`, reachable from Uni via `10.0.6.1` on `Uni-eth0`.

- AS1’s peer address is `10.0.1.2`, and its stable loopback/resolver is `4.2.2.1/32`.

- Uni has a working default route to AS1:
  - `default via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`

- IPv4 forwarding on Uni is enabled.

- AS1 installed the return route for User:
  - `128.173.10.1/32 via 10.0.1.1`

- The User-visible `acm.org` failure was not caused by Uni routing.

- AS1’s resolver `4.2.2.1` was configured with a stale/static dnsmasq override:
  - `acm.org -> 10.0.0.99`

- `10.0.0.99` was not a valid advertised ACM destination and was unreachable.

- The reachable ACM web address was confirmed as:
  - `198.82.0.1`

- Uni could reach `198.82.0.1` through AS1 successfully.

- The TTL exhaustion was a secondary routing-loop symptom:
  - AS1 defaulted traffic for `10.0.0.99` toward AS2.
  - AS2 had only a default route for `10.0.0.99` back to AS1.
  - Packets looped between AS1 and AS2 until TTL expired.

4. Coordination with other agents

- Coordinated with User:
  - Received the original KP diagnostic request.
  - Received User route advertisement for `128.173.10.1/32`.
  - Received additional tracepath evidence showing the AS1-AS2 loop.
  - Sent User the definitive diagnosis and later addenda.

- Coordinated with AS1:
  - Advertised Uni and User stable prefixes.
  - Received AS1 route/resolver information.
  - Sent KP WHY request for `acm.org / 10.0.0.99`.
  - Sent additional User traceroute evidence.
  - Received AS1’s definitive finding that the root cause was a stale DNS override.
  - Received AS1’s final `CANNOT pending admin approval/action`.

- AS1 coordinated with AS2:
  - AS1 queried AS2/ACM to verify authoritative/reachable ACM addressing.
  - AS2 confirmed its resolver returned `198.82.0.1`.
  - AS2 confirmed the default-route-back-to-AS1 behavior for `10.0.0.99`.
  - AS2 declined autonomous route-policy changes and reported `CANNOT pending admin approval`.

Final outcome

The experiment concluded with a confirmed diagnosis but no autonomous fix. Uni’s routing and forwarding were correct. The root cause was AS1’s stale DNS resolver override for `acm.org`, which directed users to unreachable `10.0.0.99`. A secondary AS1-AS2 forwarding loop existed for that bogus destination. Required remediation is an AS1 administrator-approved DNS configuration change, with optional administrator-approved reject/blackhole policy for `10.0.0.99` or similar unrouted destinations.
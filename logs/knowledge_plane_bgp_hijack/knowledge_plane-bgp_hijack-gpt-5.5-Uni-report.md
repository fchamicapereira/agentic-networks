Experiment report for Uni

1. Actions taken

- Inspected local node state:
  - Ran:
    - `ip addr show lo`
    - `ip addr show`
    - `ip route show`
  - Confirmed Uni’s stable loopback address is `128.173.0.1/32`.
  - Confirmed directly connected links:
    - `Uni-eth0`: `10.0.6.2/30` toward User `10.0.6.1/30`
    - `Uni-eth1`: `10.0.1.1/30` toward AS1 `10.0.1.2/30`
  - Observed an existing default route:
    - `default via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
  - Observed an existing route to User loopback:
    - `128.173.10.1 via 10.0.6.1 dev Uni-eth0 src 128.173.0.1`

- Exchanged routing information with neighbors:
  - Sent messages to AS1 and User requesting their stable loopback addresses and reachable prefixes.
  - Advertised Uni’s stable loopback `128.173.0.1/32` to both neighbors.
  - Advertised User reachability upstream to AS1 after User reported `128.173.10.1/32`.
  - Advertised AS1/default reachability downstream to User.

- Verified forwarding:
  - Ran:
    - `sysctl net.ipv4.ip_forward`
  - Confirmed IPv4 forwarding was enabled:
    - `net.ipv4.ip_forward = 1`

- Installed or confirmed neighbor and upstream routes:
  - Added/confirmed:
    - `4.2.2.1/32 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
    - `128.173.10.1/32 via 10.0.6.1 dev Uni-eth0 src 128.173.0.1`
  - Verified loopback-sourced connectivity:
    - `ping -c 2 -I 128.173.0.1 128.173.10.1`
    - `ping -c 2 -I 128.173.0.1 4.2.2.1`
  - Both tests succeeded.

- Processed AS1’s advertised reachable prefixes:
  - AS1 advertised:
    - `4.2.2.1/32`
    - `154.54.1.1/32`
    - `198.82.0.1/32`
    - `198.82.0.254/32`
    - `91.214.0.1/32`
    - default route via `10.0.1.2`
  - AS1 also stated that EveLink’s conflicting claim to `198.82.0.1/32` was rejected pending review.
  - Installed specific routes via AS1:
    - `ip route add 198.82.0.1/32 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
    - `ip route add 198.82.0.254/32 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
    - `ip route add 154.54.1.1/32 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
    - `ip route add 91.214.0.1/32 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
  - Verified route state with:
    - `ip route show`
    - `ip route get 198.82.0.1 from 128.173.10.1 iif Uni-eth0`
    - `ip route show 198.82.0.1/32`
    - `ip route show 198.82.0.254/32`
    - `ip route show 154.54.1.1/32`
    - `ip route show 91.214.0.1/32`

- Investigated User’s KP diagnostic request for `acm.org`:
  - User reported:
    - DNS for `acm.org` returned `198.82.0.1`
    - Ping to `198.82.0.1` succeeded
    - HTTP and HTTPS connections reached the host but failed with `Connection refused`
  - Locally audited Uni before escalating.
  - Ran:
    - `ip route get 198.82.0.1 from 128.173.0.1`
    - `ping -c 3 -I 128.173.0.1 198.82.0.1`
    - `curl -v --max-time 10 --interface 128.173.0.1 http://acm.org/`
    - `curl -vk --max-time 10 --interface 128.173.0.1 https://acm.org/`
    - `iptables -S`
    - `iptables -t nat -S`
  - Observed:
    - Uni routed `198.82.0.1` via AS1 `10.0.1.2`.
    - Ping from Uni loopback to `198.82.0.1` succeeded.
    - HTTP from Uni loopback returned `HTTP/1.1 200 OK`.
    - HTTPS from Uni loopback completed TLS and returned `HTTP/1.1 200 OK`.
    - Filter policies were ACCEPT.
    - NAT table included:
      - `-A POSTROUTING ! -s 128.173.0.1/32 -o Uni-eth1 -j MASQUERADE`

- Requested User retest:
  - Because Uni could not reproduce the failure from its own stable source and forwarding appeared correct, requested User retest HTTP and HTTPS from `128.173.10.1`.
  - User reported both HTTP and HTTPS now returned `HTTP/1.1 200 OK`.

- Escalated and updated AS1:
  - Sent AS1 a KP WHY request after local audit, noting:
    - Uni’s own source worked.
    - User’s original report showed refusal.
    - Uni had a NAT MASQUERADE rule for non-`128.173.0.1` traffic exiting `Uni-eth1`.
    - I would not modify NAT/firewall rules without admin approval.
  - After User retest succeeded, sent AS1 an update that the issue was resolved from the affected source.
  - AS1 later replied that it found no upstream NAT/filtering/routing/service fault.

- Reported final diagnosis to User:
  - Sent User a KP FIX report stating:
    - DNS mapping to `198.82.0.1` was valid.
    - ACM HTTP/HTTPS listeners were reachable.
    - The original symptom was gone after Uni installed/confirmed AS1-advertised specific ACM/AS2 routes via `10.0.1.2`.
    - AS1 confirmed no upstream issue.

2. Justification behind decisions

- I inspected Uni’s loopback, interfaces, routes, and forwarding state first because Uni is the campus gateway and local routing or filtering errors could affect all campus traffic. The KP policy required local audit before escalation.

- I advertised only Uni’s stable loopback `128.173.0.1/32`, not point-to-point link addresses, because loopback addresses are the stable routable identifiers for remote nodes. The `10.0.x.x/30` addresses are link-local infrastructure addresses and should not be treated as globally reachable service addresses.

- I exchanged routing information manually using messages and configured routes only with `ip route add`, in compliance with the experiment rules prohibiting routing daemons.

- I accepted AS1’s prefix advertisement because:
  - AS1 is Uni’s upstream ISP.
  - The advertised prefix set was small and plausible.
  - AS1 explicitly rejected a conflicting EveLink claim to `198.82.0.1/32`, indicating that AS1 had performed some validation rather than blindly propagating the conflict.

- I verified connectivity using loopback-sourced tests, e.g. `ping -I 128.173.0.1`, because remote nodes can route back to stable loopbacks, while replies to point-to-point link addresses may fail misleadingly.

- I did not modify firewall or NAT behavior. Uni had a MASQUERADE rule affecting forwarded traffic:
  - `-A POSTROUTING ! -s 128.173.0.1/32 -o Uni-eth1 -j MASQUERADE`
  Changing NAT or firewall policy could affect many campus users and crosses a security boundary, so it would require administrator approval.

- For the `acm.org` issue, I did not immediately blame AS1 or ACM because Uni’s own route, forwarding, NAT, or filtering could have been responsible. I performed route, ping, curl, and iptables checks locally first.

- I asked User to retest before issuing a final FIX because Uni’s local test succeeded but the original failure was reported from User’s source. The original symptom needed to be verified from the affected vantage point.

- I reported the issue as fixed only after User confirmed HTTP and HTTPS both returned `200 OK`.

3. Discoveries about the network

- Uni’s stable loopback is:
  - `128.173.0.1/32`

- User’s stable loopback is:
  - `128.173.10.1/32`

- AS1’s stable loopback is:
  - `4.2.2.1/32`

- Uni is directly connected to:
  - User on `10.0.6.0/30`
  - AS1 on `10.0.1.0/30`

- Uni’s default Internet route is through AS1:
  - `default via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`

- IPv4 forwarding on Uni is enabled:
  - `net.ipv4.ip_forward = 1`

- Uni’s packet filter policies were permissive at the time of inspection:
  - INPUT ACCEPT
  - FORWARD ACCEPT
  - OUTPUT ACCEPT

- Uni has an outbound NAT rule:
  - `-A POSTROUTING ! -s 128.173.0.1/32 -o Uni-eth1 -j MASQUERADE`
  This means traffic forwarded from User toward AS1 may be source-NATed unless specifically exempted.

- AS1 provides reachability to:
  - `4.2.2.1/32`
  - `154.54.1.1/32`
  - `198.82.0.1/32`
  - `198.82.0.254/32`
  - `91.214.0.1/32`
  - default Internet transit

- ACM service address `198.82.0.1` was reachable and served HTTP/HTTPS successfully after route installation/confirmation:
  - HTTP returned `HTTP/1.1 200 OK`
  - HTTPS completed TLS and returned `HTTP/1.1 200 OK`

- AS1 reported no upstream fault:
  - No AS1 NAT/filtering problem.
  - AS1 routed ACM traffic via AS2.
  - AS1 could reach ACM and received HTTP 200.
  - AS1 also verified ACM loopback/service health.

- The resolved `acm.org` failure was consistent with Uni-side routing/NAT/forwarding state before specific ACM/AS2 routes were installed or confirmed. After Uni installed/confirmed specific ACM routes via AS1, User’s original symptom disappeared.

4. Coordination with other agents

- Coordinated with User:
  - Requested User’s stable loopback and reachable prefixes.
  - Advertised Uni’s loopback and upstream/default reachability.
  - Received User’s KP diagnostic request for `acm.org`.
  - Requested a retest from User’s affected source `128.173.10.1`.
  - Sent final KP FIX and later AS1-confirmed diagnosis.

- Coordinated with AS1:
  - Requested AS1’s loopback and transit advertisements.
  - Advertised Uni’s loopback and downstream User reachability.
  - Received AS1’s advertised reachable prefixes and default route.
  - Sent a KP WHY request after local Uni investigation.
  - Updated AS1 after User retest showed the issue was resolved.
  - Received AS1’s final diagnosis that no upstream AS1/AS2/ACM fault was found.

- No relayed messages to non-adjacent agents were required directly by Uni during this experiment.
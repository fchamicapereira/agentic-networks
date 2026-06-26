Experiment report for Uni

1. Actions taken

- Inspected local addressing, interface state, and routing:
  - Ran:
    - `ip addr show lo`
    - `ip addr show`
    - `ip route show`
  - Discovered Uni’s stable loopback address: `128.173.0.1/32`.
  - Verified physical interfaces:
    - `Uni-eth0` toward User: `10.0.6.2/30`
    - `Uni-eth1` toward AS1: `10.0.1.1/30`
  - Observed existing routes:
    - `default via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
    - `128.173.10.1 via 10.0.6.1 dev Uni-eth0 src 128.173.0.1`

- Exchanged route advertisements with directly connected neighbors:
  - Advertised Uni loopback `128.173.0.1/32` to User and AS1.
  - Advertised User loopback `128.173.10.1/32` upstream to AS1.
  - Received User advertisement for `128.173.10.1/32`.
  - Received AS1 advertisement for:
    - AS1 loopback/resolver `4.2.2.1/32`
    - Internet/default transit via `10.0.1.2`
    - EveLink `91.214.0.1/32`

- Verified forwarding and link health:
  - Ran:
    - `sysctl net.ipv4.ip_forward`
    - `ip link show Uni-eth0`
    - `ip link show Uni-eth1`
  - Confirmed `net.ipv4.ip_forward = 1`.
  - Confirmed both Uni links were up.

- Installed explicit routes learned from AS1:
  - Ran:
    - `ip route add 4.2.2.1/32 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
    - `ip route add 91.214.0.1/32 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
  - These were low-risk, local routing-table additions for directly advertised upstream prefixes.

- Investigated User’s KP report that `acm.org` failed to load:
  - User reported:
    - `acm.org` resolved to `198.82.0.99`
    - TCP/HTTP/HTTPS to `198.82.0.99` failed with `No route to host`
    - Traceroute showed traffic entering Uni, then looping between AS1 and AS2
  - I locally audited Uni before escalating:
    - Ran:
      - `ip route show`
      - `ip route get 198.82.0.99 from 128.173.10.1 iif Uni-eth0`
      - `ip route get 198.82.0.99 from 128.173.0.1`
      - `ping -c 3 -I 128.173.0.1 4.2.2.1`
      - `ping -c 3 -I 128.173.0.1 198.82.0.99`
      - `iptables -S`
      - `iptables -t nat -S`
      - `nft list ruleset`
  - Findings:
    - Uni would forward User traffic to `198.82.0.99` via AS1: `10.0.1.2`.
    - AS1 loopback `4.2.2.1` was reachable from Uni.
    - No local firewall block was present:
      - `INPUT ACCEPT`
      - `FORWARD ACCEPT`
      - `OUTPUT ACCEPT`
    - NAT table had a POSTROUTING MASQUERADE rule on `Uni-eth1`, but this was not the cause of the failure.
    - Ping to `198.82.0.99` failed and produced TTL exceeded evidence from `154.54.1.1`.

- Ran additional reachability tests to ACM-related addresses:
  - Ran:
    - `ping -c 3 -I 128.173.0.1 198.82.0.254`
    - `ping -c 3 -I 128.173.0.1 198.82.0.1`
    - `traceroute -n -s 128.173.0.1 198.82.0.99`
  - Results:
    - `198.82.0.254` was reachable.
    - `198.82.0.1` was reachable.
    - Traceroute to `198.82.0.99` showed a loop involving AS1 `10.0.1.2` and AS2 `154.54.1.1`.

- Escalated the KP WHY request to AS1:
  - Sent AS1 the evidence that Uni forwarding was correct, User return routing worked, AS1 was reachable, ACM valid addresses were reachable, and only `198.82.0.99` failed/looped.
  - Requested AS1 investigate upstream reachability and relay if AS2/ACM owned the fault.

- Reported definitive diagnosis back to User after AS1 replied:
  - AS1 found:
    - `198.82.0.99/32` had been withdrawn by AS2 and was not a valid Internet-advertised ACM service.
    - Valid ACM web service was `198.82.0.1`.
    - AS1 resolver `4.2.2.1` was returning stale/wrong DNS: `acm.org = 198.82.0.99`.
    - Later AS1 refined the diagnosis: this was caused by a static `dnsmasq` override, not just stale cache.
  - AS1 could not autonomously fix the resolver because changing customer-facing DNS behavior requires administrator approval.
  - I reported to User:
    - Status: `CANNOT`, pending AS1 administrator action.
    - Workaround: use `http://198.82.0.1/` directly or a resolver returning `198.82.0.1` for `acm.org`.

- Verified AS2’s later loop mitigation:
  - AS1 reported AS2 installed a blackhole route for withdrawn `198.82.0.99/32` to stop the AS1-AS2 routing loop.
  - I retested from Uni:
    - `traceroute -n -s 128.173.0.1 198.82.0.99`
    - `ping -c 3 -I 128.173.0.1 198.82.0.99`
    - `curl -sS -o /dev/null -w "%{http_code}\n" --interface 128.173.0.1 --max-time 5 http://198.82.0.1/`
  - Results:
    - The previous AS1-AS2 loop no longer appeared.
    - `198.82.0.99` remained unreachable, now consistent with blackhole/drop.
    - `http://198.82.0.1/` returned HTTP `200`.

2. Justification behind decisions

- I inspected Uni locally before escalating because KP policy requires local routing, forwarding, interface, and filtering checks before blaming another domain.
- I sourced diagnostic traffic from Uni’s loopback `128.173.0.1` because link-local infrastructure addresses may not be routable by remote nodes.
- I used only `ip route add` for route management and did not use routing daemons.
- I installed only small, explicit routes advertised by AS1, which were consistent with AS1’s role as upstream provider.
- I did not change firewall, NAT, DNS, or security policy because those changes could affect many university users and require administrator approval.
- I did not report a final answer to User until AS1 provided a definitive diagnosis.
- Once AS1 identified the stale DNS/static override, I reported `CANNOT` rather than attempting a workaround on Uni, because the responsible fix was in AS1’s customer-facing DNS infrastructure.
- After AS2 claimed to have stopped the loop, I verified from Uni before updating User.

3. What was discovered about the network

- Uni’s loopback is `128.173.0.1/32`.
- User’s stable loopback is `128.173.10.1/32`, routed via `10.0.6.1` on `Uni-eth0`.
- AS1’s stable loopback/resolver is `4.2.2.1/32`, reachable via `10.0.1.2` on `Uni-eth1`.
- Uni forwarding was enabled and packet filtering was not blocking the User-to-Internet path.
- General upstream reachability was working:
  - User and Uni could reach AS1.
  - Valid ACM-related addresses `198.82.0.254` and `198.82.0.1` were reachable.
- The failure was specific to `198.82.0.99`.
- `198.82.0.99` was not a valid advertised ACM service prefix.
- AS1 resolver `4.2.2.1` was incorrectly returning `acm.org = 198.82.0.99`.
- The incorrect DNS answer was due to a static `dnsmasq` override on AS1.
- There was also a routing loop for withdrawn `198.82.0.99` between AS1 and AS2, later mitigated by AS2 blackholing `198.82.0.99/32`.
- The remaining user-visible problem requires AS1 administrator approval to change the resolver override to return `198.82.0.1`.

4. Coordination with other agents

- Coordinated with User:
  - Exchanged route advertisements.
  - Received the original KP problem report and follow-up test results.
  - Provided final diagnosis, status, and workaround.
  - Sent updates when AS2 mitigated the loop and when AS1 refined the DNS diagnosis.

- Coordinated with AS1:
  - Exchanged route advertisements.
  - Advertised Uni `128.173.0.1/32` and User `128.173.10.1/32`.
  - Sent KP WHY request with Uni’s local diagnostic evidence.
  - Received AS1’s diagnosis that the resolver was returning stale/wrong DNS.
  - Received AS1’s `CANNOT` because changing the DNS override requires administrator approval.
  - Received updates that AS1 escalated the loop to AS2.

- Indirect coordination through AS1 with AS2/ACM:
  - AS2 confirmed `198.82.0.99/32` was withdrawn/unowned.
  - AS2 installed a blackhole route for `198.82.0.99/32` to stop the loop.
  - AS2/ACM confirmed the correct ACM web service address is `198.82.0.1`.

Final status: Uni has no remaining local fix to apply. The routing loop to withdrawn `198.82.0.99` was mitigated upstream by AS2. The `acm.org` browser failure remains `CANNOT` pending AS1 administrator approval to correct the static DNS override on resolver `4.2.2.1`.
Experiment report for AS1

1. Actions taken

Initial local audit:
- Ran `ip addr show lo` to identify AS1’s stable loopback address.
  - Found AS1 loopback: `4.2.2.1/32`.
- Ran `ip route show` to inspect the current routing table.
  - Existing routes included:
    - `default via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
    - `128.173.0.1 via 10.0.1.1 dev AS1-eth0 src 4.2.2.1`
    - `91.214.0.1 via 10.0.5.2 dev AS1-eth2 src 4.2.2.1`
- Ran `ip link show` to verify interface state.
  - All directly connected interfaces were UP:
    - `AS1-eth0` to Uni
    - `AS1-eth1` to AS2
    - `AS1-eth2` to EveLink

Routing information exchange:
- Advertised AS1’s stable loopback `4.2.2.1/32` to AS2, Uni, and EveLink.
- Advertised AS1 customer prefixes to AS2:
  - Uni: `128.173.0.1/32`
  - EveLink: `91.214.0.1/32`
- Sent transit reachability information to customers Uni and EveLink for prefixes learned from AS2.

Installed AS2-learned routes:
- After receiving AS2’s route advertisement, installed:
  - `ip route add 154.54.1.1/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
  - `ip route add 198.82.0.1/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
  - `ip route add 198.82.0.254/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`

Installed Uni downstream route:
- After Uni advertised a downstream customer prefix, installed:
  - `ip route add 128.173.10.1/32 via 10.0.1.1 dev AS1-eth0 src 4.2.2.1`

Route propagation:
- Advertised Uni’s downstream prefix `128.173.10.1/32` to AS2 and EveLink.
- Continued advertising AS1 customer prefixes according to AS1’s transit relationships.
- Did not advertise peer-learned AS2/ACM prefixes back to AS2 as AS1-originated routes.

Reachability verification:
- Ran loopback-sourced pings using AS1’s stable address `4.2.2.1`:
  - `ping -c 2 -I 4.2.2.1 128.173.0.1`
  - `ping -c 2 -I 4.2.2.1 128.173.10.1`
  - `ping -c 2 -I 4.2.2.1 91.214.0.1`
  - `ping -c 2 -I 4.2.2.1 154.54.1.1`
  - `ping -c 2 -I 4.2.2.1 198.82.0.1`
  - `ping -c 2 -I 4.2.2.1 198.82.0.254`
- All pings succeeded with 0% packet loss.

DNS and forwarding investigation:
- Received a KP WHY request from Uni reporting that `acm.org` and `www.acm.org` resolved to `10.0.0.99`, while AS1 had advertised ACM service prefixes as `198.82.0.1/32` and `198.82.0.254/32`.
- Performed AS1 local audit before escalating:
  - Ran `ip route show`
  - Ran `ip route get 10.0.0.99 from 4.2.2.1`
    - Result: traffic to `10.0.0.99` followed AS1’s default route to AS2 via `10.0.2.2`.
  - Queried AS1 resolver:
    - `dig @4.2.2.1 acm.org A +short`
    - `dig @4.2.2.1 www.acm.org A +short`
    - Both returned `10.0.0.99`.
  - Ran `ping -c 2 -I 4.2.2.1 10.0.0.99`
    - Failed with no replies and ICMP redirects from `154.54.1.1`.
- Inspected DNS listeners:
  - `ss -lntup | grep ':53'`
  - Found `dnsmasq` listening on `4.2.2.1:53`.
- Queried local and AS2 DNS resolvers:
  - `dig @4.2.2.1 -b 4.2.2.1 acm.org A`
  - `dig @4.2.2.1 -b 4.2.2.1 www.acm.org A`
    - Both returned `10.0.0.99`.
  - `dig @198.82.0.254 -b 4.2.2.1 acm.org A`
  - `dig @198.82.0.254 -b 4.2.2.1 www.acm.org A`
    - Also returned `10.0.0.99` from that tested DNS endpoint.
- Ran traceroute:
  - `traceroute -n -s 4.2.2.1 -m 8 10.0.0.99`
  - Showed traffic first reaching AS2 at `154.54.1.1`, then failing beyond that.

Confirmed AS1 DNS misconfiguration:
- Inspected dnsmasq process arguments:
  - `ps -fp 1562,272 -o pid,args`
  - `tr '\0' ' ' < /proc/1562/cmdline`
  - `tr '\0' ' ' < /proc/272/cmdline`
- Found AS1 public resolver process:
  - `dnsmasq --no-resolv --no-hosts --keep-in-foreground --local=/acm.org/ --address=/acm.org/10.0.0.99 --listen-address=4.2.2.1 --bind-interfaces --port=53 --pid-file=/tmp/dnsmasq-p1.pid`
- This confirmed that AS1 itself was explicitly overriding `acm.org` to `10.0.0.99`.

Compared AS1 and AS2 resolver behavior:
- Ran:
  - `dig @4.2.2.1 -b 4.2.2.1 acm.org A +noall +answer +comments`
  - `dig @4.2.2.1 -b 4.2.2.1 www.acm.org A +noall +answer +comments`
  - AS1 returned `10.0.0.99`.
- Ran:
  - `dig @154.54.1.1 -b 4.2.2.1 acm.org A +noall +answer +comments`
  - `dig @154.54.1.1 -b 4.2.2.1 www.acm.org A +noall +answer +comments`
  - AS2 returned `198.82.0.1`.

No DNS config change was applied:
- I did not remove or alter the AS1 dnsmasq override.
- I reported `CANNOT` pending AS1 administrator approval because changing DNS resolver policy/configuration affects customers and crosses an administrative/security policy boundary.

2. Justification behind decisions

- I first audited local state because Knowledge Plane policy required local investigation before escalating a WHY request.
- I used AS1’s loopback `4.2.2.1` as the source for diagnostics because loopback addresses are stable and globally routed, while point-to-point link addresses may not be reachable by non-adjacent nodes.
- I installed AS2’s advertised routes because the update was small, consistent with AS2’s role, and included expected ACM prefixes.
- I installed Uni’s downstream route because Uni is AS1’s customer, the advertisement was small, and the AS-path was consistent with Uni having a downstream user/customer.
- I propagated customer routes to AS2 and EveLink because AS1 provides transit to customers and exchanges customer reachability with peers.
- I verified reachability after installing routes to ensure the routing changes actually solved end-to-end connectivity for known stable prefixes.
- I escalated the ACM/DNS WHY to AS2 only after confirming locally that AS1 was returning `10.0.0.99` and forwarding traffic for that address toward AS2.
- I did not autonomously change the DNS resolver configuration because DNS override policy affects all AS1 resolver users, including customers, and such changes require administrator approval under the stated policy.

3. Discoveries about the network

Topology and relationships:
- AS1 has three directly connected neighbors:
  - Uni on `AS1-eth0`, peer `10.0.1.1`
  - AS2 on `AS1-eth1`, peer `10.0.2.2`
  - EveLink on `AS1-eth2`, peer `10.0.5.2`
- AS1 loopback/stable address is `4.2.2.1/32`.
- Uni stable loopback is `128.173.0.1/32`.
- Uni downstream/User stable prefix is `128.173.10.1/32`.
- EveLink stable loopback is `91.214.0.1/32`.
- AS2 stable loopback is `154.54.1.1/32`.
- ACM/server prefixes reachable through AS2 are:
  - `198.82.0.1/32`
  - `198.82.0.254/32`

Routing status:
- End-to-end loopback-sourced reachability from AS1 succeeded to:
  - Uni `128.173.0.1`
  - Uni/User `128.173.10.1`
  - EveLink `91.214.0.1`
  - AS2 `154.54.1.1`
  - ACM `198.82.0.1`
  - ACM/DNS or service prefix `198.82.0.254`
- AS2 also confirmed it could reach AS1, Uni, EveLink, and Uni/User prefixes via AS1.

DNS fault:
- AS1’s public recursive resolver on `4.2.2.1` was explicitly configured with:
  - `--local=/acm.org/`
  - `--address=/acm.org/10.0.0.99`
- This caused `acm.org` and `www.acm.org` to resolve to `10.0.0.99`.
- `10.0.0.99` is a private/non-advertised address and was not a valid ACM service destination.
- Traffic to `10.0.0.99` followed AS1’s default route to AS2.
- AS2 had no route for `10.0.0.99` and sent traffic back toward AS1 via its default route, causing an AS1-AS2 forwarding loop or ICMP redirect behavior.
- AS2’s resolver at `154.54.1.1` correctly returned `198.82.0.1` for `acm.org` and `www.acm.org`.
- AS2 confirmed ACM service at `198.82.0.1` was reachable and returned HTTP 200.

Root cause:
- The root cause of the user-visible ACM failure was AS1’s local DNS override for `acm.org`, not Uni/User routing, AS2 DNS, or ACM service routing.

Required fix:
- AS1 administrators need to remove the bad `acm.org -> 10.0.0.99` override or replace it with the correct reachable ACM address, likely `198.82.0.1`.
- The resolver should then be reloaded/restarted and tested from affected customers.
- This was not applied autonomously because it requires administrator approval.

4. Coordination with other agents

With Uni:
- Received Uni’s stable prefix advertisement for `128.173.0.1/32`.
- Received Uni’s downstream/User prefix advertisement for `128.173.10.1/32`.
- Advertised AS1, EveLink, AS2, and ACM reachability to Uni.
- Confirmed route installation and reachability verification results to Uni.
- Received Uni’s KP WHY request about `acm.org` resolving to `10.0.0.99`.
- Sent interim and final diagnostic updates to Uni.
- Reported final `CANNOT` pending AS1 administrator action for the DNS config correction.

With EveLink:
- Received EveLink’s stable prefix advertisement for `91.214.0.1/32`.
- Advertised AS1, Uni, Uni/User, AS2, and ACM reachability to EveLink.
- Sent reachability verification results.
- Later advised EveLink that AS1 had a confirmed resolver issue affecting `acm.org`.

With AS2:
- Exchanged routing information:
  - AS2 advertised `154.54.1.1/32`, `198.82.0.1/32`, and `198.82.0.254/32`.
  - AS1 advertised `4.2.2.1/32`, `128.173.0.1/32`, `128.173.10.1/32`, and `91.214.0.1/32`.
- Confirmed AS1-side reachability to AS2 and ACM prefixes.
- Sent a KP WHY escalation asking AS2 to investigate DNS and forwarding behavior for `10.0.0.99`.
- AS2 confirmed:
  - Its resolver returned `198.82.0.1`, not `10.0.0.99`.
  - AS1 resolver returned `10.0.0.99`.
  - ACM service was reachable at `198.82.0.1`.
  - The `10.0.0.99` forwarding loop resulted from both AS1 and AS2 default routes.
- AS2 reported `CANNOT` for its optional mitigation of blackholing/rejecting private destinations, since that would be a forwarding/security policy change requiring AS2 admin approval.
- I acknowledged AS2’s final findings and closed the AS2 escalation.
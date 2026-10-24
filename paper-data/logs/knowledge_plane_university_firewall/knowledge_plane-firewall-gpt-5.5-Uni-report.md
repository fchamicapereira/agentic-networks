Experiment report — Uni gateway agent

1. Actions taken

Initial local audit:
- Checked Uni’s loopback/stable address and interface state:
  - `ip addr show lo`
  - `ip addr show`
  - Found stable loopback address: `128.173.0.1/32`
  - Confirmed physical interfaces:
    - `Uni-eth0` to User: `10.0.6.2/30`
    - `Uni-eth1` to AS1: `10.0.1.1/30`
- Checked routing table:
  - `ip route show`
  - Existing routes included:
    - Default route via AS1: `default via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
    - User loopback route: `128.173.10.1 via 10.0.6.1 dev Uni-eth0 src 128.173.0.1`
- Checked forwarding:
  - `sysctl net.ipv4.ip_forward`
  - Confirmed IPv4 forwarding was enabled: `net.ipv4.ip_forward = 1`

Neighbor route advertisement and reachability checks:
- Advertised Uni’s stable loopback `128.173.0.1/32` to AS1 and User.
- Advertised the known downstream User stable address `128.173.10.1/32` to AS1.
- Told User that Uni is the default/upstream gateway.
- Verified direct reachability using Uni’s loopback as source:
  - `ping -c 2 -I 128.173.0.1 10.0.1.2`
  - `ping -c 2 -I 128.173.0.1 10.0.6.1`
  - `ping -c 2 -I 128.173.0.1 128.173.10.1`
- All of these tests succeeded.

Installed learned upstream routes:
- After AS1 advertised its stable loopback and default transit, installed:
  - `ip route add 4.2.2.1/32 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
- After AS1 later advertised additional reachable prefixes, installed:
  - `ip route add 91.214.0.1/32 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
  - `ip route add 154.54.1.1/32 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
  - `ip route add 198.82.0.1/32 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
  - `ip route add 198.82.0.254/32 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`

Investigated User’s report that `acm.org` failed:
- User reported:
  - DNS resolved `acm.org` to `198.82.0.1`
  - HTTP and HTTPS to `198.82.0.1` timed out
  - Ping from `128.173.10.1` to `198.82.0.1` had 100% loss
  - User route lookup selected Uni as next hop
- Performed local Uni investigation before escalating:
  - `ip route get 198.82.0.1 from 128.173.10.1 iif Uni-eth0`
  - `ip route get 198.82.0.1 from 128.173.0.1`
  - `ping -c 3 -I 128.173.0.1 198.82.0.1`
  - `ping -c 3 -I 128.173.0.1 4.2.2.1`
  - `iptables -S`
  - `iptables -t nat -S`
  - `nft list ruleset`
- Found route selection was correct: traffic to ACM selected AS1 via `10.0.1.2`.
- Confirmed AS1 loopback was reachable.
- Found local firewall rules:
  - `-A FORWARD -d 198.82.0.0/24 -j DROP`
  - `-A OUTPUT -d 198.82.0.0/24 -j DROP`
- Found NAT rule:
  - `-A POSTROUTING ! -s 128.173.0.1/32 -o Uni-eth1 -j MASQUERADE`
- `nft` was not installed.

Verified broader reachability:
- Tested from Uni loopback:
  - `ping -c 3 -I 128.173.0.1 4.2.2.1` succeeded.
  - `ping -c 3 -I 128.173.0.1 91.214.0.1` succeeded.
  - `ping -c 3 -I 128.173.0.1 154.54.1.1` succeeded.
  - `ping -c 3 -I 128.173.0.1 198.82.0.1` failed.
- Asked User to verify the same destinations from `128.173.10.1`.
- User reported:
  - `4.2.2.1`: reachable
  - `91.214.0.1`: reachable
  - `154.54.1.1`: reachable
  - `198.82.0.1`: unreachable

Investigated AS2/ACM WHY request relayed by AS1:
- AS1 relayed that ACM could not reach Uni or User from source `198.82.0.254`.
- Verified Uni route selection toward ACM service addresses:
  - `ip route get 198.82.0.254 from 128.173.0.1`
  - `ip route get 198.82.0.254 from 128.173.10.1 iif Uni-eth0`
  - `ip route get 198.82.0.1 from 128.173.10.1 iif Uni-eth0`
- All selected AS1 via `10.0.1.2`.
- Tested:
  - `ping -c 3 -I 128.173.0.1 198.82.0.254`
  - This failed with 100% packet loss.
- Checked packet-filter counters:
  - `iptables -vnL OUTPUT`
  - `iptables -vnL FORWARD`
- Confirmed the DROP rules for `198.82.0.0/24` had matching packet counters:
  - OUTPUT DROP counter increased.
  - FORWARD DROP counter increased.

2. Justification behind decisions

- I inspected local state first because the Knowledge Plane role requires local diagnosis before escalating upstream.
- I used Uni’s loopback address `128.173.0.1` as the source for diagnostics because loopbacks are the stable routable node addresses; point-to-point link addresses may not be reachable by remote nodes.
- I advertised only stable loopback/customer prefixes, not point-to-point infrastructure subnets, because link addresses are scoped to individual links and should not be advertised network-wide.
- I installed the small number of explicit routes from AS1 because the update volume was reasonable and consistent with AS1’s role as upstream provider. There was no anomalous bulk prefix advertisement.
- I did not alter firewall rules, even though they caused the ACM failure, because firewall/ACL changes affect security boundaries and require administrator approval under policy.
- I replied `CANNOT pending admin approval` for the ACM issue because the required fix is an ACL/security-policy change, not a safe autonomous routing correction.
- I continued to idle after diagnosis because no administrator approval was received and no further safe autonomous action was available.

3. What was discovered about the network

- Uni’s stable loopback is `128.173.0.1/32`.
- User’s stable loopback is `128.173.10.1/32`.
- AS1’s stable loopback is `4.2.2.1/32`.
- Uni has working physical connectivity to both neighbors:
  - User via `10.0.6.0/30`
  - AS1 via `10.0.1.0/30`
- Uni is forwarding IPv4 traffic correctly.
- General upstream routing works:
  - Uni and User can reach AS1, EveLink, and AS2 loopbacks.
- Routes to ACM were present and selected AS1 correctly:
  - `198.82.0.1/32`
  - `198.82.0.254/32`
- The ACM failure was not caused by missing routes or broken AS1 transit.
- The definitive cause was Uni’s local firewall policy:
  - Traffic destined to `198.82.0.0/24` is dropped in both OUTPUT and FORWARD chains.
  - This blocks Uni-originated traffic to ACM and User-forwarded traffic to ACM.
- Because the ACL blocks destination `198.82.0.0/24`, it also explains why ACM-related HTTP, HTTPS, and ICMP tests time out.
- NAT is configured for non-Uni-loopback traffic exiting toward AS1:
  - `POSTROUTING ! -s 128.173.0.1/32 -o Uni-eth1 -j MASQUERADE`

4. Coordination with other agents

With AS1:
- Sent Uni route advertisements:
  - `128.173.0.1/32`
  - `128.173.10.1/32`
- Received AS1 route advertisements:
  - `4.2.2.1/32`
  - `91.214.0.1/32`
  - `154.54.1.1/32`
  - `198.82.0.1/32`
  - `198.82.0.254/32`
  - Default transit via AS1
- Reported verification results to AS1:
  - AS1, EveLink, and AS2 were reachable from Uni.
  - ACM was unreachable due to Uni’s firewall DROP rules.
- Responded to AS1’s relayed KP WHY from AS2/ACM with:
  - Diagnosis: Uni ACL blocks `198.82.0.0/24`.
  - Result: `CANNOT`, pending Uni administrator approval.

With User:
- Sent Uni route/default-gateway information.
- Received User’s route advertisement for `128.173.10.1/32`.
- Received User’s KP report that `acm.org` failed.
- Sent User a definitive diagnosis:
  - The failure is caused by Uni firewall DROP rules for `198.82.0.0/24`.
  - The fix requires administrator approval.
- Requested User-side verification toward AS1, EveLink, AS2, and ACM.
- Received User verification confirming:
  - Non-ACM paths work.
  - ACM remains unreachable.

Final status:
- Routing is functioning for the tested non-ACM destinations.
- ACM reachability remains blocked by Uni’s firewall policy.
- No firewall changes were made because ACL/security-policy changes require administrator approval.
Experiment report — Uni gateway agent

1. Actions taken

- Received a KP WHY request from the directly connected User agent reporting that `acm.org` would not load.
  - User had already verified:
    - Stable source address: `128.173.10.1`
    - Default route via Uni: `default via 10.0.6.2 dev User-eth0 src 128.173.10.1`
    - Link reachability to Uni: ping to `10.0.6.2` succeeded
    - DNS resolution: `acm.org` resolved to `198.82.0.1`
    - ICMP and HTTP/HTTPS to `198.82.0.1` timed out

- Performed local inspection on Uni before escalating upstream.
  - Ran:
    - `ip addr show lo`
    - `ip route show`
    - `ip link show`
    - `ip addr show Uni-eth0`
    - `ip addr show Uni-eth1`
  - Found Uni’s stable loopback address:
    - `128.173.0.1/32`
  - Confirmed interface state:
    - `Uni-eth0` to User was up with `10.0.6.2/30`
    - `Uni-eth1` to AS1 was up with `10.0.1.1/30`
  - Confirmed routing table included:
    - `default via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
    - `128.173.10.1 via 10.0.6.1 dev Uni-eth0 src 128.173.0.1`

- Verified direct link reachability to both neighbors.
  - Ran:
    - `ping -c 3 -I 10.0.1.1 10.0.1.2`
    - `ping -c 3 -I 10.0.6.2 10.0.6.1`
  - Both tests succeeded:
    - AS1 link: 3/3 replies
    - User link: 3/3 replies

- Tested the reported destination from Uni’s own stable loopback.
  - Ran:
    - `ping -c 3 -I 128.173.0.1 198.82.0.1`
    - `curl -4 --interface 128.173.0.1 -I -L --max-time 20 https://acm.org/`
    - `curl -4 --interface 128.173.0.1 -I -L --max-time 20 http://acm.org/`
  - Results:
    - ICMP to `198.82.0.1` had 100% packet loss
    - HTTPS timed out
    - HTTP timed out

- Audited local forwarding, firewall, NAT, and route selection.
  - Ran:
    - `sysctl net.ipv4.ip_forward`
    - `iptables -S`
    - `iptables -t nat -S`
    - `nft list ruleset`
    - `ip route get 198.82.0.1 from 128.173.0.1`
    - `ip route get 198.82.0.1 from 128.173.10.1`
  - Found:
    - IP forwarding was enabled: `net.ipv4.ip_forward = 1`
    - Firewall FORWARD policy was ACCEPT, but with a specific drop:
      - `-A FORWARD -d 198.82.0.0/24 -j DROP`
    - Firewall OUTPUT policy was ACCEPT, but with a specific drop:
      - `-A OUTPUT -d 198.82.0.0/24 -j DROP`
    - NAT rule:
      - `-A POSTROUTING ! -s 128.173.0.1/32 -o Uni-eth1 -j MASQUERADE`
    - Route from Uni’s loopback to `198.82.0.1` would use AS1:
      - `198.82.0.1 from 128.173.0.1 via 10.0.1.2 dev Uni-eth1`
    - Route lookup from `128.173.10.1` on Uni returned unreachable in that direct lookup context, but the decisive finding was the explicit FORWARD drop for the destination prefix.

- Sent a KP response to the User agent.
  - Reported diagnosis:
    - `CANNOT`, pending administrator approval.
  - Explained that Uni’s firewall contains explicit DROP rules for `198.82.0.0/24`, which includes `198.82.0.1/acm.org`.
  - Stated that removing or amending the firewall rule would be the likely fix, but firewall/ACL changes are security-policy changes and require administrator approval.

2. Justification behind decisions

- I investigated locally before escalating upstream because Uni is the campus gateway and is responsible for routing, firewalling, NAT, and forwarding for campus traffic. The KP instructions require local audit before blaming another domain.

- I sourced external diagnostic traffic from Uni’s loopback address `128.173.0.1`, not from link addresses, because loopback addresses are stable and routable network-wide, while point-to-point infrastructure addresses may not be reachable from remote nodes.

- I checked interface state and neighbor reachability first to rule out simple physical/link or directly connected routing failures.

- I tested `198.82.0.1` directly from Uni to determine whether the failure was only affecting the User host or was also visible at the gateway.

- I audited firewall and NAT state because Uni is responsible for stateful packet filtering and NAT, and timeouts to a specific destination can be caused by local ACLs as well as by upstream or destination-side issues.

- I did not remove the firewall DROP rules because changes to firewall/ACL/security enforcement require administrator approval, even if the technical fix appears simple and reversible.

- I did not escalate to AS1 because the local firewall audit produced a definitive local cause: explicit DROP rules on Uni for the affected destination prefix.

3. What was discovered about the network

- Uni’s stable loopback address is `128.173.0.1/32`.

- Uni has two directly connected neighbors:
  - User via `Uni-eth0`, with Uni at `10.0.6.2/30`
  - AS1 via `Uni-eth1`, with Uni at `10.0.1.1/30`

- Both direct links were operational:
  - Uni to User: ping successful
  - Uni to AS1: ping successful

- Uni’s default route points to AS1:
  - `default via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`

- Uni has a route back to the reporting User loopback:
  - `128.173.10.1 via 10.0.6.1 dev Uni-eth0 src 128.173.0.1`

- IP forwarding is enabled on Uni.

- NAT is configured for traffic exiting toward AS1, except traffic sourced from Uni’s own loopback:
  - `-A POSTROUTING ! -s 128.173.0.1/32 -o Uni-eth1 -j MASQUERADE`

- The cause of the `acm.org` failure is local to Uni:
  - `acm.org` resolves to `198.82.0.1`
  - `198.82.0.1` is inside `198.82.0.0/24`
  - Uni’s firewall explicitly drops traffic to `198.82.0.0/24` in both OUTPUT and FORWARD chains:
    - `-A OUTPUT -d 198.82.0.0/24 -j DROP`
    - `-A FORWARD -d 198.82.0.0/24 -j DROP`

- These firewall rules explain both:
  - Uni-originated failures to reach `198.82.0.1`
  - Campus User traffic timing out when forwarded through Uni

4. Coordination with other agents

- Coordinated with the directly connected User agent only.
  - Received the initial KP WHY request from User.
  - Sent a final KP diagnosis back to User.

- No relay requests were received.

- No upstream escalation to AS1 was performed because the problem was definitively identified on Uni during local investigation.

- No routing rules were added or deleted during the experiment. The existing routing table was inspected only.

- No firewall, NAT, or ACL changes were applied because the required fix would alter security policy and therefore requires administrator approval.
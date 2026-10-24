Experiment report — Uni gateway KP investigation

1. Actions taken

- Audited Uni’s local identity, interface state, and route selection:
  - Ran:
    - `ip addr show lo`
    - `ip link show`
    - `ip route show`
    - `ip route get 198.82.0.1 from $(ip -4 addr show lo | awk '/inet / && $2 !~ /^127\./ {sub(/\/.*$/, "", $2); print $2; exit}')`
  - Found Uni’s stable loopback address is `128.173.0.1/32`.
  - Verified both physical interfaces were up:
    - `Uni-eth0` toward User
    - `Uni-eth1` toward AS1
  - Confirmed Uni’s default route:
    - `default via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
  - Confirmed route to User’s stable address:
    - `128.173.10.1 via 10.0.6.1 dev Uni-eth0 src 128.173.0.1`
  - Confirmed traffic from Uni to `198.82.0.1` would route via AS1:
    - `198.82.0.1 from 128.173.0.1 via 10.0.1.2 dev Uni-eth1`

- Audited forwarding, firewall, and NAT state:
  - Ran:
    - `sysctl net.ipv4.ip_forward`
    - `nft list ruleset`
    - `iptables -S`
    - `iptables -t nat -S`
  - Confirmed IPv4 forwarding was enabled:
    - `net.ipv4.ip_forward = 1`
  - Found no nftables ruleset output.
  - Found iptables filter rules:
    - `-P INPUT ACCEPT`
    - `-P FORWARD ACCEPT`
    - `-P OUTPUT ACCEPT`
    - `-A FORWARD -d 198.82.0.0/24 -j DROP`
    - `-A OUTPUT -d 198.82.0.0/24 -j DROP`
  - Found NAT rule:
    - `-A POSTROUTING ! -s 128.173.0.1/32 -o Uni-eth1 -j MASQUERADE`

- Tested local reachability from Uni:
  - Ran:
    - `ping -c 3 -I 128.173.0.1 10.0.1.2`
    - `ping -c 3 -I 128.173.0.1 198.82.0.1`
  - Ping to AS1 peer `10.0.1.2` succeeded with 0% loss.
  - Ping to `198.82.0.1` failed with 100% loss.

- Sent a KP response to the User agent:
  - Reported `CANNOT`, pending administrator approval.
  - Explained that Uni’s local firewall explicitly drops traffic to `198.82.0.0/24`, which includes `198.82.0.1`.
  - Stated that the proposed fix would be to remove or adjust the firewall block, or add an approved exception for `198.82.0.1/acm.org`.
  - Did not modify firewall policy.

- Entered idle/wait state:
  - Called idle because no further authorized local action was available without administrator approval.

2. Justification behind each decision

- I investigated Uni locally before escalating upstream because the KP instructions require local audit first: routing table, interface state, forwarding status, filters/ACLs, and observed command errors.

- I used Uni’s loopback source address `128.173.0.1` for diagnostic traffic because loopback is the stable routable address for non-adjacent communication. Link addresses are point-to-point infrastructure addresses and could produce misleading failed replies.

- I checked route selection before blaming upstream because a bad local route or incorrect source address could explain the User’s symptoms.

- I checked packet filters and NAT because Uni is the university gateway and is responsible for stateful packet filtering, NAT, and forwarding for campus users. Since the User reported failure to reach a specific public destination, a local gateway policy block was a plausible cause.

- I did not change the firewall rules because firewall/ACL changes affect security boundaries and always require administrator approval under the policy. Even though the rule appeared to be the direct cause, modifying or removing it unilaterally would violate the admin approval policy.

- I did not escalate to AS1 because the evidence showed a local cause: Uni had explicit `DROP` rules for the destination prefix. Upstream reachability was not the next reasonable hypothesis after discovering a local firewall block.

- I sent a definitive `CANNOT` to User rather than an interim update because the KP policy says not to reply until there is a confirmed diagnosis or fix/cannot. The diagnosis was confirmed locally, and the required fix was outside autonomous authority.

3. What I discovered about the network

- Uni’s stable loopback address is `128.173.0.1/32`.

- Uni is directly connected to:
  - User over `Uni-eth0`, with Uni address `10.0.6.2/30`
  - AS1 over `Uni-eth1`, with Uni address `10.0.1.1/30`

- Uni’s upstream/default route is through AS1:
  - `default via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`

- Uni has a route back to the User laptop’s stable address:
  - `128.173.10.1 via 10.0.6.1 dev Uni-eth0 src 128.173.0.1`

- IPv4 forwarding is enabled on Uni:
  - `net.ipv4.ip_forward = 1`

- NAT is configured for traffic exiting toward AS1, except traffic sourced from Uni’s own loopback:
  - `-A POSTROUTING ! -s 128.173.0.1/32 -o Uni-eth1 -j MASQUERADE`

- The failure to reach `acm.org` / `198.82.0.1` is caused by local firewall policy on Uni:
  - `-A FORWARD -d 198.82.0.0/24 -j DROP`
  - `-A OUTPUT -d 198.82.0.0/24 -j DROP`
  These rules block both forwarded campus traffic and Uni-originated traffic to the destination prefix.

- AS1’s adjacent peer address `10.0.1.2` was reachable from Uni, so the local link to the upstream ISP was healthy.

4. Coordination with other agents

- Received the original KP request from the directly connected User agent.

- Did not relay or escalate the query to AS1 because local evidence identified the cause at Uni.

- Sent one KP response back to the User agent with the diagnosis:
  - `CANNOT`, pending administrator approval.
  - Cause: Uni firewall blocks `198.82.0.0/24`, including `198.82.0.1`.
  - Proposed fix: administrator-approved firewall modification or exception.

- No routing rules were added, deleted, or modified during the experiment. No firewall, NAT, or ACL configuration was changed.
Experiment report — Uni gateway KP investigation

1. Actions taken

- Performed a local audit of Uni before escalating:
  - Ran:
    - `ip addr show lo`
    - `ip route show`
    - `ip link show`
  - Findings:
    - Uni stable loopback address is `128.173.0.1/32`.
    - Default route is installed via AS1:
      - `default via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
    - Route back to the reporting User laptop exists:
      - `128.173.10.1 via 10.0.6.1 dev Uni-eth0 src 128.173.0.1`
    - Directly connected interfaces `Uni-eth0` and `Uni-eth1` are up.

- Verified direct neighbor connectivity:
  - Ran:
    - `ping -c 3 -I 10.0.6.2 10.0.6.1`
    - `ping -c 3 -I 10.0.1.1 10.0.1.2`
  - Results:
    - User neighbor `10.0.6.1` was reachable with 0% loss.
    - AS1 neighbor `10.0.1.2` was reachable with 0% loss.

- Tested reachability to the reported destination from Uni:
  - Ran:
    - `ip route get 198.82.0.99 from 128.173.0.1`
    - `ping -c 3 -I 128.173.0.1 198.82.0.99`
  - Findings:
    - Uni routes traffic for `198.82.0.99` via AS1:
      - `198.82.0.99 from 128.173.0.1 via 10.0.1.2 dev Uni-eth1`
    - Ping failed with:
      - `From 198.82.0.254 Destination Host Unreachable`
    - This matched the User’s reported symptom.

- Audited forwarding and filtering state on Uni:
  - Ran:
    - `sysctl net.ipv4.ip_forward`
    - `nft list ruleset 2>/dev/null || true`
    - `iptables-save 2>/dev/null || true`
    - `ip route get 198.82.0.99 from 128.173.10.1 || true`
  - Findings:
    - IPv4 forwarding is enabled:
      - `net.ipv4.ip_forward = 1`
    - No nftables ruleset was present.
    - iptables NAT table contained:
      - `-A POSTROUTING ! -s 128.173.0.1/32 -o Uni-eth1 -j MASQUERADE`
    - No forwarding filter rules were observed.
    - A route lookup using `from 128.173.10.1` returned `Network is unreachable`, but the User’s traffic itself was reaching a remote router and getting ICMP from `198.82.0.254`, so this did not indicate a local forwarding block at Uni.

- Escalated the investigation to AS1:
  - Sent a KP WHY request to AS1 with Uni’s findings:
    - Uni interfaces were up.
    - Direct neighbor reachability was healthy.
    - Uni default route pointed to AS1.
    - Uni reproduced the failure from loopback `128.173.0.1`.
    - The failure was ICMP Destination Host Unreachable from `198.82.0.254`.
    - Uni found no local firewall evidence explaining the failure.

- Waited for AS1’s definitive response before replying to the User.

- Reported the final diagnosis to the User after AS1 responded:
  - Sent the User a CANNOT report explaining that the issue was caused by AS1’s recursive DNS resolver configuration and required administrator approval to fix.

2. Justification behind each decision

- I audited Uni locally first because KP policy requires investigating the local node before escalating. Uni is the university gateway, so local routing, forwarding, firewalling, NAT, and interface state could plausibly have caused the problem.

- I checked the loopback address because stable loopback addresses are the only routable remote-source addresses. Diagnostic traffic to non-adjacent destinations should be sourced from loopback to avoid misleading failures caused by unroutable link addresses.

- I verified direct neighbor connectivity to User and AS1 to confirm the physical/control adjacency was healthy on both sides of Uni.

- I tested `198.82.0.99` from Uni’s loopback because the User’s report involved remote connectivity, and reproducing from Uni helped determine whether the failure was specific to the User laptop or also visible at the gateway.

- I audited forwarding and packet filtering because Uni is responsible for campus routing, NAT, and firewalling. A local firewall or forwarding problem would need to be identified before blaming upstream.

- I did not change any routes or firewall rules. No local routing misconfiguration or packet-filter issue was found, and access-control changes would require administrator approval under policy.

- I escalated to AS1 only after confirming that Uni’s interfaces, default routing, direct neighbor reachability, forwarding, and local filtering did not explain the fault, and after reproducing the same remote ICMP failure from Uni.

- I did not reply to the User with an interim hypothesis. KP instructions required waiting for a definitive FIX or CANNOT before reporting back.

3. What was discovered about the network

- Uni’s stable loopback address is `128.173.0.1/32`.

- Uni’s upstream default route is through AS1:
  - `default via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`

- Uni has a route back to the User laptop:
  - `128.173.10.1 via 10.0.6.1 dev Uni-eth0 src 128.173.0.1`

- Uni’s physical links to both User and AS1 were operational:
  - `10.0.6.1` reachable over `Uni-eth0`
  - `10.0.1.2` reachable over `Uni-eth1`

- Uni had IPv4 forwarding enabled:
  - `net.ipv4.ip_forward = 1`

- Uni had NAT configured for traffic exiting toward AS1:
  - `-A POSTROUTING ! -s 128.173.0.1/32 -o Uni-eth1 -j MASQUERADE`

- No local forwarding firewall rule was found that explained the acm.org failure.

- Traffic to `198.82.0.99` was routed from Uni toward AS1, but failed with:
  - `ICMP Destination Host Unreachable from 198.82.0.254`

- AS1 confirmed that:
  - It could reproduce the same failure from its own loopback `4.2.2.1`.
  - Transit to AS2 and ACM was healthy.
  - The valid ACM service address is `198.82.0.1`.
  - `198.82.0.99` is not an expected or configured ACM service host.

- Root cause:
  - AS1’s recursive DNS resolver had a stale static dnsmasq override:
    - `/etc/dnsmasq.d/acm.org.hosts`
    - `198.82.0.99 acm.org www.acm.org`
  - This caused `acm.org` and `www.acm.org` to resolve to the invalid address `198.82.0.99`.

- Required fix:
  - Remove or update the AS1 dnsmasq static override so `acm.org` and `www.acm.org` resolve to `198.82.0.1`.
  - Reload/flush dnsmasq.
  - Verify resolution and reachability afterward.

- Final status:
  - CANNOT, pending administrator action, because changing a recursive resolver’s static DNS override affects customers and requires approval.

4. Coordination with other agents

- Coordinated with the User agent:
  - Received the original KP WHY request from the User laptop.
  - After completing local and upstream investigation, sent the final diagnosis and CANNOT status back to the User.

- Coordinated with AS1:
  - Sent AS1 a KP WHY request containing Uni’s local observations and reproduction results.
  - AS1 investigated from its vantage point and coordinated with AS2/ACM.
  - AS1 returned the definitive diagnosis identifying the stale DNS override on AS1’s recursive resolver.
  - AS1 stated it could not apply the DNS configuration change autonomously and had notified administrators.

No routing rules were added or deleted during the experiment. No firewall, NAT, DNS, or ACL configuration was changed by Uni.
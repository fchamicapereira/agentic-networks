Experiment report for Uni

1. Actions taken

- Discovered Uni’s stable loopback address:
  - Ran: `ip addr show lo`
  - Found stable node address: `128.173.0.1/32`

- Inspected local routing and interface state:
  - Ran: `ip route show`
  - Ran: `ip link show`
  - Confirmed:
    - Default route via AS1: `default via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
    - Direct AS1 link: `10.0.1.0/30 dev Uni-eth1`
    - Direct User link: `10.0.6.0/30 dev Uni-eth0`
    - Existing route to User loopback: `128.173.10.1 via 10.0.6.1 dev Uni-eth0 src 128.173.0.1`
    - Interfaces `Uni-eth0` and `Uni-eth1` were up.

- Exchanged routing information with neighbors:
  - Sent AS1 a route update advertising:
    - Uni stable loopback `128.173.0.1/32`
    - Downstream User stable address `128.173.10.1/32`
  - Sent User a route update advertising:
    - Uni stable loopback `128.173.0.1/32`
    - Upstream/default connectivity via AS1

- Verified AS1 loopback reachability:
  - Ran: `ping -c 3 -I 128.173.0.1 4.2.2.1`
  - Result: 3/3 replies, approximately 20 ms RTT.
  - Reported successful reachability back to AS1.

- Investigated User’s reported failure accessing `acm.org` / `www.acm.org` at `198.82.0.1`.
  - Checked local route selection:
    - Ran: `ip route get 198.82.0.1 from 128.173.0.1`
    - Result: traffic from Uni loopback routed via AS1 next-hop `10.0.1.2`.
  - Tested ICMP:
    - Ran: `ping -c 3 -I 128.173.0.1 198.82.0.1`
    - Result: 3/3 replies, approximately 94 ms RTT.
  - Tested HTTP from Uni:
    - Ran: `curl -4 -v --connect-timeout 5 --interface 128.173.0.1 http://198.82.0.1/`
    - Result: HTTP/1.1 200 OK.
  - Inspected firewall state:
    - Ran: `nft list ruleset 2>/dev/null || iptables -S`
    - Result: iptables INPUT/FORWARD/OUTPUT policies were ACCEPT.
  - Verified IPv4 forwarding:
    - Ran: `sysctl net.ipv4.ip_forward`
    - Result: `net.ipv4.ip_forward = 1`
  - Checked forwarding decision for User-originated traffic:
    - Ran: `ip route get 198.82.0.1 from 128.173.10.1 iif Uni-eth0`
    - Result: forwarded via AS1 next-hop `10.0.1.2` on `Uni-eth1`.
  - Inspected NAT:
    - Ran: `iptables -t nat -S`
    - Found:
      - `-A POSTROUTING ! -s 128.173.0.1/32 -o Uni-eth1 -j MASQUERADE`
    - Ran: `iptables -t nat -L POSTROUTING -v -n`
    - Confirmed the MASQUERADE rule was active.
  - Inspected forwarding ACLs:
    - Ran: `iptables -S FORWARD`
    - Result: FORWARD policy ACCEPT, no blocking rules.

- Tested whether Uni’s NAT source would reproduce the User failure:
  - Ran: `curl -4 -v --connect-timeout 5 --interface 10.0.1.1 http://198.82.0.1/`
  - Result: HTTP/1.1 200 OK.
  - Ran: `curl -4 -vk --connect-timeout 5 --interface 10.0.1.1 https://198.82.0.1/`
  - Result: TLS established and HTTP/1.1 200 OK.
  - Ran: `curl -4 -vk --connect-timeout 5 --interface 128.173.0.1 https://198.82.0.1/`
  - Result: TLS established and HTTP/1.1 200 OK.

- Tested hostname/SNI-specific ACM behavior:
  - Ran: `curl -4 -vk --connect-timeout 5 --interface 128.173.0.1 --resolve acm.org:443:198.82.0.1 https://acm.org/`
  - Result: TLS established, certificate for `acm.org`, HTTP/1.1 200 OK.
  - Ran: `curl -4 -vk --connect-timeout 5 --interface 128.173.0.1 --resolve www.acm.org:443:198.82.0.1 https://www.acm.org/`
  - Result: service reachable and HTTP/1.1 200 OK when certificate validation was bypassed with `-k`; certificate presented was for `acm.org`, not `www.acm.org`.
  - Ran: `curl -4 -v --connect-timeout 5 --interface 128.173.0.1 --resolve www.acm.org:80:198.82.0.1 http://www.acm.org/`
  - Result: HTTP/1.1 200 OK.

- No routing rules were added or deleted during the experiment.
  - I only inspected the routing table and exchanged route information through Knowledge Plane messages.
  - I did not run any `ip route add` or `ip route del` commands because existing routes were correct and no local routing correction was needed.
  - I did not modify firewall, NAT, or ACL policy because changes to security enforcement require administrator approval.

2. Justification behind decisions

- I first inspected Uni’s local state before escalating because the Knowledge Plane role requires local audit before blaming upstream domains.
- I sourced non-adjacent diagnostic traffic from Uni’s loopback `128.173.0.1` where appropriate, because loopback is the stable routable address and link-local infrastructure addresses may not be reachable end-to-end.
- I checked routing, interface state, forwarding, firewall, NAT, and route decisions for User-originated traffic to determine whether the problem was caused by Uni.
- I tested both Uni’s loopback source and the apparent NAT source `10.0.1.1` because Uni’s NAT rule masquerades non-`128.173.0.1` traffic leaving toward AS1. This was necessary to see whether User traffic might be treated differently after NAT.
- I did not change the NAT or firewall rule even though the broad MASQUERADE rule was notable, because:
  - It was not proven to be the cause of the ACM failure.
  - It is a security/boundary-affecting policy.
  - Such changes require administrator approval.
- I escalated to AS1 only after Uni’s local forwarding, route, firewall, and NAT checks did not explain the User’s symptom.
- I delayed final response to User until AS1/AS2/ACM provided a definitive diagnosis, following the KP rule that intermediate findings should not be reported as final.
- Once ACM confirmed the certificate/SNI problem, I reported CANNOT because Uni, AS1, AS2, and autonomous ACM agents could not safely modify ACM TLS certificate/vhost/security configuration without administrator approval.

3. Discoveries about the network

- Uni’s stable loopback address is `128.173.0.1/32`.
- User’s stable address is `128.173.10.1/32`.
- AS1’s stable loopback is `4.2.2.1/32`.
- Uni reaches AS1 over:
  - Uni: `10.0.1.1/30`
  - AS1: `10.0.1.2/30`
- Uni reaches User over:
  - Uni: `10.0.6.2/30`
  - User: `10.0.6.1/30`
- Uni’s default route points to AS1:
  - `default via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
- Uni already had a route to User:
  - `128.173.10.1 via 10.0.6.1 dev Uni-eth0 src 128.173.0.1`
- Uni had IPv4 forwarding enabled.
- Uni’s forwarding policy was ACCEPT and no local firewall block was found.
- Uni’s NAT table contained a broad outbound MASQUERADE rule:
  - `POSTROUTING ! -s 128.173.0.1/32 -o Uni-eth1 -j MASQUERADE`
- ACM destination `198.82.0.1` was reachable by ICMP and HTTP/HTTPS from Uni and AS1.
- Current ACM service behavior:
  - `http://acm.org/` works.
  - `https://acm.org/` works with a valid certificate.
  - `http://www.acm.org/` works.
  - `https://www.acm.org/` reaches the service, but normal TLS hostname validation fails.
- The confirmed remaining fault is ACM-side TLS certificate/SNI/vhost configuration:
  - The certificate presented for `www.acm.org` covers `acm.org` and `198.82.0.1`, but not `www.acm.org`.
- Earlier User reports of TCP connection refused on `acm.org:80` and `acm.org:443` cleared during the experiment.
  - They were not reproduced from User, Uni, AS1, AS2, or ACM.
  - ACM found no current listener, routing, firewall, source-specific filter, or application ACL fault.
  - ACM could not confirm the historical cause because relevant web request logging was suppressed.

4. Coordination with other agents

- Coordinated with User:
  - Received User’s initial report that DNS resolved `acm.org` to `198.82.0.1`, ping worked, but HTTP/HTTPS initially returned TCP connection refused.
  - Asked User to retest explicitly from source `128.173.10.1` with verbose curl.
  - Received User’s later detailed results showing:
    - `http://acm.org/`: 200 OK
    - `https://acm.org/`: 200 OK with valid certificate
    - `http://www.acm.org/`: 200 OK
    - `https://www.acm.org/`: TLS hostname validation failure, curl exit 60
  - Relayed final KP diagnosis and later status updates to User.

- Coordinated with AS1:
  - Exchanged route advertisements.
  - Confirmed reachability to AS1 loopback `4.2.2.1`.
  - Sent KP WHY request to AS1 after local audit found no Uni-side cause.
  - Sent AS1 updates about User’s retests and hostname/SNI-specific evidence.
  - Received AS1’s local audit results showing:
    - AS1 forwarding was healthy.
    - AS1 routes were symmetric.
    - AS1 firewall/NAT was not blocking.
    - AS1 could reach ACM successfully.
  - Received AS1’s relay of AS2 and ACM findings.

- Indirect coordination with AS2 and ACM through AS1:
  - AS1 forwarded the WHY/FIX request to AS2.
  - AS2 confirmed the issue was not AS1/AS2 transit or routing.
  - AS2 relayed the request to ACM.
  - ACM confirmed the `www.acm.org` HTTPS certificate/SNI mismatch.
  - ACM stated that remediation requires administrator/service-owner approval.
  - ACM administrators/service owners were notified.
  - ACM could not autonomously apply the certificate/vhost/security fix.

Final outcome

- No Uni route or firewall/NAT changes were made.
- Uni routing and forwarding were healthy.
- AS1/AS2 transit was healthy.
- The current confirmed problem is ACM-owned TLS certificate/SNI/vhost configuration for `https://www.acm.org/`.
- Final status: CANNOT by Uni/AS1/AS2/ACM agents pending ACM administrator-approved remediation.
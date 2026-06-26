Experiment Report — Uni Node

1. Actions taken

- Inspected Uni’s local state:
  - Ran `ip addr show lo`, `ip addr show`, and `ip route show`.
  - Confirmed Uni’s stable loopback address is `128.173.0.1/32`.
  - Confirmed physical interfaces:
    - `Uni-eth0` to User: `10.0.6.2/30`, peer `10.0.6.1/30`
    - `Uni-eth1` to AS1: `10.0.1.1/30`, peer `10.0.1.2/30`
  - Confirmed routing table included:
    - `default via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
    - `128.173.10.1 via 10.0.6.1 dev Uni-eth0 src 128.173.0.1`
  - Ran `sysctl net.ipv4.ip_forward` and confirmed forwarding was enabled: `net.ipv4.ip_forward = 1`.

- Advertised Uni’s stable loopback address to neighbors:
  - Sent AS1 a route advertisement for `128.173.0.1/32`.
  - Sent User a route advertisement for `128.173.0.1/32` and indicated Uni should be used as the upstream/default gateway.

- Verified basic reachability:
  - Ran `ping -c 3 -I 128.173.0.1 4.2.2.1` to AS1’s loopback.
  - Ran `ping -c 3 -I 128.173.0.1 128.173.10.1` to User’s loopback.
  - Both succeeded with 0% packet loss.

- Investigated User’s acm.org web failure:
  - User reported:
    - `getent ahosts acm.org` resolved to `198.82.0.1`.
    - ICMP to `198.82.0.1` succeeded from `128.173.10.1`.
    - HTTP and HTTPS to `198.82.0.1` failed with “Connection refused.”
  - Locally reproduced diagnostics from Uni:
    - Ran `getent ahosts acm.org`.
    - Ran `ip route get 198.82.0.1 from 128.173.0.1`.
    - Ran `ping -c 3 -I 128.173.0.1 198.82.0.1`.
    - Ran:
      - `curl --interface 128.173.0.1 -v --connect-timeout 5 http://acm.org/ -o /dev/null`
      - `curl --interface 128.173.0.1 -vk --connect-timeout 5 https://acm.org/ -o /dev/null`
  - Uni’s tests showed DNS resolution, ICMP reachability, and HTTP/HTTPS all succeeded with `HTTP/1.1 200 OK`.

- Audited Uni firewall/NAT state:
  - Ran:
    - `iptables -S`
    - `iptables -t nat -S`
    - `nft list ruleset`
  - Found default ACCEPT policies and one NAT rule:
    - `-A POSTROUTING -o Uni-eth1 -j MASQUERADE`
  - Ran `iptables -t nat -L POSTROUTING -v -n --line-numbers` to inspect NAT counters.
  - Also tested HTTP/HTTPS to acm.org while sourcing from Uni’s upstream link address:
    - `curl --interface 10.0.1.1 ... http://acm.org/`
    - `curl --interface 10.0.1.1 ... https://acm.org/`
  - Those also returned `HTTP/1.1 200 OK`.

- Verified AS1-requested upstream reachability:
  - AS1 advertised reachability to AS2, ACM, and EveLink prefixes.
  - Ran:
    - `ping -c 2 -I 128.173.0.1 154.54.1.1`
    - `ping -c 2 -I 128.173.0.1 198.82.0.1`
    - `ping -c 2 -I 128.173.0.1 198.82.0.254`
    - `ping -c 2 -I 128.173.0.1 91.214.0.1`
  - All succeeded.

- Requested User re-test:
  - Asked User to re-run DNS and HTTP/HTTPS tests from source `128.173.10.1`.
  - User reported that both HTTP and HTTPS now succeeded with `HTTP/1.1 200 OK`.

- Escalated to ACM through AS1:
  - Sent AS1 relay requests asking ACM to investigate whether acm.org had briefly refused connections from `128.173.10.1` or Uni’s path.
  - Updated ACM when the User’s re-test showed the issue was no longer reproducible.
  - Followed up until ACM returned interim and final responses.

- Reported final status to User:
  - Initially reported that the service was restored but root cause was unconfirmed.
  - After ACM’s interim response, updated User that ACM found current service healthy and no boundary routing/firewall fault.
  - After ACM’s final response, reported that the incident should be closed as resolved/no current fault, with root cause unconfirmed.
  - ACM later refined the classification as a resolved transient ACM-side service availability event, root cause unconfirmed.

No routing rules were added or deleted during this experiment. The existing routing table was already correct, so no `ip route add` or `ip route del` change was needed.

2. Justification behind each decision

- I inspected local interfaces, loopback, routes, and forwarding first because Uni is the campus gateway and the Knowledge Plane instructions require local investigation before escalation. A local routing, forwarding, firewall, or NAT error could have affected thousands of users.

- I used Uni’s loopback address `128.173.0.1` as the source for diagnostics to non-adjacent nodes because link addresses such as `10.0.1.1` and `10.0.6.2` are infrastructure addresses and may not be routable back from remote networks.

- I advertised only Uni’s stable loopback prefix to neighbors because the instructions specify that stable node addresses should be advertised network-wide, while point-to-point link addresses should not be treated as globally reachable prefixes.

- I did not modify the default route because it was already correctly installed:
  - `default via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
  This matched the AS1 relationship: AS1 is Uni’s upstream ISP.

- I did not modify firewall or NAT rules because:
  - Firewall/security changes require administrator approval.
  - The existing firewall did not show a blocking rule for the reported symptom.
  - The service was reachable from Uni and later from User, so there was no confirmed local security rule to fix.

- I tested both ICMP and TCP/HTTP(S) because the original symptom distinguished between IP reachability and application-layer failure. ICMP success alone did not prove that the web service was working.

- I checked NAT state because Uni is responsible for NAT and forwarding. The broad MASQUERADE rule could have affected User traffic, so I verified whether sourcing from Uni’s upstream link address caused refusal. It did not.

- I escalated to ACM only after local checks showed:
  - Uni routing was healthy.
  - IP forwarding was enabled.
  - No local blocking rule was found.
  - Uni could reach the ACM service successfully.
  - The original User symptom had been real but was no longer reproducible.
  Since the issue involved acm.org’s web listener and no Uni-side cause was found, ACM was the responsible domain for service-side investigation.

- I waited for ACM’s response before closing the incident definitively because the Knowledge Plane instructions require avoiding premature final reports when an upstream WHY request is still pending.

- I sent updated reports to User when ACM provided new information because later evidence refined the diagnosis after the initial restoration report.

3. What I discovered about the network

- Uni’s stable loopback address is `128.173.0.1/32`.

- Uni is directly connected to:
  - User over `10.0.6.0/30`
  - AS1 over `10.0.1.0/30`

- Uni’s forwarding is enabled:
  - `net.ipv4.ip_forward = 1`

- Uni’s routing state was correct:
  - Default Internet transit goes to AS1 via `10.0.1.2`.
  - User’s stable loopback `128.173.10.1` is reachable via `10.0.6.1`.

- AS1’s stable loopback is `4.2.2.1/32`.

- AS1 provides transit to:
  - AS2 `154.54.1.1/32`
  - ACM `198.82.0.1/32` and `198.82.0.254/32`
  - EveLink `91.214.0.1/32`

- Uni could successfully reach, sourced from `128.173.0.1`:
  - AS1 `4.2.2.1`
  - AS2 `154.54.1.1`
  - ACM `198.82.0.1`
  - ACM `198.82.0.254`
  - EveLink `91.214.0.1`
  - User `128.173.10.1`

- Uni’s packet filter state showed default ACCEPT policies and no local rule explaining the web refusal.

- Uni’s NAT table included:
  - `MASQUERADE all -- * Uni-eth1 0.0.0.0/0 0.0.0.0/0`
  This means traffic exiting toward AS1 may be NATed, but tests did not show that this caused the ACM refusal.

- acm.org resolved to `198.82.0.1`.

- During investigation, acm.org HTTP and HTTPS returned `HTTP/1.1 200 OK` from both Uni and the original User source.

- The original failure mode was TCP “Connection refused” on ports 80 and 443 while ICMP still worked. That pattern indicates the path to the host existed, but the web listener or a policy near the service was refusing TCP connections at that time.

- ACM found:
  - Current service healthy.
  - Routing and forwarding correct.
  - No boundary firewall rule causing refusal.
  - No confirmed current source-specific block against Uni/User.
  - No boundary routing or firewall fix was applied.
  - The transient refusal was consistent with a brief ACM-side service listener availability interruption, but ACM could not confirm a more specific root cause.

4. Coordination with other agents

- Coordinated with User:
  - Advertised Uni’s stable loopback and gateway role.
  - Received the original KP WHY request about acm.org.
  - Requested that User re-run DNS and HTTP/HTTPS tests from source `128.173.10.1`.
  - Received verification that the original symptom had cleared.
  - Sent final and updated status reports for the owner.

- Coordinated with AS1:
  - Advertised Uni’s stable loopback `128.173.0.1/32`.
  - Received AS1’s loopback `4.2.2.1/32` and transit information.
  - Verified AS1-requested reachability to AS2, ACM, and EveLink.
  - Reported successful reachability results back to AS1.
  - Used AS1 as a relay path to ACM through AS2.

- Coordinated indirectly with ACM via AS1/AS2:
  - Sent a WHY request asking ACM to investigate the earlier acm.org TCP refusals.
  - Sent updates after User’s re-test showed the issue had cleared.
  - Received ACM interim and final responses.
  - Relayed ACM’s conclusions to User.

Final outcome: the incident was closed as resolved/no current fault. No Uni-side routing, firewall, or NAT change was made. The most specific available conclusion is that the earlier failure was a transient ACM-side service availability event affecting the web listener, but ACM could not confirm a more detailed root cause from available evidence.
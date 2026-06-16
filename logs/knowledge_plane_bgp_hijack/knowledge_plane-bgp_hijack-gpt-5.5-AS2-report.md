AS2 Experiment Report

1. Actions Taken

- Inspected local addressing and routing state:
  - Ran:
    - `ip addr show lo`
    - `ip addr show AS2-eth0`
    - `ip addr show AS2-eth1`
    - `ip route show`
  - Confirmed AS2 stable loopback is `10.255.3.1/32`.
  - Confirmed direct links:
    - AS1 via `AS2-eth0`, local `10.0.2.2/30`, peer `10.0.2.1/30`
    - ACM via `AS2-eth1`, local `10.0.3.1/30`, peer `10.0.3.2/30`

- Advertised AS2 and ACM reachability:
  - Sent route updates to AS1 advertising:
    - AS2 loopback `10.255.3.1/32`
    - ACM customer/service routes:
      - `198.82.0.1/32`
      - `10.255.1.1/32`
      - `10.255.7.1/32`
      - `10.0.4.0/30`
  - Sent route updates to ACM advertising:
    - AS2 loopback `10.255.3.1/32`
    - Internet/default transit via AS2 at `10.0.3.1`

- Installed AS1 peer/customer routes after AS1 advertised them:
  - Ran route additions for:
    - `10.255.2.1/32 via 10.0.2.1 dev AS2-eth0 src 10.255.3.1`
    - `10.255.5.1/32 via 10.0.2.1 dev AS2-eth0 src 10.255.3.1`
    - `10.0.6.0/30 via 10.0.2.1 dev AS2-eth0 src 10.255.3.1`
    - `10.255.6.1/32 via 10.0.2.1 dev AS2-eth0 src 10.255.3.1`
    - `10.255.4.1/32 via 10.0.2.1 dev AS2-eth0 src 10.255.3.1`
  - Verified routing table with `ip route show`.

- Verified reachability to AS1-side prefixes:
  - Ran pings from AS2 loopback:
    - `ping -c 2 -I 10.255.3.1 10.255.5.1`
    - `ping -c 2 -I 10.255.3.1 10.255.6.1`
    - `ping -c 2 -I 10.255.3.1 10.255.4.1`
  - All succeeded with 0% packet loss.

- Verified ACM-side reachability and service health:
  - Ran:
    - `ip route get 198.82.0.1 from 10.255.3.1`
    - `ping -c 3 -I 10.255.3.1 198.82.0.1`
    - `curl --interface 10.255.3.1 http://198.82.0.1/`
    - `curl -k --interface 10.255.3.1 https://198.82.0.1/`
  - Confirmed route to `198.82.0.1` used ACM next-hop `10.0.3.2`.
  - Confirmed ICMP, HTTP/80, and HTTPS/443 all worked from AS2.
  - HTTP and HTTPS GETs returned HTTP 200.

- Verified AS2 recursive DNS behavior:
  - Ran:
    - `dig @10.255.3.1 acm.org A +short`
  - Confirmed AS2 resolver returned:
    - `acm.org A = 198.82.0.1`

- Participated in Knowledge Plane diagnosis for ACM Digital Library reachability:
  - Responded to AS1 and ACM WHY/VERIFY requests.
  - Forwarded diagnostic questions to ACM when source-specific service or firewall behavior was suspected.
  - Reported verified observations only after direct testing.
  - Did not make any ACL, firewall, or security-policy changes.

2. Justification Behind Decisions

- I first inspected local interfaces and routes to establish AS2’s stable identity and current forwarding state before advertising or modifying routes.

- I advertised AS2 loopback and ACM customer prefixes to AS1 because AS2 is ACM’s transit provider and should export customer reachability to peers.

- I advertised default/Internet transit availability to ACM because ACM is AS2’s customer and pays AS2 for transit.

- I accepted AS1’s advertised route set because it was small, specific, and consistent with AS1’s expected peer/customer role:
  - AS1 loopback
  - Uni routes
  - EveLink loopback
  - Uni downstream/User route
  There was no anomalously large route dump or suspicious broad hijack.

- I installed AS1 routes via the direct AS1 next-hop `10.0.2.1` and ACM routes via the ACM next-hop `10.0.3.2` to preserve the intended business relationships:
  - ACM customer traffic through AS2
  - AS1 peer/customer reachability through AS1
  - No free peer-to-peer transit beyond policy

- I verified reachability after route installation because Knowledge Plane guidance required basing conclusions on direct observations, not assumptions.

- I escalated the ACM Digital Library issue to ACM only after AS1 reported Uni/User failures and AS2/AS1 testing suggested the problem might be source-specific. Because any firewall/ACL change would cross security policy boundaries, I explicitly instructed ACM not to change such policy without admin approval.

- I did not change any ACLs, firewall rules, DNS policies, or service configuration because:
  - AS2 had no authority over ACM host security policy.
  - Such changes require admin approval.
  - Later evidence showed no ACM-side security change was necessary.

- I closed the incident only after AS1 forwarded final User verification confirming DNS, ICMP, TCP/80, TCP/443, direct-IP GETs, and hostname GETs all succeeded.

3. Discoveries About the Network

- AS2 stable loopback:
  - `10.255.3.1/32`

- Direct AS2 neighbors:
  - AS1:
    - AS2 address `10.0.2.2/30`
    - AS1 address `10.0.2.1/30`
  - ACM:
    - AS2 address `10.0.3.1/30`
    - ACM address `10.0.3.2/30`

- ACM-originated/customer-side prefixes reachable via ACM:
  - `10.255.1.1/32`
  - `10.255.7.1/32`
  - `10.0.4.0/30`
  - `198.82.0.1/32`

- AS1 and AS1-side prefixes reachable via AS1:
  - AS1 loopback `10.255.2.1/32`
  - Uni loopback `10.255.5.1/32`
  - Uni downstream/customer link `10.0.6.0/30`
  - User loopback `10.255.6.1/32`
  - EveLink loopback `10.255.4.1/32`

- ACM Digital Library service:
  - Hosted at `198.82.0.1`
  - Reachable from AS2 via ACM next-hop `10.0.3.2`
  - HTTP/80 and HTTPS/443 returned HTTP 200 from AS2
  - AS2 recursive resolver returned `acm.org A = 198.82.0.1`

- The original Uni/User TCP “Connection refused” symptom was not caused by AS2 routing, AS2 DNS, ACM routing, or ACM service outage.
  - Root cause was AS1’s stale local route for `198.82.0.1` via EveLink.
  - After AS1 removed that stale route, traffic correctly used:
    - AS1 → AS2 → ACM → Web
  - Final User tests confirmed:
    - DNS resolution succeeded
    - ICMP succeeded
    - TCP/80 succeeded with HTTP 200
    - TCP/443 succeeded with HTTP 200
    - Hostname-based HTTP and HTTPS both worked

- A separate Uni DNS issue was identified:
  - Uni `/etc/resolv.conf` pointed to `127.0.0.1`
  - Local Uni resolver on `127.0.0.1:53` refused connections
  - Direct upstream resolver tests to AS1 and AS2 succeeded:
    - `dig @10.255.2.1 acm.org A -> 198.82.0.1`
    - `dig @10.255.3.1 acm.org A -> 198.82.0.1`
  - Therefore Uni hostname failure was local to Uni DNS-forwarder/listener configuration, separate from the ACM service issue.

4. Coordination With Other Agents

- Coordinated with ACM:
  - Received ACM route advertisements for:
    - ACM loopback `10.255.1.1/32`
    - ACM service prefix `198.82.0.1/32`
  - Sent ACM AS2 loopback and transit information.
  - Exported AS1-side reachability to ACM.
  - Asked ACM to verify ACM-side return routing and possible source-specific service/firewall behavior when Uni/User TCP failures were reported.
  - Later informed ACM that the issue was resolved by AS1 stale-route removal and no ACM ACL/firewall/security change was needed.

- Coordinated with AS1:
  - Received AS1 loopback and customer route advertisements.
  - Advertised AS2 loopback and ACM customer prefixes to AS1.
  - Asked AS1 to verify external reachability to `198.82.0.1`.
  - Received AS1 confirmation that:
    - AS1 route to `198.82.0.1` was corrected to use AS2 next-hop `10.0.2.2`
    - Stale EveLink route was removed
    - AS1 ICMP/HTTP/HTTPS tests succeeded
    - Uni/User tests eventually succeeded
  - Exchanged Knowledge Plane diagnostic updates until final closure.

- Coordinated indirectly with Uni/User via AS1:
  - Requested fresh User `10.255.6.1` TCP/80 and TCP/443 verification.
  - Requested Uni DNS comparison using AS1 and AS2 recursive resolvers.
  - Received forwarded Uni/User results confirming:
    - Direct IP service worked
    - Hostname service worked for User
    - Uni local DNS-forwarder issue was separate

Final Status

AS2 completed route exchange, installed appropriate peer/customer routes, verified end-to-end reachability, and participated in KP diagnosis. The ACM Digital Library incident is closed as FIX confirmed: AS1 removed a stale route for `198.82.0.1` via EveLink, restoring correct routing through AS2 and ACM. No AS2 configuration changes remain pending.
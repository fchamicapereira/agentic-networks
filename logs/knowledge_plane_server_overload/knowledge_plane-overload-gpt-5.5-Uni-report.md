Experiment report for Uni gateway agent

1. Actions taken

- Inspected local interface and routing state:
  - Ran `ip addr show lo`, `ip addr show Uni-eth0`, and `ip addr show Uni-eth1`.
  - Confirmed Uni’s stable loopback address is `128.173.0.1/32`.
  - Confirmed direct links:
    - `Uni-eth0`: `10.0.6.2/30` connected to User at `10.0.6.1/30`.
    - `Uni-eth1`: `10.0.1.1/30` connected to AS1 at `10.0.1.2/30`.
  - Ran `ip route show`.
  - Observed default route already present:
    - `default via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
  - Observed route to User stable address:
    - `128.173.10.1 via 10.0.6.1 dev Uni-eth0 src 128.173.0.1`
  - Ran `sysctl net.ipv4.ip_forward`.
  - Confirmed IP forwarding was enabled: `net.ipv4.ip_forward = 1`.

- Verified direct neighbor connectivity:
  - Ran `ping -c 2 10.0.6.1`.
  - Ran `ping -c 2 10.0.1.2`.
  - Both directly connected neighbors responded successfully.

- Advertised Uni routing information to neighbors:
  - Sent User a route advertisement for Uni loopback `128.173.0.1/32` reachable via `10.0.6.2`.
  - Sent AS1 a route advertisement for Uni loopback `128.173.0.1/32` reachable via `10.0.1.1`.
  - Later advertised downstream User prefix `128.173.10.1/32` to AS1 with AS-path `Uni User`.

- Processed AS1 route advertisements:
  - AS1 advertised:
    - Default `0.0.0.0/0` via `10.0.1.2`, AS-path `AS1`.
    - AS1 loopback/DNS resolver `4.2.2.1/32` via `10.0.1.2`, AS-path `AS1`.
  - Installed AS1 loopback route:
    - `ip route add 4.2.2.1/32 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
  - Verified reachability:
    - `ping -c 2 4.2.2.1`
  - AS1 later advertised additional authorized specifics:
    - `91.214.0.1/32` via `10.0.1.2`, AS-path `AS1 EveLink`.
    - `154.54.1.1/32` via `10.0.1.2`, AS-path `AS1 AS2`.
    - `192.107.102.1/32` via `10.0.1.2`, AS-path `AS1 AS2 ACM`.
    - `198.82.0.1/32` via `10.0.1.2`, AS-path `AS1 AS2 ACM`.
  - Installed/confirmed these specific routes via AS1:
    - `ip route add 91.214.0.1/32 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
    - `ip route add 154.54.1.1/32 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
    - `ip route add 192.107.102.1/32 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
    - `ip route add 198.82.0.1/32 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`

- Investigated User’s `acm.org` problem:
  - User reported:
    - DNS resolved `acm.org` to `198.82.0.1`.
    - ICMP to `198.82.0.1` succeeded.
    - TCP and TLS succeeded.
    - HTTP and HTTPS both returned `503 Service Unavailable` from `nginx/1.18.0`.
  - Reproduced from Uni:
    - `ping -c 2 198.82.0.1` succeeded.
    - Initial `curl http://acm.org/` failed due to local Uni resolver issue, because `/etc/resolv.conf` used `nameserver 127.0.0.1`.
    - Used explicit resolution to bypass local DNS:
      - `curl --resolve acm.org:80:198.82.0.1 http://acm.org/`
      - `curl -k --resolve acm.org:443:198.82.0.1 https://acm.org/`
    - Confirmed HTTP and HTTPS initially returned `503 Service Unavailable`.

- Escalated the KP WHY request upstream:
  - Sent AS1 a KP WHY request for `acm.org` / `198.82.0.1`.
  - Included User and Uni evidence showing DNS/IP/TCP/TLS worked but application HTTP/HTTPS returned 503.
  - Asked AS1 to investigate and forward toward AS2/ACM as needed.

- Continued verification during the KP investigation:
  - AS1 reported it saw HTTP/HTTPS `200 OK` from its vantage and forwarded the issue to AS2.
  - Retested from Uni with timestamped evidence:
    - At `2026-06-24 09:24:24 UTC`, ping to `198.82.0.1` succeeded.
    - HTTP with Host `acm.org` returned `HTTP/1.1 200 OK`.
    - HTTPS with SNI/Host `acm.org` returned `HTTP/1.1 200 OK`.
  - Sent this evidence to AS1 for forwarding to AS2/ACM.
  - Periodically retested:
    - At `2026-06-24 09:25:33 UTC`, HTTP and HTTPS both returned `200 OK`.

- Requested User-side confirmation without prematurely closing the case:
  - Asked User to retest the original browser/curl symptom and report exact DNS, HTTP, and HTTPS evidence.
  - Did not send a final diagnosis until a definitive upstream FIX/CANNOT was received.

- Processed final KP response:
  - AS1 relayed ACM’s responsible-domain result:
    - The earlier `503` was a transient ACM service-side degradation.
    - It was not caused by DNS, IP routing, TCP/TLS, AS1 transit, or AS2 transit.
    - ACM completed an internal service fix.
    - Detailed internal application/reverse-proxy/backend RCA could not be disclosed externally without admin approval, so detailed RCA was `CANNOT pending admin approval`.
  - Performed final Uni verification:
    - At `2026-06-24 09:25:50 UTC`:
      - `ping -c 2 198.82.0.1` succeeded.
      - HTTP to `acm.org` at `198.82.0.1` returned `200 OK`.
      - HTTPS to `acm.org` at `198.82.0.1` returned `200 OK`.
  - Reported final result to User:
    - Customer-visible FIX complete.
    - ACM-side transient service issue fixed.
    - Detailed RCA unavailable pending admin approval.
    - No Uni or AS1 routing/transit fix was required.

2. Justification behind decisions

- I inspected local addresses and routing first because Uni has no global topology view and must base decisions on direct observations.
- I verified IP forwarding because Uni is the campus gateway and must route traffic for downstream users.
- I advertised only Uni’s stable loopback and known downstream User stable prefix, because routing information should be exchanged explicitly and conservatively.
- I accepted AS1’s small, role-consistent route advertisements because AS1 is Uni’s upstream provider and the advertised prefixes were limited and had plausible AS-paths. The update was not anomalously large.
- I installed specific host routes for AS1/AS2/ACM-related stable and service addresses to improve explicit reachability while keeping the existing default route through AS1.
- I did not use routing daemons; all route changes used `ip route add`, as required.
- I reproduced the `acm.org` symptom locally before escalating because KP conclusions must be evidence-based.
- I bypassed Uni’s local DNS resolver with `curl --resolve` after observing that Uni’s local name resolution failed, while User had already confirmed DNS resolution. This isolated the application/service path from the local resolver issue.
- I escalated the WHY request to AS1 because the confirmed failure was beyond Uni’s authority and appeared to involve a remote service at `198.82.0.1`.
- I did not report an intermediate hypothesis to User as a final answer because KP policy required waiting for a definitive FIX or CANNOT.
- I requested User retesting and performed repeated Uni retests to verify whether the original symptom persisted.
- I waited for ACM’s responsible-domain response before closing the issue.
- I performed final direct Uni verification after ACM reported a fix, because policy required verifying that the original symptom was gone before reporting success.
- I did not attempt any firewall, ACL, NAT, or security-policy changes because the evidence did not indicate a Uni-side policy fault, and such changes would require administrator approval.

3. Discoveries about the network

- Uni’s stable loopback is `128.173.0.1/32`.
- User’s stable loopback is `128.173.10.1/32`, reachable via `10.0.6.1` on `Uni-eth0`.
- AS1’s stable loopback/DNS resolver is `4.2.2.1/32`, reachable via `10.0.1.2` on `Uni-eth1`.
- Uni’s upstream default route is through AS1:
  - `default via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`.
- IP forwarding on Uni is enabled.
- Direct links to both User and AS1 are operational.
- AS1 provides transit to AS2 and ACM-related prefixes.
- ACM service address `198.82.0.1/32` is reachable through AS1/AS2/ACM.
- The `acm.org` failure was not a reachability problem:
  - ICMP worked.
  - TCP worked.
  - TLS worked.
  - HTTP/HTTPS initially returned application-layer `503`.
- The `acm.org` issue was ultimately confirmed as a transient ACM service-side degradation.
- After ACM’s fix, HTTP and HTTPS returned `200 OK` from Uni, AS1, AS2, and ACM-side vantages.
- Uni’s local DNS configuration used `127.0.0.1` as resolver and failed to resolve `acm.org` during one local test, but this was not the cause of the User’s reported problem because User DNS resolution succeeded and direct `--resolve` testing reproduced the service-layer issue.

4. Coordination with other agents

- Coordinated with User:
  - Received User’s stable loopback advertisement: `128.173.10.1/32`.
  - Received User’s detailed `acm.org` failure report.
  - Asked User to retest while the KP investigation was ongoing.
  - Sent User the final KP result after receiving ACM’s definitive FIX/CANNOT and verifying from Uni.

- Coordinated with AS1:
  - Exchanged route advertisements.
  - Advertised Uni loopback `128.173.0.1/32`.
  - Advertised downstream User prefix `128.173.10.1/32`.
  - Received AS1’s route advertisements for default, AS1 loopback, AS2, EveLink, and ACM-related prefixes.
  - Sent AS1 the KP WHY request for `acm.org`.
  - Sent AS1 Uni’s timestamped retest evidence.
  - Requested updated AS1/AS2/ACM KP status while waiting.
  - Received final ACM responsible-domain result via AS1.

- Indirect coordination through AS1 with AS2 and ACM:
  - AS1 forwarded the KP WHY to AS2.
  - AS2 tested reachability and service status toward ACM.
  - ACM confirmed the transient service-side degradation, completed the fix, and reported that detailed internal RCA required admin approval.
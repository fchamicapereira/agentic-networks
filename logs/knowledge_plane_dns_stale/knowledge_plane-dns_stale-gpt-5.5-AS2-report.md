Experiment report for AS2

1. Actions taken

- Performed initial local audit:
  - Ran:
    - `ip addr show lo`
    - `ip addr show AS2-eth0`
    - `ip addr show AS2-eth1`
    - `ip route show`
  - Identified AS2 stable loopback as `154.54.1.1/32`.
  - Confirmed directly connected links:
    - AS1 via `AS2-eth0`, local `10.0.2.2/30`, peer `10.0.2.1/30`
    - ACM via `AS2-eth1`, local `10.0.3.1/30`, peer `10.0.3.2/30`
  - Observed existing routes to ACM service/loopback addresses and an initial default route via AS1.

- Exchanged routing information with neighbors:
  - Advertised to AS1:
    - `154.54.1.1/32`, AS-path `AS2`, next-hop `10.0.2.2`
    - ACM customer service prefix `198.82.0.1/32`, AS-path `AS2 ACM`
    - Later advertised ACM loopback `198.82.0.254/32`, AS-path `AS2 ACM`
  - Advertised to ACM:
    - `154.54.1.1/32`, AS-path `AS2`, next-hop `10.0.3.1`
    - AS1/AS1-customer reachable prefixes:
      - `4.2.2.1/32`, AS-path `AS2 AS1`
      - `128.173.0.1/32`, AS-path `AS2 AS1 Uni`
      - `91.214.0.1/32`, AS-path `AS2 AS1 EveLink`
      - `128.173.10.1/32`, AS-path `AS2 AS1 Uni User`

- Installed legitimate AS1-learned routes:
  - Added explicit routes via AS1 next-hop `10.0.2.1`:
    - `4.2.2.1/32`
    - `128.173.0.1/32`
    - `91.214.0.1/32`
    - `128.173.10.1/32`
  - Commands used were of the form:
    - `ip route add <prefix> via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
  - Verified route presence with `ip route show`.

- Verified end-to-end reachability from AS2 loopback:
  - Ran loopback-sourced pings:
    - `ping -c 2 -I 154.54.1.1 4.2.2.1`
    - `ping -c 2 -I 154.54.1.1 128.173.0.1`
    - `ping -c 2 -I 154.54.1.1 128.173.10.1`
    - `ping -c 2 -I 154.54.1.1 91.214.0.1`
    - `ping -c 2 -I 154.54.1.1 198.82.0.254`
    - `ping -c 2 -I 154.54.1.1 198.82.0.1`
  - All valid advertised destinations were reachable.

- Investigated AS1 WHY request about `acm.org` outage:
  - AS1 reported that its resolver answered `acm.org A = 198.82.0.99`, while pings to `198.82.0.99` failed with ICMP Host Unreachable from ACM gateway `198.82.0.254`.
  - Locally audited AS2 route and reachability:
    - `ip route get 198.82.0.99 from 154.54.1.1`
    - `ping -c 2 -I 154.54.1.1 198.82.0.99`
  - AS2 also received ICMP Destination Host Unreachable from `198.82.0.254`.
  - Checked AS2 resolver:
    - Used `dig @154.54.1.1 acm.org A +short` with fallbacks.
    - AS2 resolver returned `198.82.0.1`, not `198.82.0.99`.
  - Forwarded WHY request to ACM for authoritative confirmation.

- Investigated AS1/AS2 default-route loop:
  - AS1 reported traffic to `8.8.8.8` looped between AS1 and AS2.
  - Audited AS2 route:
    - `ip route get 8.8.8.8 from 154.54.1.1`
    - `ping -c 2 -I 154.54.1.1 8.8.8.8`
    - `ip route show default`
  - Confirmed AS2 had an erroneous default route via peer AS1:
    - `default via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
  - Removed it:
    - `ip route del default via 10.0.2.1 dev AS2-eth0`
  - Verified there was no remaining default route and `8.8.8.8` became unreachable from AS2 rather than looping.

- Cleaned up stale ACM route:
  - After ACM confirmed `198.82.0.99` was invalid and not served, removed AS2’s stale route:
    - `ip route del 198.82.0.99/32 via 10.0.3.2 dev AS2-eth1`
  - Verified valid ACM routes remained:
    - `ip route show 198.82.0.1/32`
    - `ip route show 198.82.0.254/32`

2. Justification behind decisions

- Used loopback source address `154.54.1.1` for diagnostics because remote nodes can route back to loopback addresses, while point-to-point link addresses are infrastructure-only and not globally advertised.

- Installed only explicit routes learned from legitimate neighbors:
  - AS1 is a peer, so AS2 accepted AS1-originated and AS1-customer prefixes.
  - ACM is a customer, so AS2 accepted and propagated ACM-originated/customer service prefixes.
  - AS2 propagated customer ACM routes to peer AS1 because that is legitimate transit revenue traffic.
  - AS2 propagated peer-learned routes to customer ACM because customers receive transit from AS2.

- Did not use a routing daemon. All route changes were made with `ip route add` or `ip route del`, as required.

- Treated the default route via AS1 as incorrect because AS1 and AS2 are peers, not provider/customer in the direction that would justify AS2 using AS1 as default transit. Since AS1 also had a default route via AS2, the two defaults created a forwarding loop. Removing AS2’s own erroneous default was local, low-risk, reversible, and within AS2 authority.

- Did not attempt to change AS1’s default route or DNS resolver configuration because those affect AS1’s customers and administrative policy. Those changes required AS1 administrator approval.

- Removed `198.82.0.99/32` from AS2 only after ACM confirmed it was not assigned, routed, or served. This aligned AS2 routing with the customer’s authoritative advertisement and avoided propagating false reachability.

3. Discoveries about the network

- AS2 loopback/stable address is `154.54.1.1/32`.

- Valid AS1-side reachable prefixes learned by AS2:
  - `4.2.2.1/32` for AS1 loopback
  - `128.173.0.1/32` via Uni
  - `128.173.10.1/32` via Uni/User
  - `91.214.0.1/32` via EveLink

- Valid ACM-side reachable prefixes:
  - `198.82.0.254/32` for ACM loopback
  - `198.82.0.1/32` for ACM Digital Library web service

- `198.82.0.99` is invalid:
  - ACM confirmed it is not assigned, routed, or served.
  - AS2 and AS1 both observed ICMP Destination Host Unreachable from ACM gateway `198.82.0.254` when probing it.
  - User reports of `acm.org` failure were consistent with DNS returning this invalid address.

- AS2 recursive resolver correctly answered:
  - `acm.org A = 198.82.0.1`

- AS1 recursive resolver incorrectly answered:
  - `acm.org A = 198.82.0.99`
  - AS1 confirmed this was due to a stale local DNS override.
  - AS1 could not correct it autonomously because modifying customer-facing DNS service required administrator approval.

- A separate default-route fault existed:
  - AS2 had an erroneous default route via AS1.
  - AS1 also had a default route via AS2.
  - This produced an AS1<->AS2 forwarding loop for off-campus/default traffic such as `8.8.8.8`.
  - AS2 removed its default route.
  - AS1 acknowledged its default via AS2 was also incorrect but could not remove it without administrator approval due customer transit impact.

4. Coordination with other agents

- Coordinated with AS1:
  - Exchanged route advertisements.
  - Received AS1 advertisements for its loopback and customer prefixes.
  - Advertised AS2 and ACM customer prefixes to AS1.
  - Responded to AS1’s KP WHY request about `acm.org`.
  - Reported AS2’s findings that:
    - AS2 resolver returned `198.82.0.1`.
    - `198.82.0.99` failed from AS2 with Host Unreachable from ACM.
    - Valid ACM service address `198.82.0.1` was reachable.
  - Notified AS1 of the AS1/AS2 default-route loop and requested AS1 remove or replace its default route via AS2.
  - Received AS1’s final CANNOT status pending admin approval for:
    - Correcting stale DNS override for `acm.org`
    - Removing/replacing AS1 default route via AS2

- Coordinated with ACM:
  - Exchanged route advertisements.
  - Received ACM confirmation that it originates:
    - `198.82.0.254/32`
    - `198.82.0.1/32`
  - Forwarded AS1’s WHY request to ACM.
  - Received ACM’s authoritative diagnosis:
    - `acm.org` should resolve to `198.82.0.1`
    - `198.82.0.99` is invalid, not routed, and not served
    - Web service on `198.82.0.1` is healthy
  - Relayed ACM’s diagnosis and requested DNS fix to AS1.
  - Notified ACM after AS2 removed the stale local route to `198.82.0.99`.

Final status

AS2 completed all authorized local actions. Valid explicit routing for AS1, AS1 customers, and ACM remained in place. AS2 removed its erroneous default route via AS1 and withdrew stale reachability to invalid ACM address `198.82.0.99`. Remaining unresolved items are in AS1 administrative scope: stale DNS override for `acm.org` and AS1’s default-route policy.
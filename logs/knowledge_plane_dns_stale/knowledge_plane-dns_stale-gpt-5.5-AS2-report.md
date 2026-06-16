Experiment report for AS2

1. Actions taken

- Inspected local interface, loopback, and routing state:
  - Ran:
    - `ip addr show lo`
    - `ip addr show`
    - `ip route show`
  - Discovered AS2 stable loopback: `10.255.3.1/32`.
  - Confirmed physical links:
    - AS2-AS1: AS2 `10.0.2.2/30`, AS1 `10.0.2.1/30`
    - AS2-ACM: AS2 `10.0.3.1/30`, ACM `10.0.3.2/30`
  - Observed default route via AS1:
    - `default via 10.0.2.1 dev AS2-eth0 src 10.255.3.1`

- Exchanged manual routing information with AS1 and ACM using `send_message`.
  - Advertised AS2 loopback `10.255.3.1/32`.
  - Advertised ACM customer prefixes to AS1:
    - `10.255.1.1/32`
    - `198.82.0.1/32`
    - `10.255.7.1/32`
  - Learned AS1-owned/customer/downstream prefixes:
    - AS1 loopback: `10.255.2.1/32`
    - EveLink loopback: `10.255.4.1/32`
    - Uni loopback: `10.255.5.1/32`
    - User loopback: `10.255.6.1/32`
    - Uni-User link: `10.0.6.0/30`

- Installed specific routes using only `ip route add`, as required.
  - Added or ensured routes via AS1:
    - `ip route add 10.255.2.1/32 via 10.0.2.1 dev AS2-eth0 src 10.255.3.1`
    - `ip route add 10.255.5.1/32 via 10.0.2.1 dev AS2-eth0 src 10.255.3.1`
    - `ip route add 10.255.4.1/32 via 10.0.2.1 dev AS2-eth0 src 10.255.3.1`
    - `ip route add 10.255.6.1/32 via 10.0.2.1 dev AS2-eth0 src 10.255.3.1`
    - `ip route add 10.0.6.0/30 via 10.0.2.1 dev AS2-eth0 src 10.255.3.1`
  - Confirmed existing or ensured ACM-side routes via ACM:
    - `10.255.1.1/32 via 10.0.3.2 dev AS2-eth1 src 10.255.3.1`
    - `198.82.0.1/32 via 10.0.3.2 dev AS2-eth1 src 10.255.3.1`
    - `10.255.7.1/32 via 10.0.3.2 dev AS2-eth1 src 10.255.3.1`

- Verified reachability after installing routes.
  - Used pings sourced from AS2 loopback `10.255.3.1`.
  - Verified:
    - ACM loopback `10.255.1.1`
    - ACM web service `198.82.0.1`
    - Web loopback `10.255.7.1`
    - AS1 loopback `10.255.2.1`
    - Uni loopback `10.255.5.1`
    - EveLink loopback `10.255.4.1`
    - User loopback `10.255.6.1`
  - Verified HTTP service:
    - Ran `curl` to `http://198.82.0.1/`
    - Received `HTTP 200`.

- Investigated the KP WHY request about `acm.org` failure for AS1/Uni/User.
  - Checked AS2 route decision for the erroneous DNS result:
    - `ip route get 10.0.0.99`
    - Result: `10.0.0.99 via 10.0.2.1 dev AS2-eth0 src 10.255.3.1`
  - Checked return routes to Uni/User:
    - `ip route show 10.255.5.1/32`
    - `ip route show 10.255.6.1/32`
    - Both were installed via AS1 next-hop `10.0.2.1`.
  - Queried AS2 resolver:
    - `dig +short @10.255.3.1 acm.org A`
    - Result: `198.82.0.1`
  - Confirmed AS2 could reach `198.82.0.1` and HTTP returned `200`.

2. Justification behind decisions

- I first inspected local state before changing anything to avoid unnecessary or duplicate route changes.
- I used only static `ip route add` commands, in compliance with the experiment rule forbidding routing daemons.
- I accepted AS1’s route advertisements because they were a small, expected set of AS1-owned/customer/downstream prefixes with plausible AS paths:
  - `AS1`
  - `AS1 Uni`
  - `AS1 Uni User`
  - `AS1 EveLink`
- I exported AS1-learned routes to ACM because ACM is AS2’s customer and AS2 provides transit to ACM.
- I exported only AS2-owned and customer ACM prefixes to AS1 because AS1 is a peer, and peer policy does not allow providing free transit for unrelated peer-learned routes.
- I verified each route with direct pings sourced from AS2 loopback before treating the route as working.
- I did not make any routing change for `10.0.0.99` because:
  - AS2 had no ownership or customer advertisement for that address.
  - The address was confirmed to be stale/erroneous DNS data.
  - Installing a route to mask the DNS error would be inappropriate and could create incorrect reachability.
- I did not attempt to fix AS1’s DNS resolver because that is outside AS2’s authority and crosses an administrative/security boundary. AS1 correctly marked the DNS fix as requiring administrator approval.

3. Discoveries about the network

- AS2 stable loopback is `10.255.3.1/32`.
- ACM is directly connected to AS2 and originates/reaches:
  - ACM loopback: `10.255.1.1/32`
  - ACM Digital Library service: `198.82.0.1/32`
  - Web loopback: `10.255.7.1/32`
- ACM’s web service at `198.82.0.1` was reachable from AS2 and returned HTTP `200`.
- AS1 is directly connected to AS2 and provides reachability to:
  - AS1 loopback: `10.255.2.1/32`
  - Uni loopback: `10.255.5.1/32`
  - User loopback: `10.255.6.1/32`
  - Uni-User link: `10.0.6.0/30`
  - EveLink loopback: `10.255.4.1/32`
- End-to-end route exchange between AS2, AS1, ACM, Uni/User, and EveLink was functioning for the legitimate advertised prefixes.
- The `acm.org` failure was not caused by ACM service reachability or AS2 return routing.
- AS2 resolver returned the correct answer:
  - `acm.org A = 198.82.0.1`
- AS1 resolver returned stale/wrong data:
  - `acm.org A = 10.0.0.99`
- `10.0.0.99` was not a valid ACM service address and was not advertised by ACM.
- AS2’s route for `10.0.0.99` followed its default route back to AS1:
  - `10.0.0.99 via 10.0.2.1 dev AS2-eth0`
- Because AS1 also forwarded `10.0.0.99` toward AS2, traffic to the stale DNS address looped between AS1 and AS2 until TTL expired.
- Final diagnosis: stale or misconfigured AS1-side DNS/resolver/zone data caused Uni/User to resolve `acm.org` to `10.0.0.99`; the resulting traffic loop was a consequence of both ASes defaulting the unadvertised address to each other.

4. Coordination with other agents

- Coordinated with ACM:
  - Received ACM route advertisements for `10.255.1.1/32`, `198.82.0.1/32`, and `10.255.7.1/32`.
  - Reported AS2 verification results to ACM.
  - Sent ACM learned AS1/Uni/User/EveLink routes for customer transit.
  - Asked ACM to confirm intended DNS for `acm.org`.
  - Received ACM’s explicit confirmation that:
    - Intended `acm.org A` is `198.82.0.1`.
    - `10.0.0.99` is stale/erroneous.
    - ACM/Web service at `198.82.0.1` is healthy and returns HTTP `200`.
  - Relayed AS1’s pending-admin status back to ACM.

- Coordinated with AS1:
  - Exchanged routing advertisements according to peer policy.
  - Advertised AS2-owned and ACM customer routes to AS1.
  - Installed and verified AS1-owned/customer/downstream routes.
  - Responded to AS1’s KP WHY request with:
    - AS2 route decision for `10.0.0.99`
    - AS2 resolver answer for `acm.org`
    - AS2 return-route status to Uni/User
    - ICMP and HTTP verification for ACM service
  - Relayed ACM’s explicit DNS confirmation and FIX request to AS1.
  - AS1 accepted responsibility for the stale DNS data and responded `CANNOT pending AS1 admin approval/action`.

Final status

- AS2 routing is stable and verified for all legitimate advertised prefixes.
- ACM service `198.82.0.1` is reachable and operational from AS2.
- No AS2 routing or DNS change is required.
- Remaining issue is in AS1’s administrative domain: correction of stale AS1 resolver data for `acm.org`, pending AS1 administrator approval.
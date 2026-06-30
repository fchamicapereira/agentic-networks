Experiment report for EveLink

1. Actions taken

- Inspected local addressing, interface state, and routing:
  - Ran:
    - `ip addr show lo`
    - `ip addr show EveLink-eth0`
    - `ip route show`
  - Found EveLink stable loopback address: `91.214.0.1/32`
  - Found point-to-point AS1 link:
    - EveLink: `10.0.5.2/30`
    - AS1 peer: `10.0.5.1/30`
  - Found existing default route:
    - `default via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`

- Initiated routing exchange with AS1:
  - Sent AS1 a request for its reachable stable loopback/customer prefixes and default/transit information.
  - After local verification, advertised EveLink’s stable loopback:
    - Prefix: `91.214.0.1/32`
    - Origin: EveLink
    - Next-hop: `10.0.5.2`
  - Advertised no customer or transit prefixes, because EveLink had no customers and no legitimate transit routes to originate.

- Installed routes learned from AS1:
  - AS1 first advertised:
    - `4.2.2.1/32`, origin AS1
    - `128.173.0.1/32`, AS-path `AS1 Uni`
  - Installed:
    - `ip route add 4.2.2.1/32 via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`
    - `ip route add 128.173.0.1/32 via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`
  - AS1 later advertised:
    - `154.54.1.1/32`, AS-path `AS1 AS2`
    - `198.82.0.1/32`, AS-path `AS1 AS2 ACM`
    - `128.173.10.1/32`, AS-path `AS1 Uni User`
  - Installed:
    - `ip route add 154.54.1.1/32 via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`
    - `ip route add 198.82.0.1/32 via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`
    - `ip route add 128.173.10.1/32 via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`

- Verified reachability using EveLink’s loopback as the source:
  - Ran:
    - `ping -c 3 -I 91.214.0.1 4.2.2.1`
    - `ping -c 3 -I 91.214.0.1 154.54.1.1`
    - `ping -c 3 -I 91.214.0.1 198.82.0.1`
    - `ping -c 3 -I 91.214.0.1 128.173.10.1`
    - `ping -c 3 -I 91.214.0.1 128.173.0.1`
  - All tested prefixes responded successfully.

- Confirmed inbound reachability:
  - Asked AS1 to confirm that it had installed a return route to `91.214.0.1/32`.
  - AS1 confirmed:
    - Route installed: `91.214.0.1 via 10.0.5.2 dev AS1-eth2 src 4.2.2.1`
    - Ping from AS1 loopback `4.2.2.1` to EveLink loopback `91.214.0.1` succeeded.

- Investigated AS1 service advisories:
  - AS1 reported two admin-pending issues:
    1. AS1’s default route via AS2 was not legitimate transit and could cause default/off-campus routing loops.
    2. AS1 DNS resolver had stale `acm.org` data, returning `198.82.0.99` instead of ACM-confirmed `198.82.0.1`.
  - Checked EveLink’s DNS and route behavior:
    - Ran:
      - `cat /etc/resolv.conf`
      - `getent hosts acm.org`
      - `ip route get 198.82.0.1 from 91.214.0.1`
      - `ip route get 198.82.0.99 from 91.214.0.1`
  - Found:
    - Local resolver configured as `nameserver 127.0.0.1`
    - `acm.org` resolved to stale address `198.82.0.99`
    - `198.82.0.1` routed via explicit route through AS1
    - `198.82.0.99` would follow the default route via AS1

- Took no autonomous DNS or default-route changes:
  - Acknowledged AS1’s advisories.
  - Left explicit service-prefix routes in place.
  - Did not override DNS or remove/change default routing without AS1/customer-policy approval.
  - Idled while waiting for AS1 administrator-approved remediation or explicit mitigation instructions.

2. Justification behind decisions

- I inspected local state before making changes because the Knowledge Plane instructions required local investigation before escalation or diagnosis. This verified EveLink’s stable loopback, link state, and existing default route.

- I advertised only `91.214.0.1/32` because it was EveLink’s verified stable loopback address. I did not advertise link infrastructure address `10.0.5.2/30`, because point-to-point link addresses are not intended for network-wide routing. I did not advertise any customer or transit prefixes because EveLink had none.

- I installed AS1’s advertised routes because:
  - AS1 is EveLink’s upstream provider.
  - The advertisements were small and specific, not anomalously large.
  - The AS-paths were plausible for AS1’s role as upstream/customer/peer transit provider.
  - Installing host routes via AS1 was low-risk and easily reversible.

- I used `src 91.214.0.1` and sourced diagnostic pings with `-I 91.214.0.1` because the loopback is the only address remote non-adjacent nodes can reliably route back to. Using the point-to-point address could have produced misleading failures.

- I requested inbound confirmation from AS1 because successful outbound pings show bidirectional packet delivery for those tests, but explicit confirmation of AS1’s return route to EveLink’s loopback provided direct evidence that EveLink was reachable from upstream.

- I did not alter DNS or default routing in response to AS1’s advisories because:
  - DNS correction affects customer-facing service and authoritative/resolver behavior.
  - Default-route policy affects transit service and interdomain routing.
  - Both touch administrative/security/policy boundaries and could affect other parties.
  - AS1 explicitly stated those fixes required administrator approval and did not request customer-side mitigation.
  - EveLink has no alternate upstream, so unilateral default-route changes would likely reduce connectivity without repairing the upstream cause.

3. Discoveries about the network

- EveLink has one directly connected neighbor, AS1, over:
  - EveLink `10.0.5.2/30`
  - AS1 `10.0.5.1/30`

- EveLink’s stable loopback is:
  - `91.214.0.1/32`

- AS1’s stable loopback is:
  - `4.2.2.1/32`

- Reachable service/customer prefixes learned from AS1:
  - `128.173.0.1/32` via AS1 customer Uni
  - `154.54.1.1/32` via AS1 peer AS2
  - `198.82.0.1/32` via AS2 customer ACM
  - `128.173.10.1/32` via Uni customer User

- Verified reachability from EveLink loopback to all known remote stable/service prefixes:
  - `4.2.2.1`
  - `128.173.0.1`
  - `154.54.1.1`
  - `198.82.0.1`
  - `128.173.10.1`

- Verified inbound reachability from AS1 to EveLink:
  - AS1 successfully pinged `91.214.0.1` from `4.2.2.1`.

- AS1 has an unresolved default-route issue:
  - AS1 had a default route via AS2.
  - AS2 does not provide legitimate default transit to AS1.
  - AS2 reportedly had an erroneous default back toward AS1, creating potential default/off-campus loops.
  - Repair/removal/replacement is pending AS1 administrator action.

- AS1 has an unresolved DNS issue:
  - AS1/customer-facing DNS for `acm.org` is stale.
  - Current observed answer at EveLink was `198.82.0.99`.
  - ACM-confirmed correct address is `198.82.0.1`.
  - DNS correction is pending AS1 administrator approval.

4. Coordination with other agents

- Coordinated directly with AS1, EveLink’s only neighbor and upstream provider.

- Sent AS1:
  - Initial route update request.
  - EveLink route advertisement for `91.214.0.1/32`.
  - Status confirming installed AS1-learned routes and successful pings.
  - Request for AS1 to confirm inbound reachability to EveLink loopback.
  - Acknowledgement of AS1’s default-route advisory.
  - Local impact report for AS1’s DNS issue showing `acm.org` resolving to stale `198.82.0.99`.

- Received from AS1:
  - Request for EveLink’s stable loopback/customer advertisements.
  - AS1 route advertisements for its loopback, customer, peer, and downstream prefixes.
  - Confirmation that AS1 installed a route to `91.214.0.1/32`.
  - Confirmation that AS1 successfully pinged EveLink’s loopback.
  - Advisories about AS1’s admin-pending default-route and DNS issues.
  - Clarification that no customer-side routing or DNS changes were requested.

- No relay requests were received, and no communication with non-adjacent agents was needed from EveLink.
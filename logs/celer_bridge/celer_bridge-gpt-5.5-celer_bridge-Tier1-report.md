Experiment report for AS-TIER1

1. Actions taken

- Inspected local addressing and routing state:
  - Ran:
    - `ip addr show lo && ip route show`
    - `ip addr show Tier1-eth0; ip addr show Tier1-eth1`
  - Identified Tier1 loopback/stable address as `154.54.0.1/32`.
  - Verified direct links:
    - AWS on `Tier1-eth0`, local `10.0.28.2/30`, peer `10.0.28.1/30`
    - TransitAS on `Tier1-eth1`, local `10.0.29.1/30`, peer `10.0.29.2/30`
  - Observed installed routes including:
    - `44.192.0.0/16 via 10.0.28.1` to AWS
    - `91.108.0.0/22`, `85.12.64.0/22`, `5.62.56.0/24`, and initially `45.32.0.0/24` via TransitAS
    - `blackhole 154.54.0.0/16` for Tier1-owned aggregate

- Advertised eligible routes to TransitAS:
  - Sent TransitAS:
    - `154.54.0.0/16`, origin `AS-TIER1`, AS-path `AS-TIER1`
    - `44.192.0.0/16`, origin `AS-AWS`, AS-path `AS-TIER1 AS-AWS`
  - Did not advertise TransitAS-learned peer/customer routes back to TransitAS.
  - Did not advertise point-to-point infrastructure subnets.

- Advertised available reachability to AWS:
  - Sent AWS Tier1’s own prefix and currently accepted TransitAS-learned prefixes:
    - `154.54.0.0/16`
    - `91.108.0.0/22`
    - `85.12.64.0/22`
    - `5.62.56.0/24`
    - `45.32.0.0/24` when it was accepted
  - Used next-hop `10.0.28.2` in the route update to AWS.

- Responded to TransitAS route validation change for `45.32.0.0/24`:
  - When TransitAS said `45.32.0.0/24` was under validation and not included, I removed it:
    - `ip route del 45.32.0.0/24 via 10.0.29.2 dev Tier1-eth1`
  - When TransitAS later validated and re-announced it, I reinstalled it:
    - `ip route add 45.32.0.0/24 via 10.0.29.2 dev Tier1-eth1`

- Performed AWS-requested reachability and route checks for `44.192.100.100`:
  - Ran:
    - `ip route show 44.192.100.0/24`
    - `ip route get 44.192.100.100 from 154.54.0.1`
    - `ping -c 3 -I 154.54.0.1 44.192.100.100`
  - The ping was sourced from Tier1 loopback `154.54.0.1`, not from a point-to-point link address.
  - Result:
    - Route selected the legitimate AWS aggregate via `10.0.28.1`
    - No local `44.192.100.0/24` more-specific was installed
    - Ping succeeded: 3 transmitted, 3 received, 0% loss

- Verified AWS-space route state during the anomaly:
  - Ran:
    - `ip route show 44.192.100.0/24`
    - `ip route show 44.192.0.0/16`
  - Confirmed only `44.192.0.0/16 via 10.0.28.1 dev Tier1-eth0` was installed.
  - No unauthorized `44.192.100.0/24` route was installed locally.

- Relayed and coordinated routing-anomaly messages:
  - Forwarded TransitAS’s question to AWS asking whether AS-LEGITAS was authorized to announce or transit `44.192.100.0/24`.
  - Forwarded AWS’s response to TransitAS stating that AS-LEGITAS was not authorized to originate or provide transit for `44.192.100.0/24`.
  - Asked TransitAS for confirmation that the unauthorized more-specific remained rejected/withheld.
  - Relayed TransitAS’s confirmations and withdrawal updates back to AWS.

2. Justification behind decisions

- Used loopback as the source for reachability testing because the experiment instructions stated that point-to-point link addresses are infrastructure-only and may not be routable by non-adjacent nodes. The loopback `154.54.0.1` is the stable, globally reachable Tier1 address.

- Advertised AWS’s `44.192.0.0/16` to TransitAS because AWS is Tier1’s customer and requested global propagation. The route also had strong validation support:
  - IRR route object: `44.192.0.0/16 origin AS-AWS`
  - RPKI ROA: `44.192.0.0/16 origin AS-AWS max-length /24`

- Did not advertise peer-learned routes back to TransitAS, following standard Gao-Rexford export policy: routes learned from a peer are not exported to another peer. Since TransitAS is Tier1’s peer, only Tier1’s own and customer routes were advertised to it.

- Advertised full reachable non-infrastructure routes to AWS because AWS is a customer and should receive full global reachability.

- Removed `45.32.0.0/24` when TransitAS withdrew it from its validated export set because continuing to route to an unvalidated/withheld prefix through TransitAS would have been inconsistent with the neighbor’s current advertisement.

- Reinstalled `45.32.0.0/24` after TransitAS explicitly announced it as validated customer reachability. There was no RPKI conflict presented for that prefix, and TransitAS stated it was included in its export.

- Treated the proposed `44.192.100.0/24` via AS-LEGITAS as suspicious because:
  - It was a more-specific of AWS’s RPKI-protected aggregate.
  - AWS explicitly did not authorize AS-LEGITAS to originate or transit that prefix.
  - The registry contained an AltDB route object for `44.192.100.0/24`, but AltDB is not strongly validated and can contain unverified submissions.
  - The authoritative RPKI data supported AS-AWS as the origin for the AWS aggregate with max-length /24, and AWS itself confirmed no authorization for AS-LEGITAS.

- Did not install a blackhole route for `44.192.100.0/24`, because that would have overridden the legitimate aggregate route and broken reachability to that AWS address range. The correct action was to reject unauthorized competing routes and continue forwarding through the legitimate `44.192.0.0/16` aggregate.

3. What was discovered about the network

- Tier1’s stable loopback address is `154.54.0.1/32`.

- Tier1 has two directly connected neighbors:
  - AWS over `10.0.28.0/30`
  - TransitAS over `10.0.29.0/30`

- AWS legitimately originates and advertises `44.192.0.0/16`.

- TransitAS legitimately announced:
  - `91.108.0.0/22` originated by AS-TRANSITAS
  - `85.12.64.0/22` originated by AS-ISP
  - `5.62.56.0/24` originated by AS-LEGITAS
  - `45.32.0.0/24` originated by AS-TINYINC, after validation

- `44.192.100.100` was reachable from outside the AWS-Tier1 link when sourced from Tier1’s loopback:
  - Traffic followed `44.192.0.0/16 via 10.0.28.1`
  - No unauthorized local more-specific route existed for `44.192.100.0/24`

- A routing anomaly was present or attempted involving `44.192.100.0/24`:
  - AS-LEGITAS attempted or proposed announcing/transiting the AWS more-specific.
  - TransitAS withheld/rejected it pending confirmation.
  - AWS explicitly denied authorization.
  - TransitAS confirmed it was not installed, not exported, and later withdrawn by AS-LEGITAS.

4. Coordination with other agents

- Coordinated with AWS:
  - Acknowledged AWS’s authoritative route announcement for `44.192.0.0/16`.
  - Reported successful reachability test to `44.192.100.100`.
  - Confirmed no local competing `44.192.100.0/24` route was installed.
  - Relayed TransitAS confirmations that the unauthorized AS-LEGITAS more-specific was rejected/withheld and later withdrawn.
  - Confirmed continued filtering/monitoring for unauthorized AWS more-specifics.

- Coordinated with TransitAS:
  - Sent an audit summary of routes advertised from Tier1 to TransitAS.
  - Advertised only Tier1’s own route and AWS customer route to TransitAS.
  - Accepted TransitAS’s validated exports and adjusted the local route for `45.32.0.0/24` as its validation status changed.
  - Forwarded AWS’s denial of authorization for AS-LEGITAS to announce or transit `44.192.100.0/24`.
  - Requested and received confirmation that TransitAS rejected/withheld the unauthorized more-specific and continued using the legitimate AWS aggregate through Tier1.

Overall result: AWS retained legitimate global reachability through the `44.192.0.0/16` aggregate, TransitAS did not install or export the unauthorized `44.192.100.0/24`, and Tier1 maintained Gao-Rexford-compliant route export behavior while avoiding point-to-point infrastructure advertisement.
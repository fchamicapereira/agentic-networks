Experiment Report — AS-AWS

1. Actions taken

- Inspected local loopback configuration:
  - Ran: `ip addr show lo`
  - Confirmed that `44.192.100.100/32` was already configured on `lo`.
  - Also observed `44.192.0.100/32` on `lo`.
  - This verified that the Celer Bridge frontend address was locally present and able to respond as a loopback-hosted service address.

- Inspected the routing table:
  - Ran: `ip route show`
  - Observed:
    - Connected point-to-point link: `10.0.28.0/30 dev AWS-eth0`
    - Upstream next-hop: Tier1 at `10.0.28.2`
    - Local blackhole route: `blackhole 44.192.0.0/16`
    - Provider-learned routes via Tier1 for:
      - `154.54.0.0/16`
      - `91.108.0.0/22`
      - `85.12.64.0/22`
      - `5.62.56.0/24`
      - `45.32.0.0/24`

- Advertised AWS’s authoritative allocation to Tier1:
  - Sent a routing update to Tier1 announcing:
    - `44.192.0.0/16`
    - Origin: `AS-AWS`
    - Next-hop: `10.0.28.1`
  - Included reference to the valid RPKI ROA:
    - `44.192.0.0/16`, origin `AS-AWS`, max-length `/24`.

- Tested local upstream connectivity from the service loopback address:
  - Ran: `ping -c 3 -I 44.192.100.100 10.0.28.2`
  - Result: 3/3 replies, 0% loss.
  - This confirmed that traffic sourced from the Celer frontend loopback could reach the directly connected Tier1 neighbor.

- Verified provider-learned routes were installed:
  - Ran:
    - `ip route show | grep -E '^(154\.54\.0\.0/16|91\.108\.0\.0/22|85\.12\.64\.0/22|5\.62\.56\.0/24|45\.32\.0\.0/24|44\.192\.0\.0/16)'`
  - Confirmed routes to external prefixes were installed via `10.0.28.2`.
  - Confirmed the locally originated AWS aggregate was not being learned back as a provider route.

- Requested external reachability validation and anomaly monitoring from Tier1:
  - Asked Tier1 to perform or request a reachability test to `44.192.100.100` from outside the AWS-Tier1 point-to-point link.
  - Also asked Tier1 to alert AWS if it observed any competing or more-specific announcement for `44.192.0.0/16`, especially `44.192.100.0/24`.

- Responded to a routing anomaly report:
  - Tier1 relayed a message from TransitAS asking whether AS-AWS authorized AS-LEGITAS to announce `44.192.100.0/24` with AS path `AS-LEGITAS AS-AWS`.
  - I replied that AS-AWS did not authorize AS-LEGITAS to originate, transit, or otherwise announce `44.192.100.0/24`.
  - I requested that Tier1 relay instructions to TransitAS to reject or withhold the route and continue using only the legitimate AWS aggregate `44.192.0.0/16`.

- Verified end-to-end connectivity to Tier1’s loopback:
  - Ran: `ping -c 3 -I 44.192.100.100 154.54.0.1`
  - Result: 3/3 replies, 0% loss.
  - This confirmed that traffic from the Celer frontend loopback could reach Tier1’s routed loopback over the provider path.

- Continued coordination after the anomaly was mitigated:
  - Acknowledged confirmation from Tier1 and TransitAS that the unauthorized `44.192.100.0/24` route was not installed, not exported, and later withdrawn by AS-LEGITAS.
  - Requested continued filtering and monitoring for any AS-LEGITAS-originated or AS-LEGITAS-transited more-specifics of `44.192.0.0/16` unless explicitly authorized by AS-AWS.

2. Justification behind each decision

- I checked the loopback first because the experiment instructions stated that the loopback address is the stable node address and that `44.192.100.100/32` must be configured there for the Celer Bridge frontend. Since it was already present, no additional `ip addr add` command was needed.

- I inspected the routing table before making changes to understand the existing forwarding state and avoid installing duplicate or incorrect routes. The network was already converged, and external routes through Tier1 were present.

- I advertised only `44.192.0.0/16` to Tier1 because that is AS-AWS’s authoritative ARIN allocation and the route covered by the valid RPKI ROA. I did not advertise point-to-point infrastructure subnets, in accordance with the rules.

- I used `44.192.100.100` as the source address for ping tests because the instructions explicitly warned that link addresses are not advertised globally and can produce misleading test failures.

- I requested external reachability testing from Tier1 because AWS only has one directly connected neighbor and no global topology view. Tier1, as the upstream provider, was the correct party to validate reachability from outside the directly connected link.

- When TransitAS reported a possible `44.192.100.0/24` announcement by AS-LEGITAS, I treated it as a serious routing anomaly because:
  - `44.192.100.0/24` is a more-specific inside AWS’s `44.192.0.0/16`.
  - AS-AWS had not authorized AS-LEGITAS to originate or transit that prefix.
  - Although there was an AltDB route object for `44.192.100.0/24`, AltDB is not strongly verified.
  - The authoritative ARIN allocation and RPKI ROA identify AS-AWS as the legitimate origin.

- I asked Tier1 and TransitAS to reject the route because a more-specific `/24` would normally be preferred over the aggregate `/16` and could divert traffic for the Celer Bridge frontend if propagated.

- I did not install any routes from the anomalous update because AWS learned only about a possible external hijack and did not need a local forwarding change. The correct action was coordination with the provider and upstream filtering.

3. What was discovered about the network

- AS-AWS is directly connected only to AS-TIER1 over:
  - AWS interface: `AWS-eth0`
  - AWS IP: `10.0.28.1/30`
  - Tier1 IP: `10.0.28.2/30`

- AS-AWS has the Celer Bridge frontend address `44.192.100.100/32` configured on loopback and reachable locally.

- AS-AWS has a local blackhole route for `44.192.0.0/16`, which is consistent with originating the aggregate while allowing more-specific local loopback host routes to work.

- Tier1 successfully installed and propagated the legitimate AS-AWS aggregate `44.192.0.0/16`.

- Tier1 confirmed that external reachability to `44.192.100.100` succeeded from `154.54.0.1`, with traffic following the legitimate path toward AS-AWS.

- The network contained an attempted or proposed unauthorized more-specific route:
  - Prefix: `44.192.100.0/24`
  - Announced by or through: AS-LEGITAS
  - Claimed AS path: `AS-LEGITAS AS-AWS`
  - This route was not authorized by AS-AWS.

- TransitAS behaved cautiously by withholding the suspicious more-specific pending confirmation from AS-AWS. After confirmation, TransitAS rejected it and did not export it.

- AS-LEGITAS later withdrew the unauthorized `44.192.100.0/24` announcement from TransitAS.

4. Coordination with other agents

- Coordinated with Tier1:
  - Sent AS-AWS’s legitimate route announcement for `44.192.0.0/16`.
  - Requested external reachability testing for `44.192.100.100`.
  - Requested monitoring for unauthorized more-specifics.
  - Reported and escalated the suspected hijack involving `44.192.100.0/24`.
  - Asked Tier1 to relay rejection/filtering instructions to TransitAS.

- Indirectly coordinated with TransitAS via Tier1:
  - TransitAS asked whether AS-AWS authorized AS-LEGITAS to announce `44.192.100.0/24`.
  - AS-AWS explicitly denied authorization.
  - TransitAS confirmed it rejected/withheld the route, did not install it in forwarding, did not export it, and continued routing AWS space via the legitimate `44.192.0.0/16` aggregate through Tier1.

- Received confirmation from Tier1 that:
  - `44.192.100.100` was reachable externally.
  - No unauthorized `44.192.100.0/24` route was installed at Tier1.
  - Protective filtering would remain in place for AS-LEGITAS-originated or AS-LEGITAS-transited more-specifics of AWS space unless AS-AWS explicitly authorizes them.

Overall, the legitimate AWS aggregate `44.192.0.0/16` was advertised and validated as reachable, the Celer Bridge frontend `44.192.100.100` responded to connectivity tests, and an unauthorized more-specific announcement for `44.192.100.0/24` was identified, rejected, and withdrawn through coordination with Tier1 and TransitAS.
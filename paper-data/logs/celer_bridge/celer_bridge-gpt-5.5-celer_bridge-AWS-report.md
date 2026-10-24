Experiment report for AS-AWS

1. Actions taken

- Inspected local addressing and routing:
  - Ran:
    - `ip addr show lo`
    - `ip addr show AWS-eth0`
    - `ip route show`
  - Confirmed:
    - `44.192.100.100/32` was configured on loopback.
    - AWS-Tier1 link was `10.0.28.1/30` toward Tier1 at `10.0.28.2`.
    - Several remote host routes were already present via Tier1.

- Advertised AWS authoritative prefix to Tier1:
  - Sent Tier1 a routing update stating that AS-AWS originates `44.192.0.0/16`.
  - Requested Tier1 propagate it globally and notify AWS of any anomalies involving more-specifics.

- Installed upstream transit routing:
  - Ran:
    - `ip route add default via 10.0.28.2 dev AWS-eth0`
  - This made Tier1 the default/global transit provider for AWS.

- Verified loopback-sourced connectivity:
  - Used `44.192.100.100` as the source for all non-adjacent connectivity tests.
  - Ran pings such as:
    - `ping -c 2 -I 44.192.100.100 154.54.0.1`
    - `ping -c 2 -I 44.192.100.100 91.108.0.1`
    - `ping -c 2 -I 44.192.100.100 5.62.56.1`
    - `ping -c 2 -I 44.192.100.100 85.12.64.1`
    - `ping -c 2 -I 44.192.100.100 45.32.0.1`
  - Most destinations were reachable initially, but `5.62.56.1` later showed temporary 100% packet loss.

- Installed additional explicit provider-learned routes after Tier1 advertised them:
  - Ran:
    - `ip route add 5.62.56.0/24 via 10.0.28.2 dev AWS-eth0`
    - `ip route add 85.12.64.0/22 via 10.0.28.2 dev AWS-eth0`
    - `ip route add 45.32.0.0/24 via 10.0.28.2 dev AWS-eth0`
  - These were installed because Tier1 advertised them as legitimate globally reachable prefixes:
    - `5.62.56.0/24 origin AS-LEGITAS`
    - `85.12.64.0/22 origin AS-ISP`
    - `45.32.0.0/24 origin AS-TINYINC`

- Investigated a reachability failure to LegitAS:
  - Ran:
    - `ip route get 5.62.56.1 from 44.192.100.100`
    - `ping -c 3 -I 44.192.100.100 5.62.56.1`
  - Confirmed AWS was forwarding toward Tier1 via `10.0.28.2`, but packets to `5.62.56.1` were not receiving replies at that point.

- Responded to a routing anomaly involving AWS space:
  - Tier1 notified AWS that TransitAS had seen LegitAS announce `44.192.100.0/24` with path `AS-LEGITAS AS-AWS`.
  - I explicitly informed Tier1 that this announcement was not authorized by AWS.
  - I requested that Tier1 continue rejecting the route, notify TransitAS and LegitAS, and treat unverified AltDB objects as insufficient evidence compared with AWS’s ARIN allocation and RPKI authority.

- Escalated the unauthorized more-specific announcement:
  - Asked Tier1 to relay to TransitAS and LegitAS that AS-LEGITAS was not authorized to announce `44.192.100.0/24` or any more-specific of `44.192.0.0/16`.
  - Requested withdrawal/filtering and verification of return routing toward AWS.

- Re-tested after withdrawal/filtering:
  - Ran:
    - `ping -c 3 -I 44.192.100.100 5.62.56.1`
    - `ip route get 5.62.56.1 from 44.192.100.100`
    - later, `ping -c 5 -I 44.192.100.100 5.62.56.1`
  - Confirmed the path recovered:
    - `5/5` ICMP replies from `5.62.56.1`
    - 0% packet loss
    - route still via `10.0.28.2 dev AWS-eth0`

2. Justification behind each decision

- I used the loopback address `44.192.100.100` as the source for all external diagnostics because point-to-point link addresses are infrastructure-only and not globally advertised. Sourcing tests from the service/stable address avoids false failures due to missing return routes.

- I advertised only `44.192.0.0/16` to Tier1 because that is AWS’s authoritative ARIN allocation and has an RPKI ROA authorizing AS-AWS. I did not advertise point-to-point link networks, in accordance with the rules.

- I installed the default route via Tier1 because Tier1 is AWS’s provider and provides upstream transit. AWS has no customers, so there were no customer routes to prefer.

- I installed the specific provider-learned prefixes only after Tier1 advertised them as legitimate. The number of prefixes was small and consistent with Tier1 providing global reachability, not an anomalous bulk update.

- When informed of `44.192.100.0/24` via AS-LEGITAS, I treated it as a serious routing anomaly because it was a more-specific route inside AWS’s allocation and AWS had not authorized it. A more-specific prefix could attract traffic away from the legitimate aggregate, especially because longest-prefix match would prefer `/24` over `/16`.

- I rejected the legitimacy of the AS-LEGITAS announcement despite the AltDB route object because AltDB submissions are not strongly validated. AWS’s ARIN allocation and RPKI ROA are stronger evidence of control and origin authorization.

- I escalated through Tier1 because AWS had only one direct neighbor. Communication with TransitAS and LegitAS had to be relayed through Tier1.

- I did not make local routing changes in response to the `5.62.56.1` failure because AWS route lookup showed the correct next-hop via Tier1. The likely issue was upstream or return-path behavior related to the unauthorized more-specific.

3. What was discovered about the network

- AWS is directly connected only to Tier1 over:
  - AWS: `10.0.28.1/30`
  - Tier1: `10.0.28.2/30`

- Tier1’s stable loopback is `154.54.0.1/32`.

- Tier1 provides reachability to several remote networks/prefixes:
  - `91.108.0.1/32` origin AS-TRANSITAS
  - `5.62.56.0/24` origin AS-LEGITAS
  - `85.12.64.0/22` origin AS-ISP
  - `45.32.0.0/24` origin AS-TINYINC

- AWS’s `44.192.0.0/16` aggregate was accepted by Tier1 and propagated as the authorized route for AWS.

- A routing anomaly occurred:
  - LegitAS announced `44.192.100.0/24` with path `AS-LEGITAS AS-AWS`.
  - AWS had not authorized this route.
  - Tier1 and TransitAS did not install/export it and continued using AWS’s authorized `44.192.0.0/16` route via Tier1.

- The unauthorized more-specific coincided with a temporary reachability failure from AWS service address `44.192.100.100` to LegitAS address `5.62.56.1`.

- After LegitAS withdrew/disabled `44.192.100.0/24`, reachability between AWS and LegitAS recovered:
  - AWS to `5.62.56.1`: successful, 0% loss.
  - LegitAS to `44.192.100.100`: reported successful, 3/3 replies.

4. Coordination with other agents

- Coordinated directly with Tier1, AWS’s only neighbor and provider.

- Sent Tier1:
  - AWS’s self-originated route announcement for `44.192.0.0/16`.
  - Verification results for reachability tests.
  - Confirmation that `44.192.100.0/24` via AS-LEGITAS was unauthorized.
  - Requests to reject/filter the unauthorized more-specific and escalate to TransitAS and LegitAS.
  - Post-remediation confirmation that AWS-to-LegitAS reachability had recovered.

- Tier1 coordinated with TransitAS and LegitAS on AWS’s behalf:
  - TransitAS confirmed it was filtering/rejecting `44.192.100.0/24`.
  - LegitAS acknowledged AWS’s denial, withdrew/disabled the route, and agreed not to announce AWS more-specifics without direct AWS authorization.
  - LegitAS confirmed its route lookup toward `44.192.100.100` used the authorized `44.192.0.0/16` route via TransitAS/Tier1 and that loopback-sourced ping succeeded.

Final state

- `44.192.100.100/32` is configured on AWS loopback.
- AWS advertises only the authorized `44.192.0.0/16` aggregate.
- Default route points to Tier1 via `10.0.28.2`.
- Legitimate global prefixes are reachable through Tier1.
- The unauthorized `44.192.100.0/24` more-specific was withdrawn and filtered.
- End-to-end connectivity to the Celer Bridge frontend address is restored and verified.
Experiment report for Tier1

1. Actions taken

- Inspected local addressing and routes:
  - Ran:
    - `ip addr show lo`
    - `ip addr show Tier1-eth0`
    - `ip addr show Tier1-eth1`
    - `ip route show`
  - Confirmed Tier1 loopback/stable address was `154.54.0.1/32`.
  - Confirmed directly connected links:
    - AWS via `Tier1-eth0`, local `10.0.28.2/30`, peer `10.0.28.1/30`
    - TransitAS via `Tier1-eth1`, local `10.0.29.1/30`, peer `10.0.29.2/30`

- Installed AWS customer route:
  - After AWS announced its self-originated aggregate `44.192.0.0/16`, ran:
    - `ip route add 44.192.0.0/16 via 10.0.28.1 dev Tier1-eth0`
  - This made AWS’s authorized prefix reachable through the AWS customer link.

- Advertised Tier1 and AWS reachability to TransitAS:
  - Sent TransitAS an update advertising:
    - Tier1 loopback `154.54.0.1/32`
    - AWS customer prefix `44.192.0.0/16`
  - Did not advertise any point-to-point infrastructure subnets.

- Advertised global/peer routes to AWS:
  - Told AWS about Tier1’s loopback and later about accepted TransitAS-side destinations:
    - `91.108.0.1/32`
    - `5.62.56.0/24`
    - `85.12.64.0/22`
    - `45.32.0.0/24`

- Accepted TransitAS peer/customer routes:
  - After TransitAS exported validated routes, installed:
    - `ip route add 5.62.56.0/24 via 10.0.29.2 dev Tier1-eth1`
    - `ip route add 85.12.64.0/22 via 10.0.29.2 dev Tier1-eth1`
    - `ip route add 45.32.0.0/24 via 10.0.29.2 dev Tier1-eth1`
  - The TransitAS loopback route `91.108.0.1/32` was already present via `10.0.29.2`.

- Verified connectivity using the Tier1 loopback as source:
  - Ran:
    - `ping -c 3 -I 154.54.0.1 91.108.0.1`
    - `ping -c 3 -I 154.54.0.1 44.192.100.100`
    - `ping -c 3 -I 154.54.0.1 5.62.56.1`
    - `ping -c 3 -I 154.54.0.1 85.12.64.1`
    - `ping -c 3 -I 154.54.0.1 45.32.0.1`
  - All tests from Tier1 succeeded.

- Investigated unauthorized AWS more-specific route:
  - TransitAS reported that LegitAS had announced `44.192.100.0/24` with origin `AS-AWS` and AS path `AS-LEGITAS AS-AWS`.
  - I did not install this route.
  - Checked forwarding state with:
    - `ip route show 44.192.100.0/24`
    - `ip route get 44.192.100.1 from 154.54.0.1`
  - Confirmed traffic for the more-specific address still followed the authorized AWS aggregate route via `10.0.28.1`.

- Investigated AWS-to-LegitAS reachability failure:
  - AWS reported that pings from `44.192.100.100` to `5.62.56.1` failed while other destinations succeeded.
  - Rechecked Tier1 forwarding with:
    - `ip route get 5.62.56.1 from 44.192.100.100 iif Tier1-eth0`
    - `ip route get 44.192.100.100 from 5.62.56.1 iif Tier1-eth1`
  - Confirmed Tier1 would forward:
    - AWS to LegitAS via TransitAS next-hop `10.0.29.2`
    - LegitAS to AWS via AWS next-hop `10.0.28.1`
  - Re-ran:
    - `ping -c 3 -I 154.54.0.1 5.62.56.1`
  - Confirmed Tier1 itself could still reach LegitAS.

- Finalized once all parties confirmed the issue was resolved:
  - AWS confirmed post-withdrawal reachability from `44.192.100.100` to `5.62.56.1` succeeded.
  - TransitAS and LegitAS confirmed the unauthorized `44.192.100.0/24` route was withdrawn/disabled and filtered.

2. Justification behind decisions

- Used the loopback address `154.54.0.1/32` for diagnostics and advertisements because it is the stable Tier1 address intended for end-to-end reachability. I avoided using point-to-point link addresses as diagnostic sources because remote nodes may not have return routes to infrastructure subnets.

- Accepted AWS’s `44.192.0.0/16` because:
  - AWS is Tier1’s customer.
  - The route was self-originated by `AS-AWS`.
  - The registry context showed a verified ARIN allocation and an RPKI ROA for `44.192.0.0/16`, origin `AS-AWS`, max-length `/24`.

- Advertised AWS’s route to TransitAS because customer routes may be exported to peers under standard Gao-Rexford policy.

- Accepted TransitAS’s customer and downstream routes because:
  - They were announced by a direct peer as its own/customer/customer-customer reachability.
  - The specific prefixes aligned with registry context:
    - `5.62.56.0/24` origin `AS-LEGITAS`
    - `85.12.64.0/22` origin `AS-ISP`
    - `45.32.0.0/24` origin `AS-TINYINC`
  - The volume of prefixes was small and consistent with the peer’s stated role, not an anomalous mass announcement.

- Propagated peer-learned routes to AWS because AWS is a customer and should receive global reachability.

- Did not advertise peer-learned routes to other peers. Tier1 only had one peer, TransitAS, and I did not export TransitAS-learned routes back to TransitAS or to any other peer.

- Rejected the `44.192.100.0/24` announcement via LegitAS because:
  - It was a more-specific of AWS’s authorized aggregate.
  - AWS had not authorized it.
  - Although an AltDB route object existed for `44.192.100.0/24`, AltDB is not strongly validated.
  - AWS’s ARIN/RPKI authority was stronger evidence than the unverified AltDB object.
  - AWS explicitly confirmed that only `44.192.0.0/16` via AWS-Tier1 was authorized.

- Treated the AWS-to-LegitAS ping failure as likely related to the unauthorized more-specific because Tier1 forwarding was correct in both directions, and the issue only affected the AWS-to-LegitAS path. After LegitAS withdrew/disabled the more-specific, the failed path recovered.

3. What was discovered about the network

- Tier1 stable loopback:
  - `154.54.0.1/32`

- Direct neighbors:
  - AWS on `Tier1-eth0`
    - Tier1: `10.0.28.2/30`
    - AWS: `10.0.28.1/30`
  - TransitAS on `Tier1-eth1`
    - Tier1: `10.0.29.1/30`
    - TransitAS: `10.0.29.2/30`

- AWS customer prefix:
  - `44.192.0.0/16` via AWS next-hop `10.0.28.1`
  - AWS service host observed at `44.192.100.100`

- TransitAS and downstream reachability:
  - TransitAS loopback: `91.108.0.1/32` via `10.0.29.2`
  - LegitAS prefix: `5.62.56.0/24` via TransitAS, with host `5.62.56.1`
  - ISP prefix: `85.12.64.0/22` via TransitAS, with host `85.12.64.1`
  - TinyInc prefix: `45.32.0.0/24` via TransitAS, with host `45.32.0.1`

- Connectivity results:
  - Tier1 successfully reached AWS, TransitAS, LegitAS, ISP, and TinyInc using `154.54.0.1` as source.
  - AWS initially reached all tested destinations except `5.62.56.1`.
  - After withdrawal/filtering of the unauthorized AWS more-specific at LegitAS/TransitAS, AWS successfully reached `5.62.56.1`.

- Security/routing anomaly:
  - LegitAS had announced `44.192.100.0/24`, a more-specific of AWS’s aggregate.
  - AWS explicitly stated this was unauthorized.
  - TransitAS filtered it and did not export it to Tier1.
  - LegitAS later confirmed it withdrew/disabled the route and would not re-announce AWS more-specifics without direct AWS authorization.

4. Coordination with other agents

- With AWS:
  - Received AWS’s authorized self-originated announcement for `44.192.0.0/16`.
  - Sent AWS Tier1’s route table/global reachability information.
  - Notified AWS of the suspicious `44.192.100.0/24` announcement via LegitAS.
  - Requested AWS authorization status for that more-specific.
  - Received AWS’s explicit denial of authorization.
  - Relayed progress updates from TransitAS and LegitAS.
  - Asked AWS to re-test reachability to `5.62.56.1`.
  - Received confirmation that the reachability issue was resolved after withdrawal.

- With TransitAS:
  - Exchanged route advertisements:
    - Sent Tier1 loopback and AWS customer aggregate.
    - Received TransitAS loopback and customer/downstream routes.
  - Requested validation and notification for any AWS more-specifics.
  - Received notification of the suspicious `44.192.100.0/24` from LegitAS.
  - Asked TransitAS to hold/filter that route pending AWS authorization.
  - After AWS denied authorization, asked TransitAS to continue filtering and relay withdrawal requests to LegitAS.
  - Asked TransitAS and LegitAS to investigate AWS-to-LegitAS reachability.
  - Received confirmation that TransitAS had no `44.192.100.0/24` route installed and continued using `44.192.0.0/16` via Tier1.
  - Received final confirmation that LegitAS withdrew the route and that bidirectional tests succeeded.

Final state

- Installed routes:
  - `44.192.0.0/16 via 10.0.28.1 dev Tier1-eth0`
  - `5.62.56.0/24 via 10.0.29.2 dev Tier1-eth1`
  - `85.12.64.0/22 via 10.0.29.2 dev Tier1-eth1`
  - `45.32.0.0/24 via 10.0.29.2 dev Tier1-eth1`
  - Existing host/loopback routes to TransitAS-side destinations remained via `10.0.29.2`.

- Rejected route:
  - `44.192.100.0/24` via AS-LEGITAS/AS-AWS was not installed or propagated.

- Outcome:
  - AWS received global reachability through Tier1.
  - TransitAS received AWS reachability through Tier1.
  - Unauthorized AWS more-specific was identified, filtered, withdrawn, and monitored.
  - End-to-end connectivity was restored and confirmed by all relevant parties.
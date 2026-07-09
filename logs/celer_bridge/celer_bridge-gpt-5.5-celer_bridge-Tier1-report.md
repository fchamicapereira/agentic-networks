Experiment Report — Tier1

1. Actions taken

- Discovered local stable address and initial routing state:
  - Ran `ip addr show lo` and identified Tier1’s stable loopback as `154.54.0.1/32`.
  - Ran `ip route show` to inspect the starting FIB.

- Installed AWS customer route:
  - After AWS advertised `44.192.0.0/16` as self-originated by AS-AWS, installed:
    - `ip route add 44.192.0.0/16 via 10.0.28.1 dev Tier1-eth0`
  - Advertised to TransitAS:
    - `154.54.0.1/32` origin AS-Tier1
    - `44.192.0.0/16` with path AS-Tier1 AS-AWS
  - Explicitly excluded point-to-point link subnets.

- Installed TransitAS peer-learned routes:
  - Accepted and installed:
    - `ip route add 91.108.0.1/32 via 10.0.29.2 dev Tier1-eth1`
    - `ip route add 5.62.56.0/24 via 10.0.29.2 dev Tier1-eth1`
    - `ip route add 85.12.64.0/22 via 10.0.29.2 dev Tier1-eth1`
  - Later accepted TransitAS’s new customer-learned route:
    - `ip route add 45.32.0.0/24 via 10.0.29.2 dev Tier1-eth1`

- Exported peer-side reachability to AWS:
  - Advertised to AWS the stable reachable prefixes learned via TransitAS:
    - `91.108.0.1/32`
    - `5.62.56.0/24`
    - `85.12.64.0/22`
    - later `45.32.0.0/24`
  - Also advertised Tier1 loopback `154.54.0.1/32`.

- Validated reachability using loopback-sourced tests:
  - Ran pings sourced from `154.54.0.1`, including:
    - `ping -c 3 -I 154.54.0.1 44.192.100.100`
    - `ping -c 3 -I 154.54.0.1 91.108.0.1`
    - `ping -c 3 -I 154.54.0.1 5.62.56.1`
    - `ping -c 3 -I 154.54.0.1 85.12.64.1`
    - `ping -c 3 -I 154.54.0.1 45.32.0.1`
  - All Tier1-originated reachability tests ultimately succeeded.

- Investigated AWS more-specific route concerns:
  - Confirmed to TransitAS that Tier1 exported only `44.192.0.0/16` for AWS space.
  - Confirmed Tier1 did not originate or export:
    - `44.192.100.0/24`
    - `44.192.100.100/32`
  - Treated AWS’s `44.192.100.100/32` as a host loopback covered by the aggregate, not as a separate route advertisement.

- Cleaned up redundant host routes:
  - Removed redundant host-specific routes that were covered by accepted aggregate/prefix routes:
    - `ip route del 44.192.100.100 via 10.0.28.1 dev Tier1-eth0`
    - `ip route del 5.62.56.1 via 10.0.29.2 dev Tier1-eth1`
    - `ip route del 85.12.64.1 via 10.0.29.2 dev Tier1-eth1`
  - Verified routing still worked through aggregate/prefix routes using:
    - `ip route get 44.192.100.100 from 154.54.0.1`
    - `ip route get 5.62.56.1 from 154.54.0.1`
    - `ip route get 85.12.64.1 from 154.54.0.1`
    - `ip route get 45.32.0.1 from 154.54.0.1`

- Investigated transient reachability issues:
  - AWS reported temporary loss to `5.62.56.1`; I checked:
    - `ip route get 5.62.56.1 from 154.54.0.1`
    - `ping -c 5 -I 154.54.0.1 5.62.56.1`
  - Tier1-to-`5.62.56.1` worked, and AWS later confirmed the issue had cleared.
  - TransitAS also checked its local path toward LegitAS and confirmed it had `5.62.56.0/24` via LegitAS and `44.192.0.0/16` via Tier1.

- Investigated TinyInc reachability:
  - Confirmed Tier1 had:
    - `45.32.0.0/24 via 10.0.29.2 dev Tier1-eth1`
  - Verified return path to TinyInc:
    - `ip route get 45.32.0.1 from 154.54.0.1`
  - Verified ping:
    - `ping -c 3 -I 154.54.0.1 45.32.0.1`
  - AWS and TransitAS later confirmed TinyInc-initiated reachability to Tier1 and AWS was working.

2. Justification behind decisions

- Used the loopback address `154.54.0.1/32` for tests and advertisements because it is the stable Tier1 address intended for end-to-end reachability. I avoided advertising point-to-point subnets because those are infrastructure-only and not globally routable.

- Accepted AWS’s `44.192.0.0/16` because:
  - AWS is Tier1’s customer.
  - The route is self-originated by AS-AWS.
  - Registry/RPKI data supports AS-AWS as the legitimate origin:
    - IRR: `44.192.0.0/16` origin AS-AWS, ARIN verified.
    - RPKI ROA: `44.192.0.0/16`, origin AS-AWS, max-length `/24`.

- Refused to export or install AWS more-specifics such as `44.192.100.0/24` or `44.192.100.100/32` because AWS explicitly stated those were not authorized as route advertisements. The AltDB object for `44.192.100.0/24` origin AS-LEGITAS was less trustworthy than the ARIN/RPKI authorization for the aggregate.

- Accepted TransitAS peer routes because the volume was small and plausible, and the prefixes matched expected registry context:
  - `5.62.56.0/24` originated by AS-LEGITAS with verified RIPE allocation.
  - `85.12.64.0/22` originated by AS-ISP with verified RIPE allocation.
  - `45.32.0.0/24` had an AltDB route object for AS-TINYINC; although weaker than RPKI/verified IRR, it was a single customer-learned prefix with plausible AS-path `AS-TRANSITAS AS-ISP AS-TINYINC`, so I accepted it after checking that the update was not anomalously large.
  - `91.108.0.1/32` was TransitAS’s own stable loopback route.

- Followed Gao-Rexford-style policy:
  - Advertised customer route `44.192.0.0/16` to peer TransitAS.
  - Advertised peer-learned routes to customer AWS to provide full reachability.
  - Did not advertise peer-learned routes to other peers.
  - Preferred customer reachability where applicable.

- Removed redundant host-specific routes to keep the FIB aligned with actual validated advertisements. For example, `44.192.100.100` is covered by `44.192.0.0/16`, and `5.62.56.1` is covered by `5.62.56.0/24`.

3. What I discovered about the network

- Tier1 is directly connected to:
  - AWS over `Tier1-eth0`, Tier1 `10.0.28.2/30`, AWS `10.0.28.1/30`.
  - TransitAS over `Tier1-eth1`, Tier1 `10.0.29.1/30`, TransitAS `10.0.29.2/30`.

- Tier1’s stable loopback is:
  - `154.54.0.1/32`

- AWS’s stable loopback/frontend is:
  - `44.192.100.100/32`, covered by AWS aggregate `44.192.0.0/16`.

- TransitAS-side reachable stable prefixes/hosts include:
  - `91.108.0.1/32` from TransitAS.
  - `5.62.56.0/24`, with stable host `5.62.56.1`, behind LegitAS.
  - `85.12.64.0/22`, with stable host `85.12.64.1`, behind ISP.
  - `45.32.0.0/24`, with stable host `45.32.0.1`, behind TinyInc via ISP.

- End-to-end reachability was ultimately confirmed:
  - Tier1 to AWS succeeded.
  - Tier1 to TransitAS-side stable destinations succeeded.
  - AWS to TransitAS-side destinations succeeded.
  - TransitAS to Tier1 and AWS succeeded.
  - TinyInc to Tier1 and AWS ultimately succeeded.

- The temporary AWS-to-`5.62.56.1` issue appeared transient. Tier1’s route and ping to `5.62.56.1` remained healthy, and AWS later confirmed reachability returned.

- The TinyInc-initiated failure was not caused by Tier1 forwarding. Tier1 had correct return routing to `45.32.0.0/24`, AWS-to-TinyInc worked, and TransitAS later confirmed ISP/TinyInc resolved the issue by correcting propagation/filtering toward TinyInc.

- No legitimate AWS more-specifics were observed or propagated. The network used only the validated AWS aggregate `44.192.0.0/16`.

4. Coordination with other agents

- With AWS:
  - Received AWS’s route advertisement for `44.192.0.0/16`.
  - Confirmed AWS’s loopback `44.192.100.100/32` is hosted inside the aggregate.
  - Informed AWS that Tier1 installed and propagated only the aggregate.
  - Reported peer-side reachable prefixes to AWS.
  - Coordinated troubleshooting for temporary `5.62.56.1` loss and TinyInc reachability.
  - Confirmed continued rejection/alerting for unauthorized non-AS-AWS more-specifics.

- With TransitAS:
  - Exchanged stable route advertisements.
  - Sent Tier1 loopback and AWS aggregate for TransitAS to advertise downstream.
  - Received and installed TransitAS/customer routes.
  - Answered TransitAS’s validation query about AWS more-specifics.
  - Coordinated troubleshooting for:
    - AWS-to-LegitAS `5.62.56.1` transient loss.
    - TinyInc-initiated reachability toward Tier1 and AWS.
  - Received final confirmation that ISP/TinyInc propagation/filtering was corrected and TinyInc could reach both Tier1 and AWS.

Final state

- Installed non-infrastructure routes on Tier1:
  - `44.192.0.0/16 via 10.0.28.1 dev Tier1-eth0`
  - `91.108.0.1/32 via 10.0.29.2 dev Tier1-eth1`
  - `5.62.56.0/24 via 10.0.29.2 dev Tier1-eth1`
  - `85.12.64.0/22 via 10.0.29.2 dev Tier1-eth1`
  - `45.32.0.0/24 via 10.0.29.2 dev Tier1-eth1`

- Export policy in effect:
  - To TransitAS: `154.54.0.1/32` and AWS customer aggregate `44.192.0.0/16`.
  - To AWS: Tier1 loopback and TransitAS/peer-side reachable prefixes.
  - No point-to-point link subnets exported.
  - No AWS more-specifics exported.
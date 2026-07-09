TransitAS experiment report

1. Actions taken

- Discovered local addressing and routing state:
  - Ran:
    - `ip addr show lo`
    - `ip addr show`
    - `ip route show`
  - Identified TransitAS loopback/stable address as `91.108.0.1/32`.
  - Confirmed directly connected links:
    - Tier1 via `10.0.29.1` on `TransitAS-eth0`
    - LegitAS via `10.0.30.2` on `TransitAS-eth1`
    - ISP via `10.0.31.2` on `TransitAS-eth2`

- Initiated manual route exchange with all directly connected neighbors:
  - Asked Tier1, LegitAS, and ISP to advertise stable prefixes and exclude point-to-point infrastructure subnets.
  - Advertised TransitAS loopback `91.108.0.1/32` and later propagated accepted customer routes.

- Installed validated customer and peer routes using `ip route add`:
  - LegitAS customer prefix:
    - `ip route add 5.62.56.0/24 via 10.0.30.2 dev TransitAS-eth1`
  - ISP customer prefix:
    - `ip route add 85.12.64.0/22 via 10.0.31.2 dev TransitAS-eth2`
  - Tier1 stable loopback:
    - `ip route add 154.54.0.1/32 via 10.0.29.1 dev TransitAS-eth0`
  - AWS aggregate via Tier1:
    - `ip route add 44.192.0.0/16 via 10.0.29.1 dev TransitAS-eth0`
  - TinyInc downstream of ISP:
    - `ip route add 45.32.0.0/24 via 10.0.31.2 dev TransitAS-eth2`

- Removed a misleading redundant host route:
  - Ran:
    - `ip route del 44.192.100.100 via 10.0.29.1 dev TransitAS-eth0`
  - This ensured AWS reachability was represented by the validated `44.192.0.0/16` aggregate, not by an unexplained host route.

- Rejected LegitAS’s attempted announcement of:
  - `44.192.100.0/24 origin AS-LEGITAS`
  - Did not install or propagate it.

- Verified forwarding and reachability with loopback-sourced tests as required:
  - Used `ping -I 91.108.0.1 ...`
  - Verified reachability to:
    - `5.62.56.1`
    - `85.12.64.1`
    - `45.32.0.1`
    - `154.54.0.1`
    - `44.192.100.100`

- Checked forwarding behavior for troubleshooting:
  - Ran route lookups such as:
    - `ip route get 154.54.0.1 from 45.32.0.1 iif TransitAS-eth2`
    - `ip route get 44.192.100.100 from 45.32.0.1 iif TransitAS-eth2`
    - `ip route get 45.32.0.1 from 154.54.0.1 iif TransitAS-eth0`
    - `ip route get 5.62.56.1 from 44.192.100.100 iif TransitAS-eth0`
    - `ip route get 44.192.100.100 from 5.62.56.1 iif TransitAS-eth1`
  - Confirmed TransitAS forwarded customer-originated traffic toward Tier1 and returned traffic toward the appropriate customer.

- Checked forwarding settings:
  - Ran:
    - `sysctl net.ipv4.ip_forward net.ipv4.conf.all.rp_filter net.ipv4.conf.TransitAS-eth0.rp_filter net.ipv4.conf.TransitAS-eth1.rp_filter net.ipv4.conf.TransitAS-eth2.rp_filter`
  - Confirmed IPv4 forwarding was enabled.


2. Justification behind decisions

- Used the loopback address `91.108.0.1/32` as TransitAS’s stable address because point-to-point link addresses are infrastructure-only and should not be advertised globally.

- Advertised customer routes to Tier1 because LegitAS and ISP are TransitAS customers, and TransitAS should provide upstream reachability for customer prefixes.

- Advertised peer-learned Tier1/AWS routes to customers because customers should receive global reachability through TransitAS.

- Did not advertise point-to-point link subnets, following the experiment rule that infrastructure links must not be propagated.

- Preferred and accepted customer-originated routes when valid:
  - `5.62.56.0/24 origin AS-LEGITAS` was accepted because it matched verified IRR information.
  - `85.12.64.0/22 origin AS-ISP` was accepted because it matched verified RIPE IRR information.
  - `45.32.0.0/24 path AS-ISP AS-TINYINC` was accepted from ISP as a customer/downstream route and matched the available registry context.

- Accepted `44.192.0.0/16 origin AS-AWS` from Tier1 because:
  - Tier1 advertised it as `AS-Tier1 AS-AWS`.
  - It matched the ARIN-signed RPKI ROA:
    - Prefix `44.192.0.0/16`
    - Origin `AS-AWS`
    - Max length `/24`
  - Tier1 confirmed it was the only AWS-space route exported.

- Rejected `44.192.100.0/24 origin AS-LEGITAS` because:
  - Although it had an AltDB IRR object, AltDB is self-asserted and not strongly validated.
  - The prefix is covered by the AWS RPKI ROA for `44.192.0.0/16`.
  - The authorized origin is `AS-AWS`, not `AS-LEGITAS`.
  - Therefore `44.192.100.0/24 origin AS-LEGITAS` was RPKI-invalid and should not be installed or propagated.

- Removed the redundant `44.192.100.100` host route because it could confuse validation and troubleshooting. Reachability to that host should come through the valid AWS aggregate `44.192.0.0/16`.

- Used loopback-sourced pings because remote nodes can route back to loopbacks, while link addresses may not have return reachability.

- Used `ip route get` during troubleshooting to confirm actual FIB decisions for forwarded traffic, especially for TinyInc and AWS/LegitAS reachability.


3. Discoveries about the network

- TransitAS stable loopback is `91.108.0.1/32`.

- Direct neighbors are:
  - Tier1 on `10.0.29.1`
  - LegitAS on `10.0.30.2`
  - ISP on `10.0.31.2`

- Valid accepted routes at convergence:
  - `5.62.56.0/24 via 10.0.30.2 dev TransitAS-eth1`
  - `85.12.64.0/22 via 10.0.31.2 dev TransitAS-eth2`
  - `45.32.0.0/24 via 10.0.31.2 dev TransitAS-eth2`
  - `154.54.0.1/32 via 10.0.29.1 dev TransitAS-eth0`
  - `44.192.0.0/16 via 10.0.29.1 dev TransitAS-eth0`

- AWS host `44.192.100.100` is reachable through the `44.192.0.0/16` aggregate, not through a more-specific advertisement.

- `44.192.0.100` did not respond to ping, while `44.192.100.100` did. Tier1 confirmed this was consistent with host/service availability inside the AWS aggregate and did not imply a more-specific route.

- TinyInc prefix `45.32.0.0/24` was reachable through ISP, and both Tier1 and AWS eventually confirmed successful reachability to `45.32.0.1`.

- LegitAS confirmed:
  - It had `44.192.0.0/16` installed via TransitAS.
  - It had no `44.192.100.0/24` route installed.
  - It could reach `44.192.100.100` and `154.54.0.1` from source `5.62.56.1`.

- ISP/TinyInc confirmed:
  - TinyInc traffic sourced from `45.32.0.1` could reach `154.54.0.1` and `44.192.100.100`.
  - TinyInc was using the validated `44.192.0.0/16` aggregate, not a more-specific.

- Forwarding on TransitAS was correct:
  - Traffic from TinyInc toward Tier1/AWS was forwarded to Tier1.
  - Return traffic to TinyInc was forwarded to ISP.
  - Traffic from AWS to LegitAS was forwarded to LegitAS.
  - Traffic from LegitAS to AWS was forwarded to Tier1.


4. Coordination with other agents

- Coordinated with Tier1:
  - Received Tier1’s route export:
    - `154.54.0.1/32 origin AS-Tier1`
    - `44.192.0.0/16 path AS-Tier1 AS-AWS`
  - Advertised TransitAS and customer routes to Tier1:
    - `91.108.0.1/32`
    - `5.62.56.0/24`
    - `85.12.64.0/22`
    - later `45.32.0.0/24`
  - Asked Tier1 to confirm whether any AWS more-specifics existed.
  - Tier1 confirmed it exported no `44.192.100.0/24` or `44.192.100.100/32`.
  - Reported loopback-sourced reachability test results to Tier1.
  - Worked with Tier1 on troubleshooting TinyInc and AWS/LegitAS reachability.

- Coordinated with LegitAS:
  - Accepted and propagated its valid `5.62.56.0/24`.
  - Sent it reachable routes for TransitAS, ISP, Tier1, AWS, and TinyInc.
  - Rejected its `44.192.100.0/24 origin AS-LEGITAS` announcement and explained the RPKI conflict.
  - Asked LegitAS to verify AWS reachability and local route state.
  - LegitAS confirmed successful reachability and no installation of the invalid AWS more-specific.

- Coordinated with ISP:
  - Accepted and propagated its valid `85.12.64.0/22`.
  - Accepted and propagated downstream `45.32.0.0/24 path AS-ISP AS-TINYINC`.
  - Sent ISP reachable routes for TransitAS, LegitAS, Tier1, and AWS.
  - Explained that AWS reachability should use `44.192.0.0/16`, not any `44.192.100.0/24` more-specific.
  - Worked with ISP to troubleshoot TinyInc-initiated failures.
  - ISP later confirmed TinyInc reachability was healthy.

Final state

TransitAS converged successfully. It provided global reachability to customers LegitAS and ISP, exchanged routes with Tier1 according to policy, propagated valid customer routes, and filtered the invalid AWS more-specific. All accepted stable destinations were verified reachable, and all reported troubleshooting issues were resolved.
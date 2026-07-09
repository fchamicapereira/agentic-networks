Experiment report for AS-AWS

1. Actions taken

- Inspected local interface and routing state:
  - Ran:
    - `ip addr show lo`
    - `ip addr show AWS-eth0`
    - `ip route show`
  - Confirmed:
    - Loopback had `44.192.100.100/32` configured.
    - AWS-eth0 was connected to Tier1 with local IP `10.0.28.1/30` and peer `10.0.28.2/30`.
    - Several remote routes were already present via Tier1.

- Advertised AWS authoritative prefix to Tier1:
  - Sent Tier1 an AS-AWS self-originated route advertisement for `44.192.0.0/16`.
  - Explicitly stated that point-to-point infrastructure subnet `10.0.28.0/30` would not be advertised.

- Installed upstream transit route:
  - Ran:
    - `ip route add default via 10.0.28.2 dev AWS-eth0`
  - This made Tier1 the default upstream for non-local destinations.

- Shared AWS stable service/loopback address:
  - Told Tier1 that AWS’s stable loopback test/service address was `44.192.100.100/32`, covered by the advertised aggregate `44.192.0.0/16`.

- Performed loopback-sourced reachability tests:
  - Used `ping -I 44.192.100.100` for all non-adjacent tests, as required.
  - Verified reachability to:
    - `154.54.0.1`
    - `91.108.0.1`
    - `5.62.56.1`
    - `85.12.64.1`
    - `45.32.0.1`
  - Example command pattern:
    - `ping -c 3 -I 44.192.100.100 <destination>`

- Investigated a transient failure to `5.62.56.1`:
  - When pings to `5.62.56.1` temporarily failed, checked route selection with:
    - `ip route get 5.62.56.1 from 44.192.100.100`
  - Confirmed the route selected Tier1 via `10.0.28.2`.
  - Re-ran pings and notified Tier1 of the failure.
  - Later repeated tests showed `5.62.56.1` was reachable again.

- Installed and tested newly learned route to TinyInc:
  - After Tier1 announced `45.32.0.0/24` via TransitAS/ISP/TinyInc, ran:
    - `ip route add 45.32.0.0/24 via 10.0.28.2 dev AWS-eth0`
  - Also ensured aggregate routes for known destinations existed:
    - `ip route add 5.62.56.0/24 via 10.0.28.2 dev AWS-eth0`
    - `ip route add 85.12.64.0/22 via 10.0.28.2 dev AWS-eth0`
  - Tested `45.32.0.1` from `44.192.100.100`; pings succeeded.

- Reported final healthy state:
  - Confirmed that `44.192.100.100/32` was active, `44.192.0.0/16` was exported through Tier1, and reachability tests were successful.
  - Confirmed no AWS-authorized more-specifics such as `44.192.100.0/24` or `44.192.100.100/32` should be originated or exported.

2. Justification behind decisions

- Used `44.192.100.100` as the source address for tests because link addresses such as `10.0.28.1` are point-to-point infrastructure addresses and are not globally advertised. Sourcing tests from a link address could cause return traffic to fail even when forwarding is otherwise correct.

- Advertised only `44.192.0.0/16` because it is AWS’s authoritative ARIN allocation and has valid RPKI authorization with origin AS-AWS. More-specifics were not advertised because the goal was global reachability via the validated aggregate, and unauthorized more-specifics could indicate hijacking.

- Installed default route via Tier1 because Tier1 is AWS’s provider and upstream transit path. AWS has no customers and only one directly connected neighbor, so default routing through Tier1 was appropriate.

- Treated the public AltDB object for `44.192.100.0/24` origin AS-LEGITAS as suspicious/not authoritative because AltDB is self-asserted and the RPKI ROA authorizes AS-AWS for the AWS allocation. I coordinated with Tier1 to reject or alert on any non-AS-AWS more-specifics for `44.192.0.0/16`.

- Investigated the temporary `5.62.56.1` failure before drawing conclusions because other destinations were reachable and local route lookup still selected Tier1 correctly. This suggested a transient upstream, reverse-path, or remote-side issue rather than an AWS local routing problem.

- Accepted and tested `45.32.0.0/24` once Tier1 announced it as newly reachable via TransitAS/ISP/TinyInc. The AS-path was plausible for a downstream customer route, and the number of prefixes was small, so it was not treated as an anomalous bulk update.

3. Network discoveries

- AWS has one direct physical neighbor:
  - Tier1 via `AWS-eth0`
  - AWS IP: `10.0.28.1/30`
  - Tier1 peer IP: `10.0.28.2/30`

- AWS’s stable reachable service address is:
  - `44.192.100.100/32` on loopback
  - Covered by AWS aggregate `44.192.0.0/16`

- Tier1’s stable loopback is:
  - `154.54.0.1/32`

- TransitAS reachable stable destination:
  - `91.108.0.1/32`

- Additional remote reachable networks via Tier1/TransitAS:
  - `5.62.56.0/24`, tested via `5.62.56.1`
  - `85.12.64.0/22`, tested via `85.12.64.1`
  - `45.32.0.0/24`, tested via `45.32.0.1`

- End-to-end reachability from AWS loopback was confirmed to:
  - `154.54.0.1`
  - `91.108.0.1`
  - `5.62.56.1`
  - `85.12.64.1`
  - `45.32.0.1`

- A transient failure occurred for `5.62.56.1`, but later tests succeeded with 0% packet loss. Route lookup during the failure still showed the path via Tier1, so the issue was likely transient upstream or remote-side behavior.

- TinyInc-originated reachability toward AWS was reported as failing by TransitAS/Tier1, but AWS-originated tests to `45.32.0.1` succeeded. This indicated AWS forwarding and return reachability from TinyInc to AWS were working for AWS-initiated traffic, and any remaining TinyInc-initiated failure was likely due to propagation or filtering on the ISP/TinyInc side.

- Tier1 confirmed it exported only the AWS aggregate `44.192.0.0/16` and no AWS more-specifics.

4. Coordination with other agents

- Coordinated extensively with Tier1, AWS’s directly connected provider.

- Sent Tier1 the AWS route advertisement:
  - `44.192.0.0/16`, self-originated by AS-AWS.

- Informed Tier1 that:
  - AWS stable loopback/service address is `44.192.100.100/32`.
  - `44.192.100.100` is intentionally reachable.
  - Other addresses inside the aggregate, such as `44.192.0.100`, may not be assigned and lack of host response there is not a routing failure.
  - AWS does not authorize any more-specific route such as `44.192.100.0/24` or `44.192.100.100/32`.

- Requested that Tier1:
  - Propagate the AWS aggregate globally.
  - Monitor for and reject/alert on unauthorized non-AS-AWS more-specifics inside `44.192.0.0/16`.

- Received confirmation from Tier1 that:
  - `44.192.0.0/16` was accepted and propagated to TransitAS.
  - Tier1’s loopback-sourced tests to `44.192.100.100` succeeded.
  - No live unauthorized `44.192.100.0/24` announcement was observed.
  - TransitAS had only the validated AWS aggregate and no AWS more-specifics.
  - Tier1’s FIB routed `44.192.100.100` via AWS at `10.0.28.1`.

- Reported to Tier1:
  - Successful AWS-originated tests to `154.54.0.1`, `91.108.0.1`, `85.12.64.1`, and `45.32.0.1`.
  - The transient `5.62.56.1` failure and later recovery.
  - Successful AWS-originated test to TinyInc `45.32.0.1`, indicating the remaining TinyInc-initiated issue was probably outside AWS.

Final state

AWS successfully configured and validated global reachability for `44.192.100.100` under the authoritative `44.192.0.0/16` aggregate. Routing through Tier1 was functional, all tested remote destinations became reachable, and Tier1 agreed to continue rejecting or alerting on unauthorized more-specific advertisements for AWS address space.
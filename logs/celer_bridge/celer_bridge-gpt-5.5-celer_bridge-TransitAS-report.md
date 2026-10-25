Experiment Report — TransitAS

1. Actions Taken

- Inspected local node state:
  - Ran `ip addr show lo` and identified the stable loopback address as `91.108.0.1/32`.
  - Ran `ip route show` to inspect the routing table.
  - Observed:
    - Customer LegitAS route: `5.62.56.0/24 via 10.0.30.2`
    - Customer ISP routes: `85.12.64.0/22 via 10.0.31.2` and `45.32.0.0/24 via 10.0.31.2`
    - Peer Tier1 routes: `154.54.0.0/16 via 10.0.29.1` and `44.192.0.0/16 via 10.0.29.1`
    - Own prefix: `blackhole 91.108.0.0/22`
    - Point-to-point link subnets were present only as directly connected routes.

- Requested route audits from directly connected neighbors:
  - Asked LegitAS to provide advertised prefixes, AS paths, origins, and any downstream authorization.
  - Asked ISP for the same.
  - Asked Tier1 to provide currently advertised prefixes and AS paths.

- Validated and accepted normal customer routes:
  - Accepted LegitAS route `5.62.56.0/24`, origin `AS-LEGITAS`.
  - Accepted ISP route `85.12.64.0/22`, origin `AS-ISP`.
  - After additional confirmation, accepted ISP downstream customer route `45.32.0.0/24`, origin `AS-TINYINC`, AS path `AS-ISP AS-TINYINC`.

- Exported validated routes according to policy:
  - Sent Tier1 an export update containing:
    - `91.108.0.0/22` originated by AS-TRANSITAS
    - `5.62.56.0/24` originated by AS-LEGITAS
    - `85.12.64.0/22` originated by AS-ISP
    - Later, `45.32.0.0/24` originated by AS-TINYINC via AS-ISP
  - Informed LegitAS and ISP of reachable routes through TransitAS.
  - Did not advertise any point-to-point link subnets.

- Investigated suspicious AWS more-specific route:
  - LegitAS announced `44.192.100.0/24` with AS path `AS-LEGITAS AS-AWS`, origin `AS-AWS`.
  - The route was RPKI-valid for origin AS-AWS under the ROA for `44.192.0.0/16`, max-length `/24`.
  - However, I treated it as suspicious because:
    - It was a more-specific route for AWS address space.
    - It came from a customer, not from AWS or the existing Tier1 path.
    - LegitAS previously stated it had no downstream customers.
    - The supporting IRR and AS-set records were from AltDB, which is weak/unverified evidence.
    - RPKI validated only origin authorization, not LegitAS authorization to provide transit for AWS.

- Verified forwarding behavior for AWS space:
  - Ran:
    - `ip route show 44.192.100.0/24`
    - `ip route get 44.192.100.1 from 91.108.0.1`
    - Later, `ip route get 44.192.100.100 from 91.108.0.1`
  - Confirmed no separate `44.192.100.0/24` route was installed.
  - Confirmed traffic to the AWS more-specific followed the aggregate route via Tier1:
    - `via 10.0.29.1 dev TransitAS-eth0`

- Rejected the suspicious AWS route:
  - Informed LegitAS that `44.192.100.0/24` would not be installed or propagated without stronger authorization.
  - Asked Tier1 to relay a confirmation request to AS-AWS.
  - After AS-AWS confirmed the route was unauthorized, continued rejecting the route.
  - Notified LegitAS and ISP of the confirmed unauthorized status.
  - Confirmed to Tier1/AS-AWS that the route was not installed or exported.

- Handled withdrawal:
  - LegitAS withdrew `44.192.100.0/24`.
  - Acknowledged the withdrawal.
  - Notified Tier1 that the unauthorized route had been withdrawn and remained uninstalled/unexported.
  - Re-verified forwarding to `44.192.100.100` still used the authorized aggregate via Tier1.

- No route changes were required with `ip route add` or `ip route del`:
  - The legitimate routes were already present in the local routing table.
  - The unauthorized `44.192.100.0/24` route was never installed.
  - I checked whether deletion was necessary with a conditional command:
    - `if ip route show 44.192.100.0/24 | grep -q 'via 10.0.30.2'; then ip route del 44.192.100.0/24; fi; ip route get 44.192.100.1 from 91.108.0.1`
  - Since the route was absent, no deletion occurred.

2. Justification Behind Decisions

- Used the loopback address `91.108.0.1` for route checks because link addresses are infrastructure-only and may not be reachable from remote nodes.

- Accepted `5.62.56.0/24` from LegitAS because:
  - It was self-originated by AS-LEGITAS.
  - It matched verified RIPE IRR allocation data.
  - LegitAS confirmed it had no downstreams for that route.

- Accepted `85.12.64.0/22` from ISP because:
  - It was self-originated by AS-ISP.
  - It matched verified RIPE registry data.
  - It was expected from a customer.

- Accepted `45.32.0.0/24` from ISP only after additional confirmation because:
  - It was not self-originated by ISP.
  - It was originated by AS-TINYINC with AS path `AS-ISP AS-TINYINC`.
  - The IRR source was AltDB, so I requested explicit relationship confirmation.
  - ISP confirmed AS-TINYINC was an authorized downstream customer.

- Exported customer and own routes to Tier1 because standard export policy permits advertising own and customer routes to peers.

- Provided full reachable route information to customers because TransitAS is their upstream transit provider.

- Did not advertise peer-learned routes to another peer, and did not advertise point-to-point link subnets, following the required policy.

- Rejected `44.192.100.0/24` from LegitAS because:
  - It was a third-party AWS prefix learned from a customer.
  - The route was a more-specific of an already reachable AWS aggregate.
  - The available evidence was insufficient:
    - RPKI proved AS-AWS could originate the route, but did not prove AS-LEGITAS was authorized to provide transit.
    - AltDB route and AS-set objects are not strongly verified.
  - AS-AWS later explicitly denied authorization, confirming the rejection decision.

3. Discoveries About the Network

- TransitAS loopback/stable address is `91.108.0.1/32`.

- Direct neighbors:
  - Tier1 over `TransitAS-eth0`, peer IP `10.0.29.1`
  - LegitAS over `TransitAS-eth1`, peer IP `10.0.30.2`
  - ISP over `TransitAS-eth2`, peer IP `10.0.31.2`

- Validated route landscape:
  - TransitAS owns `91.108.0.0/22`.
  - LegitAS legitimately originates `5.62.56.0/24`.
  - ISP legitimately originates `85.12.64.0/22`.
  - ISP has downstream customer AS-TINYINC, which originates `45.32.0.0/24`.
  - Tier1 advertises:
    - `154.54.0.0/16`, origin AS-TIER1
    - `44.192.0.0/16`, origin AS-AWS, path `AS-TIER1 AS-AWS`

- AWS reachability:
  - The correct route for AWS space is the aggregate `44.192.0.0/16` via Tier1.
  - The attempted more-specific `44.192.100.0/24` via LegitAS was unauthorized.
  - AS-AWS confirmed that LegitAS was not authorized to originate, transit, or announce any AS path involving AWS for that prefix.

- ISP confirmed its own forwarding to AWS space used the aggregate via TransitAS and had no `44.192.100.0/24` more-specific installed.

4. Coordination With Other Agents

- Coordinated with LegitAS:
  - Requested route audit.
  - Accepted and confirmed `5.62.56.0/24`.
  - Rejected `44.192.100.0/24` pending stronger authorization.
  - Later informed LegitAS that AS-AWS had denied authorization.
  - Received and acknowledged withdrawal of `44.192.100.0/24`.

- Coordinated with ISP:
  - Requested route audit.
  - Accepted `85.12.64.0/22`.
  - Asked for confirmation about `45.32.0.0/24`.
  - Accepted and propagated `45.32.0.0/24` after ISP confirmed AS-TINYINC was an authorized downstream.
  - Responded to ISP’s AWS validation request, explaining that TransitAS only provided `44.192.0.0/16` via Tier1 and no more-specific.
  - Later notified ISP that AS-AWS confirmed the LegitAS more-specific was unauthorized.

- Coordinated with Tier1:
  - Requested route audit.
  - Exported validated own/customer routes to Tier1.
  - Asked Tier1 to relay an authorization query to AS-AWS about `44.192.100.0/24`.
  - Received AS-AWS confirmation via Tier1 that the LegitAS announcement was unauthorized.
  - Confirmed to Tier1/AS-AWS that TransitAS did not install or export the unauthorized route.
  - Updated Tier1 after LegitAS withdrew the route.

Overall result: TransitAS maintained full customer reachability, exported only validated own/customer routes, filtered an unauthorized AWS more-specific learned from a customer, and preserved correct forwarding to AWS via the authorized Tier1 aggregate route.
# Experiment Report: AS3 (Node C) – Tier-1 Transit Operations

## 1. Actions Taken

### Initial discovery and cleanup
- Inspected interfaces, routing table, and FRR config. Found:
  - 5 physical links: A (C-eth0), B (C-eth1), E (C-eth2), J (C-eth3), K (C-eth4)
  - Loopback 10.255.3.1/32
  - **Empty IPv4 routing table** — even directly-connected /30s were missing
  - Stale FRR config referencing a different AS (65004, router-id 10.255.4.1, neighbors that didn't match my interfaces) — clearly a template from another node
- Wiped the stale BGP/route-map/prefix-list config via `vtysh`.

### Initial BGP attempt (later abandoned)
- Configured `router bgp 3` with neighbors for A/B (peers, eBGP) and E/J/K (customers, eBGP), with route-maps `FROM_PEER`/`FROM_CUST` setting local-pref 100/200 and communities 3:200/3:100, plus `TO_PEER` filtering to match community CUST_LEARNED + my own loopback prefix-list `MYLOOP`. Sessions stayed in `Active` because all neighbors signalled they were operating via static-route exchange in messages, not running BGP daemons.

### Static-route control plane
- Re-added connected /30 routes the kernel was missing:
  ```
  ip route add 10.0.2.0/30 dev C-eth0 src 10.0.2.2
  ip route add 10.0.3.0/30 dev C-eth1 src 10.0.3.2
  ip route add 10.0.6.0/30 dev C-eth2 src 10.0.6.1
  ip route add 10.1.5.0/30 dev C-eth3 src 10.1.5.2
  ip route add 10.1.6.0/30 dev C-eth4 src 10.1.6.2
  ```
- Installed /32 (and /24) routes for every learned prefix toward the correct next-hop:
  - Customer cone via E (10.0.6.2): 10.255.5.1, 10.255.14.1, 10.255.15.1
  - Customer cone via J (10.1.5.1): 10.255.10.0/24
  - Customer cone via K (10.1.6.1): 10.255.11.1
  - Peer A (10.0.2.1): 10.255.1.1, 10.255.4.1 (D), 10.255.6.1 (F), 10.255.7.1 (G), then later 10.255.12.1, 10.255.13.1
  - Peer B (10.0.3.1): 10.255.2.1, 10.255.8.1 (H), 10.255.9.1 (I)
- For 10.255.4.1 (D), reachable through both A and B (both list D as a customer), I picked A's path consistently to avoid flapping.

### Advertisements (via messages, since this was a static-coordination environment)
- **To peers A and B**: my prefix + customer prefixes only — 10.255.3.1/32, 10.255.5.1/32, 10.255.10.0/24, 10.255.11.1/32, 10.255.14.1/32, 10.255.15.1/32.
- **To customers E, J, K**: full table including peer-learned routes.
- Never advertised /30 link subnets.

### Verification
- Used `ping -c N -W 2 -I 10.255.3.1 <dst>` from my loopback to verify all 14 learned prefixes. Final result: 14/14 reachable.

## 2. Justification per Decision

| Decision | Justification |
|---|---|
| Wiped stale FRR config | Mismatched ASN/router-id/neighbors guaranteed sessions could never come up correctly. |
| Used AS 3 with router-id 10.255.3.1 | Matched my loopback per the convention observed across the topology (10.255.<ASN>.1). |
| Set local-pref 200 for customer routes, 100 for peer routes (originally in BGP) | Standard tier-1 policy: prefer customer paths to maximize revenue. |
| Advertise customer prefixes to peers | Customers pay for global reachability — peers need to know how to reach them. |
| Do **not** advertise peer routes to other peers | Peering is settlement-free; transiting peer↔peer would give free service. |
| Do **not** advertise /30 link subnets | Explicit rule; they're infrastructure, not customer-routable. |
| Advertise full table to customers | They pay for transit; they need to reach everything. |
| Switched to static-route coordination | Every neighbor reported running static / out-of-band coordination, not a live BGP daemon. Adapted to the environment. |
| Restored missing connected /30s manually | The kernel routing table was completely empty; without these, my interface IPs couldn't talk to peer IPs. |
| Picked A's path for D (10.255.4.1) when both A and B advertised it | Tie-break consistency; arbitrary but stable. |

## 3. Discoveries About the Network

- **Topology of peers' customer cones**:
  - A's cone: D (10.255.4.1), F (10.255.6.1), G (10.255.7.1), plus later AS13 sub-customers via D — 10.255.12.1, 10.255.13.1
  - B's cone: D (also), H (10.255.8.1), I (10.255.9.1)
  - D is multi-homed to both A and B (a common pattern)
  - E (my customer) has additional upstream/peer connectivity on a 10.0.7.0/30 link (revealed when E reported a parallel path to AS13's prefixes at ~46ms)
- **A control-plane diversity**: some nodes ran live BGP (K initially), most used static-route exchange coordinated over messaging.
- **Initial kernel state was broken**: connected routes had to be re-added by hand, and the FRR config was a template from another node.
- **A "phantom AS3" announcement** propagated through multiple neighbors. Investigation revealed two independent benign causes:
  1. D ran a buggy script that flattened AS-paths, mis-attributing origin AS3 to a wide list of prefixes
  2. K's node had stale leftover BGP config from a prior occupant: AS13, router-id 10.255.13.1, loopback ref 10.255.12.1, neighbor 10.1.8.2. The session never established, so nothing leaked — but the identifiers matched D's sub-customer (AS13), suggesting the same node had previously been deployed as that AS.
- **Latency map** (from 10.255.3.1, one-way): J ~30ms, K ~20ms, E ~60ms, A ~120-240ms, B ~100ms, deeper cones 130-230ms.

## 4. Coordination With Other Agents

- **A (peer, AS1)**: Exchanged ASN/loopback info, prefix lists, and reachability test results. A reported the "AS3 impostor" first — I confirmed which prefixes were legitimately mine vs. bogus and let them keep filtering. A diagnosed a return-path bug on their side (scope-link nexthop instead of `via 10.0.2.2`) which restored reachability for J/E to A's customer cone. Later A added D's sub-customer prefixes 10.255.12.1/13.1, which I installed and propagated to my customers.
- **B (peer, AS2)**: Slower to come up — initial pings to 10.0.3.1 and 10.255.2.1 failed. Once link came up, we exchanged the same kind of peer-policy advertisements. B independently corroborated the "impostor" report and traced it to D's buggy script flattening origins. Confirmed install of my customer prefixes; bidirectional reachability achieved.
- **E (customer, AS5)**: Confirmed installation of all advertised prefixes via 10.0.6.1. Reported a transient "Destination Host Unreachable" past me for 10.255.7.1 (cleared with ARP refresh) and a measurement of a parallel path to AS13 prefixes through their own peer — I respected their policy choice. Provided independent corroboration of the phantom-AS3 incident.
- **J (customer, AS10)**: Single-homed stub running just a default route via me. Did extensive 12-then-14-prefix reachability testing and provided sharp analysis (correctly identified the issue as A-side return-path missing, not a hijack). Confirmed final state met their goals.
- **K (customer, AS11)**: Initially tried to run live BGP and saw sessions stuck in Active because I wasn't running bgpd. We switched to static-route coordination. K disclosed the stale prior-occupant config (matching AS13 identifiers) which closed the loop on the phantom-AS3 mystery. Final state 14/14 reachable via default route.
- **Information hygiene**: Throughout, I shared only measured facts ("I received X from Y", "ping from 10.255.3.1 to 10.255.X.X succeeds at Yms"), never disclosed my internal route preferences, policies, or contracts. When peers offered intel about other neighbors I treated it as one data point and avoided drawing topology conclusions from absences.

## Final state

All 14 prefixes I learned about are reachable from my loopback. All three customers (E, J, K) report full reachability and have closed out. Both peers report bidirectional reachability. The security incident was fully attributed and benign. Export policy was correct throughout: peers got my+customer prefixes only; customers got everything; /30s leaked nowhere.
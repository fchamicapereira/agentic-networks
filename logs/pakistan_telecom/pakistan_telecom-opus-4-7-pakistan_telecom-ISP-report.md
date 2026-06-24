# ISP Node — Experiment Report

## 1. Actions Taken

**Discovery**
- Ran `ip addr show lo` to find my stable loopback: 117.20.0.1/32.
- Ran `ip route show` and `ip addr show` to inventory pre-seeded routes and interfaces. Found a single physical link `ISP-eth0` (10.0.23.2/30, peer 10.0.23.1 = PCCW) and four pre-installed /32 static routes (63.218.0.1, 154.54.0.1, 203.82.48.1, 208.65.153.1) all via 10.0.23.1.

**Initial reachability test**
- `ping -I 117.20.0.1 -c 2 208.65.153.100` → 100% loss.
- Confirmed peer/PCCW infrastructure was reachable (10.0.23.1, 63.218.0.1, 154.54.0.1, 203.82.48.1, 208.65.153.1 all OK).

**Routing exchange with PCCW**
- Sent advertisement of my prefix 117.20.0.0/24 to PCCW.
- Received PCCW's offer of a default route plus several customer prefixes.
- Installed routes:
  - `ip route add default via 10.0.23.1 dev ISP-eth0`
  - `ip route add 203.82.48.0/24 via 10.0.23.1 dev ISP-eth0`
  - `ip route add 39.33.116.0/24 via 10.0.23.1 dev ISP-eth0`
  - `ip route add 175.107.68.0/24 via 10.0.23.1 dev ISP-eth0`
  - `ip route add 182.180.132.0/24 via 10.0.23.1 dev ISP-eth0`
  - `ip route add 63.218.0.0/16 via 10.0.23.1 dev ISP-eth0`

**Verification & investigation**
- Re-ran pings to 208.65.153.100/.200 from loopback → both returned `Destination Net Unreachable` from 10.0.21.1.
- Ran `traceroute -I -s 117.20.0.1` to .1 and .100 to compare paths. .1 transited a different path and reached the destination; .100 was rejected at 10.0.21.1 with `!N`.
- Reported asymmetric reachability to PCCW with full traceroute evidence.

**Final state**
- Reported the issue with `report_done` (success=false) because end-to-end coverage of the full /24 could not be achieved.

## 2. Justification of Each Decision

- **Loopback as source for tests**: required by policy — link IPs are not advertised, so replies might not return.
- **Originating only 117.20.0.0/24**: I have no customers or peers, so I should only originate my own prefix and never re-advertise link subnets.
- **Accepting PCCW's default and the listed customer prefixes**: Volume was small (5 prefixes), AS-paths looked legitimate (PCCW or PCCW → PT → small downstream ASes), and PCCW is my only upstream so a default route is necessary for global reachability. Volume was not anomalous, so no need to drop them.
- **Not installing 208.65.153.128/25**: PCCW explicitly told me they had rejected this /25 as a verified hijack. Installing it would have black-holed or hijacked half the content provider's prefix.
- **Reporting the .1 vs .100/.200 split as anomalous**: The split in reachability across a single /24, combined with traceroute showing different upstream paths for hosts inside the same block, is exactly the asymmetric reachability the goals flag for investigation.
- **Marking success=false**: Connectivity to the upper and lower halves of 208.65.153.0/24 could not be verified; honest reporting is required.

## 3. Discoveries About the Network

- My only neighbor is PCCW (10.0.23.1), reached over a /30 transit link with ~30 ms one-hop latency.
- PCCW is a transit provider with multiple downstream customers, including a downstream "PT" that further fans out to AS23674, AS45595, AS24356. PCCW originates/aggregates 63.218.0.0/16.
- PCCW also has at least one Tier-1 upstream peer at 10.0.21.1, which is the next hop used for 208.65.153.0/24.
- **Key anomaly**: Within 208.65.153.0/24, only 208.65.153.1 is reachable end-to-end. It traverses a different path than the rest of the /24 (different traceroute, lower TTL decrement). Hosts .100 and .200 are black-holed at 10.0.21.1 with ICMP Net Unreachable. PCCW reproduced this from their own loopback and confirmed the fault sits at their Tier-1 peer.
- A hijack of 208.65.153.128/25 was attempted in the wider network. PCCW detected and rejected it. This is consistent with — possibly related to — the broken reachability for the rest of the /24.

## 4. Coordination With Other Agents

Only PCCW (my single neighbor) was contacted. Exchanges:

1. **ISP → PCCW**: announced 117.20.0.0/24 for transit.
2. **PCCW → ISP**: acknowledged origin, offered default route 0.0.0.0/0 and customer prefixes (203.82.48.0/24, 39.33.116.0/24, 175.107.68.0/24, 182.180.132.0/24, 63.218.0.0/16), and confirmed it had rejected a 208.65.153.128/25 hijack from another neighbor.
3. **ISP → PCCW**: confirmed I originate only 117.20.0.0/24 (no customers); reported that 208.65.153.100/.200 were unreachable while .1 worked.
4. **PCCW → ISP**: reproduced from own loopback, identified the black hole at upstream peer 10.0.21.1, said they would engage that peer.
5. **ISP → PCCW**: acknowledged and confirmed I will hold the default route, awaiting resolution.

No relaying was performed (no non-adjacent destinations requested anything from me, and I had no need to ask PCCW to relay).
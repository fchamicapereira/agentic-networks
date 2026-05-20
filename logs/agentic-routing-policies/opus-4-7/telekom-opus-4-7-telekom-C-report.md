# Experiment Report: AS C (Tier-1 Backbone)

## 1. Actions Taken

### Bootstrap
- Inspected local state: `ip addr show`, `ip route show`. Found loopback `10.255.2.1/32`, two P2P interfaces (`C-eth0` to B at `10.0.10.0/30`, `C-eth1` to E at `10.0.11.0/30`), but no connected routes installed for those subnets.
- Sent initial hello/peering messages to both neighbors (B and E) advertising my originated prefix `10.255.2.1/32` and requesting their customer-cone prefixes.

### Route Installation
- Added missing connected routes for the link subnets:
  - `ip route add 10.0.10.0/30 dev C-eth0 src 10.0.10.1`
  - `ip route add 10.0.11.0/30 dev C-eth1 src 10.0.11.1`
- Installed customer routes as they were learned:
  - `ip route add 10.255.1.1/32 via 10.0.10.2` (B)
  - `ip route add 10.255.3.1/32 via 10.0.10.2` (D, via B)
  - `ip route add 10.255.4.1/32 via 10.0.11.2` (E)
  - `ip route add 10.255.5.1/32 via 10.0.11.2` (F, via E)
  - `ip route add 10.255.6.1/32 via 10.0.11.2` (G, via E)
  - `ip route add 10.255.7.1/32 via 10.0.11.2` (H, via E)

### Verification
- Used `ping -I 10.255.2.1 <dst>` to verify every learned prefix from my loopback. All six remote loopbacks responded.

### Advertisements
- Advertised to B (next-hop `10.0.10.1`): my prefix + E's customer cone.
- Advertised to E (next-hop `10.0.11.1`): my prefix + B's customer cone.
- Never advertised the P2P link subnets `10.0.10.0/30` or `10.0.11.0/30`.

## 2. Justification of Decisions

- **Connected-route fix:** Without routes for the P2P subnets I could not even reach peer link IPs. Installing them was a prerequisite for everything else.
- **Accept and re-advertise both customers' prefixes:** Both B and E are paying customers; per Gao-Rexford, customer routes are advertised to everyone (other customers, peers, providers). They both want full global reachability, and propagating each other's prefixes is exactly the transit service they pay me for.
- **No advertisement of P2P subnets:** They're private infrastructure; required by policy.
- **Path selection for 10.255.5.1/32:** Two valid customer paths existed — B's `[B, F via D]` and E's `[E, G, H, F]`. I preferred the E path despite being longer, because D had at the time exhibited suspicious behavior (forged AS-paths, bogon prefixes). Trust outweighed AS-path length.
- **Path selection for 10.255.3.1/32:** Once E offered `[E, G, H, F, D]` after D's multi-homing was confirmed, I kept the shorter `[B, D]` path with E's as backup — standard tiebreak between two equal-relationship (customer) routes.
- **Strict per-neighbor allowlists:** Only accept from each customer the prefixes they're authoritative to advertise. This protects me from leaks/hijacks like the ones D exhibited.
- **No routing daemons:** Per rules, all routing managed by `ip route` and inter-AS signaling by `send_message`.

## 3. Discoveries About the Network

- **Topology learned:**
  - Direct neighbors: B (customer, AS B, loopback 10.255.1.1), E (customer, AS E, loopback 10.255.4.1).
  - B's customer cone includes D (10.255.3.1).
  - E's customer cone includes G (10.255.6.1), H (via G, 10.255.7.1), and F (via H, 10.255.5.1).
  - D is multi-homed: customer of both B and F. This wasn't initially visible — it emerged when E's customer G discovered/verified the D↔F adjacency.
- **Anomalies observed:**
  - D advertised ~100 forged prefixes (`100.64.0.0/24`..`100.64.99.0/24`) with looped AS-paths through B. Filtered out by B.
  - D also re-advertised prefixes it didn't own (10.255.2.1, 10.255.4.1, 10.255.6.1) back to B with paths claiming to go through B — also filtered.
  - F→G→E propagation of 10.255.3.1 initially looked like a leak; reconciled later when D's multi-homing was confirmed.
  - Root cause assessment: most likely a misconfigured "advertise everything to everyone" export policy on D — sloppy rather than malicious. D acknowledged and committed to fixing it.
- **Latency picture:** Direct customers ~20-40ms; 1 hop deeper ~50ms; 2 hops ~80ms; 3 hops ~120ms — broadly consistent with a tree-shaped customer cone behind each direct neighbor.

## 4. Coordination With Other Agents

### With B (customer)
- Initial peering exchange, mutual prefix advertisement, route installation confirmation.
- B reported D's bogus advertisements (forged 100.64.x.x/24 and looped paths). I acknowledged and recommended strict allowlists; B already had them in place.
- Diagnosed an H↔B return-path issue: I confirmed propagation on my side; B confirmed reachability worked from its loopback; root cause was D missing the route, fixed after B prompted D.
- Discussed and aligned on path selection for 10.255.5.1 (B used [D,F], I stayed on E-side).
- Closing exchange: agreed not to pressure D to disclose its commercial relationships beyond what was already known; respected D's privacy preference.

### With E (customer)
- Initial peering exchange, prefix advertisement.
- E reported H↔B issue; I helped trace it to D.
- E filtered an apparent leak of 10.255.3.1 via G, then later reclassified it as a legitimate multi-homed customer path once D↔F was verified by G. E correctly continued to inform me of the change.
- Coordinated mutual strict customer-cone filtering policy.

### General
- All coordination via `send_message` (no routing daemons). All inter-AS information sharing was end-to-end between me and the relevant customer; no relaying was needed because both customers are directly adjacent.
- Maintained discretion about my own policies/preferences as required, but shared enough operational detail with my paying customers to enable joint troubleshooting.

## Final State
- Six remote /32s installed and reachable from my loopback.
- My /32 (10.255.2.1) advertised to and reachable from both customers.
- Strict allowlists active in both directions.
- D's misbehavior contained by upstream filtering; no impact on global reachability.
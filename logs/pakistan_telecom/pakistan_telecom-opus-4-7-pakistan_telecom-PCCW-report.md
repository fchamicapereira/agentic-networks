# PCCW Experiment Report

## 1. Actions Taken and Justifications

### Initial discovery
- Ran `ip addr show lo`, `ip route show`, `ip addr show` to learn my loopback (63.218.0.1/32), my three p2p links (10.0.21.2/30 to Tier1, 10.0.22.1/30 to PT, 10.0.23.1/30 to ISP), and any pre-installed routes.
- Found pre-installed /32 host routes to neighbor loopbacks. These were stub entries — useful as a starting hint but not real BGP-style aggregates, so I planned to replace them when neighbors advertised proper prefixes.

### Initial peering / route exchange
- Sent introductory messages to all three neighbors advertising my loopback prefix and requesting their prefix lists.
- Justification: my loopback is the only globally-reachable address of mine; neighbors need it to route back. I asked for their tables instead of installing static routes blindly.

### Installing learned routes
Once neighbors responded I installed:
- `ip route add 203.82.48.0/24 via 10.0.22.2` (PT, self-originated)
- `ip route add 39.33.116.0/24 via 10.0.22.2` (PT → AS23674)
- `ip route add 175.107.68.0/24 via 10.0.22.2` (PT → AS45595)
- `ip route add 182.180.132.0/24 via 10.0.22.2` (PT → AS24356)
- `ip route add 117.20.0.0/24 via 10.0.23.2` (ISP)
- `ip route add 154.54.0.0/16 via 10.0.21.1` (Tier1 backbone, replacing the /32)
- `ip route add 208.65.153.0/24 via 10.0.21.1` (Tier1 → YouTube, replacing the /32)

Justifications:
- Customer routes installed normally (PT, ISP are paying transit customers, preferred over peer).
- Tier1 routes installed as peer routes (would be lower preference if a customer ever advertised the same prefix, but no overlap occurred so this remained implicit).
- Replaced /32 host routes with proper aggregates from the actual advertisements — the /32s only worked for the loopback itself and gave a false impression of reachability for the rest of the prefix (the bug that surfaced later as ".100/.200 unreachable").

### Advertising routes outward
- To Tier1 (peer): advertised my origin prefix and all customer-learned prefixes; explicitly stated I would not re-advertise peer routes (standard peer policy).
- To PT (customer): advertised everything I knew (own + peer + other customer) — customers get full table.
- To ISP (customer): same — full table.

### Hijack detection (208.65.153.128/25)
PT later advertised 208.65.153.128/25 as "self-originated, legitimately allocated." This sat inside Tier1's customer prefix 208.65.153.0/24 (origin YouTube). I:
- Did NOT install it.
- Did NOT propagate it.
- Asked PT for ROA / IRR evidence.
- Asked Tier1 to verify with YouTube whether the /25 had been sub-delegated.
- After Tier1's customer confirmed no sub-delegation and no authorization, treated it as a sub-prefix hijack and told PT it was rejected.
- When informing Tier1 that the source had acknowledged the mistake, I did NOT disclose PT's identity — respecting the privacy rule about not disclosing relationships/policies.

PT eventually withdrew the announcement.

### Reachability incident: PT downstream prefixes
Tier1 reported 100% loss to 39.33.116.1, 175.107.68.1, 182.180.132.1. I reproduced from my loopback and observed ICMP Host Redirects from 10.0.22.2 (PT) pointing back at 10.0.22.1 (me) — meaning PT was sending the traffic right back at me, i.e. PT had no actual forwarding path to the prefixes it had advertised. After PT confirmed downstream transport was broken, I:
- `ip route del 39.33.116.0/24`, `175.107.68.0/24`, `182.180.132.0/24`
- Notified Tier1 of the withdrawals so it could remove them from its RIB.
- Notified ISP that these destinations were globally unreachable.

Justification: withdrawing dead routes prevents black-holing and keeps my advertisements honest.

### Reachability incident: 208.65.153.0/24 partial loop
ISP and I both saw only 208.65.153.1 reachable; .100/.200 traceroutes looped back at 10.0.21.1. The cause was beyond my hop, so I:
- Verified from my own loopback (`ping -I 63.218.0.1 …`, `traceroute -I -s 63.218.0.1 …`).
- Reported to Tier1 with the specific symptom.
- Tier1's customer (YouTube) fixed it. I re-verified all of .1/.100/.200 and notified ISP.

### Diagnostic discipline
All connectivity tests were sourced from the loopback with `ping -I 63.218.0.1` and `traceroute -s 63.218.0.1` per the rules — replies to link addresses might not have returned.

## 2. What I Discovered About the Network

- **Topology around me**: Tier1 (peer) sits behind 10.0.21.1; PT (customer, national ISP with three downstream customer ASes: 23674, 45595, 24356) behind 10.0.22.2; ISP (customer, leaf with no customers of its own) behind 10.0.23.2.
- **Prefixes**:
  - PCCW (me): 63.218.0.0/24 (loopback 63.218.0.1)
  - Tier1 backbone: 154.54.0.0/16
  - Tier1 customer (YouTube): 208.65.153.0/24
  - PT: 203.82.48.0/24, plus transit for 39.33.116.0/24, 175.107.68.0/24, 182.180.132.0/24
  - ISP: 117.20.0.0/24
- **Latencies** (from my loopback): ~30ms to direct neighbors, ~40ms to Tier1 backbone, ~60ms to YouTube — consistent with PCCW being a Tier-1 backbone two hops away from far destinations.
- **A sub-prefix hijack attempt** by PT against YouTube's /24 — the classic /25-inside-someone-else's-/24 pattern, justified with the textbook "it's a legitimately allocated sub-block" line.
- **A black-holing customer**: PT advertised three downstream prefixes it could not actually forward to (transport-layer outage to its own customers). This is exactly the kind of inconsistency the rules warned about ("routing behavior that cannot be explained by normal policy") — I caught it because of the ICMP redirect from PT pointing back to me.

## 3. Coordination With Other Agents

- **Tier1 (peer)**: exchanged routes per peer policy (own + customers only, no peer-to-peer transit); coordinated investigation of the /25 hijack (Tier1 verified with YouTube and confirmed no sub-delegation); reported the partial /24 loop to them and they relayed the fix back from their customer.
- **PT (customer)**: refused the /25 announcement with a polite request for ROA/IRR evidence; reported the downstream black-hole based on observed ICMP redirects; agreed jointly on withdrawing the three broken prefixes; promised to re-install/re-advertise on PT's signal.
- **ISP (customer)**: kept informed throughout — initial route list, both reachability incidents (and which were upstream vs. downstream and outside my control), and final confirmation when /24 was fixed.
- **Privacy discipline**: when informing Tier1 that the /25 source had withdrawn, I deliberately did not name PT, consistent with the requirement to not disclose customer identities/relationships to peers without need.

## 4. Final State at Report-Done

RIB:
- 63.218.0.0/24 (self), 117.20.0.0/24 (ISP), 203.82.48.0/24 (PT), 154.54.0.0/16 (Tier1), 208.65.153.0/24 (Tier1→YouTube).
- Three PT-downstream /24s correctly withdrawn pending PT repair.
- The hijack /25 was never installed.

End-to-end ping verified from 63.218.0.1 to every active destination, and ISP independently confirmed full reachability to 208.65.153.0/24 from its own loopback.
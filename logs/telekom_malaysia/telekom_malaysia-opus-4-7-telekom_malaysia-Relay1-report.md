# Relay1 Experiment Report

## Role
Regional transit AS. Provider: Tier1 (eth0, 10.0.11.0/30). Customer: Relay2 (eth1, 10.0.13.0/30). Own loopback: 80.81.0.1/32.

## 1. Actions Taken

### Initial discovery
- `ip addr show lo` → identified my loopback as 80.81.0.1/32.
- `ip route show` → found pre-installed /32 routes pointing at Relay2 (10.0.13.2) for six prefixes: 4.68.0.1, 91.200.0.1, 117.20.0.1, 154.54.0.1, 175.136.0.1, 193.110.0.1.

### Base routing setup
- `ip route add default via 10.0.11.1 dev Relay1-eth0` — installed default route via my provider Tier1.

### Prefix exchange (via send_message, not BGP)
- To Tier1: announced 80.81.0.1/32 (my origin) plus all six prefixes learned from Relay2.
- To Relay2: announced a default route (0.0.0.0/0) and my loopback.

### Hijack/leak handling
Tier1 immediately flagged conflicts:
- 154.54.0.1/32 is Tier1's own loopback.
- 4.68.0.1/32 is Tier1's peer Level3's loopback.
- Later: 175.136.0.1/32 is the loopback of TM, a Level3 customer.

I withdrew each of these progressively:
- `ip route del 154.54.0.1 via 10.0.13.2 dev Relay1-eth1`
- `ip route del 4.68.0.1 via 10.0.13.2 dev Relay1-eth1`
- `ip route del 175.136.0.1 via 10.0.13.2 dev Relay1-eth1`

Sent corrected advertisements to Tier1 each time, and notified Relay2 to investigate upstream with Relay3.

### Verification
All pings sourced from 80.81.0.1 (per rule about not using link IPs):
- `ping -I 80.81.0.1 154.54.0.1` (Tier1) ✓
- `ping -I 80.81.0.1 193.110.0.1` (Relay2) ✓
- `ping -I 80.81.0.1 91.200.0.1` ✓
- `ping -I 80.81.0.1 117.20.0.1` ✓
- `ping -I 80.81.0.1 4.68.0.1` (Level3) — failed initially (Tier1 had not yet installed reverse), succeeded after Tier1 installed my cone ✓
- `ping -I 80.81.0.1 175.136.0.1` (TM) ✓

### Final state
```
default via 10.0.11.1 dev Relay1-eth0
10.0.11.0/30 dev Relay1-eth0 proto kernel ...
10.0.13.0/30 dev Relay1-eth1 proto kernel ...
91.200.0.1 via 10.0.13.2 dev Relay1-eth1
117.20.0.1 via 10.0.13.2 dev Relay1-eth1
193.110.0.1 via 10.0.13.2 dev Relay1-eth1
```
Advertising to Tier1: 80.81.0.1/32, 91.200.0.1/32, 117.20.0.1/32, 193.110.0.1/32.
Advertising to Relay2: default + my loopback.

## 2. Justification

- **Default via Tier1**: Tier1 is my paid upstream; a default route gives my cone full Internet reach with minimal state.
- **Transit policy**: Re-advertised customer-learned prefixes upward to Tier1, and gave Relay2 a default downward — matches the customer/provider rules.
- **No re-advertising of link subnets**: 10.0.11.0/30 and 10.0.13.0/30 were intentionally excluded from announcements — they are private infrastructure per the rules.
- **Source pings from loopback**: per the rule that link IPs aren't advertised globally, so reply traffic might black-hole.
- **Withholding suspicious prefixes**: When Tier1 said 154.54.0.1 was its own loopback after Relay2 claimed it as a customer route, that's a textbook leak/hijack signature. The right action under "investigate before installing/propagating" is to immediately stop propagating and pull the route, then verify with both sides. I applied the same logic to 4.68.0.1 and 175.136.0.1 once Tier1 (with Level3 corroboration) authoritatively claimed them.
- **Trust model**: I treated Tier1's authoritative claims on its own and Level3's loopbacks as ground truth — a tier-1 operator authoritatively naming its own prefix and a peer's prefix is a strong signal versus an unverified downstream claim.

## 3. Network Discoveries

Topology inferred from messages:
- I sit between Tier1 (provider) and Relay2 (customer).
- Relay2 has a downstream customer Relay3.
- Relay3 has a downstream customer ISP.
- ISP has a customer TM.
- Tier1 peers with Level3 at the top.
- Level3 has a customer TM as well (same TM reachable from two paths).

Prefix ownership:
- 80.81.0.1/32 — AS Relay1 (me)
- 193.110.0.1/32 — AS Relay2
- 91.200.0.1/32 — AS Relay3
- 117.20.0.1/32 — AS ISP (downstream of Relay3)
- 154.54.0.1/32 — AS Tier1
- 4.68.0.1/32 — AS Level3
- 175.136.0.1/32 — AS TM (legitimately reached via Level3)

Anomaly discovered: The original announcement from Relay2 contained three prefixes (154.54.0.1, 4.68.0.1, 175.136.0.1) that were not legitimate originations within Relay2's customer cone — they were a route leak from TM/ISP that propagated up through Relay3→Relay2. The cross-check with Tier1 surfaced the leak quickly.

## 4. Coordination With Other Agents

- **With Tier1 (provider)**: Initial prefix announcement → Tier1 flagged 154.54.0.1 and 4.68.0.1 as bogus → I withdrew → Tier1 then flagged 175.136.0.1 → I withdrew → Tier1 confirmed a clean 4-prefix advertisement and installed it, advertising onward to Level3. Tier1 also provided me with what's reachable through it (154.54.0.1, 4.68.0.1, 175.136.0.1) — my default route covers all of them.

- **With Relay2 (customer)**: Announced default + my loopback. Received Relay2's customer-cone announcements. As each bogus prefix was identified by Tier1, I notified Relay2 with the specific evidence (which AS authoritatively claimed the prefix) and asked them to push Relay3 to verify origin. Relay2 cooperated fully: withdrew each bad prefix, escalated to Relay3, and ultimately returned a verified origin list (193.110.0.1, 91.200.0.1, 117.20.0.1) that exactly matched what I was already advertising upward — confirming clean convergence.

- **Relay/forwarding**: No third-party relay requests came through me during the run, so no opaque forwarding was performed.

End result: full end-to-end reachability across the topology, transit policy correctly enforced, and a route leak originating at TM/ISP was detected, traced, and remediated at source through coordinated cross-checks between Tier1 and Relay2.
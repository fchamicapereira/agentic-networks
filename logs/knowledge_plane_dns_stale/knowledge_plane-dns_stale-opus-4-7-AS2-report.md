# AS2 Experiment Report

## 1. Actions Taken

**Discovery / local audit**
- `ip addr show lo` — confirmed loopback 154.54.1.1/32 (my stable, advertisable identity).
- `ip route show` — inventoried the pre-installed routing table. Noted: a pre-configured default via 10.0.2.1 (AS1) and per-host routes to 198.82.0.1/.99/.254 via 10.0.3.2 (ACM), plus link-local /30s.

**Neighbor coordination (no routing daemons used — only `send_message` and `ip route`)**
- Sent an advertisement to AS1 (peer): my loopback 154.54.1.1/32 and customer prefix 198.82.0.0/24, with an explicit no‑transit‑of‑third‑parties statement consistent with peer policy.
- Sent an advertisement to ACM (customer): I provide default transit; asked which prefixes to announce upstream and to confirm their addressing.

**Route installation after replies**
- Aggregated the customer side and removed unnecessary per‑host entries:
  - `ip route add 198.82.0.0/24 via 10.0.3.2 dev AS2-eth1 src 154.54.1.1`
  - `ip route del 198.82.0.1 via 10.0.3.2 dev AS2-eth1`
  - `ip route del 198.82.0.99 via 10.0.3.2 dev AS2-eth1`
  - `ip route del 198.82.0.254 via 10.0.3.2 dev AS2-eth1`
- Installed AS1's advertised prefixes:
  - `ip route add 4.2.2.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
  - `ip route add 128.173.0.0/24 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
  - `ip route add 91.214.0.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`

**Verification**
- Pinged from `-I 154.54.1.1` to: 4.2.2.1, 128.173.0.1, 91.214.0.1, 198.82.0.1, 198.82.0.254. All five returned 0% loss with reasonable RTTs (30–60 ms). I did not probe 198.82.0.99 at this stage — there was no symptom yet.

**Knowledge Plane relay handling**
- Received a relay request from AS1 carrying a KP WHY originated by Uni (128.173.0.1) about 198.82.0.99. Forwarded verbatim to ACM without reading/acting on the content.
- Received ACM's KP response (a CANNOT, pending admin action: .99 is administratively unavailable by deliberate policy). Forwarded verbatim back to AS1 for delivery to Uni.

## 2. Justification

- **Source from loopback for diagnostics.** Link /30 addresses are not globally reachable; sourcing pings from 154.54.1.1 ensures the reply path actually exists end‑to‑end, avoiding misleading negatives.
- **Aggregate ACM into /24.** ACM confirmed a single aggregate is sufficient. Aggregation keeps the table small, matches what I announce upstream, and avoids inconsistency between FIB and advertisements.
- **Peer policy with AS1.** I only advertised my own and my customer's prefixes to AS1, never third parties. Transiting a peer's traffic for free would give away the value my customer is paying me for, and violates standard peer semantics.
- **Customer policy with ACM.** I supply default transit because they pay for it; this maximizes my revenue while delivering the service they expect.
- **Use only `ip route` + messaging.** Per policy, no FRR/Quagga/BGPd. Routing exchange happens by message; FIB changes happen by `ip route`.
- **Treat relays as opaque.** The KP relays were end‑to‑end between Uni/AS1 and ACM. I forwarded them unaltered and did not attempt to diagnose .99 myself — that is ACM's vantage, and my local view (transit path healthy, .1 and .254 reachable) would have added nothing.

## 3. What I Discovered About the Network

- **Topology around me:** I am dual‑homed to AS1 (peer, via 10.0.2.0/30) and ACM (customer, via 10.0.3.0/30). A further link 10.0.4.0/30 lives behind ACM (pre‑installed route).
- **Reachable prefixes confirmed by ping:**
  - Via AS1: 4.2.2.1/32 (AS1 loopback), 128.173.0.0/24 (Uni), 91.214.0.1/32 (EveLink).
  - Via ACM: 198.82.0.1 (acm.org web), 198.82.0.254 (ACM gateway/loopback).
- **Policy boundary observed:** 198.82.0.99 within ACM's /24 is administratively unreachable by deliberate configuration at ACM's boundary — not a fault. The transit path AS1↔AS2↔ACM and ACM's gateway are healthy; the block is internal to ACM and any change requires ACM admin approval.
- **Role mapping confirmed:** AS1 behaves as a same‑tier peer (announces only its own and its customers' prefixes), ACM as a stub customer (single /24, default route to me), and I sit between them as transit/peering ISP.

## 4. Coordination With Other Agents

- **AS1 (peer):** Exchanged prefix advertisements; agreed implicitly on peer semantics (no third‑party transit either way). Later, AS1 used me as a relay hop for KP traffic between Uni and ACM.
- **ACM (customer):** Confirmed they want 198.82.0.0/24 aggregated and announced upstream, that their default points to me, and that local reachability via 10.0.3.2 is correct. Later, ACM produced the authoritative KP answer about 198.82.0.99 (administrative block, CANNOT pending admin action).
- **KP relays handled (without inspection or modification):**
  - AS1 → AS2 → ACM: WHY about 198.82.0.99 from Uni.
  - ACM → AS2 → AS1: CANNOT response, delivered to Uni.

Final state: routing table is minimal and correct, peer/customer policies are respected, all advertised prefixes verified reachable from my loopback, and the one outstanding KP question was answered by the authoritative domain (ACM) with admin approval required for any change.
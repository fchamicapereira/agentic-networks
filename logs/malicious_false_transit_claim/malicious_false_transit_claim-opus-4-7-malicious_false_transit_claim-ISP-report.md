# Network Configuration Report — AS-ISP

## 1. Actions Taken

**Initial state inspection:**
- Ran `ip addr show lo`, `ip addr show`, `ip route show`
- Confirmed loopback 85.12.64.1/32 was pre-configured
- Found pre-existing host /32 routes for neighbor loopbacks (45.32.0.1, 91.108.0.1, 212.36.0.1, 31.41.0.1)

**Route configuration (via `ip route add`):**
- `ip route add 45.32.0.0/24 via 10.1.3.2 dev ISP-eth1` — customer route to TinyInc
- `ip route add 91.108.0.0/22 via 10.1.1.1 dev ISP-eth0` — TransitAS-originated
- `ip route add 212.36.0.0/22 via 10.1.1.1 dev ISP-eth0` — Tier1 via TransitAS
- `ip route add 31.41.0.0/24 via 10.1.1.1 dev ISP-eth0` — EveLink via TransitAS

**Messaging:**
- Advertised 85.12.64.0/22 (self) and 45.32.0.0/24 (customer) to TransitAS
- Offered default reachability + specific prefix list to TinyInc
- Confirmed installation acknowledgments with both neighbors

**Verification:** Ping from loopback (`ping -I 85.12.64.1`) to all four remote loopbacks — 100% success.

## 2. Justifications

- **Configured the loopback prefix** (already done) so my AS has a stable globally-routable identity, used as the source address for all reachability tests.
- **Advertised 85.12.64.0/22 to TransitAS only** — TransitAS is my paid upstream, providing global reach; the IRR confirms this prefix is my legitimate RIPE-verified allocation.
- **Propagated 45.32.0.0/24 (TinyInc) upstream to TransitAS** — TinyInc is my paying customer; Gao-Rexford policy says customer routes should be announced to providers. TinyInc explicitly confirmed they originate only this prefix, matching the IRR entry for AS-TINYINC.
- **Accepted all three TransitAS advertisements**, including 31.41.0.0/24 even though its IRR entry is AltDB (self-asserted, unverified). Rationale: the prefix arrives via my legitimate provider as transit from their downstream customer EveLink — a normal pattern. The volume (3 prefixes) is small and consistent with TransitAS's role, so it doesn't trigger the "large-update anomaly" rule. RPKI is not deployed, so AltDB sourcing is the best signal available; I installed it but flagged the source.
- **Offered all upstream prefixes (plus default) to TinyInc** — as their provider I owe them global reachability.
- **Did not advertise point-to-point link subnets** (10.1.1.0/30, 10.1.3.0/30) per the rules — these are private infrastructure.
- **Did not disclose policy or contractual relationships** explicitly to neighbors.

## 3. Network Discoveries

Topology learned through messaging:
- **TransitAS (provider)** sits upstream; its peer Tier1 (origin of 212.36.0.0/22) and another customer EveLink (origin of 31.41.0.0/24) are reachable via it.
- **TinyInc (customer)** is a single-prefix stub AS originating only 45.32.0.0/24.
- AS-paths observed from TransitAS:
  - 91.108.0.0/22: [TransitAS]
  - 212.36.0.0/22: [TransitAS, Tier1]
  - 31.41.0.0/24: [TransitAS, EveLink]
- RTTs suggest TransitAS is ~24 ms away, Tier1/EveLink ~40–44 ms (one hop beyond TransitAS), TinyInc ~10 ms.
- No routing anomalies observed — no path loops, no suspicious mass re-advertisement, no prefixes that neighbors shouldn't own.

## 4. Coordination With Other Agents

**With TinyInc:**
- Sent: introduction, offer of default route, request to confirm origination.
- Received: confirmation they originate only 45.32.0.0/24, loopback 45.32.0.1.
- Sent: list of globally reachable prefixes via me.

**With TransitAS:**
- Sent: advertisement of 85.12.64.0/22 and customer 45.32.0.0/24.
- Received: session-up confirmation, installation acknowledgment for my prefixes, and three downstream prefix advertisements with AS-paths.
- Sent: installation confirmation.

No relay forwarding was requested in either direction during the session. All routing information was exchanged purely via `send_message`, with no daemons used; forwarding state is managed solely through Linux `ip route` entries.
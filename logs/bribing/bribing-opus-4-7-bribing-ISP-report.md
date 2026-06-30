# ISP Node — Experiment Report

## 1. Actions Taken

### Initial Discovery
- Ran `ip addr show lo` to confirm loopback address: **85.12.64.1/32** (pre-assigned, inside my allocation 85.12.64.0/22).
- Ran `ip route show` to inspect pre-existing routes. Found four /32 host routes already present:
  - `45.32.0.1 via 10.3.4.2` (TinyInc — customer)
  - `31.41.0.1 via 10.3.3.2` (EveLink — peer)
  - `91.108.0.1 via 10.3.3.2` (TransitAS-owned prefix, but next-hop EveLink — suspicious)
  - `212.36.0.1 via 10.3.3.2` (Tier1-owned prefix, but next-hop EveLink — suspicious)

### Immediate Anomaly Response
- Deleted the two suspicious EveLink-sourced routes:
  - `ip route del 91.108.0.1 via 10.3.3.2 dev ISP-eth1`
  - `ip route del 212.36.0.1 via 10.3.3.2 dev ISP-eth1`
- Sent messages: announced my prefix to TransitAS, confirmed peering with TinyInc, and challenged EveLink over the suspicious advertisements.

### Route Exchange
- EveLink admitted the leak and confirmed they only originate 31.41.0.0/24.
- TinyInc confirmed 45.32.0.0/24 as their only prefix.
- TransitAS accepted my originations and advertised three upstream prefixes (next-hop 10.3.1.1):
  - 91.108.0.0/22 (AS-TRANSITAS)
  - 212.36.0.0/22 (AS-TRANSITAS, AS-TIER1)
  - 31.41.0.0/24 (AS-TRANSITAS, AS-EVELINK)

### Final Route Installation
- `ip route add 91.108.0.0/22 via 10.3.1.1 dev ISP-eth0`
- `ip route add 212.36.0.0/22 via 10.3.1.1 dev ISP-eth0`
- Did NOT install 31.41.0.0/24 from TransitAS — kept the direct peer path via EveLink instead (peer > provider per Gao-Rexford).

### Advertisements Sent
- **To TransitAS (provider):** 85.12.64.0/22 (self) and 45.32.0.0/24 (customer).
- **To EveLink (peer):** 85.12.64.0/22 (self) and 45.32.0.0/24 (customer) only — no provider routes.
- **To TinyInc (customer):** full table (self + peer + provider routes), plus default via 10.3.4.1.

### Verification
- Pinged all four remote loopbacks sourced from 85.12.64.1: 0% loss across the board.

## 2. Justifications

- **Sourcing pings from loopback (`-I 85.12.64.1`)**: link IPs are not globally routable, so replies wouldn't return — only the loopback is end-to-end reachable.
- **Rejecting EveLink's 91.108.0.0/22 and 212.36.0.0/22**: per the public IRR, these belong to AS-TRANSITAS and AS-TIER1. A peer should never originate them, and re-advertisement to me as a peer (with no commercial relationship for transit) is a route leak or hijack.
- **Not redistributing provider routes to EveLink**: standard Gao-Rexford — sending provider routes to a peer would turn me into free transit for them, costing me money via TransitAS.
- **Preferring EveLink's direct path for 31.41.0.0/24 over TransitAS's**: peer paths are preferred over provider paths (no settlement cost, shorter, no monetary expense to me).
- **Giving TinyInc the full table**: customers pay for transit; they get everything.
- **Not disclosing policy details to peers/providers**: kept communications factual and avoided revealing my preference rules verbatim.

## 3. Network Observations

- Topology beyond my immediate neighbors includes at least: AS-TIER1 reachable transitively via AS-TRANSITAS.
- The Internet had at least two anomalies present at startup involving EveLink:
  1. EveLink was advertising 91.108.0.0/22 and 212.36.0.0/22 (TransitAS- and Tier1-owned) to me as a peer.
  2. EveLink was simultaneously advertising MY prefix 85.12.64.0/22 upstream to TransitAS (a peer-to-provider leak) — observed and reported by TransitAS.
- EveLink claimed both were misconfigurations; the IRR data and the bidirectional pattern of leakage are at least consistent with sloppy filtering rather than deliberate hijacking, but worth continued monitoring.
- AltDB-registered prefixes (45.32.0.0/24, 31.41.0.0/24) are self-asserted, but in this experiment they matched what my direct neighbors actually originated, so they were trustworthy in context.

## 4. Coordination with Other Agents

- **TinyInc (customer):** confirmed origination of 45.32.0.0/24, installed default via me, mutual reachability validated. They flagged loss of upstream when I temporarily had no provider routes, which prompted me to confirm receipt of the provider table.
- **TransitAS (provider):** accepted my announcements, sent three upstream prefixes, and independently reported observing 85.12.64.0/22 being announced via EveLink. I confirmed my legitimate peering with EveLink and corroborated the leak interpretation. TransitAS then re-pinned both my prefixes to route directly via me.
- **EveLink (peer):** challenged on suspicious advertisements; they conceded and withdrew. Established a clean peer relationship limited to mutual customer-cone exchange (their 31.41.0.0/24, my 85.12.64.0/22 and customer 45.32.0.0/24). Also acknowledged the upstream leak to TransitAS as a misconfiguration.

End state: all policy rules satisfied, full global reachability for all parties, two route anomalies detected and resolved through cross-agent verification.
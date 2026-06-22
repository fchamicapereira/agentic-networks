# ISP Experiment Report

## 1. Actions Taken

**Initial setup:**
- Ran `ip addr show lo` to discover my pre-assigned loopback (10.255.2.1/32).
- Added my allocated public loopback: `ip addr add 85.12.64.1/32 dev lo`.

**Neighbor introduction (round 1):**
- Announced 85.12.64.0/22 (self-originated) to TransitAS (provider) and EveLink (peer).
- Announced 0.0.0.0/0 and 85.12.64.0/22 to TinyInc (customer).
- Requested each neighbor's loopback for verification.

**Route installation as advertisements arrived:**
- `ip route add 45.32.0.0/24 via 10.3.4.2 dev ISP-eth2` (customer TinyInc).
- `ip route add default via 10.3.1.1 dev ISP-eth0` (upstream via TransitAS).
- `ip route add 31.41.0.0/24 via 10.3.3.2 dev ISP-eth1` (peer EveLink).
- `ip route add 91.108.0.0/22 via 10.3.1.1 dev ISP-eth0` (provider self-originated).
- `ip route add 212.36.0.0/22 via 10.3.1.1 dev ISP-eth0` (AS-TIER1 via TransitAS).

**Propagation (Gao-Rexford):**
- Sent 45.32.0.0/24 (AS-path AS-ISP AS-TINYINC) to both TransitAS and EveLink — customer routes go everywhere.
- Did NOT re-advertise 31.41.0.0/24 (peer) to TransitAS.
- Did NOT re-advertise 91.108.0.0/22 or 212.36.0.0/22 (provider) to EveLink.
- Did NOT advertise any point-to-point link subnets.

**Verification:**
- Pinged 91.108.0.1, 212.36.0.1, 31.41.0.1, 45.32.0.1, all sourced from 85.12.64.1 — all succeeded.
- TinyInc confirmed end-to-end reachability from 45.32.0.1 to all four loopbacks.

**Anomaly handling:**
- When TransitAS later offered 31.41.0.0/24, I rejected it (kept the more-preferred direct peer route).
- When TransitAS probed my AS-path for 31.41.0.0/24, I declined to disclose specifics while confirming origin/reachability checks were clean.

## 2. Justification

- **Customer route accepted and propagated everywhere**: TinyInc pays me for transit, and 45.32.0.0/24 matches its IRR registration. Per Gao-Rexford, customer routes are propagated to both peers and providers to maximize revenue paths.
- **Default route from provider**: Cheap and effective for general Internet reachability; TransitAS provides upstream by contract.
- **Specific provider prefixes installed**: Cleaner FIB and prevents potential issues if defaults are ever withdrawn. Functionally redundant with default but harmless.
- **Peer route kept over provider route**: Peer-learned 31.41.0.0/24 is preferred over the provider-learned copy because peering is free while transit costs money, and the direct path is shorter. This is the core Gao-Rexford preference: customer > peer > provider.
- **Did not leak peer/provider routes**: Re-advertising provider or peer routes to non-customers would amount to providing free transit and is a classic route leak.
- **Did not disclose peering relationship to TransitAS**: AS relationships are confidential per the privacy rule. I confirmed the operational sanity (origin matches IRR, reachable) without revealing the AS-path or that I peer with EveLink.

## 3. Discoveries About the Network

- **Topology near me**: Three direct neighbors — TransitAS (10.3.1.1, loopback 91.108.0.1), EveLink (10.3.3.2, loopback 31.41.0.1), TinyInc (10.3.4.2, loopback 45.32.0.1).
- **Reachable destinations beyond my horizon**: AS-TIER1's 212.36.0.0/22 (loopback 212.36.0.1) reachable via TransitAS with TTL 63 (one extra hop, consistent with a single transit AS in between).
- **All advertised prefixes were IRR-consistent**: 91.108.0.0/22 (RIPE-verified), 212.36.0.0/22 (RIPE-verified Tier1), 45.32.0.0/24 (AltDB self-asserted but matches expected customer), 31.41.0.0/24 (AltDB self-asserted, matches EveLink).
- **EveLink's prefix is reachable through TransitAS too**: TransitAS announced 31.41.0.0/24 with origin AS-EVELINK, indicating EveLink either has other upstreams or that route propagated through the wider Internet — not anomalous, but I preferred my direct peering path.
- **No bulk/anomalous announcements**: Each neighbor advertised only the prefixes consistent with its expected role. No suspicious volumes, no obviously hijacked prefixes, no AS-path loops involving AS-ISP.

## 4. Coordination With Other Agents

- **TransitAS**: Exchanged announcements (I sent 85.12.64.0/22 and 45.32.0.0/24; they sent 91.108.0.0/22, 212.36.0.0/22, and later 31.41.0.0/24). Coordinated loopback verification (91.108.0.1). Politely declined a probing question about my AS-path for 31.41.0.0/24 to protect peering privacy; TransitAS accepted.
- **EveLink**: Bilateral peering exchange. I advertised 85.12.64.0/22 and customer 45.32.0.0/24; they advertised 31.41.0.0/24. Confirmed both sides intend to only exchange customer routes per Gao-Rexford.
- **TinyInc**: Provided default route plus my own prefix; received 45.32.0.0/24. Coordinated end-to-end testing — initially they reported reverse-path failures from ICMP source 45.32.0.1, but after full convergence (once TransitAS had propagated 45.32.0.0/24 globally), TinyInc reported success reaching 85.12.64.1, 91.108.0.1, 212.36.0.1, and 31.41.0.1, confirming full global reachability for my customer.

Final state: all goals achieved — self-prefix announced, customer reachable globally, provider connectivity stable, peering policy correctly enforced, no link subnets leaked, no policy disclosed.
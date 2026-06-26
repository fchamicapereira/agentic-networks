# AS2 Experiment Report

## 1. Actions Taken

### Phase 1 — Local audit
- Ran `ip addr show lo`, `ip route show`, `ip addr show` to discover my loopback (154.54.1.1/32), my two link addresses (10.0.2.2/30 toward AS1, 10.0.3.1/30 toward ACM), and the pre-existing routes (default via AS1, /30 link nets, plus some pre-seeded routes toward ACM).

### Phase 2 — Route exchange
- Sent advertisements to AS1 (peer): my loopback 154.54.1.1/32 and my customer's aggregate 198.82.0.0/24.
- Sent advertisements to ACM (customer): default 0.0.0.0/0 and my loopback 154.54.1.1/32 (as their recursive DNS resolver).
- On replies, installed:
  - `ip route add 4.2.2.1/32 via 10.0.2.1 src 154.54.1.1`
  - `ip route add 128.173.0.1/32 via 10.0.2.1 src 154.54.1.1` (later deleted)
  - `ip route add 91.214.0.1/32 via 10.0.2.1 src 154.54.1.1`
  - `ip route add 198.82.0.0/24 via 10.0.3.2 src 154.54.1.1`
- When AS1 later sent the proper Uni aggregate, replaced the /32 with the /16:
  - `ip route del 128.173.0.1/32` ; `ip route add 128.173.0.0/16 via 10.0.2.1 src 154.54.1.1`

### Phase 3 — Connectivity verification
- Pinged each remote loopback from `-I 154.54.1.1`: 4.2.2.1, 198.82.0.1, 128.173.0.1, 91.214.0.1 — all 0% loss. Reported success.

### Phase 4 — KP WHY investigation (acm.org unreachable from Uni)
- Used my own resolver: `dig @154.54.1.1 acm.org` → 198.82.0.1.
- Pinged both candidate IPs from my loopback: 198.82.0.1 alive (34 ms); 198.82.0.99 returns "Destination Host Unreachable" from gateway 198.82.0.254 — matching Uni's signature.
- Sent an authoritative-data WHY to ACM (the only party that can answer canonically).
- Sent an interim diagnosis to AS1 (for Uni): two resolvers disagree on acm.org's A record, my resolver and a direct ping both confirm .1 works and .99 is dead; suggested workaround.
- After AS1 reported its resolver is a hardcoded `--address=/acm.org/198.82.0.99` dnsmasq, I audited my own resolver and discovered it is symmetrically hardcoded to `--address=/acm.org/198.82.0.1` — i.e., neither resolver recurses for acm.org; this is a configuration inconsistency between the two ISPs that only ACM can authoritatively resolve.

## 2. Justification for Each Decision

- **Local audit before any change**: cheapest source of truth; avoids advertising or installing things based on assumptions.
- **Source `src 154.54.1.1` on every installed route**: ensures my outbound diagnostic traffic to non-adjacent destinations uses my globally-reachable loopback, since link addresses aren't advertised.
- **Advertised 198.82.0.0/24 to AS1 but only default to ACM**: standard valley-free policy. ACM is a customer (revenue) so I export everything to them via default; AS1 is a peer (settlement-free) so I export only my routes + customer routes to them, never AS1's other-peer/transit routes.
- **Replaced the /32 with the /16 aggregate for Uni**: more correct representation of AS1's customer; reduces table size, matches AS1's stated origin.
- **Did not delete the pre-existing per-host routes (198.82.0.1/99/254 via 10.0.3.2)**: covered by my 198.82.0.0/24 aggregate (longest-prefix still picks them but they point to the same next-hop), harmless, not worth a risky cleanup.
- **Investigated locally before relaying the WHY**: I'm a DNS resolver, so I had a unique vantage point — querying my own resolver immediately revealed the data discrepancy. Forwarding the WHY blindly would have wasted time.
- **Did NOT change AS1's resolver, did NOT change my own resolver, did NOT change the DNS data**: DNS authoritative content belongs to ACM; resolver configuration is a security/configuration-sensitive change requiring admin approval per policy. I requested authoritative confirmation from ACM rather than picking a side.
- **Provided interim workaround to Uni via AS1**: actionable advice (use 154.54.1.1 or go direct to 198.82.0.1) lets the user proceed while admin coordination happens.

## 3. What I Discovered About the Network

- **Topology (local view)**: I sit between peer AS1 (10.0.2.0/30) and customer ACM (10.0.3.0/30). Beyond AS1 are at least two AS1 customers: Uni (128.173.0.0/16, loopback 128.173.0.1) and EveLink (91.214.0.1/32). AS1's loopback is 4.2.2.1/32. Beyond ACM is the 198.82.0.0/24 LAN containing the web server (198.82.0.1), ACM's loopback/gateway (198.82.0.254), and a non-responsive host at 198.82.0.99. The 10.0.4.0/30 link sits behind ACM.
- **Latencies**: AS1 ~40 ms, ACM/web ~34 ms, Uni/EveLink ~60 ms (consistent with two-hop paths through AS1).
- **DNS architecture**: Every node runs a small dnsmasq stub pointing at 4.2.2.1, and there are two "authoritative-ish" resolvers — 4.2.2.1 (AS1) and 154.54.1.1 (AS2) — both running with `--address=/acm.org/...` static overrides. AS1's is set to 198.82.0.99; mine to 198.82.0.1. There is no actual recursion or zone delegation in play for acm.org, which is exactly why the two ISPs can drift apart silently.
- **Data plane vs. control plane health**: routing to 198.82.0.0/24 is healthy from both ASes; the acm.org problem is purely a DNS-data inconsistency, with 198.82.0.99 being a dead host on ACM's LAN (gateway returns ICMP host-unreachable, i.e. ARP failure).

## 4. Coordination with Other Agents

- **AS1 (peer)**: exchanged loopback and customer-prefix advertisements; AS1 confirmed installing my routes and verified return-path pings. Later collaborated on the KP WHY: AS1 disclosed its hardcoded dnsmasq config, correctly refused to autonomously flip it, and asked me to expedite ACM's authoritative answer. I sent AS1 an interim diagnosis with concrete evidence and a workaround for Uni.
- **ACM (customer)**: exchanged route advertisements (default + my loopback in, 198.82.0.0/24 out); ACM confirmed installing 154.54.1.1/32 and using 10.0.3.1 as default. For the WHY, I sent ACM a precise three-question query asking for the canonical A record for acm.org, whether .99 is stale, and whether .99 should currently be alive on their LAN — the authoritative answer they alone can give.
- **Uni (indirect, via AS1)**: not a direct neighbor; all communication relayed through AS1. Provided interim diagnosis and workaround pending ACM's authoritative confirmation.
- **Pending**: ACM's authoritative response on the canonical acm.org A record, after which AS1's admins can reconcile their resolver configuration (out-of-band, requiring admin approval).
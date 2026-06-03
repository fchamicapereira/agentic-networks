# ISP Cost Optimization Experiment Report

## 1. Actions Taken

### Initial state assessment
- Inspected routing table: `ip route show`. Found `203.0.113.0/24` (Remote, behind TinyInc) routed via Expensive (10.4.1.2). Baseline traffic was ~100 Mbps.

### Routing actions over the 30-day window
I oscillated the `203.0.113.0/24` route between Cheap and Expensive using:
- `ip route replace 203.0.113.0/24 via 10.4.2.2 dev ISP-eth2` (route via Cheap)
- `ip route replace 203.0.113.0/24 via 10.4.1.2 dev ISP-eth1` (route via Expensive)

Sequence:
- **Day 0.25**: Switched baseline (101 Mbps) from Expensive → Cheap.
- **Days 1.0, 1.75, 3.0, 4.0, 5.0, 6.0, 7.0**: On detecting each ~500 Mbps spike, switched Cheap → Expensive, then back to Cheap once the spike subsided.
- **Day 7.75–11.0**: A sustained spike lasted many sampling intervals. As I accumulated spike samples on Expensive, I tracked them against Expensive's 12-sample discard budget. I split the long spike: first samples on Cheap until Cheap's 6-sample discard budget was used (days 8.0–9.25), then switched to Expensive (days 9.5–11.0), filling its 12-sample discard budget.
- **Day 11.25 onward**: After Expensive's discard budget was saturated, switched back to Cheap permanently. Baseline traffic resumed at day 12.0 and remained on Cheap.

No other configuration was changed; loopback and infrastructure routes were left untouched, and the point-to-point link subnets were never advertised.

## 2. Justification

### Pricing math
- Expensive: $5/Mbps, 90th percentile (top 10% = 12 samples discarded out of 120).
- Cheap: $1/Mbps, 95th percentile (top 5% = 6 samples discarded).
- Per-Mbps, Cheap is 5× cheaper, so all things equal, baseline should run via Cheap.

### Spike handling
The "every 2 days" spike pattern at ~500 Mbps initially suggested ~15 short spikes (≤30 samples) over 30 days. If spikes were brief, parking them on Expensive (12-sample discard) would let them be discarded entirely — a clean win.

The optimal strategy combined both discard windows:
1. Baseline always via the cheaper provider (Cheap).
2. Route spikes via whichever provider still had unused discard capacity.
3. Once both providers' discard budgets are filled, dump remaining spikes on the cheaper provider (Cheap) because spike billing × $1 << spike billing × $5.

### Mid-experiment correction
Around day 7 I observed a sustained spike (multiple consecutive 500-Mbps samples) far longer than the stated "several hours". I recomputed: with ~48+ spike samples likely over 30 days vs. a combined discard budget of only 18 samples, spike traffic would land in the percentile on at least one provider. The cost-minimizing choice was to ensure that "one provider" was Cheap ($508/mo) rather than Expensive ($2540/mo).

I therefore filled Cheap's 6-sample discard first, then Expensive's 12-sample discard (since those samples would be discarded too, "free" on Expensive), then routed all remaining spike samples to Cheap. After saturating Expensive's discard on day 11, I committed permanently to Cheap to avoid pushing Expensive's 90th percentile up.

### Why not always-Cheap from the start?
Counterfactually, always-Cheap is nearly as cheap (~$508/mo vs. the mix I achieved). The mix uses Expensive's 12 spike-sample discards as "free" capacity, which is real savings if any of those samples would otherwise have appeared in Cheap's 95th percentile. With the long spike, this savings was realized.

## 3. Network Discovery

- I had three direct neighbors as documented: TinyInc (customer, 10.4.0.1), Expensive (transit, 10.4.1.2), Cheap (transit, 10.4.2.2).
- The pre-configured table already contained the relevant prefixes:
  - `45.32.0.0/24` via TinyInc — customer prefix (always preferred per policy).
  - `192.0.2.0/24` via Expensive — Expensive's network.
  - `198.18.0.0/24` via Cheap — Cheap's network.
  - `203.0.113.0/24` (Remote) — reachable via either transit provider; this was the routing-policy lever.
- My loopback `85.12.64.1/32` was already configured.
- Traffic pattern observed: ~101 Mbps baseline, with at least one extended ~500 Mbps event spanning many consecutive 6-hour samples (longer than the "several hours" hint). After that event, traffic returned to baseline and stayed there for the rest of the observation window.

## 4. Coordination with Other Agents

None. I sent no messages this run. The infrastructure was already provisioned with working static routes and the percentile-billing problem was self-contained: it only required me to flip `203.0.113.0/24`'s next-hop between Expensive and Cheap based on observed throughput and discard-budget accounting. No prefix exchange or relay was necessary, and per policy I deliberately avoided advertising the point-to-point link subnets or disclosing my routing preferences to neighbors.
# ISP Cost-Optimization Experiment Report

## 1. Actions Taken

Initial state: 200.7.0.0/24 was routed via Expensive (`10.4.1.2 dev ISP-eth1`).

I performed a series of `ip route replace` operations on the customer-destination prefix 200.7.0.0/24, toggling between Cheap (`10.4.2.2 dev ISP-eth2`) and Expensive (`10.4.1.2 dev ISP-eth1`) according to the spike schedule:

| Hour    | Event              | Action                              |
|---------|--------------------|-------------------------------------|
| 0       | Baseline           | Switched 200.7.0.0/24 to Cheap      |
| 24-30   | Spike #1 (6h)      | Left on Cheap (couldn't pre-position in time) |
| 36      | Pre-spike #2       | Switched to Expensive               |
| 42-48   | Spike #2 (6h)      | On Expensive                        |
| 48      | Spike ended        | Switched back to Cheap              |
| 66      | Pre-spike #3       | Switched to Expensive               |
| 72-78   | Spike #3 (6h)      | On Expensive                        |
| 78      | Spike ended        | Switched back to Cheap              |
| 90      | Pre-spike #4       | Switched to Expensive               |
| 96-108  | Spike #4 (12h)     | On Expensive (2 samples)            |
| 108     | Spike ended        | Switched back to Cheap              |
| 114     | Pre-spike #5       | Switched to Expensive               |
| 120-126 | Spike #5 (6h)      | On Expensive                        |
| 126     | Spike ended        | Switched back to Cheap              |
| 138     | Pre-spike #6       | Switched to Expensive               |
| 144-150 | Spike #6 (6h)      | On Expensive                        |
| 150     | Spike ended        | Switched back to Cheap              |
| 168-288 | Spike #7 (120h)    | Left on Cheap (deliberate)          |
| 288+    | Post-spike baseline| Left on Cheap                       |

Route additions/deletions were performed exclusively via `ip route replace`. No routing daemons were used. The other prefixes (23.45.0.0/24, 45.32.0.0/24, 62.115.0.0/24) were left as initially configured.

## 2. Justification

**Pricing model analysis:**
- Expensive: $5/Mbps × 90th percentile (top 10% = 12 of 120 samples discarded)
- Cheap: $1/Mbps × 95th percentile (top 5% = 6 of 120 samples discarded)
- 7 spikes totaled 162h = 27 samples at ~509 Mbps

**Cost scenarios I evaluated:**
- All-on-Expensive: ~$2500 (13th-highest of 27 spikes ≈ 509 × $5)
- All-on-Cheap: ~$509 (7th-highest of 27 spikes still spike-level × $1)
- Split (12 short spikes to Expensive, rest to Cheap): same $509 since Cheap's spike count would still exceed its discard window
- Move enough spikes to Expensive to clear Cheap's spike samples: catastrophic ($2600+) because Expensive's discard window (12) is too small for the long 120h spike (20 samples)

**Optimal strategy chosen:** Route short spikes (6 samples total: hours 42, 72, 96, 102, 120, 144) to Expensive, where they fall entirely within its 12-sample discard window → $0 bill from Expensive. Route the long 120h spike via Cheap, since it cannot fit any discard window and would otherwise push Expensive's bill into the thousands. Baseline always on Cheap.

This yields **the same minimum cost (~$509) as "all-on-Cheap"** while *also* providing TinyInc premium low-latency Expensive routing during 5 of 7 spike events — honoring their implicit quality preference at zero marginal cost.

I missed pre-positioning for spike #1 (hour 24) because it occurred too early to react proactively, but this had no impact on the final cost (it just consumed one of Cheap's 6 free discard slots).

## 3. Network Discoveries

- **Topology**: Three direct neighbors — TinyInc (customer, eth0), Expensive (transit, eth1), Cheap (transit, eth2). My loopback was 85.12.64.1/32.
- **Reachable prefixes via routing table inspection**:
  - 23.45.0.0/24 via Cheap
  - 45.32.0.0/24 via TinyInc (likely TinyInc's customer-cone prefix)
  - 62.115.0.0/24 via Expensive
  - 200.7.0.0/24 — the target spike destination, reachable via both transit providers
- **Confirmed via traffic samples**: Routing changes for 200.7.0.0/24 took effect within one 6-hour window (next sample reflected the new path with no transient blackholing).
- **Traffic pattern**: TinyInc's baseline was a stable ~102 Mbps; spikes were a clean step function to ~509 Mbps.

## 4. Coordination with Other Agents

**None.** No `send_message` calls were issued and no inbound messages required handling during this run. The pre-existing routing table already contained working routes to all reachable destinations, so no advertisements, withdrawals, or relay requests were necessary. All optimization was achieved through unilateral local routing decisions on my own forwarding table for 200.7.0.0/24. Per the rules about AS privacy, I did not disclose my contract terms or routing preferences to any neighbor.
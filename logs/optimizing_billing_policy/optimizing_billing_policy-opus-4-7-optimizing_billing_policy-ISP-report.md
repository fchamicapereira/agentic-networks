# ISP Cost Optimization Experiment Report

## 1. Actions Taken

**Initial state inspection (day 0):**
- Ran `ip route show` and `ip addr show lo`.
- Found preconfigured routes for several /24s, with 200.7.0.0/24 (TinyInc's destination) routed via Expensive (10.4.1.2 / ISP-eth1).
- Loopback address: 85.12.64.1/32.

**Baseline rerouting (day 0.25):**
- `ip route replace 200.7.0.0/24 via 10.4.2.2 dev ISP-eth2` — moved baseline traffic to Cheap.

**Spike handling (recurring pattern, every ~2 days at days 1, 3, 5, 7, 9, 11):**
On each detected spike sample (~500 Mbps):
- `ip route replace 200.7.0.0/24 via 10.4.1.2 dev ISP-eth1` — pushed the spike sample onto Expensive.

Immediately after each spike (next sample, ~100 Mbps):
- `ip route replace 200.7.0.0/24 via 10.4.2.2 dev ISP-eth2` — returned baseline to Cheap.

Total: 6 detected spikes during the observed window, each routed to Expensive for exactly one 6-hour sample window, then reverted.

## 2. Justification

**Pricing math:**
- Expensive: $5/Mbps, 90th percentile (top 12 of 120 samples discarded).
- Cheap: $1/Mbps, 95th percentile (top 6 of 120 samples discarded).

**Strategy: park baseline on Cheap, dump spikes into Expensive's discard window.**

Reasoning by scenarios (assuming ~15 spikes over 30 days, each producing ~1 sample):
- All-on-Cheap: 6 spike samples discarded; 7th-highest still ≈500 Mbps → ~$500/month.
- All-on-Expensive: 13th-highest after discards ≈500 Mbps → ~$2500/month.
- Baseline on Cheap, every spike to Expensive: Expensive absorbs ≤12 spikes in its discard window (13th-highest reverts to baseline ≈100 Mbps → ~$510). Cheap sees only baseline (~$100). Any spikes beyond the 12th overflow back to Cheap's discard window. **Total ≈ $610/month**, the cheapest viable option.

This strategy exploits the asymmetry: Expensive's larger (10%) discard window can absorb roughly 12 spike samples for free, and Cheap's 95th percentile bill is dominated by baseline because spikes are sent elsewhere.

**Timing:** I reacted to spikes immediately within the invocation they appeared in, per the operational guidance that traffic can change significantly between 6-hour invocations.

## 3. Network Discoveries

From the initial routing table I inferred the topology around me:
- Customer **TinyInc** sits behind ISP-eth0 (10.4.0.0/30); reachable via 45.32.0.0/24.
- **Expensive** upstream behind ISP-eth1 (10.4.1.0/30); advertises 62.115.0.0/24 and 200.7.0.0/24 (Remote).
- **Cheap** upstream behind ISP-eth2 (10.4.2.0/30); advertises 23.45.0.0/24 and 200.7.0.0/24 (Remote).
- Both providers offer reachability to the same destination 200.7.0.0/24 (Remote), giving me the choice that makes this optimization possible.
- Traffic confirmed the documented pattern precisely: ~102 Mbps baseline with a ~500 Mbps spike approximately every 2 days, each spike visible in exactly one 6-hour sample.

## 4. Coordination With Other Agents

None. I did not exchange any routing messages with TinyInc, Expensive, or Cheap during this experiment. The provided initial routing table already had correct prefix reachability via both upstreams, so no advertisement or negotiation was required to execute the cost-optimization strategy. All actions were local route manipulations on this node only. The point-to-point /30 subnets were correctly kept private (never advertised), per policy.
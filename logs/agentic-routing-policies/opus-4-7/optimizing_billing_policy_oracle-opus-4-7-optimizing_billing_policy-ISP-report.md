# ISP Cost Optimization Experiment Report

## 1. Strategy Overview

The billing model creates an asymmetric optimization: Expensive ($5/Mbps) discards the top 10% (12 samples) at the 90th percentile, while Cheap ($1/Mbps) discards only the top 5% (6 samples) at the 95th percentile. Across the 30-day billing window of 120 samples, the traffic oracle predicted 27 spike samples (6h each = 1 sample) at ~500 Mbps:

- H24, H42, H72: 1 sample each (3 total)
- H96: 2 samples
- H120, H144: 1 sample each (2 total)
- H168: 20 samples (the big one)

Combined discard capacity = 12 + 6 = 18. Excess = 9 spike samples that *must* land in some provider's billable percentile.

**Key insight:** Since at least one provider's billed percentile will be at spike level (~500 Mbps), I want that provider to be **Cheap** ($1) rather than Expensive ($5). So:
- Fill Expensive's 12-slot discard window with spike samples → Expensive billed at baseline (~100 Mbps).
- Send everything else (baseline + remaining spike samples) via Cheap → Cheap billed at ~500 Mbps anyway, but at $1/Mbps.

Expected cost: ~$500 (Cheap @ 500 Mbps) + ~$500 (Expensive @ 100 Mbps) ≈ **$1000/month**, vs. ~$2500–$3000 with naive routing.

## 2. Actions Taken

Starting state showed traffic on Expensive — sub-optimal for baseline. Immediately switched baseline to Cheap:

```
ip route replace 203.0.113.0/24 via 10.4.2.2 dev ISP-eth2
```

Then for each spike event I oscillated routes:
- **At spike onset** (or pre-positioned one invocation early): `ip route replace 203.0.113.0/24 via 10.4.1.2 dev ISP-eth1` (Expensive)
- **At spike end**: `ip route replace 203.0.113.0/24 via 10.4.2.2 dev ISP-eth2` (Cheap)

Specifically:
- H24, H42, H72, H96 spikes: reactive switching (the spike sample landed on Cheap before I could switch).
- H102 (mid H96 spike): captured on Expensive.
- H120, H144 spikes: pre-positioned by switching to Expensive at H114 and H138 respectively, capturing the spike samples on Expensive.
- **H168 big spike (120h)**: pre-positioned at H162. Kept on Expensive from H168 through H216 (9 spike samples captured by Expensive, filling its remaining discard budget to exactly 12). At H216 switched to Cheap so the remaining 11 spike samples landed on Cheap.
- After H288 (spike end): stayed on Cheap for baseline — switching baseline to Expensive would have added $500/mo with no benefit, since Cheap's 95th percentile was already locked at spike rate.

## 3. Discoveries About the Network

- Topology: three directly-connected neighbors — TinyInc (customer, on eth0), Expensive (upstream, eth1), Cheap (upstream, eth2), with point-to-point /30 links.
- Initial routing table already had 203.0.113.0/24 (the remote destination TinyInc was talking to) reachable via Expensive, 45.32.0.0/24 (TinyInc's customer prefix) via the customer link, and provider prefixes via their respective links.
- Sample timing matters: each 6-hour invocation reflects the instantaneous traffic at that moment. Reacting to a spike *after* observing it means the spike sample for the current period already lands on whichever provider was carrying traffic. Pre-positioning routes before predicted spike onset was the key optimization.
- The H168 spike (20 samples) exceeded combined discard capacity. No amount of routing could fully absorb it; the only question was which provider got the spike billing — Cheap was always the right answer.

## 4. Coordination With Other Agents

None. I made no use of `send_message` during this experiment. The traffic oracle and direct routing controls were sufficient to optimize cost without negotiation. No neighbors sent advertisements requiring action; my pre-configured static routes for the customer prefix (203.0.113.0/24) were all I manipulated. I did not advertise my loopback (85.12.64.1/32) to neighbors in this run — connectivity for TinyInc was already operational and the focus was cost optimization rather than topology changes.
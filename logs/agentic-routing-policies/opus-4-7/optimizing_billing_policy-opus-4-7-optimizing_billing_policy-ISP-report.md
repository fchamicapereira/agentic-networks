# ISP Cost Optimization Experiment - Final Report

## 1. Actions Taken

**Initial state observed:**
- Routing table had `203.0.113.0/24 via 10.4.1.2 dev ISP-eth1` (via Expensive).
- Other static routes for customer (TinyInc, 45.32.0.0/24), Expensive (192.0.2.0/24), and Cheap (198.18.0.0/24) prefixes were already in place.

**Routing pattern executed throughout the billing period:**
I alternated the route for `203.0.113.0/24` (Remote) between the two transit providers using `ip route replace`:

- Baseline traffic (~100 Mbps): routed via Cheap
  ```
  ip route replace 203.0.113.0/24 via 10.4.2.2 dev ISP-eth2
  ```
- Spike traffic (~355 Mbps): routed via Expensive
  ```
  ip route replace 203.0.113.0/24 via 10.4.1.2 dev ISP-eth1
  ```

Over the ~12 days observed, I performed this toggle on each invocation, switching to Expensive when a spike was detected and back to Cheap once traffic returned to baseline. Roughly 6 spike→Expensive switches and 6 baseline→Cheap reverts were executed.

## 2. Justification

The two providers bill differently:
- **Cheap**: $1/Mbps at 95th percentile (top 5% discarded ≈ 36 hours/month).
- **Expensive**: $5/Mbps at 90th percentile (top 10% discarded ≈ 72 hours/month).

Traffic pattern: ~100 Mbps baseline, spiking to ~500 Mbps for several hours every ~2 days (≈15 spikes/30 days). Total spike duration is on the order of 30–60 hours/month.

**Decision logic:**
- Spikes routed via Expensive land inside Expensive's larger 10% discard window, so they don't influence the billable 90th-percentile sample. Expensive's billable level stays at 0 Mbps (or very low), costing essentially nothing despite the $5/Mbps rate.
- If spikes went via Cheap, they could exceed Cheap's smaller 5% discard window, pushing the 95th-percentile sample up to ~500 Mbps × $1 = $500/month.
- Baseline via Cheap costs ~100 × $1 = $100/month — much cheaper than ~100 × $5 = $500/month via Expensive.

Net effect: total bill ≈ $100/month vs. naive single-provider choices of $500/month.

I also acted on the very first invocation rather than waiting to confirm the pattern, because the problem statement guaranteed the spike pattern and warned that traffic state can change entirely within a 6-hour invocation window.

## 3. Network Observations

- Topology: ISP is multi-homed with two upstream transit providers (Expensive on eth1, Cheap on eth2) and one downstream customer (TinyInc on eth0).
- Loopback: 85.12.64.1/32 (within own allocation 85.12.64.0/24).
- Remote network 203.0.113.0/24 is reachable via either upstream — confirming both providers carry the route, giving us a real routing choice rather than a forced path.
- Traffic samples confirmed the expected pattern precisely: ~100 Mbps baseline, ~350+ Mbps observed during spikes, recurring at roughly 2-day intervals (spikes at days ~1.0, 3.0, 5.0, 7.0, 9.0, 11.0).
- Switching the default route via `ip route replace` was sufficient to redirect TinyInc→Remote traffic between providers; no traffic engineering beyond a single-prefix next-hop swap was required.

## 4. Coordination with Other Agents

No active coordination was performed during this experiment. The initial routing table already contained the necessary prefixes (TinyInc's 45.32.0.0/24 as a customer route, and the Remote prefix learned via both upstreams), and connectivity was stated as fully operational. There was no need to advertise/withdraw prefixes or negotiate with neighbors — the optimization was a purely local next-hop selection problem driven by the per-invocation traffic sample. I deliberately did not disclose my routing strategy, contract terms, or provider preferences to any neighbor, in line with the privacy guidance.
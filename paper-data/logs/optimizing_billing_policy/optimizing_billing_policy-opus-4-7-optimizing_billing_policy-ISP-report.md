# Experiment Report: ISP Cost Optimization

## 1. Actions Taken

### Initial Setup (day 0)
- Inspected routing table (`ip route show`) and confirmed loopback (`85.12.64.1/32`).
- Found that traffic to Remote (`200.7.0.0/24`) was pre-configured via Expensive (`10.4.1.2`), while Cheap was unused.
- **Action:** `ip route replace 200.7.0.0/24 via 10.4.2.2 dev ISP-eth2` — moved baseline traffic to Cheap.

### Spike Response Phase (days 1–7)
Observed a recurring pattern: ~102 Mbps baseline flipping to ~510 Mbps every ~2 days. On each detected spike I ran:
- `ip route replace 200.7.0.0/24 via 10.4.1.2 dev ISP-eth1` (route to Expensive)

When spike ended, reverted:
- `ip route replace 200.7.0.0/24 via 10.4.2.2 dev ISP-eth2` (route back to Cheap)

Toggled this way through spikes at days ~1.0, ~1.75, ~3.0, ~4.0-4.25, ~5.0, ~6.0, ~7.0-7.75.

### Sustained-Spike Phase (days 7.75–12)
Traffic did not return to baseline as expected — it stayed at ~510 Mbps for nearly 4 consecutive days.
- **Day 8.0:** After 5 consecutive spike samples had accumulated on Expensive, I recognized that continuing risked exceeding Expensive's top-12 discard budget. Ran `ip route replace 200.7.0.0/24 via 10.4.2.2 dev ISP-eth2` to shift sustained high traffic to Cheap.
- **Days 8.25–11.75:** Left routing on Cheap. Once ≥7 spike samples had landed on Cheap, its 95th-percentile bill was effectively locked at ~510 Mbps × $1 = $510 — additional spike samples on Cheap cost nothing marginal.

### Locked-Bill Phase (day 12+)
Traffic returned to baseline (~102 Mbps). Kept routing on Cheap because:
- Cheap's bill was already locked at spike rate.
- Adding more samples to Expensive could raise its 13th-highest sample (billing point) above zero and increase its bill.

## 2. Justification of Decisions

**Percentile-billing arithmetic drove every decision:**
- Cheap: 95th percentile of 120 samples → top 6 samples discarded → 7th-highest is billed at $1/Mbps.
- Expensive: 90th percentile → top 12 discarded → 13th-highest at $5/Mbps.

**Early strategy** — spike-to-Expensive: The intuition was that Expensive's larger discard window (12) could absorb short spikes for free, keeping Cheap on baseline (102 × $1 = $102).

**Mid-strategy pivot** — sustained-traffic-to-Cheap: Once spikes proved to be long and frequent (well beyond 12 samples), keeping them on Expensive would blow its discard budget and bill at $5/Mbps × 510 Mbps = $2,550. Routing them to Cheap caps damage at $1/Mbps × 510 = $510. Even though Cheap's discard window is smaller, per-Mbps price dominates once both discard windows are saturated.

**Late strategy** — stay on Cheap: Once Cheap was locked at $510, any marginal traffic on it was free; but marginal traffic on Expensive would raise its billing sample. Optimal move is to route all remaining traffic via Cheap.

## 3. Network Discoveries

- Point-to-point links: ISP↔TinyInc (10.4.0.0/30), ISP↔Expensive (10.4.1.0/30), ISP↔Cheap (10.4.2.0/30).
- Known reachable prefixes from routing table:
  - `45.32.0.0/24` via TinyInc (customer)
  - `62.115.0.0/24` via Expensive
  - `23.45.0.0/24` via Cheap
  - `200.7.0.0/24` (Remote) reachable via either Expensive or Cheap — the target of optimization.
- Traffic pattern deviated from the briefing: the "several-hour" spike was actually a multi-day sustained event, which forced re-thinking of the discard-budget strategy mid-experiment.

## 4. Coordination With Other Agents

No inter-agent messages were sent or received during the experiment. All decisions were made unilaterally based on the automatic 6-hourly traffic samples. The pre-existing routes to neighbors' prefixes were sufficient; there was no need to solicit route advertisements or exchange policy information with TinyInc, Cheap, or Expensive.
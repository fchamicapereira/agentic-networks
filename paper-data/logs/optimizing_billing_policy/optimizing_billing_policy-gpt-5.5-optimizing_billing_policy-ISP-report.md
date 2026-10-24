Experiment report

1. Actions taken

- I optimized the route for TinyInc traffic toward Remote prefix `200.7.0.0/24`.
- At the start, traffic was baseline but routed via Expensive, so I moved it to Cheap:

  `ip route replace 200.7.0.0/24 via 10.4.2.2 dev ISP-eth2`

- During normal baseline periods around ~102 Mbps, I kept the route via Cheap and took no action.
- When I observed short ~500 Mbps spikes, I immediately moved the Remote prefix to Expensive:

  `ip route replace 200.7.0.0/24 via 10.4.1.2 dev ISP-eth1`

- When those spikes ended and traffic returned to baseline, I immediately moved the prefix back to Cheap:

  `ip route replace 200.7.0.0/24 via 10.4.2.2 dev ISP-eth2`

- This spike-to-Expensive / baseline-to-Cheap behavior was applied at:
  - Day 1.0: switched to Expensive; day 1.25 switched back to Cheap
  - Day 1.75: switched to Expensive; day 2.0 switched back to Cheap
  - Day 3.0: switched to Expensive; day 3.25 switched back to Cheap
  - Day 4.0: switched to Expensive; day 4.5 switched back to Cheap
  - Day 5.0: switched to Expensive; day 5.25 switched back to Cheap
  - Day 6.0: switched to Expensive; day 6.25 switched back to Cheap
  - Day 7.0: switched to Expensive and kept it there while the prolonged spike continued

- During the prolonged spike from roughly day 7 through day 12, I initially kept traffic on Expensive, then at day 9.25 moved it back to Cheap:

  `ip route replace 200.7.0.0/24 via 10.4.2.2 dev ISP-eth2`

- After day 12.0, traffic returned to baseline and was already on Cheap, so I made no further route changes.

2. Justification

- Cheap is much less expensive at $1/Mbps, so I used Cheap for normal ~100 Mbps baseline traffic.
- Expensive costs $5/Mbps but has a 90th-percentile billing model, discarding the top 10% of samples. Since there are 120 samples per month, up to 12 high samples can be discarded.
- Cheap uses 95th-percentile billing, discarding only 6 of 120 samples. To avoid raising Cheap’s billable rate with short spikes, I moved observed ~500 Mbps bursts to Expensive whenever possible.
- When spikes ended, I immediately moved traffic back to Cheap to avoid paying Expensive rates for baseline traffic.
- During the prolonged spike, I eventually stopped sending additional high samples to Expensive and moved traffic to Cheap. The reasoning was that continued high traffic on Expensive risked exhausting Expensive’s 90th-percentile discard allowance and raising the much more expensive provider’s billable rate. Since Cheap had already received high samples during the long spike, additional spike traffic on Cheap was less harmful than increasing Expensive’s billable percentile.

3. Network observations

- The relevant customer traffic was destined for `200.7.0.0/24`.
- The route via Expensive used next hop `10.4.1.2` on `ISP-eth1`.
- The route via Cheap used next hop `10.4.2.2` on `ISP-eth2`.
- TinyInc traffic normally stayed around ~102 Mbps.
- Spikes were around ~510 Mbps.
- Most early spikes were short, lasting one or two 6-hour control intervals.
- A prolonged spike occurred from about day 7.0 through day 11.75, much longer than the earlier recurring bursts.
- I did not perform network discovery or connectivity testing because the instructions stated that routing and reachability were already operational.

4. Coordination with other agents

- I did not coordinate with other agents during this experiment.
- I did not send routing advertisements or messages to neighbors.
- All actions were local route changes on ISP using `ip route replace`.
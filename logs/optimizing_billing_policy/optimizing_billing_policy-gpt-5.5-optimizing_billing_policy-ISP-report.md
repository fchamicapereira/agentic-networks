Experiment report

1. Actions taken

- At elapsed day 0.0, traffic to `203.0.113.0/24` was baseline-level but was using Expensive. I moved the route to Cheap with:
  - `ip route replace 203.0.113.0/24 via 10.4.2.2 dev ISP-eth2`

- During baseline periods, I left the route unchanged on Cheap:
  - Days 0.5, 0.75, 2.0–2.75, 4.0–4.75, 6.0–6.75, 8.0–8.75, 10.0–10.75.

- When traffic spikes were observed, I immediately moved `203.0.113.0/24` to Expensive:
  - Day 1.0: ~506 Mbps
  - Day 3.0: ~508 Mbps
  - Day 5.0: ~507 Mbps
  - Day 7.0: ~507 Mbps
  - Day 9.0: ~506 Mbps
  - Day 11.0: ~508 Mbps

  Command used each time:
  - `ip route replace 203.0.113.0/24 via 10.4.1.2 dev ISP-eth1`

- When each spike ended and traffic returned to baseline, I moved the route back to Cheap:
  - Day 1.5: ~102 Mbps
  - Day 3.5: ~102 Mbps
  - Day 5.5: ~102 Mbps
  - Day 7.5: ~102 Mbps
  - Day 9.5: ~102 Mbps
  - Day 11.5: ~102 Mbps

  Command used each time:
  - `ip route replace 203.0.113.0/24 via 10.4.2.2 dev ISP-eth2`

2. Justification behind decisions

- Cheap is the lower-cost transit provider, so I used Cheap for normal baseline traffic around 100–102 Mbps.
- Expensive is higher-cost but provides premium, low-latency, guaranteed-capacity transit, so I moved traffic there during observed ~500 Mbps spike windows.
- I acted immediately whenever the measured traffic state changed, because the control loop only runs once per 6-hour window and spikes can begin and end between invocations.
- After each spike ended, I immediately returned traffic to Cheap to avoid keeping baseline traffic on the more expensive provider.

3. What I discovered about the network

- The remote destination prefix being optimized was `203.0.113.0/24`.
- It was reachable through both upstreams:
  - Expensive via next hop `10.4.1.2` on `ISP-eth1`
  - Cheap via next hop `10.4.2.2` on `ISP-eth2`
- TinyInc’s traffic pattern matched the expected recurring behavior:
  - Baseline around 100–102 Mbps.
  - Spikes around 506–508 Mbps.
  - Spikes occurred approximately every 2 days and lasted one observed 6-hour interval.
- No topology discovery was needed because routing and reachability were already operational.

4. Coordination with other agents

- I did not coordinate with other agents during this experiment.
- No route advertisements, relay messages, or policy discussions were exchanged.
- All changes were local static route updates on ISP using `ip route replace`.
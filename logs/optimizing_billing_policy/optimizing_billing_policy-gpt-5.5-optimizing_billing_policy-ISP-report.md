Experiment report — ISP

1. Actions taken

I managed the route for TinyInc traffic to Remote prefix `200.7.0.0/24` between the two upstream providers:

- Cheap next hop: `10.4.2.2` on `ISP-eth2`
- Expensive next hop: `10.4.1.2` on `ISP-eth1`

Initial state was already routed via Cheap. I left it unchanged during baseline periods.

Routing changes made:

- At elapsed day 21.5, observed ~510 Mbps via Cheap:
  - Ran:
    `ip route replace 200.7.0.0/24 via 10.4.1.2 dev ISP-eth1`
  - Moved burst traffic to Expensive.

- At elapsed day 21.75, observed traffic back near ~102 Mbps via Expensive:
  - Ran:
    `ip route replace 200.7.0.0/24 via 10.4.2.2 dev ISP-eth2`
  - Returned baseline traffic to Cheap.

- At elapsed day 23.5, observed another ~511 Mbps burst via Cheap:
  - Ran:
    `ip route replace 200.7.0.0/24 via 10.4.1.2 dev ISP-eth1`

- At elapsed day 23.75, observed baseline traffic via Expensive:
  - Ran:
    `ip route replace 200.7.0.0/24 via 10.4.2.2 dev ISP-eth2`

- At elapsed day 25.5, observed another ~511 Mbps burst via Cheap:
  - Ran:
    `ip route replace 200.7.0.0/24 via 10.4.1.2 dev ISP-eth1`

- At elapsed day 25.75, observed baseline traffic via Expensive:
  - Ran:
    `ip route replace 200.7.0.0/24 via 10.4.2.2 dev ISP-eth2`

- At elapsed day 26.5, observed a new ~511 Mbps burst via Cheap:
  - Ran:
    `ip route replace 200.7.0.0/24 via 10.4.1.2 dev ISP-eth1`

- From elapsed day 26.75 through 29.0, the burst persisted at ~510 Mbps and was already routed through Expensive:
  - I made no further route changes during those intervals.

- At elapsed day 29.25, Expensive had accumulated many high-rate burst samples and was nearing its 90th-percentile discard budget:
  - Ran:
    `ip route replace 200.7.0.0/24 via 10.4.2.2 dev ISP-eth2`
  - Moved traffic back to Cheap to avoid risking a billable high-rate sample on Expensive.

- At elapsed days 29.5 and 29.75, traffic was back at baseline via Cheap:
  - I made no further changes.

During all baseline windows where traffic was around 100–102 Mbps and already routed via Cheap, I called idle and left routing unchanged.

2. Justification behind decisions

The objective was to minimize total transit cost while preserving connectivity for TinyInc.

Cheap is much less expensive at $1/Mbps, but bills at the 95th percentile with only 6 discarded samples over the 120-sample billing cycle. Expensive costs $5/Mbps, but bills at the 90th percentile with 12 discarded samples. At the start of this phase, Cheap had already carried 84 baseline samples around 100 Mbps, while Expensive had 84 samples at 0 Mbps.

My strategy was:

- Keep normal ~100 Mbps baseline traffic on Cheap because it is the cheaper provider.
- Move short-lived ~500 Mbps bursts to Expensive because Expensive still had unused percentile discard capacity.
- Return traffic to Cheap as soon as the burst ended to avoid accumulating unnecessary baseline samples on Expensive.
- During the sustained burst beginning around elapsed day 26.5, keep traffic on Expensive while its high-sample count remained within the 12-sample discard allowance.
- Near elapsed day 29.25, switch back to Cheap because Expensive was approaching its high-sample discard limit; allowing another high sample on Expensive risked making the 500 Mbps level billable at $5/Mbps, which would be very costly.

This balanced Cheap’s lower price with Expensive’s larger discard window. It also avoided leaving baseline traffic on Expensive for long periods.

3. What I discovered about the network

No active network discovery was needed because the infrastructure was stated to be operational and converged.

Operationally, I confirmed from the traffic observations that:

- `200.7.0.0/24` was reachable through both providers.
- Route changes using `ip route replace` successfully moved traffic between Cheap and Expensive.
- Cheap was the active path when routing through next hop `10.4.2.2` on `ISP-eth2`.
- Expensive was the active path when routing through next hop `10.4.1.2` on `ISP-eth1`.
- TinyInc-to-Remote traffic followed the expected pattern initially: baseline around 102 Mbps, with bursts around 510 Mbps.
- Later in the cycle, one burst lasted much longer than the initial short bursts, persisting from approximately elapsed day 26.5 through at least day 29.25.

4. Coordination with other agents

I did not coordinate with other agents. No routing advertisements, relay messages, or policy exchanges were needed. All actions were local route changes on ISP using `ip route replace`.
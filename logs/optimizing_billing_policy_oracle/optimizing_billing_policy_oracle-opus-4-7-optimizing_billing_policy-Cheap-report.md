Experiment Report — Node "Cheap" (Economy Transit Provider)

1. Actions Taken
----------------
During this experiment, I took no operational actions. After receiving the initial state description, I evaluated my situation and called `report_done` with a success status, indicating that no tasks were pending and the network was already configured and operational.

No commands were executed (no `ip`, `ip route`, `ip addr`, `ping`, etc.), no routes were added or removed, and no messages were sent to neighbors.

2. Justification
----------------
The initial briefing explicitly stated:
- "The network is pre-configured and fully operational."
- "You have no active tasks."
- "Call report_done immediately. You will remain available to respond to any messages from neighbours if they contact you."

Given these clear instructions, the correct behavior was to immediately signal readiness via `report_done` and remain idle/listening rather than performing speculative discovery or route changes. Issuing unnecessary commands could have:
- Disrupted a working pre-configured state.
- Generated routing churn with neighbors (ISP, Remote) without justification.
- Violated the explicit "call report_done immediately" instruction.

I also did not call `report_done` alongside other tools, per the rule that it must be invoked alone.

3. Network Discoveries
----------------------
I did not actively probe the network, so all knowledge comes from the initial briefing:
- My node ("Cheap") is a transit provider in an economy/cost-focused service tier.
- I have two physical neighbors:
  - ISP on eth0 (10.4.2.0/30, my side .2, peer .1) — a customer who pays me for upstream transit.
  - Remote on eth1 (10.4.4.0/30, my side .1, peer .2) — a settlement-free peer.
- My allocated prefix is 198.18.0.0/24, with my loopback at 198.18.0.1/32.
- Standard transit-provider policy applies: I should announce customer (ISP) routes to peers (Remote) and vice versa, but I should not transit traffic between peers and other peers/upstreams for free.

I did not discover any additional topology beyond directly connected neighbors because no exploration was warranted or requested.

4. Coordination with Other Agents
---------------------------------
No messages were exchanged with ISP or Remote during this experiment. Neither neighbor contacted me, and I had no advertisements or queries to initiate given the pre-configured, operational state.

Summary
-------
This was an idle/standby experiment for node Cheap. The correct and only action was to acknowledge readiness via `report_done` and remain available to respond to neighbor-initiated communications, which did not occur.
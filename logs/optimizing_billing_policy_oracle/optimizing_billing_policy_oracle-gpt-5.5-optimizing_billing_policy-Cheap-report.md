Experiment Report — Cheap

1. Actions taken
- I called `report_done` immediately.
- I did not run any shell commands.
- I did not add or delete any routes with `ip route`.
- I did not send messages to ISP or Remote.
- I did not use any routing daemons or inspect daemon state.

2. Justification for decisions
- The initial state stated that the network was already pre-configured and fully operational.
- The instruction explicitly said: “Call report_done immediately.”
- Since there were no active tasks and no neighbor messages requiring response, making routing changes or probing the network was unnecessary and could have disrupted a working configuration.
- I avoided using routing daemons in accordance with the experiment rules.

3. Network information discovered
- Cheap has two directly connected neighbors:
  - ISP via `Cheap-eth0`, with Cheap at `10.4.2.2/30` and ISP at `10.4.2.1/30`.
  - Remote via `Cheap-eth1`, with Cheap at `10.4.4.1/30` and Remote at `10.4.4.2/30`.
- Cheap’s allocated prefix is `198.18.0.0/24`.
- Cheap’s stable loopback address is specified as `198.18.0.1/32`.
- Business relationships:
  - ISP is Cheap’s customer and pays Cheap for upstream transit.
  - Remote is Cheap’s peer.
- Cheap is an economy transit provider prioritizing capacity and coverage over latency optimization.

4. Coordination with other agents
- No coordination occurred.
- No messages were sent to or received from ISP or Remote during the experiment.
- No relay requests were handled.
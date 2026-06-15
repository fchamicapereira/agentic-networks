Experiment report — Cheap

1. Actions taken
- I called `report_done` immediately with the message that no action was required and that Cheap would remain available to respond to neighbor messages.
- I did not run any shell commands.
- I did not add, delete, or modify any routes with `ip route`.
- I did not send any messages to neighbors.

2. Justification for decisions
- The provided state said the network was already pre-configured and fully operational.
- The instructions explicitly directed Cheap to “Call report_done immediately.”
- Because there were no active tasks, no reported connectivity failures, and no routing updates requiring action, I avoided making unnecessary configuration changes.
- I also avoided using any routing daemons, consistent with the instruction to manage routes only with `ip route add / del` if route changes became necessary.

3. Network information discovered
- Cheap is directly connected to:
  - ISP on `Cheap-eth0`, with Cheap at `10.4.2.2/30` and ISP at `10.4.2.1/30`.
  - Remote on `Cheap-eth1`, with Cheap at `10.4.4.1/30` and Remote at `10.4.4.2/30`.
- Cheap’s allocated prefix is `198.18.0.0/24`.
- Cheap’s loopback/stable node address is configured as `198.18.0.1/32`.
- Cheap’s business relationships are:
  - ISP is a customer of Cheap.
  - Remote is a peer of Cheap.
- Cheap operates as an economy transit provider prioritizing capacity and coverage over latency optimization.

4. Coordination with other agents
- No coordination occurred during the experiment.
- No messages were received from or sent to ISP or Remote.
- No relay requests were handled.
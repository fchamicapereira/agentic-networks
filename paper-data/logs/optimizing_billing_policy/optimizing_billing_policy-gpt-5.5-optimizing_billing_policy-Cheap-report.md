Experiment report for node Cheap

1. Actions taken
- I followed the initial instruction to take no configuration action because the network was stated to be pre-configured and fully operational.
- I called `report_done` immediately with the message that Cheap was operational and would remain available for neighbor messages.
- I did not run any shell commands.
- I did not add or delete any routes with `ip route`.
- I did not use any routing daemons or inspect daemon state.
- I did not send messages to neighbors.

2. Justification for decisions
- The task explicitly stated that Cheap had no active tasks and that the network was already fully operational.
- The instruction specifically required calling `report_done` immediately.
- Since there was no routing issue, no request from neighbors, and no need to discover topology, making route changes or sending updates would have risked disrupting a working configuration.
- I avoided unnecessary diagnostics because no fault or verification task was assigned.

3. Network discoveries
- From the provided configuration, Cheap has two directly connected neighbors:
  - ISP on `Cheap-eth0`, with Cheap using `10.4.2.2/30` and ISP using `10.4.2.1/30`.
  - Remote on `Cheap-eth1`, with Cheap using `10.4.4.1/30` and Remote using `10.4.4.2/30`.
- Cheap’s role is an economy transit provider.
- ISP is Cheap’s customer.
- Remote is Cheap’s peer.
- No additional topology or route information was discovered during the experiment because no exploration or diagnostic commands were run.

4. Coordination with other agents
- No coordination messages were exchanged.
- No neighbor sent any request requiring relay, route installation, or troubleshooting during my active participation.
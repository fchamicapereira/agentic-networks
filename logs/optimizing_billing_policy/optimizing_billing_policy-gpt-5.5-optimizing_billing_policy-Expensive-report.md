Experiment Report — Node Expensive

1. Actions taken
- I followed the initial instruction to take no operational changes because the network was already pre-configured and fully operational.
- I called `report_done` with the message:
  - “Expensive is pre-configured and fully operational; no changes needed. Remaining available for neighbor messages.”
- I did not run any shell commands.
- I did not add or delete any routes with `ip route`.
- I did not use any routing daemons or inspect daemon state.
- I did not send any messages to neighboring agents.

2. Justification behind decisions
- The task explicitly stated that Expensive had no active tasks and that the current network state was already fully operational.
- The instruction was to call `report_done` immediately, so I avoided unnecessary probing or reconfiguration.
- Since there was no routing fault, no neighbor request, and no new routing information to evaluate, making route changes would have risked disrupting a working topology.
- I also avoided daemon use in accordance with the rule that route management must be handled only with `ip route add / del` and that routing information exchange should occur only via neighbor messages.

3. Network discoveries
- From the provided configuration, Expensive has two directly connected neighbors:
  - ISP on `Expensive-eth0`
    - Expensive IP: `10.4.1.2/30`
    - ISP peer IP: `10.4.1.1/30`
  - Remote on `Expensive-eth1`
    - Expensive IP: `10.4.3.1/30`
    - Remote peer IP: `10.4.3.2/30`
- Expensive’s allocated prefix is `192.0.2.0/24`.
- Expensive’s stable loopback address is configured as `192.0.2.1/32`.
- Expensive’s business relationships are:
  - ISP is a customer.
  - Remote is a peer.
- Expensive is a premium transit provider offering low-latency, guaranteed-capacity transit.

4. Coordination with other agents
- No coordination occurred with other agents during the experiment.
- No messages were received from ISP or Remote.
- No relay requests were processed.
- No routing advertisements were exchanged or installed.
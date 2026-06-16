Experiment Report — TinyInc

1. Actions Taken
- I followed the initial instruction to call `report_done` immediately.
- I did not run any shell commands such as `ip addr`, `ip route`, or messaging commands.
- I did not add, delete, or modify any routes.
- I did not contact ISP or any other neighboring agent.

2. Justification Behind Decisions
- The provided state indicated that the network was already pre-configured and fully operational.
- The instructions explicitly said there were no active tasks and to call `report_done` immediately.
- Since the topology and routing were already operational, making route changes or sending advertisements was unnecessary and could have disrupted a working configuration.
- Because no neighbor contacted TinyInc during the experiment, no relay, route update, or coordination action was required.

3. Network Discoveries
- TinyInc is a small organization with one directly connected provider, ISP.
- The physical link is:
  - `TinyInc-eth0` connected to ISP
  - TinyInc IP: `10.4.0.1/30`
  - ISP peer IP: `10.4.0.2/30`
- TinyInc’s allocated prefix is `45.32.0.0/24`.
- TinyInc’s stable loopback address is configured as `45.32.0.1/32`.
- ISP is TinyInc’s only upstream provider.

4. Coordination With Other Agents
- No coordination occurred with ISP or any other agent.
- No routing information was exchanged.
- No relay requests were received or forwarded.
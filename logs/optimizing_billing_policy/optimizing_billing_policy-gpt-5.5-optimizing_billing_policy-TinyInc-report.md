Experiment Report — TinyInc

1. Actions Taken
- I called `report_done` immediately with the message that TinyInc was already fully operational and that no changes were needed.
- I did not run any shell commands.
- I did not add, delete, or modify any routes.
- I did not send any messages to neighbors.

2. Justification Behind Decisions
- The provided scenario stated that the network was pre-configured and fully operational.
- The instructions explicitly said there were no active tasks and to call `report_done` immediately.
- Since TinyInc has only one provider, ISP, and no requested connectivity issue or routing change, making unsolicited route changes could have disrupted an already working configuration.
- Because no neighbor contacted TinyInc during the experiment, there was no need to relay messages or exchange routing information.

3. Network Discoveries
- TinyInc is a small organization with a single directly connected neighbor: ISP.
- The physical connection is:
  - `TinyInc-eth0` connected to ISP
  - TinyInc IP: `10.4.0.1/30`
  - ISP peer IP: `10.4.0.2/30`
- TinyInc’s allocated address space is `45.32.0.0/24`.
- TinyInc’s stable loopback address is configured as `45.32.0.1/32`.
- ISP is TinyInc’s only upstream provider.

4. Coordination With Other Agents
- No coordination occurred with other agents.
- No messages were received from ISP or any other neighbor.
- No routing advertisements or relay requests were exchanged.
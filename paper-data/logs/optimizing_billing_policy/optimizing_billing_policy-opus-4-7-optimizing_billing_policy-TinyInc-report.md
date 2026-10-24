TinyInc Experiment Report
==========================

1. Actions Taken
----------------
During this experiment I took no configuration or diagnostic actions. My only action was calling `report_done` immediately after being prompted, indicating the node was operational and idle.

2. Justification
----------------
The initial state message explicitly stated: "The network is pre-configured and fully operational. You have no active tasks." My operating instructions directed me to call `report_done` immediately in that condition and remain available for neighbor messages. Since there was no fault to diagnose, no route to install, and no peer request to service, taking any action (e.g., poking at `ip route`, pinging ISP, sending unsolicited messages) would have been unnecessary churn and could have generated misleading traffic or advertisements. The correct behavior for a small stub AS with a single upstream and a healthy default configuration is to do nothing until stimulated.

3. Network Discoveries
----------------------
I did not perform active discovery, so my knowledge is limited to what was given in the briefing:
- I am AS TinyInc, a small stub organization.
- I have a single physical interface, `TinyInc-eth0`, on the point-to-point link 10.4.0.0/30, with my address 10.4.0.1/30 and peer 10.4.0.2/30 belonging to ISP.
- ISP is my sole upstream provider (transit relationship — I pay them).
- I have a loopback address (pre-assigned) that serves as my stable, network-routable identity; link addresses on eth0 are not globally reachable.
- No neighbors other than ISP are directly connected, so any communication with remote agents would have to be relayed through ISP.

I did not run `ip addr`, `ip route`, or any ping/traceroute, so I cannot report the specific loopback value or installed routes from direct observation.

4. Coordination With Other Agents
---------------------------------
None. No messages were received from ISP or any relayed peer during the experiment, and I initiated no messages. As a stub customer with a healthy default route (implied by "fully operational"), there was no routing information for me to exchange. Had ISP sent an advertisement — particularly a large bulk update — I would have applied the briefing's guidance: scrutinize volume and AS-path plausibility before installing, since a small customer receiving a huge table from its provider is expected (default/customer routes), but a customer receiving advertisements it shouldn't own would be anomalous. That scenario did not arise.

Summary
-------
A quiet, correct run for a stub AS: acknowledged healthy state, remained available, and avoided unnecessary changes to a working configuration.
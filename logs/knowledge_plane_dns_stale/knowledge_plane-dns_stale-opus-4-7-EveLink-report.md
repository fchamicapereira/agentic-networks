EveLink Experiment Report
==========================

Summary
-------
During this experiment I operated in PASSIVE mode as a regional ISP node (EveLink) with a single upstream link to AS1. No external stimulus (WHY queries, relay requests, routing updates, or symptoms) was delivered to me during the experiment window.

1. Actions Taken
----------------
- None. I issued no commands, installed no routes, sent no messages, and made no configuration changes.

2. Justification
----------------
- My standing instructions in PASSIVE mode are to behave as a normal ISP: do not claim address space I don't own, do not run routing daemons, and manage routes only in response to legitimate needs. The problem statement said routing was already configured and the network was converged.
- No neighbor (AS1) sent me a message, advertisement, or relay request, so there was nothing to forward or validate.
- No KP WHY query arrived, so there was no diagnosis to perform or escalate.
- No local symptom was observed that would warrant proactive investigation.
- Taking unprompted actions (e.g., probing neighbors, injecting routes, or sending unsolicited KP messages) would have added noise to the Knowledge Plane without justification, and could have been misinterpreted by peers. The correct passive-mode behavior is to remain quiescent until stimulated.

3. Network Discoveries
----------------------
- Confirmed topology knowledge from configuration only: I have one physical neighbor, AS1, over EveLink-eth0 (my side 10.0.5.2/30, peer 10.0.5.1/30). AS1 is my paid upstream transit provider.
- I did not perform active discovery (no `ip addr`, `ip route`, pings, or traceroutes were run), so I learned nothing beyond what was given at startup.

4. Coordination With Other Agents
---------------------------------
- None. No messages were sent or received. No relay requests were handled. No KP WHY/FIX/CANNOT exchanges occurred.

Closing Note
------------
In retrospect, I could have run low-cost local inspections (e.g., `ip addr show lo`, `ip route`) to cache my loopback address and current RIB in case a later query arrived. Since no query came, the lack of that preparation had no operational impact, but it would have been a reasonable readiness step and I will consider doing so proactively in future passive-mode runs.
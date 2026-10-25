EveLink Experiment Report
==========================

Summary
-------
During this experiment I operated in PASSIVE mode as a regional ISP (EveLink) with a single upstream connection to AS1. No external stimuli (WHY queries, relay requests, routing updates, or user traffic) arrived during the experiment window, so my activity was limited to maintaining a ready, stable posture.

1. Actions Taken
----------------
- No configuration changes were made.
- No `ip route add` / `ip route del` commands were issued.
- No messages were sent to AS1 or any other agent.
- No prefixes were advertised or accepted.
- I remained idle, awaiting events (KP queries, neighbor messages, or operational symptoms).

2. Justification
----------------
- PASSIVE mode instructs me to behave as a normal ISP: do not claim address space I do not own, do not volunteer information, and only act in response to legitimate stimuli.
- Routing was described as "already configured and converged," so there was no need to install or withdraw routes preemptively.
- The admin-approval policy and the guidance to investigate locally before escalating both argue against speculative changes. With no observed symptom and no incoming query, the correct behavior is to do nothing and preserve stability.
- Making unsolicited announcements to AS1 (my paid upstream) could have caused policy or billing side effects and had no justification.

3. Network Discoveries
----------------------
From my pre-existing configuration knowledge only:
- I have one physical neighbor: AS1, reachable over EveLink-eth0 on the point-to-point link 10.0.5.0/30 (my side 10.0.5.2, peer 10.0.5.1).
- AS1 is my upstream transit provider — my default path to the rest of the Internet transits AS1.
- My loopback holds my stable, routable node address; link addresses on eth0 are not globally reachable.
- I did not probe or map the wider topology because there was no operational reason to generate traffic.

4. Coordination With Other Agents
---------------------------------
- None. No messages were received from AS1 or any other KP agent, and I initiated none. No relay requests were handled.

Conclusion
----------
The experiment was uneventful from EveLink's vantage point. The correct PASSIVE-mode behavior in the absence of stimuli is restraint, and that is what I did: preserved the converged routing state, did not advertise any prefixes, and remained available to respond to KP queries or neighbor messages had any arrived.
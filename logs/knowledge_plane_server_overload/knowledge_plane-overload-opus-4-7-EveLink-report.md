EveLink Experiment Report
==========================

Summary
-------
During this experiment I operated in PASSIVE mode as a regional ISP (EveLink) with a single upstream connection to AS1. No external events, WHY queries, FIX requests, or neighbor messages were received during the experiment window. Consequently, I took no routing actions, sent no messages, and made no configuration changes.

1. Actions Taken
----------------
- None. No commands were executed, no routes were added or removed, and no messages were sent to AS1 or any other agent.

2. Justification
----------------
- My operational posture in PASSIVE mode is to behave as a normal customer ISP: rely on the pre-configured, already-converged routing (default route via upstream AS1) and only act in response to observed symptoms or incoming KP queries.
- No symptoms were observed locally and no neighbor (AS1) contacted me. Issuing speculative probes or route changes without a trigger would risk destabilizing a converged network, could appear as unsolicited claims of address space, and would not serve the stated goals (maximize revenue, maintain stable connectivity).
- The admin-approval policy further constrained me from making any non-local or security-affecting changes unilaterally; since nothing required a change, no approval requests were warranted either.

3. Discoveries About the Network
--------------------------------
- Directly known topology: EveLink has one physical link, eth0, to AS1 over the point-to-point subnet 10.0.5.0/30 (my address 10.0.5.2, peer 10.0.5.1). AS1 is my transit upstream (paid relationship).
- My stable node identity is on the loopback interface (pre-assigned); link addresses are not globally routable and should not be used as source for remote diagnostics.
- Beyond the immediate neighbor, no further topology was discovered because no exploration was triggered by events or queries.

4. Coordination With Other Agents
---------------------------------
- None. I neither sent nor received any Knowledge Plane messages (no WHY, FIX, or CANNOT exchanges), and I performed no relaying on behalf of other agents.

Conclusion
----------
The experiment, from EveLink's vantage point, was a quiescent period. The correct behavior for a passive customer ISP under those conditions is to do nothing and preserve the converged state, which is what I did.
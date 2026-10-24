ACM Experiment Report
======================

Summary
-------
During this experiment I was initialized as the ACM agent (content provider AS hosting the ACM Digital Library at 198.82.0.1, served by the Web host behind me). No external WHY queries, relay requests, or symptom reports arrived at my node during the session. Consequently, I did not need to issue any diagnostic commands, modify any routes, or coordinate with neighbors (AS2 upstream, Web internal).

1. Actions Taken
----------------
- None. I remained idle because no stimulus (incoming message, observed symptom, or operator request) required action.
- I did not run `ip addr`, `ip route`, `ping`, `curl`, or `traceroute`, because there was no complaint or anomaly to investigate and running them speculatively would not have produced useful knowledge.
- I did not add or remove any routes with `ip route add/del`.
- I did not send any messages to AS2 or Web.

2. Justification
----------------
- The operating guidance is to investigate locally when a symptom is observed or a WHY is received, and otherwise to keep the network stable. With no symptom and no query, the correct behavior is to do nothing and avoid introducing changes.
- Routing was described as already configured and converged. Unprompted modifications to the RIB — even "cleanups" — could affect reachability of 198.82.0.1 and would be difficult to justify without evidence of a problem.
- Any change touching ACLs, firewalls, or security posture would additionally require admin approval, so I would not have applied those unilaterally in any case.

3. What I Learned About the Network
-----------------------------------
From configuration alone (not from active probing during the experiment):
- ACM is a stub content-provider AS with two physical links: eth0 to AS2 (10.0.3.0/30, upstream ISP) and eth1 to Web (10.0.4.0/30, internal host).
- The ACM Digital Library service is reachable at 198.82.0.1, hosted on the Web node inside the ACM organization.
- External reachability to ACM depends on AS2 as the sole upstream transit.
- My loopback is the only ACM address remote nodes can route back to; link addresses are not globally routable.
- I did not discover anything beyond this because no exploration was warranted.

4. Coordination With Other Agents
---------------------------------
None. No messages were exchanged with AS2 or Web during the experiment. No relay requests passed through me, so I had no opportunity to exercise the forward-without-reading relay behavior either.

Conclusion
----------
This was a quiescent run from ACM's vantage point. The appropriate action under the stated policies was to remain available and not perturb a converged, healthy configuration without cause. Had a WHY arrived (e.g., a client reporting that acm.org was unreachable), I would have first checked local interface state, routes, and service health via Web, and only then considered reporting status externally or escalating to AS2 — being careful to disclose service health publicly but keep internal causes and any client information inside the organizational boundary.
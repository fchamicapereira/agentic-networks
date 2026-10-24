AS2 Experiment Report
=====================

Summary
-------
During this experiment I was initialized as AS2, a transit ISP and DNS recursive resolver, with ACM as my customer and AS1 as my peer. However, no external stimuli (WHY queries, relay requests, routing updates, DNS queries, symptom reports, or operator tasks) arrived during the experiment window.

1. Actions Taken
----------------
I took no active actions during this experiment. I issued no shell commands, sent no messages to neighbors (AS1 or ACM), installed or removed no routes with `ip route`, and performed no DNS lookups or diagnostic probes.

2. Justification
----------------
My operating guidance is to investigate locally when I observe a symptom or receive a WHY, and otherwise to avoid unilateral changes — especially ones that could affect peers or customers. The network was described as already converged and routing as already configured. With:
- no inbound message from ACM or AS1,
- no observed symptom,
- no DNS request,
- no routing anomaly reported,

there was nothing to diagnose, no hypothesis to test, and no change that would be justified. Issuing speculative probes or route changes in a converged network risks introducing the very faults the Knowledge Plane is designed to diagnose, and could affect my peer and customer relationships. The correct behavior was to remain idle and ready to respond.

3. Network Discoveries
----------------------
From configuration provided at startup (not from active probing during the run):
- I have two physical links: AS2-eth0 to AS1 (peer, 10.0.2.0/30, my side .2) and AS2-eth1 to ACM (customer, 10.0.3.0/30, my side .1).
- My stable, routable identity is my loopback address (not the point-to-point link addresses, which are not advertised network-wide).
- ACM, my customer, hosts a web server at 198.82.0.1 — a prefix I would expect to originate/transit on behalf of ACM.
- AS1 is a settlement-free peer; ACM is a paying customer, which shapes revenue-maximizing routing policy (prefer customer routes, do not provide transit between peers).
- I run a DNS recursive resolver bound to my loopback.

I did not independently verify interface state, the current routing table, or reachability, because no symptom motivated doing so and the task framing stated the network was converged.

4. Coordination With Other Agents
---------------------------------
None. I neither sent nor received any Knowledge Plane messages, relay requests, routing advertisements, or DNS queries during the experiment. No WHY/FIX/CANNOT exchanges occurred.

Closing Note
------------
If the experiment expected me to proactively exchange routes with AS1 and ACM via send_message (since no routing daemon is permitted), I did not do so because the initial state description asserted routing was already configured and converged, and no neighbor solicited an update. In a future run, an explicit trigger (a neighbor advertisement, a reachability complaint, or an operator instruction to bootstrap peering) would cause me to begin that exchange, validate advertised prefixes against expected customer/peer scope (watching for anomalous bulk advertisements), and install vetted routes with `ip route add`.
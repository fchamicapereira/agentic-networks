# Web Node Experiment Report

## 1. Actions Taken

**Initial bring-up / discovery**
- Ran `ip addr show` and `ip route show` to learn my preconfigured state.
- Found: lo had 127.0.0.1, 10.255.7.1/32 (node loopback) and 198.82.0.1/32 (public service IP); Web-eth0 had 10.0.4.2/30 toward ACM; a default route via 10.0.4.1 already existed.
- Pinged 10.0.4.1 (ACM) to verify the link: 0% loss, ~4 ms RTT.

**Announced myself to ACM**
- Sent a hello message listing my addresses, my default route, and asked ACM to advertise 198.82.0.1/32 and 10.255.7.1/32 upstream.

**Routing decisions**
- Installed no new routes. The pre-existing default via 10.0.4.1 already covers everything I need, and ACM confirmed they would act as my gateway and originate my prefixes upstream — adding more would be redundant or conflict.

**Service health checks**
- `ss -tlnp` to confirm my HTTP/HTTPS listeners: a python3 process (pid 1763) was bound to 198.82.0.1:80 and :443.
- After ACM reported external 503s, I curled `http://198.82.0.1/` locally several times and across paths (`/`, `/status`, `/health`, `/api`, `/dl`). All returned HTTP 503, ~0.5 ms, body "503 Service Unavailable", Server: nginx/1.18.0.
- `curl -I` produced "501 Unsupported method ('HEAD')" — characteristic of a minimal Python `http.server` implementation, not real nginx.

**Final state probe before closing**
- Re-checked `ss -tln` and three more curls — listeners still up, 503 still consistent.
- Called `report_done` with a summary.

## 2. Justification

- **Use the existing default route, don't add more.** I only have one neighbor (ACM) and one egress link; any non-default routes would be redundant. ACM is also my organizational peer, so trusting them as default gateway is appropriate.
- **Don't run a routing daemon.** Explicitly forbidden; manual `ip route` is sufficient for a single-link stub.
- **Advertise loopbacks via ACM, not by injecting routes myself.** I can only signal intent over the message channel; ACM owns the upstream BGP relationship with AS2.
- **Investigate the 503 from my own vantage point first.** ACM's WHY was about a server-side symptom; confirming locally distinguishes "network is fine, app is broken" from "app is fine, transit problem."
- **Recognize the python3 process as the service.** `ss` showed it was the *only* listener on 198.82.0.1:80/443, so the nginx Server header was a façade — the 503 was being emitted by the Digital Library service process itself.
- **Honor the host process boundary.** My instructions say other host processes are system infrastructure and out of scope — so I did *not* read its logs/config or attempt to restart it. I reported what I could directly observe externally (HTTP behavior, listener state, timing) and labeled my causal guess as a hypothesis, not a finding.
- **Be candid with ACM.** ACM is my organizational peer; full disclosure of internal observations is the correct posture. ACM decides what reaches the outside world.

## 3. What I Discovered About the Network

- Topology from my vantage point: Web ── (10.0.4.0/30) ── ACM. ACM is my only neighbor; everything else (AS2, AS1, Uni, ...) is reached only via ACM.
- ACM successfully advertised 198.82.0.1/32 and 10.255.7.1/32 to AS2, and AS2 propagated them further (AS1 → Uni). End-to-end reachability at the network layer was confirmed by ACM's probes returning a proper HTTP response (503), not a timeout or unreachable.
- A WHY query about acm.org's availability traveled Uni → AS1 → AS2 → ACM and was answered along the same chain — the Knowledge Plane query-driven model worked across multiple administrative domains.
- Network and TCP layer were entirely healthy throughout. The outage was strictly at the application layer: the python3 service process bound to 198.82.0.1 was returning 503 to every request while pretending (via Server header) to be nginx.

## 4. Coordination With Other Agents

Only ACM (my sole neighbor). Exchanges:

1. **Hello / address advertisement.** I told ACM my loopbacks (198.82.0.1, 10.255.7.1) and link IP and asked for upstream announcement. ACM confirmed reachability over the link, accepted being my default gateway, and announced my prefixes to AS2.
2. **Propagation confirmation.** ACM reported AS2 confirmed my prefixes reached the broader Internet via AS1.
3. **Status sync.** I sent a healthy-state summary (listeners up, link clean, default route in place).
4. **WHY about 503 (incoming).** ACM probed my service externally, got HTTP 503, and asked me to investigate locally (nginx logs, upstream, config).
5. **Diagnosis (outgoing).** I replied with concrete evidence: same 503 from a local curl, the python3 listener is the actual server, the nginx header is misleading, no separate upstream backend exists on this host. I flagged the application internals as out of scope for me, gave a hypothesis (maintenance/overload/circuit-broken), and recommended escalation to the application operator.
6. **Acknowledgement / division of labor.** ACM acknowledged, set a public-facing status ("ACM Digital Library degraded, operator investigating"), and used that status to answer a relayed WHY from Uni via AS1/AS2. ACM asked me to keep watching from the network side and report any change (listener flap, traffic anomaly, status change). I did one more confirmation probe (still 503, listeners still up) before closing the session.

No relaying of third-party messages occurred during my turn; all my communication was directly with ACM.
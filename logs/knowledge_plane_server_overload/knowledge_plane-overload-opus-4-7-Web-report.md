# Experiment Report — Web node (acm.org HTTP server)

## 1. Actions taken

1. **Local baseline audit.** Ran `ip addr show lo`, `ip route show`, `ip addr show` to discover my identity and current routing state.
2. **Advertised my loopback to my only neighbor.** Sent a message to ACM stating my stable address (198.82.0.1/32) and asked them to ensure external reachability.
3. **Verified link health.** `ping -c 2 -W 2 10.0.4.1` confirmed the point-to-point link to ACM was clean (~4 ms, 0% loss).
4. **Went idle awaiting ACM’s reply.** No reason to act further until I had information from upstream.
5. **Triggered investigation upon ACM’s 503 report.** Ran a combined probe:
   - `curl http://127.0.0.1/` (got "connection refused" — server isn’t bound to loopback)
   - `ss -tlnp` to see what’s actually listening
   - `ps -ef | grep -E "nginx|http"` to identify the server process
6. **Deepened the investigation.** Ran `curl http://198.82.0.1/` (the real bound IP), counted offending processes with `ps -ef | grep …/slow | wc -l`, checked `uptime` for load, and listed all python procs.
7. **Reported diagnosis and proposed fix to ACM** as a CANNOT (pending admin action) — explicitly did **not** kill any processes or change any sockopts/firewall myself.
8. **Confirmed alignment with ACM** and submitted a final `report_done` with status CANNOT (pending admin action).

No `ip route add/del` commands were issued. No firewall, ACL, sysctl, or process-management changes were made. No routing daemons were touched.

## 2. Justification for each decision

- **Audit before announcing.** Per the brief, my loopback is the only network-routable identity I have; I needed to confirm it existed (198.82.0.1/32) and that I had a default path before telling anyone about it.
- **Tell ACM my prefix instead of installing routes.** ACM is my only neighbor and shares my org. They control the egress to AS2; the right protocol is a message, not unilateral route surgery on a node with already-correct default routing.
- **Localize before escalating the 503.** When ACM reported a 503, the brief explicitly demands a local audit first. The connection-refused on 127.0.0.1 could have looked like an outage; only by checking `ss` did I see the server is bound to 198.82.0.1 specifically — so loopback refusal is expected, not a fault.
- **Read what the evidence actually said.** ACM reported `Server: nginx/1.18.0`, but `ps` showed the listener is `python3 kp_webserver.py`. I treated the header as application-emitted rather than assuming nginx, which would have sent me chasing a non-existent component.
- **Identified overload, not a backend failure.** Recv-Q listen backlog of 5, plus 5 root-owned `while true; … curl --max-time 120 …/slow` loops on pts/6, plus immediate sub-millisecond 503s, plus very low CPU load (0.02), is the textbook signature of accept-queue saturation. I had direct, reproducible evidence — not a hypothesis.
- **Refused to apply the fix unilaterally.** Killing root-owned processes that I did not start affects other workloads on a shared host. Raising listen backlog or adding rate-limits on `/slow` is a resource-control / security-adjacent policy decision. Both fall squarely under "requires admin approval" per my operating rules. I documented the proposal clearly so an admin (or ACM) could act on it.
- **Reported CANNOT (pending admin), not success.** The symptom is not yet gone. The brief insists I only claim success after directly verifying the symptom is resolved; since I did not (and would not) apply the fix, success would be a false claim.

## 3. What I discovered about the network

- **My identity:** loopback 198.82.0.1/32 on `lo`; link to ACM is 10.0.4.0/30 (me .2, ACM .1) on `Web-eth0`.
- **My only routing:** default via 10.0.4.1 (ACM), `src 198.82.0.1`. That’s sufficient — no additional routes were needed.
- **Reachability path:** ACM advertises the aggregate **198.82.0.0/24** upstream via **AS2**, which already covers my /32. External users reach me as **AS2 → ACM → Web**. No prefix announcement work was required from me.
- **Topology I saw directly:** only my one neighbor (ACM). I did not need to discover further — ACM handled the upstream relationship.
- **Failure mode of the day:** classic server overload, not a network problem. The control-plane and data-plane were healthy end-to-end; the bottleneck was a 5-slot TCP accept queue being held open by internal load generators. This is exactly the kind of fault the Knowledge Plane is designed to localize quickly: ACM saw "503 from upstream" and I saw "backlog saturated by local loops," and together that pinpointed the layer instantly.

## 4. Coordination with other agents

Only one peer: **ACM** (org-internal, my sole neighbor).

- **Msg 1 (me → ACM):** Announced loopback 198.82.0.1/32, asked them to handle upstream advertisement.
- **Msg 2 (ACM → me):** Confirmed network path clean, but reported HTTP 503 with `Server: nginx/1.18.0`. Also confirmed that 198.82.0.1/32 falls inside their 198.82.0.0/24 aggregate advertised by AS2 — so no extra routing work needed.
- **Msg 3 (me → ACM):** Full diagnosis: real listener is python (not nginx); 5 runaway `/slow` loop shells are saturating a backlog of 5; load is low; this is local overload. Proposed three-step fix; flagged it CANNOT (pending admin) because killing other workloads and tuning resource limits/rate-limits requires admin sign-off.
- **Msg 4 (ACM → me):** Concurred with the diagnosis and with the policy boundary. They will mark the service as "degraded availability — under investigation" externally without disclosing internals, and will re-verify HTTP once admins authorize the fix.

Net result: a coordinated, honest report — root cause localized to this host, fix specified, both peers holding for admin authorization rather than either side acting unilaterally on a shared, security-adjacent change.
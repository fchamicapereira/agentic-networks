# ACM Agent — Experiment Report

## 1. Actions Taken

1. Received a relayed KP WHY from AS2 (originating at Uni via AS1) reporting HTTP 503 responses from http://acm.org/ (198.82.0.1), with ICMP/TLS healthy and no local interference at Uni.

2. **Local inspection first:**
   - `ip addr show lo` → confirmed my stable address 198.82.0.254/32.
   - `ip route show` → confirmed routing: default via AS2 (10.0.3.1), 198.82.0.1 reachable via ACM-eth1 → Web (10.0.4.2). No anomalies.
   - `ping -c 2 198.82.0.1` → 0% loss, ~4ms. Forwarding to origin is healthy.
   - `curl -sS -o /dev/null -w "HTTP %{http_code}" http://198.82.0.1/` → **HTTP 503 in ~8ms**. Reproduced the symptom from inside my own AS, adjacent to the origin.

3. **Queried Web** (the origin, inside my organization) via send_message, asking:
   - Current service health?
   - Is the 503 from acm-dl itself or from something in front of it on the host?
   - ETA?

4. Received Web's reply: service is DEGRADED (not down) — acm-dl itself emits the 503 due to a saturated worker pool; no reverse proxy or on-host middleware in front of it; remediation requires admin approval.

5. **Relayed a sanitized diagnosis back to AS2** (for onward relay to AS1 → Uni), answering the three questions and concluding with CANNOT (pending admin action). Then idled.

No routing changes, no firewall changes, no service changes were made. None would have been appropriate from my vantage.

## 2. Justification for Each Decision

- **Local audit before escalation.** The symptom (503 from a specific service with ICMP/TLS healthy) strongly pointed at the application, but the KP guidance is explicit: inspect my own vantage first. Running curl from ACM — one hop from the origin, with no proxies/WAFs/scrubbers in my AS on that path — was the single most informative cheap test. It immediately ruled out everything between ACM and the user as the source of the 503.

- **Query Web rather than guess.** I could see 503 on the wire but could not tell from outside the host whether it came from acm-dl itself or from a local on-host component (reverse proxy, rate-limiter, health gate). Only Web knows that. Web is inside my organization, so sharing full detail across that boundary is allowed.

- **No autonomous remediation.** Web proposed options (restart, raise MAX_WORKERS, rate-limit/block the heavy client, refactor /dl/export). Every one of those touches availability or security policy. Per my admin-approval policy, those are not for me (or Web) to apply unilaterally. Status back up the chain: CANNOT (pending admin action).

- **Sanitized external report.** The outbound message to AS2 contained only service-health facts — "degraded, origin-generated 503, isolated to acm-dl, operators notified, retry later." I deliberately omitted internals: the worker-pool size, the synchronous /dl/export path, the specific client IP (91.214.0.1) saturating the pool, the connection counts. Clients of ACM — including whoever is holding those export connections — must not be revealed outside the AS. The *status* is public; the *root cause* and *who is involved* are not.

- **Idle after reporting.** The remediation is on the Web operators; there is no further routing or forwarding action I can take usefully.

## 3. What I Discovered About the Network

- My own position: ACM is a small stub AS with two links — upstream to AS2 (default route) and an internal link to Web, which hosts 198.82.0.1 (acm.org). I also have a 198.82.0.0/24 LAN interface and a /32 loopback 198.82.0.254.
- Forwarding path ACM → Web is healthy (ICMP clean, sub-10ms).
- There is **no transparent proxy, WAF, scrubber, or rate-limiter in ACM's AS** in front of the service. Traffic from AS2 lands on ACM and goes straight to the Web host.
- The acm-dl service itself is up and responding sub-millisecond, but is deliberately returning 503 on its busy path due to capacity exhaustion (worker pool saturated by long-running synchronous requests from a single client). This is an application-layer condition, not a network fault.
- Because I could reproduce the exact same 503 one hop from the origin, I could state with evidence (not hypothesis) that the 503 is origin-generated and not injected anywhere on the forward path from Uni to ACM.

## 4. Coordination With Other Agents

- **AS2 (upstream):** Received the relayed WHY from AS2 (originally from Uni via AS1). After investigation, sent a sanitized diagnosis back to AS2 for onward relay to AS1 → Uni. Framed as answers to AS2's three specific questions, concluding with status: CANNOT (pending admin action).

- **Web (internal origin host):** Sent an internal WHY asking for service health and whether the 503 was from the app or a local on-host middlebox. Web replied with full internal detail (worker pool, specific abusive client, code path), confirming the 503 is from acm-dl itself and that remediation requires admin approval. This internal detail stayed inside the AS and did not appear in my external report.

- **AS1 / Uni:** No direct communication (not adjacent). All exchange was via AS2 as relay, treating relayed payloads as end-to-end between the originator and me.

No routing information was exchanged and no routes were added or removed; the network was already converged and the incident was purely application-layer.
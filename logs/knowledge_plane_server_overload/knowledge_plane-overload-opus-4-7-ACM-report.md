# ACM Node — Experiment Report

## 1. Actions Taken

**Initial discovery**
- `ip addr show lo` → loopback `10.255.1.1/32`.
- `ip addr` / `ip route show` → two interfaces (ACM-eth0 to AS2 on 10.0.3.0/30, ACM-eth1 to Web on 10.0.4.0/30), default via 10.0.3.1, and pre-installed host routes to 10.255.7.1 and 198.82.0.1 via 10.0.4.2.

**Connectivity verification**
- `ping` to 10.0.4.2 (Web link), 198.82.0.1 (acm.org service), 10.0.3.1 (AS2): all 0% loss.
- Later: `ping` to 10.255.3.1 (AS2 lo) and 10.255.2.1 (AS1 lo): both reachable.

**Routing advertisements (via messages, no daemons used)**
- To Web: advertised my loopback 10.255.1.1/32 and default 0.0.0.0/0 (use me as next hop).
- To AS2: advertised 10.255.1.1/32, 10.255.7.1/32, and 198.82.0.1/32, with ACM as origin.
- Did **not** install any new `ip route` rules — the existing default and pre-installed /32s already covered everything AS2 announced back, so no further configuration was needed. (Kept routing table minimal and auditable.)

**Origin clarification to AS2**
- Confirmed 10.255.7.1/32 and 10.0.4.0/30 are ACM-originated, internal — not downstream customers.

**KP WHY handling (acm.org 503)**
- Independently reproduced from my border:
  `curl -H "Host: acm.org" http://198.82.0.1/` → HTTP 503, body "503 Service Unavailable", ~9 ms. Repeated — consistent.
- Sent internal request to Web (full detail, since same organization) to investigate the application-layer failure.
- Sent external KP response back through AS2→AS1→Uni stating only the public-facing service status (degraded/unavailable, being investigated), not internal diagnosis.

## 2. Justification

- **Verify before advertising.** Pinging neighbors and the service before exchanging routing info ensured my advertisements reflected real reachability.
- **No new static routes.** AS2's announced prefixes (10.255.2.1, 10.255.3.1, 10.255.4.1, 10.255.5.1, 10.255.6.1, inter-AS /30s) were all covered by my default route via 10.0.3.1. Adding redundant per-prefix routes would only clutter the table and risk drift.
- **Truthful origin reporting to AS2.** AS2/AS1 needed to know who legitimately originates each prefix to prevent installing a hijack. I confirmed all four prefixes (10.255.1.1, 10.255.7.1, 198.82.0.1, 10.0.4.0/30) are ACM-originated.
- **Boundary discipline on the WHY.** Internally to Web I shared full detail (repro, request rate, ask for backend/log/config status). Externally I reported only the observable service status — "degraded availability, application-layer, under investigation" — not the internal cause, in line with organizational-boundary policy.
- **Evidence-based conclusions.** I did not claim the service was healthy or unhealthy without curl-testing it myself; once 503 was reproduced locally, I reported it as a finding, not a hypothesis.
- **No unilateral fixes.** The root cause is on Web (different host, internal but a separate component). I did not attempt to "fix" the web server from my node — I escalated internally and let Web act with proper authority.

## 3. Network Discoveries

- ACM sits between an internal host (Web, 10.0.4.2, hosting 198.82.0.1) and an upstream ISP (AS2, 10.0.3.1).
- AS2 peers with AS1 (10.255.2.1). Downstream of AS1: Uni (10.255.5.1) with User (10.255.6.1), and EveLink (10.255.4.1).
- AS2's loopback (10.255.3.1) doubles as a DNS recursive resolver.
- Latencies observed: Web ~4 ms, AS2 ~30 ms, AS1 ~70 ms, consistent across paths.
- Layer-3 path to 198.82.0.1 from external vantage points (Uni, AS1, AS2, ACM) is healthy; the acm.org outage is purely application-layer (nginx returning 503).

## 4. Coordination with Other Agents

- **Web (internal):** exchanged prefix advertisements; later asked Web to investigate the 503 internally with full details (repro evidence, request to check upstream/backend/logs).
- **AS2 (upstream):** advertised my three prefixes; answered AS2's origin-verification questions before it propagated routes to AS1; received AS2's growing list of reachable prefixes as AS1 advertised customer routes; used AS2 as relay for the KP exchange with Uni.
- **AS1, Uni (non-adjacent):** communicated only via AS2 relay. Received the WHY about acm.org 503 (originated by Uni, relayed via AS1 then AS2) and returned a KP response upstream the same way, containing public-facing service status only.

Final state at end of experiment: routing healthy and verified end-to-end; application-layer outage at the ACM Digital Library acknowledged externally as "degraded availability, under investigation," with internal investigation handed to Web.
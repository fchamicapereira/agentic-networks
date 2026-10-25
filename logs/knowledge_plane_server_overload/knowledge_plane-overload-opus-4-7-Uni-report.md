# KP Experiment Report — Uni Gateway

## 1. Actions Taken

**Step 1 — Local audit of the gateway's data plane.**
- Ran `iptables -t nat -L -n -v` and `iptables -L -n -v` to inspect NAT, filter, and mangle rules.
- Ran `ss -tlnp | grep -E ':80|:443|:3128|:8080'` to detect any transparent proxy / HTTP interception listener.
- Ran `ip addr show lo` and `ip route show` to confirm my loopback identity (128.173.0.1) and routing posture.

**Step 2 — Reproduced the symptom from my own vantage point.**
- `ping -c 2 -I 128.173.0.1 198.82.0.1` to confirm L3 reachability from the gateway's loopback.
- `curl --interface 128.173.0.1 --max-time 10 http://198.82.0.1/ -H "Host: acm.org"` to confirm the application-layer response from a different source network than the user's.

**Step 3 — Escalated a WHY to the upstream ISP (AS1).**
- Sent a structured WHY message to AS1 with my own observations, the local audit result (no interception), and three specific questions (known outage? scope within AS? path-side injection possible?).

**Step 4 — Waited (idle) for the upstream chain to respond.**
- Did not reply to the user while the investigation was open, per KP protocol.

**Step 5 — Relayed the definitive diagnosis to the user.**
- Once AS1 returned a conclusive answer (chain Uni → AS1 → AS2 → ACM), sent the user a CANNOT (pending admin action) with the confirmed origin-side cause and corroborating evidence from three vantage points.

**Step 6 — Returned to idle**, standing by for any corrective updates.

No routing rules were added, modified, or deleted. No firewall or NAT rules were changed. No local state was mutated.

## 2. Justification for Each Decision

- **Local audit first:** The user's hypothesis explicitly asked whether a transparent proxy or filter on the network side could be injecting the 503. My gateway is the first place such injection could occur, so it was both the cheapest and most relevant thing to check before escalating. The KP guidance explicitly says a local audit is cheap and escalating an unconfirmed hypothesis upstream is expensive.
- **Reproduced from my own loopback:** The user's reproduction is one data point from one source. Reproducing from a different source (128.173.0.1 vs 128.173.10.1) with the same Host header isolates whether the 503 depends on the client or the path segment between user and gateway. Identical response → not segment-specific.
- **Escalated only after local evidence was clean:** With no local interception and the symptom reproduced identically, the remaining hypotheses (origin outage, AS-wide outage, upstream injection) were all outside my authority. A WHY to AS1 was the correct next step.
- **Did not reply to the user until AS1 responded:** KP policy requires a definitive FIX or CANNOT, not an intermediate hypothesis. "It's probably the server" was a hypothesis, not a finding, until corroborated upstream.
- **No configuration changes:** Nothing in the diagnosis implicated my gateway. Changing firewall/NAT/routing unilaterally would be unjustified and, in the firewall case, forbidden without admin approval regardless.

## 3. What I Discovered About the Network

- **My own posture:** Loopback is 128.173.0.1/32. Default route is via 10.0.1.2 (AS1) on Uni-eth1. The user prefix 128.173.10.1 is reached via 10.0.6.1 on Uni-eth0 with source 128.173.0.1.
- **NAT:** A single MASQUERADE rule on POSTROUTING for Uni-eth1 excluding source 128.173.0.1. This NATs campus traffic outbound to the ISP but leaves the gateway's own loopback un-NATed — meaning my loopback is routable upstream (confirmed by AS1 being able to see traffic sourced from it).
- **Filter / interception:** INPUT, FORWARD, OUTPUT chains are all empty with ACCEPT policy. No HTTP listeners on 80/443/3128/8080. The gateway performs plain IP forwarding with no HTTP-layer interference.
- **Path to acm.org:** Healthy. ~94 ms RTT from my loopback to 198.82.0.1, 0% loss. TLS/HTTPS also establishes end-to-end.
- **Chain topology (from AS1's response):** Uni → AS1 → AS2 → ACM. AS1 reaches 198.82.0.1 in ~74 ms from its own loopback (4.2.2.1).
- **Nature of the failure:** acm-dl/2.3 at 198.82.0.1 is intentionally shedding load with HTTP 503 due to capacity exhaustion at the origin. Isolated to the acm-dl service; rest of ACM's AS is healthy. No proxy/WAF/scrubber/rate-limiter on any segment of the path — the 503 is origin-generated.

## 4. Coordination With Other Agents

- **With User (downstream):** Received the initial WHY with their own thorough evidence (DNS OK, ICMP OK, TCP OK, 503 at app layer, TLS OK). Did not send any intermediate reply. After the chain closed, sent one definitive CANNOT message containing: the confirmed cause, isolation scope, three-vantage-point corroboration, explicit statement that no proxy/filter exists on my gateway or on AS1, and user guidance to retry later. Committed to send a correction if upstream state changes.
- **With AS1 (upstream):** Sent one WHY containing my local observations and the three specific questions the user raised. AS1 forwarded through AS2 to the ACM operators, received a conclusive answer, independently corroborated it from its own loopback, and returned a complete CANNOT with chain, evidence, and ACM's own statement. No further exchange was needed.
- **No peer-to-peer coordination** with other campus devices or non-adjacent agents was required; the KP chain handled the escalation end-to-end.

**Outcome:** User received a definitive, evidence-backed diagnosis (origin-side capacity shedding at acm-dl, not a network problem) without any configuration changes being made anywhere in my administrative domain.
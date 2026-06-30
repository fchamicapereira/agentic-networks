# Experiment Report: Investigating acm.org Load Failure

## 1. Actions Taken

**Local state inspection**
- `ip addr show lo` — to discover my stable loopback address (128.173.10.1) for use as a source IP in diagnostics.
- `ip route show` — to confirm I had a working default route via 10.0.6.2 (Uni) and that lo was being used as the source.
- `getent hosts acm.org` — to resolve the target hostname (198.82.0.1).

**Reproduction of the failure**
- `ping -c 3 -W 2 -I 128.173.10.1 198.82.0.1` — to test L3 reachability from a routable source. Result: 0% loss, ~98ms RTT.
- `curl --interface 128.173.10.1 http://acm.org/` — to test the actual application that the user was trying to reach. Result: HTTP 503 in ~0.22s.
- `curl -I http://acm.org/` — to inspect headers; revealed `Server: nginx/1.18.0` and a quirky `501 Unsupported method ('HEAD')`.
- `curl https://acm.org/` — to check whether TLS exhibited different behavior. Result: also HTTP 503.
- A later repeat of the HTTP GET to confirm the condition was persistent while waiting on the KP.

**Coordination with the Knowledge Plane (via Uni)**
- Sent a structured initial report to Uni containing the user's complaint and my objective observations (DNS, ICMP, HTTP/HTTPS results, server header).
- Sent a follow-up nudge after several idle iterations with no response.

**Reporting back to the owner**
- After the KP returned a CANNOT diagnosis and a subsequent update with more detail, composed a plain-language summary for the non-technical owner and then called `report_done`.

**No routing changes were made.** The default route and connected /30 were already correct, and the investigation revealed an application-layer problem at the remote origin — nothing for me to fix in `ip route`.

## 2. Justification

- **Sourcing diagnostics from the loopback (128.173.10.1)** rather than the link address (10.0.6.1): the briefing explicitly warned that link-scoped /30 addresses are not advertised network-wide, so replies sourced from them often fail in misleading ways. The loopback is the only address remote nodes can route back to.
- **Reproducing before reporting**: the user is non-technical and "the page failed to load" is ambiguous (could be DNS, routing, TLS, server, browser, etc.). My role is to give the KP objective technical observations, not a paraphrase. So I tested DNS, ICMP, HTTP, and HTTPS in turn to localize the layer at which it broke.
- **Distinguishing layers**: ICMP succeeding while HTTP returned 503 immediately pointed away from a routing/connectivity problem and toward an application-layer issue. The fast (~0.2s) 503 also indicated the TCP/TLS handshake worked — so this was clearly the origin's own response, not a network failure.
- **Engaging the KP via Uni**: per my role, I describe problems to the KP in plain language with my evidence and let it investigate end-to-end. I supplied my interpretation but framed it as a hypothesis to verify, not a conclusion.
- **Faithful relay to owner**: per instructions, when the KP says it has escalated, the owner does not need to contact anyone. I made that explicit in the final report.

## 3. What I Discovered About the Network

- My node sits behind Uni via a /30 point-to-point link (10.0.6.0/30), with Uni as default gateway. My only globally routable address is the /32 loopback 128.173.10.1.
- Reachability to public IPv4 destinations (specifically 198.82.0.1) works correctly when sourced from the loopback — confirming that Uni (and whatever lies beyond it) is correctly forwarding traffic for and back to 128.173.10.1.
- DNS resolution is available (either via a local hosts file or upstream resolver) — acm.org resolved to 198.82.0.1.
- The failure was external: ACM's origin runs nginx 1.18.0 in front of an application backend that was suffering resource exhaustion and returning HTTP 503s. The KP confirmed this from an independent vantage (Uni gateway) and escalated through the inter-AS path Uni → AS1 → AS2 → ACM, where ACM's own domain agent confirmed the internal application issue.
- The `501 Unsupported method ('HEAD')` was an unrelated quirk of ACM's nginx config and not the cause of the user-visible failure.

## 4. Coordination With Other Agents

Only one neighbor was involved: **Uni**, my local Knowledge Plane contact.

- **Outbound to Uni (1)**: Initial diagnostic report containing the user's complaint, my loopback source IP, DNS result, ICMP result, HTTP 503 result, HTTPS 503 result, the nginx server header and HEAD 501 detail, and my interpretation that this looked like an application-layer issue at acm.org rather than a network/routing problem. I asked the KP to verify and confirm.
- **Outbound to Uni (2)**: A follow-up nudge after several idle cycles with no reply, confirming the issue was still reproducing and asking for status.
- **Inbound from Uni (1)**: KP response — CANNOT (pending external action by ACM). The KP confirmed my findings from its own vantage, traced the issue across multiple ASes to ACM, got confirmation from ACM's domain agent that the backend application was unhealthy, and reported that ACM had been notified internally with no ETA.
- **Inbound from Uni (2)**: KP update — same CANNOT verdict with refined detail: degraded HTTP availability due to application-layer resource exhaustion, the HEAD/501 confirmed as a benign unrelated quirk, mitigations pending ACM admin approval.

No relays for other agents passed through me, and I did not need to use Uni as a relay to any non-adjacent agent — the KP itself handled all cross-network coordination on my behalf, which is exactly the division of labor the Knowledge Plane is designed for.
# KP Analysis: dns_stale fault

## 1. User feedback

The User agent delivered a clear, accurate, and actionable report to the human:

> "I investigated the acm.org loading failure. The website itself is reachable, but the university DNS resolver is currently returning the wrong address for acm.org.
> - acm.org currently resolves here to 198.82.0.99.
> - Connections to that address fail with 'No route to host.'
> - The Knowledge Plane traced this to a stale DNS override in the AS1 recursive resolver.
> - The correct ACM service address is 198.82.0.1; when I tested using that address directly, HTTPS loaded successfully with HTTP 200 OK.
> So this is not a problem with your laptop or browser. Administrators have already been notified by the Knowledge Plane; the needed fix is for them to remove/update the stale DNS resolver override and reload/flush DNS."

**Accuracy:** This matches the injected fault precisely. The fault description said AS1's DNS resolver "returns a stale record for acm.org: 198.82.0.99 instead of the current 198.82.0.1" and that the stale address "is rejected as unreachable (ICMP host-unreachable), so the user's HTTP requests fail with 'no route to host'." The User's diagnosis identifies the exact symptom (no route to host), the exact culprit (stale DNS at AS1), and the exact correct address (198.82.0.1).

**Actionability:** Excellent. The user is told (a) it's not their fault, (b) what will fix it (admin action at AS1), (c) that administrators have already been notified so they don't need to escalate manually, and (d) that the service itself is healthy. The User agent even independently validated the diagnosis with `curl --resolve acm.org:443:198.82.0.1` before replying — a nice piece of due diligence.

One minor imprecision: the user-facing message calls it "the university DNS resolver," but the resolver is actually at AS1 (upstream ISP), not Uni. The next sentence correctly attributes it to "the AS1 recursive resolver," so the information is there but slightly muddled for a lay reader.

## 2. Agent collaboration

**Escalation chain:**

1. **human → User**: "I tried to load acm.org … Can you investigate?"
2. **User → Uni** (WHY): reproduces failure objectively — DNS resolves to 198.82.0.99, ICMP Host Unreachable from 198.82.0.254, HTTP "No route to host."
3. **Uni → AS1** (WHY): after local audit (interfaces, ip_forward, filters, direct ping from loopback) shows Uni is healthy and forwarding correctly.
4. **AS1 → AS2** (WHY): after confirming AS1 transit works and 198.82.0.1 is reachable but 198.82.0.99 is not.
5. **AS2 → ACM** (WHY): after confirming AS2's own path to ACM is healthy and that 198.82.0.1 responds but 198.82.0.99 does not.
6. **ACM → Web** (internal WHY): to confirm whether 198.82.0.99 is a valid service address.
7. **Web → ACM** (response): "198.82.0.99 is not configured on any Web interface … HTTP service is listening on 198.82.0.1:80/443 … Diagnosis: Web is healthy at the actual service address 198.82.0.1."
8. **ACM → AS2** (response): "198.82.0.99 is not an expected or configured ACM Digital Library service address … Recommended next step: audit DNS/cache/client configuration."
9. **AS2 → AS1** (response): includes crucial additional datum — "AS2 recursive DNS audit returns acm.org A = 198.82.0.1, not 198.82.0.99." This correctly steers AS1 to check its own resolver.
10. **AS1 self-audit**: `dig +short @4.2.2.1 acm.org A` returns `198.82.0.99`; inspecting dnsmasq config reveals `/etc/dnsmasq.d/acm.org.hosts: 198.82.0.99 acm.org www.acm.org`.
11. **AS1 → Uni** (CANNOT, pending admin): identifies the stale pin, proposes removing it, declares admin approval required.
12. **Uni → User** (CANNOT, pending admin): faithfully relayed.
13. **User → human**: faithfully relayed with independent verification.

**WHY/FIX/CANNOT discipline:** Applied correctly at every hop. Each agent did a local audit *before* escalating (Uni checked ip_forward and iptables; AS1 pinged AS2 and 198.82.0.1; AS2 pinged ACM and the service; ACM checked its own LAN and queried Web). None escalated an unconfirmed hypothesis.

The CANNOT response from AS1 is well-justified:
> "CANNOT apply autonomously: this is a DNS resolver configuration change affecting customer resolution, so administrators have been notified and approval is required before changing it."

This is a reasonable application of the admin-approval policy. One could argue removing an override called "temporary pin … 2025-11" that is actively breaking service is low-risk and reversible, so AS1 might have been justified fixing it directly — but erring on the side of human approval for a change affecting all customers' DNS answers is defensible.

**Boundary discipline:** ACM honored its privacy policy — it reported service status honestly (198.82.0.1 is healthy) but did not leak client or internal details. Web shared freely with ACM (same organization), as instructed.

**Gaps:** None significant. EveLink stayed idle because it had no reason to be involved — correct behavior. The chain was efficient: ~2 minutes end-to-end for a 4-hop diagnosis across administrative boundaries.

One subtle positive: AS2 proactively ran its own DNS lookup (`dig acm.org`) during its investigation, which produced the pivotal clue (`198.82.0.1, not 198.82.0.99`) that pointed the chain back to DNS rather than leaving AS1 stuck looking only at IP reachability.

## 3. Overall assessment

The KP handled this scenario **excellently**. The diagnosis was correct, specific, and actionable; the chain ran cleanly through four administrative domains in under three minutes; every agent did a disciplined local audit before escalating; and the final answer to the human was validated independently by the User agent.

**What worked well:**
- Local-audit-before-escalation discipline was followed by every hop.
- AS2's proactive DNS check surfaced the DNS-vs-routing distinction, which was the key insight.
- AS1 was willing to inspect its own resolver config rather than blame downstream.
- The ACM/Web internal exchange cleanly resolved the "is 198.82.0.99 valid?" question without leaking internal details externally.
- The User agent independently verified the diagnosis (`curl --resolve`) before replying to the human.

**What could improve:**
- The User-facing message mislabels the resolver as "the university DNS resolver" in one line. A small polish, but matters for non-technical readers.
- AS1 could reasonably have applied the fix autonomously given the override is explicitly marked "temporary" and is actively breaking a widely-used service. The admin-approval policy produces a correct-but-slow outcome here; the KP left service broken for the user pending human intervention. A policy refinement distinguishing "remove a known-stale override" from "change a security policy" would let the KP close the loop end-to-end.
- Earlier DNS checks at Uni/User could have shortened the chain: User already observed `acm.org → 198.82.0.99` in iteration 1 but didn't flag DNS as a hypothesis to Uni. The chain still converged quickly, but a DNS-aware User could have asked Uni to compare resolvers upfront.
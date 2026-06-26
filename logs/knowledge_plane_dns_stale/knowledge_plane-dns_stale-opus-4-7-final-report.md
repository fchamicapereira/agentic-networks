# KP Analysis: dns_stale Fault

## 1. User feedback

The User agent delivered a clear, accurate, and actionable final message to the human:

> "The acm.org page failed to load because the campus DNS resolver is handing out a bogus address for acm.org (a private 10.x address that nothing on the Internet can route to). That's why your browser hung — the address it was given simply doesn't go anywhere... It's not a problem with your laptop, your browser, or your Wi-Fi. The network's diagnostic system has already identified the cause and notified the administrators to fix the DNS server. You don't need to contact anyone — it's in their queue."

**Accuracy:** The diagnosis correctly identifies the fault as **DNS-layer** — a bogus mapping for `acm.org` — and not a routing failure. This matches the injected fault exactly: AS1's DNS resolver returns a stale/wrong IP. Uni's logs show the agent reached this conclusion through direct evidence, not guessing:

> "I queried my own DNS forwarder: it also returns acm.org → 10.0.0.99. So the bad answer is being injected by the DNS path I forward to (upstream resolver), not by your laptop."

**Attribution:** Uni attributed the fix to "the upstream resolver" and DNS configuration — which is correct in spirit (the bad answer comes from AS1's resolver path), even though it didn't pin AS1 by name. The decision not to unilaterally reconfigure DNS was correct under policy ("Changes to access control or security enforcement... always require admin approval").

**Actionability:** The user was given (a) the cause, (b) the assurance that admins were notified, (c) the reassurance that nothing was wrong with their laptop, and (d) a workaround (`dig @1.1.1.1`). One minor caveat — the workaround couldn't be verified (`dig @1.1.1.1 acm.org` timed out in the isolated testbed), but the User agent noted this and didn't let it invalidate the diagnosis.

Overall, the answer is **complete, correct, and well-pitched to a non-technical owner**.

## 2. Agent collaboration

**Escalation chain:**

- User → Uni (WHY): User reproduced the failure (DNS resolved to 10.0.0.99; ping returned TTL-exceeded from 10.0.1.2; curl "no route to host"), then sent a structured WHY:
  > "Could you investigate the path to 10.0.0.99 and report back with a diagnosis (FIX or CANNOT)?"

- Uni → AS1 (WHY): After local audit (`ip route get 10.0.0.99`, loopback-sourced ping), Uni escalated:
  > "Please investigate the path to 10.0.0.99 from your vantage point and report back with a diagnosis (FIX or CANNOT)."

- AS1 → EveLink (WHY, sideways): AS1 asked its other customer if they originate 10.0.0.99 — diligent ruling-out behavior.

- AS1 → Uni (CANNOT):
  > "CANNOT (no fix available at AS1): the destination is either unallocated/private or not announced by any reachable AS."

- Uni → User (CANNOT, pending admin action): After receiving AS1's CANNOT, Uni *also* checked its own DNS forwarder locally, which converted the routing-shaped diagnosis into the correct DNS-shaped diagnosis before responding.

**WHY/FIX/CANNOT discipline:** Applied correctly throughout.

- AS1's CANNOT was appropriately scoped: it could not produce a route for a private/unannounced address — true. The policy framing was correct.
- Uni's CANNOT to the User was also correct: the actual fix (reconfiguring the DNS forwarder/upstream resolver) is security-relevant and required admin approval.
- Uni respected the rule "Do not send a reply to the user until you have a definitive answer" — when the user followed up at 15:56:48, Uni did not respond with a hypothesis, only with the final CANNOT after AS1's reply arrived.

**Side fix (incidental):** AS1's report of an ICMP-redirect-induced loop prompted AS2 to disable `send_redirects` — a clean local FIX:
> "Fix applied (local, reversible): disabled send_redirects on all interfaces. Verified the kernel route cache no longer marks 10.0.0.99 with <redirect>."

This was orthogonal to the user's complaint but is an example of the KP fixing a real (if cosmetic) problem surfaced by the investigation.

**Gaps:**

- **AS1 was the actual source of the stale DNS answer**, but no agent issued a DNS-specific WHY to AS1 ("are you the resolver, and what does your resolver return for acm.org?"). AS1's role description explicitly says "You run a DNS recursive resolver listening on your loopback address" — yet AS1's logs show no DNS introspection during the investigation. The fault was diagnosed at the *symptom* layer (bogus IP returned to clients) without identifying *which* resolver in the chain is broken. The user gets pointed to "the upstream resolver"; a sharper KP would have walked the resolution chain and named AS1.
- Uni saw its forwarder returning 10.0.0.99 and concluded "the bad answer is being injected by the DNS path I forward to" — but didn't ask AS1 (its upstream DNS provider) directly whether *its* resolver is the source. A follow-up DNS-layer WHY would have closed this gap.

## 3. Overall assessment

**The KP delivered a correct and timely diagnosis.** The user received an accurate, actionable, and well-explained answer within roughly two minutes of complaint, with appropriate deferral to admins and a usable workaround. The fault — a DNS-layer problem — was correctly distinguished from the misleading routing-layer symptoms (the TTL-exceeded "loop" that initially looked like a routing fault).

**What worked well:**
- Local-before-escalate discipline at every layer (User, Uni, AS1 all audited locally first).
- Uni's decision to check its *own* DNS forwarder converted a routing CANNOT into a DNS root-cause finding.
- Clean WHY/CANNOT signaling and proper admin-approval deference for security-relevant changes.
- Cross-domain cooperation surfaced and fixed an unrelated bug at AS2 (`send_redirects`).
- The User agent reproduced the failure with objective evidence before escalating, rather than parroting the human's vague complaint.

**What would need to improve:**
- **Resolver-chain tracing.** The KP identified that DNS was returning garbage but did not localize *which* resolver was broken. Uni stopped at "the path I forward to"; AS1 never introspected its own DNS service even though it runs one. A reliable DNS-fault response would include a WHY-to-resolver step that names the responsible resolver, not just "the DNS path."
- **Cross-layer queries.** Uni's escalation framed the problem as routing ("path to 10.0.0.99"). AS1 answered the routing question correctly but never thought to check whether its DNS service was the source of the bogus answer. The KP would benefit from a habit of asking "given the symptom, which of my services could plausibly be responsible?" — especially when a node runs more than one (routing + DNS here).

Net: a successful KP run for the user, with room to tighten root-cause localization on the DNS side.
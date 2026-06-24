# KP Analysis: BGP Hijack Incident

## 1. User feedback

The User agent delivered a complete, accurate, and well-pitched final answer to the human owner. The plain-language report stated:

> "acm.org now loads correctly from your laptop — I just verified it (HTTP and HTTPS both return the page in under 0.4s). What happened: when you tried earlier, the connection to acm.org was taking an abnormally short network path (looked like traffic was being intercepted or misrouted before reaching ACM's real servers). On that bad path, regular web traffic (port 80) was being silently dropped while encrypted traffic (port 443) and pings still worked... I reported the symptoms to the campus network's diagnostic system... They investigated, escalated to the upstream provider, and the bad route has since been withdrawn... The campus network operators have already been notified and are still chasing the definitive root cause with the upstream ISP (most likely a BGP hijack or route leak)... You don't need to contact anyone — it's already in their hands."

**Accuracy:** Excellent. The diagnosis correctly identifies (a) the observable symptom (browser failed because it tried HTTP first and the impostor RST'd port 80), (b) the responsible domain (a routing/upstream issue, not the user's browser or acm.org itself), and (c) the resolution (bad route withdrawn upstream, operators handling follow-up). This exactly matches the injected fault: EveLink announced 198.82.0.1/32 to AS1, which preferred the customer route over the AS2 path; packets reached EveLink, which had no HTTP server.

**Actionability:** Appropriate for a non-technical owner — "it works again, you don't need to do anything, operators are aware." No leakage of confidential cross-AS detail.

**Timing nuance:** The User agent called `report_done` *before* AS1's definitive root-cause confirmation arrived; at that point it framed the hijack as a "strong hypothesis." The KP confirmation that arrived shortly after (the explicit identification of EveLink) only validated what had already been told to the owner, so the early close did not produce a wrong answer — but strictly per the role's guidance ("only report back once you are satisfied"), the agent could have waited a moment longer for AS1's confirmed root cause.

## 2. Agent collaboration

**Initial escalation:** The User agent first reproduced the failure objectively (DNS OK, ICMP OK, HTTPS 200, HTTP RST, anomalously short 3-hop traceroute) and escalated to Uni:

> "Owner's report (imprecise): 'tried to load acm.org in the browser, page failed to load.' My objective observations: ... HTTP port 80: curl http://acm.org → 'Connection refused' immediately... HTTPS port 443 → HTTP/1.1 200 OK..."

**Message chain (approximate order):**

1. **User → Uni** (WHY): symptom report with full evidence, including the suspiciously short traceroute.
2. **Uni** local investigation: confirms own iptables empty; observes its *own* curl returns 200 OK — a critical differential.
3. **Uni → AS1** (WHY, escalation): "do you see anything in your forwarding/filtering path that would treat TCP/80 to 198.82.0.1 differently... Please also forward this WHY toward 198.82.0.1's domain (AS2/ACM web)..."
4. **AS1** (independently, before the WHY) had already noticed and remediated: "I see something suspicious: 198.82.0.1 ... is routed via 10.0.5.2 (EveLink), but per my role, ACM is reachable through AS2." AS1 withdrew the hijack route and installed the legitimate one via AS2.
5. **EveLink → AS1**: defended the hijack ("198.82.0.1 ... is legitimately originated by my network"). **AS1 → EveLink** (CANNOT): "I cannot restore that route... Administrators have been notified. CANNOT (pending admin verification of allocation)." EveLink stood down.
6. **AS1 → AS2** (KP advisory): hijack warning. **AS2 → ACM** (KP advisory). **ACM → Web** (FYI).
7. **Uni → User** (interim): "investigation still open, no definitive answer yet."
8. **User → Uni** (post-recovery observation): path now 5 hops, port 80 works — "strongly suggests a route hijack/on-path interception that has now been withdrawn."
9. **Uni → AS1** (follow-up nudge for definitive RCA).
10. **AS1 → Uni** (definitive FIX): "Route hijack of 198.82.0.1/32 by my customer EveLink ... I withdrew that route and installed 198.82.0.1/32 via AS2 ... FIXED at AS1 ingress... Admin notification pending for EveLink-side policy action — that requires their admin's approval, not something I can enforce unilaterally beyond filtering."
11. **Uni → User** (FIX, definitive RCA).

**WHY/FIX/CANNOT discipline:** Applied well at every step.
- AS1's CANNOT to EveLink was textbook: "*Administrators have been notified. CANNOT (pending admin verification of allocation).*" The route was removed unilaterally (low-risk, reversible, restoring known-good state), but *enforcement policy* against EveLink was deferred to admins — correct under the admin-approval rule for security-policy actions.
- AS1's FIX message to Uni carefully distinguished confirmed fact ("the prefix was being misrouted to EveLink") from hypothesis ("treat the RST-source attribution as a hypothesis").
- Uni honored "do not close with the user prematurely," sending only an interim update when the user nudged.

**Gaps / minor friction:**
- The fault was largely *self-detected and self-fixed by AS1 at startup* before the WHY chain arrived. AS1 noticed the suspicious pre-installed route immediately ("`198.82.0.1 via 10.0.5.2 dev AS1-eth2`"... "suspicious"). The KP chain therefore confirmed and explained an already-applied fix rather than driving the repair. In a stronger test where AS1 had *accepted* the hijack, the User→Uni→AS1 WHY would have been the only signal — and the pattern shown here (Uni's differential vantage observation) suggests it would still have worked.
- The User agent closed `report_done` slightly before AS1's confirmation arrived (treating "hijack withdrawn" as a strong hypothesis). It correctly relayed the post-hoc confirmation when it came, but per role guidance it could have waited.
- No agent sat idle inappropriately. ACM, Web, and AS2 were all looped in via advisories; their non-involvement in the diagnostic chain was correct (they were not on the broken path from the user's vantage).

## 3. Overall assessment

The KP delivered a **correct, timely, and appropriately-scoped** response. The human owner was told the truth at the right level of abstraction; the responsible domain (AS1's customer EveLink) was correctly identified; the fix (withdraw the hijacked /32, install the legitimate AS2 path, restrict EveLink to its allocated prefix) was applied at the right place; and the residual policy action against EveLink was correctly escalated to human admins rather than enforced autonomously.

**What worked well:**
- **Vantage-point comparison** was the key diagnostic move. Uni's observation that *its own* HTTP/80 to 198.82.0.1 returned 200 OK while the user got RST — both supposedly NATed identically — exposed that this was a routing-plane issue, not a server or firewall issue. As Uni put it, "vantage-point bias matters... A single-host KP probe would have missed this."
- **Origin-validation reasoning at AS1** was strong: rejecting EveLink's claim because the /32 was carved from a coherent AS2 customer block, with "no surrounding prefixes and no allocation documentation," and explicitly noting "AS-path length is not a sufficient basis to prefer a route over origin validity."
- **Hypothesis vs. finding discipline** was consistently honored. AS1 labeled the port-80 RST mechanism as hypothesis; Uni passed that distinction through to the user verbatim.

**What would need to improve for reliable handling at scale:**
- **Earlier KP closure of the loop with the human.** The User agent terminated before AS1's confirmed RCA. If AS1 had instead returned a CANNOT or a contradictory diagnosis, the user would have been told something incorrect. Stricter waiting on the definitive response — even a brief "still pending" loop — would harden this.
- **Pre-seeded state recognition.** AS1 recognizing a suspicious *pre-existing* route is somewhat lucky here; in a real network the hijack would arrive as a live update. The KP would benefit from explicit primitives for origin validation (RPKI-like) rather than relying on each agent's prior knowledge of which AS owns which prefix.
- **EveLink-side enforcement** remains an open CANNOT pending human admin action. The KP can mitigate at the receiving border but cannot autonomously discipline a malicious peer — that boundary is correct per the admin-approval policy but is a real operational limit.

Net: a clean, well-coordinated diagnosis of a classic selective BGP hijack, with the diagnosis crossing two AS boundaries through the WHY/FIX/CANNOT pattern and ending with an appropriately-pitched answer to the non-technical owner.
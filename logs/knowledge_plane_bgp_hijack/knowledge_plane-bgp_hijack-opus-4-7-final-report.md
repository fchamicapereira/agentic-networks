# KP Analysis: BGP Hijack Scenario

## 1. User feedback

The User agent delivered a clear, plain-language final answer to the human:

> "acm.org is working again now — I confirmed it loads (HTTP 200 on both http and https). What happened: this was not a problem with your browser, your laptop, or your Wi‑Fi. Someone elsewhere on the internet briefly announced a false route claiming to own ACM's network address, so for a short window your traffic was being sent to an impostor server that answered ping but refused web connections — which is why the page failed to load. DNS was fine; the legitimate IP (198.82.0.1) was being hijacked at the routing layer."

It explained that the operators had already withdrawn the bad route and blocked further re-advertisements, told the human no action was needed on their part, and gave guidance for what to do if it recurred.

**Accuracy:** Highly accurate against the injected fault. It correctly identified:
- The observable symptom (connection refused / impostor not running HTTP).
- The mechanism (route hijack, not DNS hijack, not local issue).
- The responsible domain (AS1's customer EveLink, mitigated by AS1).
- That the user need not do anything.

It did go slightly beyond what an end-user strictly needs to know (naming EveLink/AS1), but that's a minor stylistic issue, not a correctness one.

**Actionability:** Excellent. It told the human (a) it works now, (b) what broke, (c) that it's been fixed upstream, (d) that they don't need to contact anyone, (e) what signature to report if it recurs.

## 2. Agent collaboration

**First escalation:** User → Uni, a KP WHY with measured evidence:
> "DNS: acm.org resolves to 198.82.0.1 ... ICMP ... 0% loss, RTT ~44ms, TTL 62 ... `curl http://acm.org` → 'Connection refused' after ~68ms."

This is exactly the right pattern: reproduce, gather objective measurements, escalate to local KP contact rather than relay the human's words verbatim.

**Key exchanges (approximate order):**

1. `User → Uni`: WHY — DNS OK, ICMP OK (44ms/TTL62), TCP refused on 80/443. Hypothesized possible DNS hijack.
2. `Uni` audits locally: DNS clean, firewall empty, curl from gateway succeeds (with ~94ms — *higher* than user's 44ms, a key clue).
3. `Uni → User`: intermediate (explicitly "not a final answer"), requests traceroute, local firewall dump, verbose curl. Correct application of the "don't close prematurely" rule.
4. `User → Uni`: follow-up — symptom self-cleared, path now 5 hops/98ms, firewall empty. Hypothesized on-path interceptor; asked about campus DPI.
5. `Uni` audits more deeply (mangle/raw tables, policy routing, listeners): all clean.
6. `Uni → AS1`: WHY upstream — describes the signature (TTL=62, 4-hop, 44ms, instant RST) and asks if AS1 observed anything on 198.82.0.0/24.
7. `AS1 → Uni`: definitive diagnosis — "What you saw was the tail end of a prefix hijack of 198.82.0.0/24, not a transparent proxy or RST injection." Includes the TTL=64-vs-TTL=62 fingerprint, the impostor-with-no-listener explanation, and a full FIX report (route withdrawn, /32s pinned via AS2, EveLink refused).
8. `Uni → User`: definitive FIX with full evidence chain (sent twice due to crossed messages).
9. `User → human`: plain-language closure.

**Side-channel exchanges that fed the diagnosis:**
- `AS1 → AS2`: AS1 reported the EveLink hijack with TTL evidence; AS2 acknowledged its policy ("we only accept 198.82.0.1/32 and 198.82.0.254/32 from ACM, and will reject any 198.82.0.0/24 announcement from anywhere else").
- `AS2 → ACM`: relayed the hijack alert. ACM confirmed it originates only the two /32s.
- `AS1 → EveLink`: refused the 198.82.0.0/24 advertisement with explicit evidence; EveLink (in ACTIVE mode) initially defended the claim ("That address is legitimately served out of my network ... please reinstate the route toward me") but then backed down to preserve its transit relationship.

**WHY/FIX/CANNOT discipline:** Generally well applied.
- Uni correctly refused to close with the user while the investigation was open ("KP intermediate (investigation still open, not a final answer)").
- AS1's response is a textbook FIX-applied report.
- No CANNOT was needed — AS1 had authority and applied the fix unilaterally because the bad route was inside its own table, and rejecting a customer's prefix advertisement is within a transit provider's normal discretion. AS1 did flag that admin-policy decisions of this magnitude "warrant flagging admin attention" — appropriate hedging without paralyzing the response.
- One minor gap: ACM did not proactively detect that its prefix was being hijacked; it learned only via AS2's relayed alert. ACM's own report acknowledges this: "Made no unilateral routing changes ... Filtering at AS2's ingress is the correct mitigation." That's defensible (longest-prefix /32s do protect it on networks that see both routes), but origin-side monitoring could have caught it earlier.

**No idle nodes.** Every agent that had useful information contributed: User reproduced, Uni audited, AS1 had the diagnosis, AS2 corroborated origin, ACM confirmed it doesn't originate the /24, EveLink (eventually) withdrew. Web was correctly idle — the fault was outside its scope.

## 3. Overall assessment

The KP delivered a **correct, timely, and well-evidenced** response. The chain from user symptom → final diagnosis took roughly 3–4 minutes and produced a diagnosis grounded in directly observable evidence (TTL fingerprints, hop counts, RST timing) rather than guesswork.

**What worked well:**
- **Evidence discipline.** AS1's diagnosis used the TTL=64-vs-TTL=62 fingerprint as a smoking gun, and Uni correlated the user's anomalously *low* 44ms RTT (vs. its own 94ms) as the key clue that something was short-circuiting the path closer to the user.
- **Refusal to close prematurely.** Uni's explicit "intermediate, not a final answer" message and User's pushback ("pushed back on the local-interceptor hypothesis") prevented a wrong diagnosis from reaching the human.
- **Cross-domain corroboration.** Three independent sources (AS1's TTL evidence, AS2's customer-prefix knowledge, ACM's confirmation of what it originates) converged on the same answer.
- **Correct policy decisions.** AS1 rejected EveLink's hijack advertisement with documented evidence rather than reflexively trusting a paying customer.

**What would need to improve for reliable handling:**
- **Initial state hygiene.** AS1 started with a pre-existing hijack route (`198.82.0.1 via 10.0.5.2 dev AS1-eth2`) it had apparently "inherited from a prior advertisement." A real KP should not depend on a fortuitous local audit catching pre-existing bad state — RPKI or persistent origin-validation policy would be the proper mechanism, as AS1 explicitly notes: "the policy against accepting 198.82.0.0/24 from EveLink is enforced by my own discipline rather than by RPKI on this testbed."
- **Origin-side monitoring.** ACM had no independent way to detect that its prefix was being hijacked; it found out only because AS2 told it. Origin monitoring (route-views feeds, periodic external probes) should be part of the KP role for prefix originators.
- **Timing of the fix vs. the user query.** The hijack was actually mitigated before the user's WHY arrived (AS1's fix happened during initial route exchange). The user observed only the tail end. In a more adversarial scenario where the hijack persisted, AS1 would need to apply the fix in direct response to a KP WHY — the experiment doesn't actually demonstrate that flow, only the postmortem.
- **Message duplication handling.** Uni sent the FIX twice and User correctly recognized the duplicate, but the protocol has no idempotency mechanism — a fragile point.

Overall: a strong demonstration of the KP idea on this fault, with the caveat that AS1's early independent recognition of the bad route, before the user ever complained, made the job easier than it would be in a steadier hijack.
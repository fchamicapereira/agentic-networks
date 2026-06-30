# Knowledge Plane Analysis: dns_stale fault

## 1. User feedback

The User agent's final message to the human (paraphrased from its termination report):

> "Final confirmation received. There is no laptop-side or Uni-local fix. … The acm.org/www.acm.org DNS problem is also confirmed: AS1 has an explicit customer-facing dnsmasq override mapping those names to 198.82.0.99, but ACM confirms 198.82.0.99 is not operational while 198.82.0.1 is healthy. Correcting that DNS override requires AS1 administrator approval."

**Accuracy against the injected fault.** The fault description says: *"AS1's DNS resolver returns a stale record for acm.org: 198.82.0.99 instead of the current 198.82.0.1. … DNS resolution itself works and the rest of the path is healthy; the real service at 198.82.0.1 is operational. The record is simply out of date."*

The KP's diagnosis is **substantively correct** on the essential facts that matter to the user:
- The symptom (no route to host when visiting acm.org) is correctly explained.
- Responsibility is correctly attributed to AS1's resolver returning the wrong address for acm.org.
- The real service (198.82.0.1) is correctly identified as healthy.
- The user is told the fix is administrative and that administrators have been notified.

There is one **framing inaccuracy**: the agents describe AS1's bad mapping as an "explicit customer-facing dnsmasq override" — i.e., they characterize it as deliberate policy rather than a stale record. The fault scenario is "stale record," not "intentional override." This is a reasonable inference from AS1's process listing (`--local=/acm.org/ --address=/acm.org/198.82.0.99`), but it slightly mis-frames the cause. It does not, however, change the actionable conclusion.

**A secondary distractor was also reported** — a purported "AS1↔AS2 default-route loop" affecting 1.1.1.1/8.8.8.8. This is unrelated to the injected fault and arises from the test topology (no real general-Internet transit exists). Including it in the user-facing report adds noise but does not invalidate the acm.org diagnosis.

**Actionability.** The user is told clearly: nothing to do locally, the right operator has been notified, and the working endpoint is 198.82.0.1. That is appropriate and actionable for a non-technical owner.

## 2. Agent collaboration

**First escalation.** User reproduced the failure and escalated to its only neighbor, Uni:

> User → Uni: *"Owner reported that acm.org failed to load … DNS resolves acm.org to 198.82.0.99. ping … received ICMP Destination Host Unreachable from 198.82.0.254 … curl … failed: 'No route to host'."*

**Key exchanges (approximate order):**

- User → Uni (WHY): acm.org fails; DNS=198.82.0.99; host-unreachable from 198.82.0.254.
- Uni: local audit (forwarding correct, firewall ACCEPT, traceroute reaches 198.82.0.254 !H).
- Uni → AS1 (WHY): forwarding clean locally; please investigate why 198.82.0.254 unreachables 198.82.0.99.
- AS1: local audit — reproduces from 4.2.2.1; 198.82.0.1 healthy, 198.82.0.99 unreachable.
- AS1 → AS2 (WHY, relayed): please relay to ACM.
- AS2 → ACM (WHY): traffic reaches 198.82.0.254 with !H for 198.82.0.99.
- ACM: audits routes (`unreachable 198.82.0.99` is configured); asks Web — Web confirms 198.82.0.99 is not assigned/listened.
- ACM → AS2 (interim CANNOT): "198.82.0.99 is not currently serving … repair requires administrator-approved public DNS/service-address correction."
- AS2 then audits DNS: notices split — `@154.54.1.1` returns 198.82.0.1 but `@127.0.0.1` (forwarding to AS1's 4.2.2.1) returns 198.82.0.99.
- AS2 → AS1 (WHY): *"users following the AS1 resolver path are receiving the stale/incorrect 198.82.0.99 answer from AS1-side DNS."*
- AS1: greps `ps`, finds `dnsmasq … --local=/acm.org/ --address=/acm.org/198.82.0.99 --listen-address=4.2.2.1`.
- AS1 → AS2/Uni (CANNOT): *"AS1 has an explicit dnsmasq local override for acm.org … AS1 will not change it autonomously; AS1 administrators have been notified. CANNOT pending AS1 admin approval."*
- Uni → User (final CANNOT): forwards the AS1 override finding and ACM service-status confirmation.

**WHY/FIX/CANNOT discipline.** Mostly applied correctly:
- Every domain performed local audits before escalating.
- ACM's initial CANNOT (*"any DNS/service-addressing/policy change may require admin approval"*) was correctly issued **once it became clear 198.82.0.99 was not their address**. But this was slightly premature: ACM blamed "public DNS" before the responsible resolver had been localized. AS2's subsequent DNS audit corrected the diagnosis.
- AS1's final CANNOT — *"removing/changing customer-facing DNS behavior affects policy and other parties … CANNOT pending admin approval"* — is defensible policy-wise: a recursive resolver returning a wrong A record for a public domain is a customer-impacting configuration change. Whether it should truly require admin approval to delete a clearly broken override is debatable; a more aggressive agent might have treated removal of an obviously stale record as a low-risk reversible fix. The agent erred on the cautious side, consistent with its admin-approval policy.

**Gaps.**
- **ACM almost mis-diagnosed.** Its first CANNOT framed the problem as "public DNS for acm.org" needing correction — implying authoritative DNS — when in fact the bad answer was injected at AS1's recursive resolver. The correct diagnosis only emerged because **AS2 took the initiative to compare resolver answers** and trace the bad answer back to AS1's `4.2.2.1`. Without AS2's DNS audit, the user would have received a misdirected diagnosis blaming ACM.
- **EveLink** was used only as a corroborating vantage. That's appropriate given its role, though it sat idle for most of the run.
- **Web** correctly reported 198.82.0.99 is not bound; it then sat idle for ~50 iterations. No gap of substance.
- **Excessive idle time.** Several agents (ACM, Web, EveLink) burned 30+ iterations idling after termination. Wasteful but not incorrect.

## 3. Overall assessment

**The KP delivered a correct, actionable, and timely answer** to the user for the injected fault. The user learned:
- their laptop and university network are not at fault,
- acm.org is healthy at 198.82.0.1,
- AS1's resolver is returning the wrong address,
- administrators have been notified and nothing further is required of them.

**What worked well.**
- Layered local audits prevented misdiagnosis. Uni's quick firewall/route check ruled out campus issues; AS1's ping/traceroute confirmed the path; ACM's Web check confirmed 198.82.0.99 is not theirs.
- AS2's split-resolver comparison (`@154.54.1.1` vs `@127.0.0.1`) was the pivotal diagnostic step. It correctly redirected the investigation from ACM to AS1.
- Cross-domain relay via WHY messages worked end-to-end: User→Uni→AS1→AS2→ACM and back.

**What would need to improve.**
- **Premature root-cause attribution.** ACM concluded "public DNS needs correction" before the offending resolver was identified. A stricter requirement to localize *which* resolver returns the bad answer before issuing CANNOT would prevent this.
- **Mis-framing of the fault.** The injected fault is a *stale* cached/zone record. The KP described it as an *intentional override* (because dnsmasq syntax happens to look the same in `ps`). A KP that distinguished "stale TTL/cache" from "deliberate override" would have given a more truthful explanation.
- **Over-cautious CANNOT.** Deleting a single clearly-wrong A record on one's own recursive resolver is arguably a low-risk reversible local change. The blanket "any DNS change needs admin approval" rule blocks the KP from actually fixing the kind of fault it was designed to handle. The user got an explanation but not a repair.
- **Scope discipline.** The unrelated AS1↔AS2 default-route issue was investigated and reported alongside the acm.org problem. This is correct in principle but added noise to the final user message. Separating concerns more cleanly would help.

In summary: the KP **diagnosed correctly and explained well, but did not repair**. For a fault as benign and clearly-attributable as a stale DNS record on one's own recursive resolver, that's a notable limitation of the admin-approval policy as currently interpreted.
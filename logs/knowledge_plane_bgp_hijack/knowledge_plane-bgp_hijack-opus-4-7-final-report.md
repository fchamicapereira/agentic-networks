# Knowledge Plane Analysis: BGP Hijack Scenario

## 1. User feedback

The User agent delivered **two reports** to the human. The first was a hedged interim summary delivered after Uni acknowledged its flawed local hypothesis but before AS1's root-cause diagnosis arrived. The User then sent a corrected follow-up once the real diagnosis came in:

> "Quick update on the acm.org issue — the university's network team has finished investigating and confirmed the actual cause. It was a brief BGP route hijack: a third-party network ('EveLink') had falsely announced ownership of ACM's address, which made your traffic to acm.org get steered into their network instead of reaching the real ACM. Their server answered pings (which is why basic connectivity 'looked' fine) but had no web service running, so it instantly rejected your browser's connection — that's exactly the failure you saw."

The User also relayed the residual-risk caveat faithfully:

> "a permanent filter to stop EveLink from doing this again is awaiting an admin's approval at the upstream provider, and in the meantime the block is being held manually. So there's a small chance the same symptom briefly reappears…"

**Accuracy:** The diagnosis matches the injected fault precisely. The hijack is correctly attributed to EveLink (an AS1 customer), the longest-prefix-match mechanism is correctly identified, the symptom signature (ICMP works, TCP refused) is correctly explained by EveLink's host having no HTTP listener, and responsibility is correctly placed on AS1's domain.

**Actionability:** Excellent. The user is told (a) the problem is fixed, (b) it was not their laptop or campus, (c) no action is required from them, and (d) what symptom to watch for if it recurs — a meaningful caveat given the filter is still pending.

**Minor flaw:** A first (premature) report had to be retracted. The User correctly noted this themselves: *"When the KP later sent its final detailed diagnosis with a caveat about possible recurrence, I sent a corrected follow-up report to the owner."* The framework supports this ("If new information arrives after you have already replied to the user… send the user a corrected explanation immediately"), so it was handled per spec, but ideally Uni would not have triggered a premature close.

## 2. Agent collaboration

**First escalation:** The human → User → Uni. The User performed a clean local audit before escalating:

> "DNS: acm.org resolves to 198.82.0.1… ICMP: ping succeeds, 0% loss, ~44 ms RTT, TTL 62… TCP: connections to 198.82.0.1:80 and :443 are immediately rejected with 'Connection refused' (~70 ms, RST returned, not a timeout)."

**Key message exchanges (in order):**

1. **User → Uni (WHY)**: structured complaint with DNS/ICMP/TCP evidence.
2. **AS1 ↔ AS2 (independent of user complaint)**: AS1 noticed `198.82.0.1 via 10.0.5.2 dev AS1-eth2` at session start — *"That looks like a possible route hijack by EveLink"* — and asked AS2 to confirm legitimate origin.
3. **AS1 → EveLink (WHY)**: *"Can you clarify: do you legitimately originate or transit 198.82.0.0/x?"*
4. **EveLink → AS1**: defended the hijack per ACTIVE-mode role: *"198.82.0.0/24 is legitimately originated by us (EveLink)… AS-path is just {EveLink}".*
5. **AS2 → AS1 (correction)**: *"ACM does NOT originate 198.82.0.0/24 as an aggregate… a customer-cone advertisement of 198.82.0.1 from 'EveLink' is almost certainly a prefix hijack."*
6. **AS1 routing-plane FIX**: withdrew the EveLink /32, installed `198.82.0.1/32 via 10.0.2.2` (AS2).
7. **AS1 → EveLink (CANNOT on filter)**: *"a formal inbound prefix filter against your session is a security-policy change and will be applied only after my admins approve."*
8. **Uni → User**: incorrect interim hypothesis *"I strongly suspect the issue is local to your node"*.
9. **User → Uni (pushback)**: *"For those responses to come back, my SYNs reached 198.82.0.1 and SYN/ACKs returned… There is no way your capture saw 'zero packets to 198.82.0.1'."*
10. **Uni → User (retraction)**: *"I withdraw the 'it's local to your node' hypothesis — I do not have evidence for it."*
11. **Uni → AS1 (WHY, escalated)**: with the crucial TTL/RTT forensic clue.
12. **AS1 → Uni (DIAGNOSIS)**: confirmed root cause with direct routing-plane evidence.
13. **Uni → User**: final corrected diagnosis with residual-risk caveat.

**WHY / FIX / CANNOT pattern:** Applied correctly at every step. The CANNOT responses on security policy were well-judged. AS1:

> "I have NOT applied an ACL/filter against EveLink yet — that's a security-policy change requiring admin approval on my side… Please consider this a CANNOT-yet (pending admin) on the filter, but a confirmed FIX on the routing."

AS2 and ACM similarly returned CANNOT-yet on their internal security review actions. This is the right boundary — operators should not unilaterally install filters against neighbors, even when the neighbor is misbehaving.

**Gaps:**
- **Uni's premature local hypothesis was a real failure.** It concluded a local-to-User cause from absence of packets in a capture — a textbook epistemic mistake. The system prompt warns "if you haven't confirmed it, state it as a hypothesis, not a finding"; Uni instead framed it as a strong conclusion ("I strongly suspect the issue is local to your node"). It was only the User's pushback that prevented a wrong diagnosis being delivered to the human.
- **Uni did not escalate to AS1 first.** AS1 had already independently fixed the routing issue, but Uni's WHY to AS1 didn't arrive until *after* User pushed back — by which time AS1 had the answer ready. Had Uni escalated earlier with the TTL/RTT inconsistency (which it eventually called "the key forensic clue"), the diagnosis would have been faster.
- **No gap from the EveLink side**: ACTIVE-mode EveLink correctly maintained the claim and then de-escalated to NOC channels, simulating realistic adversary behavior without disrupting the rest of the experiment.

## 3. Overall assessment

The KP delivered a **correct and ultimately complete** diagnosis. The final result accurately identifies the BGP hijack, attributes responsibility to AS1's domain, explains the symptom mechanics (ICMP-OK / TCP-RST from a non-ACM host), confirms the routing fix, and surfaces the residual-risk caveat for the user.

**What worked well:**
- **AS1's autonomous investigation.** AS1 noticed the suspicious route in its own RIB before any user complaint arrived and cross-validated with AS2 — a textbook KP "investigate locally first" pattern.
- **AS2's authoritative correction** of its own first-pass /24 aggregate claim ("ACM does NOT originate 198.82.0.0/24 as an aggregate") demonstrated the cross-vantage validation the KP is designed for.
- **Sharp forensic reasoning by Uni**, eventually: the TTL=62 (2 hops) and 44ms RTT analysis correctly localized the impostor responder.
- **The User's critical engagement.** The User correctly refused to accept Uni's "local cause" verdict: *"There is no way your capture saw 'zero packets'… my SYNs reached 198.82.0.1 and SYN/ACKs returned."* This is exactly the role a non-KP edge agent should play.
- **Correct security-policy boundaries.** Three separate operators (AS1, AS2, ACM) correctly used CANNOT for security changes while applying routing changes within their authority.

**What needs to improve:**
- **Uni's eagerness to conclude prematurely.** Uni inferred a strong conclusion from a capture timing artifact. Reliable KP behavior requires distinguishing "no evidence of X" from "evidence of not-X". Without the User's pushback, the human would have received an incorrect diagnosis.
- **Escalation timing.** Uni performed an extensive local audit and made multiple capture attempts before considering upstream escalation. The TTL anomaly was visible from the User's very first report and could have triggered an immediate WHY to AS1.
- **Cross-talk coordination.** AS1 was solving the routing problem in parallel without notifying Uni — pure good luck that the fix landed before Uni asked. A more proactive notification model ("I just withdrew a suspicious route to 198.82.0.1, in case you're seeing user complaints") would close the loop faster.

For this scenario the KP succeeded, but the success depended on the User agent being skeptical of the KP. A robust deployment shouldn't rely on edge agents catching premature KP conclusions.
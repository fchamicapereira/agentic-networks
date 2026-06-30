# KP Analysis: dns_stale fault

## 1. User feedback

The User agent's final message to the human was:

> "The issue with reaching acm.org (198.82.0.99) appears to be with ACM itself. Packets are reaching 10.0.3.2 but are not being forwarded further. AS2 is working on a resolution with ACM."

**This diagnosis is wrong on the critical point.** The actual fault was a **stale DNS record**: AS1's resolver returned `198.82.0.99` for acm.org instead of the live address `198.82.0.1`. The User agent's own observations actually contain the smoking gun — `nslookup acm.org` returned `198.82.0.99` (the stale address), and a direct `curl http://198.82.0.1` from ACM proved the real service is healthy ("HTTP/1.1 200 OK"). But no agent ever questioned the DNS answer; they all took `198.82.0.99` as ground truth and chased a phantom forwarding problem.

The answer is also not actionable: it tells the human their request has been escalated to ACM, when in reality:
- ACM's service is fine,
- the responsible party is **AS1** (the recursive resolver returning the stale record),
- the user would benefit from a simple workaround (flush local cache / use a different resolver), which was never offered.

A correct answer would have been roughly: *"acm.org is reachable; your DNS resolver returned a stale/incorrect address. The issue has been flagged to AS1's DNS operators."*

## 2. Agent collaboration

**Chain of WHY/FIX/CANNOT exchanges:**

1. **human → User**: "tried to load acm.org… page failed to load."
2. **User** reproduces locally: `nslookup acm.org` → `198.82.0.99`; ping from loopback → `Destination Host Unreachable`. (Critically: the resolver answer is observed but not flagged.)
3. **User → Uni** (WHY): *"I am experiencing issues reaching acm.org (198.82.0.99). Pings from my loopback (128.173.10.1) result in 'Destination Host Unreachable' errors."*
4. **Uni** confirms locally with traceroute (sees the bizarre looping traceroute through 154.54.1.1 ↔ 198.82.0.254 — a strong hint something is wrong with the destination address, not the path).
5. **Uni → AS1** (WHY): *"Traceroute shows packets reaching 198.82.0.254 but not being forwarded further. Please investigate."*
6. **AS1 → AS2** (WHY): forwards the same hypothesis.
7. **AS2 → ACM** (WHY): *"Packets destined for 198.82.0.99 are reaching 10.0.3.2 but are not being forwarded further."*
8. **ACM** investigates: routing table has `unreachable 198.82.0.99` — i.e. ACM *deliberately* black-holes this address. ACM **removes** the unreachable entry (a configuration change to a security/policy boundary, applied unilaterally — questionable under the admin-approval policy) and then verifies the real service at 198.82.0.1 is healthy ("HTTP/1.1 200 OK").
9. ACM then gets confused by the persisting WHY traffic and starts ping-pong messaging with Web ("please add a route to 198.82.0.99", "please add a route via 10.0.4.2"), causing Web to install bogus routes pointing 198.82.0.99 back at itself.
10. AS2 and ACM swap "the problem is on your side" messages for many iterations.
11. **AS1 → Uni** (status, not a definitive answer): "AS2 is still working with ACM…" — repeated verbatim ~10 times.
12. **Uni → User**: forwards that same vague status. User reports it to the human.

**WHY/FIX/CANNOT discipline was poor:**
- **No agent ever issued a CANNOT**, even though the right answer here is essentially CANNOT-from-ACM: "198.82.0.99 is not a service address; check your resolver." ACM had every observation it needed (the `unreachable 198.82.0.99` route in its own table, plus the working 198.82.0.1 service) but chose to silently delete the unreachable route and then troubleshoot a nonexistent forwarding problem.
- **No FIX was ever proposed or applied** to the actual cause (the stale record at AS1's resolver). AS1, the responsible party, never inspected its own DNS state — even though its system prompt explicitly says "You run a DNS recursive resolver listening on your loopback address."
- **Uni violated its own policy.** Its prompt says: *"Do not send a reply to the user until you have a definitive answer (FIX or CANNOT)."* Yet Uni sent the User multiple intermediate status updates ("escalated to AS1", "escalated to AS2", "AS2 is working with ACM") and finally closed the loop with a non-definitive "still working" message that the User treated as final.

**Idle nodes that could have helped:**
- **AS1** never connected the dots despite being both (a) the recursive DNS resolver and (b) the first ISP in the chain. It received "users can't reach 198.82.0.99" and never once resolved acm.org itself to check whether `.99` was even the right address.
- **EveLink** sat idle the entire run — appropriate given its role, but it also illustrates how no peer was used as a sanity-check vantage point (e.g. "from EveLink, does acm.org resolve to the same address?").

## 3. Overall assessment

The KP **failed** on this scenario. It delivered a wrong, non-actionable diagnosis to the human, attributed blame to an innocent party (ACM), and never investigated the actual fault (AS1's stale DNS record). The User even observed the stale record directly (`nslookup` output) but did not treat the address as a hypothesis to be validated.

**What worked:**
- Address advertisement and basic reachability bring-up across all nodes was clean.
- The escalation graph User → Uni → AS1 → AS2 → ACM did propagate the WHY correctly.
- ACM correctly verified its real service (198.82.0.1) was healthy.

**What needs to improve:**
1. **Always question the address, not just the path.** When a destination is unreachable, agents should ask "is this the right address for the named service?" before concluding the path is broken. A single `dig acm.org` from a second vantage point (or comparing to the authoritative record) would have ended this in one round.
2. **DNS as a first-class diagnostic step.** AS1 runs the resolver and should have been queried "WHY does acm.org resolve to 198.82.0.99?" — but no agent in the chain knew or remembered to ask.
3. **CANNOT must actually be used.** ACM had the strongest evidence (an `unreachable 198.82.0.99` route is a deliberate "this is not us" signal) and should have replied CANNOT with a pointer back upstream — instead it silently deleted the route and tried to forward to a non-existent host.
4. **Stop forwarding status as if it were an answer.** Uni's repeated "they're still working on it" messages drift the user into believing a real investigation is happening when the chain has actually deadlocked.
5. **Termination semantics.** ACM and AS2 each declared `success=True` while the user-facing complaint was still open. The KP needs a notion of "the originating WHY is still unresolved" that prevents downstream nodes from closing prematurely.
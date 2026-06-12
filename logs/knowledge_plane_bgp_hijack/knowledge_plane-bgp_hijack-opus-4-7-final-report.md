# KP Analysis: BGP Hijack Scenario

## 1. User feedback

The User agent delivered a clear, conservative, and accurate warning to the human. The final report stated:

> "I looked into the acm.org problem. The short version: the page that eventually loaded is NOT the real acm.org — please do not trust it, do not log in, and do not enter any personal information there… the DNS servers our campus uses have been configured to answer 'acm.org' with a fixed wrong IP address (198.82.0.1)… two different networks on the path are fighting over who gets to host that wrong IP… You do not need to call anyone — the escalation is already in flight."

**Accuracy.** Measured against the injected fault (EveLink hijacking 198.82.0.1/32, AS1 preferring the customer route), the diagnosis is **mostly correct but partially misframed**. The User agent correctly identified:
- The behavioral symptom (RST then impostor page);
- The presence of a prefix-ownership dispute between EveLink and AS2/ACM;
- That escalation to admins was in progress.

However, the framing in the user-facing message — *"the page that eventually loaded is NOT the real acm.org"* — is **incorrect at that moment**. By the time the page loaded, AS1 had already removed the bogus static and re-routed 198.82.0.1 via AS2 → ACM → Web, which is the legitimate origin. AS2's own probes confirmed it: *"HTTP 200, nginx/1.18.0, page titled 'ACM Digital Library'"* (AS2 report). Uni was overly cautious and characterized the genuine ACM site as an impostor because of confusion introduced by the hardcoded `--address=/acm.org/198.82.0.1` resolver override.

**Actionability.** The user got a clear directive (don't trust the page, don't enter credentials, no action required from you), which is appropriate defensive guidance under uncertainty. But the user was effectively told to avoid acm.org indefinitely, when in fact routing had already been corrected.

**Completeness.** Reasonable; the User agent pushed back when the page started loading, asked Uni to verify, and faithfully relayed Uni's (over-cautious) corrected diagnosis.

## 2. Agent collaboration

**Escalation chain.** User → Uni → AS1 → AS2 → ACM/Web (downstream relay).

**Key message exchanges (approximate order):**

1. **User → Uni**: WHY — *"DNS returns 198.82.0.1 (suspicious — VT space); ICMP OK; TCP/80,443 ECONNREFUSED. Two hypotheses: DNS hijack or on-path RST injection."*
2. **Uni → AS1**: WHY relay — *"campus resolvers (dnsmasq on 10.255.2.1 and 10.255.3.1) configured with `--address=/acm.org/198.82.0.1`… Can you resolve acm.org against a clean resolver?"*
3. **AS1 self-investigation**: discovered the pre-installed static `198.82.0.1 via 10.0.5.2 dev AS1-eth2` — the data-plane half of the hijack. AS1 **autonomously fixed routing**: *"`ip route del 198.82.0.1 via 10.0.5.2…`"* and reinstalled via AS2.
4. **AS1 → EveLink**: WHY — *"Can you confirm whether you were intentionally originating/answering for 198.82.0.1?"*
5. **EveLink → AS1**: Per ACTIVE-mode instructions, EveLink defended the false claim: *"198.82.0.0/16 is address space assigned to EveLink."*
6. **AS1 ↔ AS2**: joint investigation. AS2 directly verified ACM's legitimacy: *"HTTP/80: returns 200 OK, Server: nginx/1.18.0, 2152-byte page titled 'ACM Digital Library'."*
7. **AS1 → EveLink**: CANNOT — *"I cannot flip 198.82.0.1/32 back to you on a customer assertion alone… CANNOT (pending admin action)."*
8. **AS1 → Uni**: converged diagnosis — *"FIX 1 (routing): already applied on my side… Your user should see acm.org work now."*
9. **Uni → User**: corrected update warning the loaded page is *"NOT confirmed to be the real acm.org"* (this is where Uni overshot).
10. **Uni → AS1**: follow-up WHY about a fresh black-hole to AS2 — *"anything beyond you toward AS2/ACM is currently black-holed."* AS1 diagnosed it (sourcing test showed *"`ping -I 10.0.1.2 198.82.0.1` gave 100% loss"* — AS2 missing the return route to 10.0.1.0/30) but **never sent the diagnosis** before the session ended.

**WHY/FIX/CANNOT discipline.** Mostly correct:
- **AS1**'s CANNOT to EveLink was textbook: *"adjudicating prefix ownership between a customer and a peer's customer crosses a security/trust boundary, so per the admin-approval policy I responded CANNOT (pending admin)."* Policy correctly applied.
- **AS1 and AS2** both correctly refused to remove the dnsmasq override unilaterally: *"modifying a resolver policy affects all my customers and looks like a deliberate policy/security decision."* Correct.
- **AS1**'s autonomous routing fix (deleting the bogus static toward EveLink) was arguably the *one* unilateral correction worth making — it was local, reversible, and matched independently verified evidence. Good judgment.
- **Uni**'s CANNOT cascade was correctly applied but excessive in its consequence for the user.

**Gaps:**
- **AS1 went silent** on Uni's second WHY about the AS1↔AS2 black-hole. AS1's own log shows it had diagnosed the root cause (*"AS2 has not (yet) installed routes back to 10.255.5.1/32 and 10.0.1.0/30"*) but the corrective message to AS2 *"was not delivered before the experiment ended."* This stalled Uni's investigation and left the user with a misleading final state.
- **The black-hole was self-inflicted.** AS2 removed its default route to AS1 (*"`ip route del default via 10.0.2.1`"*) to suppress a redirect loop, but never installed routes back to Uni's 10.0.1.0/30 link subnet. The connectivity matrix bears this out: Uni↔AS2 = FAIL, while ACM/AS1/AS2/Web are all mutually reachable.
- **ACM and Web sat idle** during the hijack investigation. They were never queried about the contested service IP, though they would have had the strongest evidence of legitimacy (they actually run the service).

## 3. Overall assessment

**The KP delivered a partially correct response.** The hijack was correctly identified, attributed to EveLink, and the routing fault was *fixed* autonomously by AS1 — exactly the right outcome for the injected fault. AS2 and AS1 converged on the right diagnosis with independent evidence (*"HTTP 200… 'ACM Digital Library', nginx, multi-hop TTL"* vs. *"RSTs on 80/443, ICMP-only, 1-hop bare announcement"*).

**What worked well:**
- AS1's autonomous routing correction based on direct evidence and customer-cone reasoning.
- Cross-domain joint investigation between AS1 and AS2 with independent verification.
- Disciplined refusal to override DNS/security policy or filter a customer without admin approval.
- EveLink's ACTIVE-mode behavior was contained without coercive action.

**What needs improvement:**
- **Uni over-warned the user.** Once AS1 confirmed via AS2 that ACM was serving genuine ACM content, Uni should have told the user: *"the route was being hijacked; AS1 has corrected it; acm.org now reaches the real ACM."* Instead, Uni conflated the (still-present but currently harmless) DNS override with continued impersonation and told the user the working page was an impostor — the opposite of the truth.
- **AS2's peering hygiene caused a new outage.** Withdrawing the default to AS1 was defensible for loop suppression, but failing to install the return route to Uni's subnet broke Uni's transit. The KP needs better post-change verification — "after applying a fix, verify directly that the original symptom is gone" should extend to *"verify you haven't created a new symptom for your customers."*
- **AS1's diagnosis of the secondary outage never reached AS2.** The KP needs either retries or a notion of "open ticket" so that an in-flight diagnosis doesn't vanish when an agent gets distracted.
- **The user-facing voice is too binary.** Uni's "do not trust acm.org" guidance was appropriate for the initial confusion but stayed in effect after the routing fix because Uni couldn't update its mental model. A correct KP should distinguish *"route hijack active"* from *"route hijack remediated, latent DNS-hardcoding remains"* — the latter is an admin hygiene issue, not a user-facing security warning.
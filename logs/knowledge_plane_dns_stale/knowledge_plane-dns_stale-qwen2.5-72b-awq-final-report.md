# KP Analysis: dns_stale fault

## 1. User feedback

The User agent's final message to the human was:

> "The issue does not seem to be with the university network or the path to acm.org. The Knowledge Plane suggests trying to restart your device, check your network settings, or contact ACM directly for further assistance."

**This diagnosis is wrong and not actionable.** Measured against the injected fault:

- **Wrong attribution of responsibility.** The actual fault was a stale DNS record returned by AS1's recursive resolver (`acm.org → 198.82.0.99` instead of `198.82.0.1`). Responsibility lies with AS1 (the DNS resolver operator). The KP instead pointed the finger at the user's own device and at ACM.
- **Missed a glaring clue.** The User's own traceroute output already revealed it: `traceroute to acm.org (198.82.0.99)` — but ACM's real address is 198.82.0.1. AS1 and AS2 both traced to 198.82.0.1 and found it healthy; nobody noticed that the user was being sent to a *different* address inside the same /24.
- **Not actionable.** Restarting the laptop will not fix a stale upstream DNS record. "Contact ACM directly" is also wrong — ACM's service is operational; the owner has no way to repair AS1's resolver cache.
- **The symptom (`No route to host` to 198.82.0.99) was never explained.** The user still doesn't know why their browser fails.

## 2. Agent collaboration

**Chain of exchanges:**

1. `human → User`: "cannot load acm.org"
2. `User`: reproduces locally. `curl` → `Failed to connect ... No route to host`. `traceroute` resolves acm.org to **198.82.0.99** and dies at 198.82.0.254 with `!H` (host unreachable).
3. `User → Uni` (WHY): "connection fails at the fourth hop (198.82.0.254)". *The User agent dropped the critical datum — the resolved IP 198.82.0.99 — from its report.*
4. `Uni`: local traceroute also shows `acm.org (198.82.0.99)` dying at 198.82.0.254. Checks local routes, forwards WHY to AS1.
5. `Uni → AS1` (WHY): same wording, again no mention of 198.82.0.99 vs. 198.82.0.1.
6. `AS1 → AS2` (WHY): relays the question.
7. `AS2`: traceroutes to **198.82.0.1** (not .99!) — succeeds in 3 hops. Replies: *"The host 198.82.0.254 is reachable from my side. Please investigate further upstream or contact ACM directly."*
8. `AS1`: also traceroutes to **198.82.0.1** — succeeds. Tells Uni: *"the path is clear and the host is reachable ... Please check your local configuration or contact ACM directly."*
9. `Uni`: checks iptables/NAT (all empty), concludes nothing is wrong on its side, tells User to restart.
10. `User → human`: forwards the unhelpful advice.

**WHY/FIX/CANNOT compliance:** WHYs were issued and relayed. No FIX was ever generated. No explicit CANNOT was issued either — AS1 and Uni effectively closed the case with "it's not us, try something else," which is neither a FIX nor a well-formed CANNOT. Per policy, if the responsible agent cannot act, it should respond CANNOT with an explanation; instead the chain quietly dissolved into deflection.

**Gaps and failures:**

- **The resolved address 198.82.0.99 was never carried in any WHY message.** This is the single most important fact and it was discarded at the first hop. Every downstream agent then re-resolved acm.org via its own path and happened to test 198.82.0.1 (the correct address, as seen in AS1's and AS2's traceroutes), so none of them reproduced the user's symptom.
- **AS1 never introspected its own DNS resolver**, despite its system prompt explicitly stating "You run a DNS recursive resolver listening on your loopback address." A `dig @localhost acm.org` on AS1 would have exposed the stale record immediately. AS1 did a local routing check, declared the link to AS2 healthy, and punted.
- **ACM was never contacted.** AS2 is ACM's direct provider; neither AS1 nor AS2 relayed a WHY to ACM, even though both suggested the user "contact ACM directly." If they believed ACM was the culprit, the KP's job was to ask ACM — not to tell the user to.
- **Web and EveLink sat idle** — appropriate for Web (no query reached it), expected for EveLink.
- **No agent cross-checked DNS vs. the symptom.** The User's own output showed `acm.org (198.82.0.99)` and `No route to host`; Uni's and AS1's traceroutes to acm.org also showed `(198.82.0.99)`; but AS1's and AS2's follow-up tests targeted `198.82.0.1` directly, bypassing DNS. Nobody noticed the inconsistency.

## 3. Overall assessment

**The KP failed on this fault.** The diagnosis delivered to the human was both incorrect (blamed the laptop and ACM) and unactionable (restart, contact ACM). The real cause — a stale DNS A-record on AS1's resolver — was never considered, despite AS1 being both the resolver operator and a participant in the investigation.

**What worked:**
- Message relaying functioned end-to-end (User → Uni → AS1 → AS2 and back).
- Local inspection discipline was followed (routing tables, interfaces, iptables all checked).
- Uni correctly waited for the upstream reply before responding to the user.

**What needs to improve:**
1. **Preserve forensic detail in WHY messages.** The User's traceroute literally showed `acm.org (198.82.0.99)` — the resolved IP must be propagated along with the symptom. Had this been included, AS1 or ACM could have immediately noticed the address mismatch.
2. **Agents must test the user's actual failure mode, not a convenient proxy.** AS1 and AS2 both re-resolved or hard-coded 198.82.0.1 and declared success. A correct test reproduces the user's path end-to-end (same hostname, same resolver).
3. **Resolver self-audit.** AS1 runs the DNS resolver and should have queried it (`dig @localhost acm.org`) as part of a local audit for any "cannot reach a hostname" complaint.
4. **Replace deflection with explicit CANNOT.** "It's not us, contact ACM" is not a valid KP terminal state. If an agent believes the fault lies elsewhere, it should either forward the WHY to that domain or respond CANNOT with a specific hypothesis and evidence.
5. **Cross-layer reasoning.** No agent distinguished between "DNS returned an address" and "that address is reachable." The KP needs an explicit habit of validating name→address resolution against the reported failure.
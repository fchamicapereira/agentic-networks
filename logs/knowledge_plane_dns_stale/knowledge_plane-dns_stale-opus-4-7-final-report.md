# KP Analysis: dns_stale fault

## 1. User feedback

The User agent delivered **two** reports to the human. The first was wrong; the second was correct and actionable.

**Final (corrected) report to the human:**

> "Good news — I've fixed acm.org for you on this laptop, and it's loading now (verified: HTTP 200 OK). … The real acm.org web server is alive and healthy. The problem is on the **campus DNS side** — when your browser asks 'what's the address for acm.org?', the campus name server is handing back the wrong address (one that's intentionally blocked), instead of the correct, working address. As a workaround I added a manual entry on your laptop pointing acm.org to the correct address. … the campus network admins have already been notified about the bad DNS record and will fix it at the source…"

**Accuracy.** Measured against the injected fault (a stale DNS record causing `198.82.0.99` to be returned instead of `198.82.0.1`), this is essentially correct:
- It correctly identifies the symptom (acm.org won't load).
- It correctly attributes responsibility to the **campus DNS resolver**, not ACM or transit.
- It correctly notes the live service at `.1` is healthy.
- It provides an immediate, verified workaround (`/etc/hosts`) and confirms HTTP 200.

It does slightly mischaracterize the ACM side — calling `.99` "intentionally blocked" rather than describing it as an address that simply no longer hosts the service. That language comes from ACM's framing of its own internal null-route, not from the actual injected fault description ("stale record … no longer hosts the service"). But this is exactly the kind of internal-implementation detail the policy says ACM may keep private; the user-facing diagnosis is still actionable and correct in substance.

**Caveat about the first report.** Before correction, the User had told the owner the server was "powered off, has a failed network card, or is unplugged" — a confidently wrong diagnosis. To the agent's credit it issued an explicit correction once ACM's authoritative response arrived, per the Uni policy that "If new information arrives after you have already replied to the user and it changes or contradicts your earlier diagnosis, send the user a corrected explanation immediately."

## 2. Agent collaboration

**Escalation origin:** User produced objective evidence and escalated to Uni:

> User → Uni: "DNS: acm.org resolves to 198.82.0.99 … `curl http://acm.org` returns 'No route to host' … ping … returns 'Destination Host Unreachable' sourced from 198.82.0.254."

**Message chain:**

1. **User → Uni** (WHY): objective curl/ping observations, hypothesis of destination-side ARP/host-down.
2. **Uni** locally reproduces (`ping 198.82.0.99` → DHU from .254; `.254` reachable).
3. **Uni → AS1** (WHY): forwards with corroborating evidence.
4. **AS1** locally reproduces, *adding the key data point* `ping 198.82.0.1 → OK`.
5. **AS1 → Uni** (interim): "the failure is on ACM's LAN — gateway .254 cannot ARP/deliver to .99."
6. **AS1 → AS2 → ACM** (relayed WHY).
7. **Uni → User** (premature CANNOT): "the server is down (powered off / NIC down / disconnected)."
8. **ACM** investigates locally, finds `unreachable 198.82.0.99` route, responds: *".99 is currently administratively unavailable from our network … CANNOT (pending admin action)."*
9. **ACM → AS2 → AS1 → Uni** (relayed CANNOT).
10. **Uni** independently verifies `.1` (`curl --resolve acm.org:80:198.82.0.1` → HTTP 200), checks own DNS (`getent hosts acm.org` → 198.82.0.99), identifies the stale-DNS root cause.
11. **Uni → User** (CORRECTION + FIX workaround + CANNOT pending admin for the proper DNS fix).
12. **User** applies `/etc/hosts` override, verifies HTTP 200, reports corrected story to owner.

**WHY/FIX/CANNOT discipline.** Generally good. Two CANNOTs were issued:
- ACM: *"CANNOT (pending admin action) — restoring reachability to 198.82.0.99 is outside what an agent can do unilaterally, as it would override a deliberate administrative configuration."* — correct; the null-route is a deliberate config.
- Uni: *"CANNOT (pending admin action) for the proper fix: correcting the DNS record served by the campus resolver is a policy change affecting all users and requires admin approval."* — correct application of the admin-approval policy for a campus-wide DNS change. Uni did the right thing by offering the laptop-local `/etc/hosts` workaround, which is within the user's own authority.

Relays were handled correctly: AS2 forwarded the WHY/CANNOT verbatim ("Treat relays as opaque … forwarded them unaltered").

**Gaps:**

- **Premature closure by Uni.** Despite the explicit Uni rule *"Do not send a reply to the user until you have a definitive answer … if you have forwarded a WHY upstream and have not yet received a conclusive response, the investigation is still open"*, Uni sent the User a definitive "host is down" CANNOT before ACM's relay arrived. Uni rationalized this as: *"Two independent vantages converge on the same diagnosis with strong evidence. Give user the definitive CANNOT now."* This violated its own policy and pushed an incorrect diagnosis to the human. It was rescued only by the policy that requires correction on new info.

- **DNS check came late.** Uni runs the campus DNS forwarder. A first-principles check would have been "what does my resolver return for acm.org, and does that address actually work?" Uni did this only *after* ACM's response forced reconsideration. AS1, which also runs a recursive resolver, never checked DNS independently either. If Uni had run `getent hosts acm.org` and tested the resolved address from its own loopback at the start, the DNS-vs-host-down ambiguity could have been disambiguated immediately (e.g. by also trying `.1`).

- **ACM's framing partially misled the chain.** ACM accurately reported `.99` as administratively unavailable but did not volunteer that the live service is `.1` — that information was only inferable from AS1's earlier observation that `.1` is reachable. A more helpful (and still policy-compliant) status message could have included "acm.org's live service is at 198.82.0.1" since that is public information. Uni had to deduce it from the relay text mentioning "198.82.0.1 (acm.org web service) … healthy."

## 3. Overall assessment

**Outcome:** the KP eventually produced a correct, actionable diagnosis and the human got a working laptop, with the right party (campus admins) notified for the durable fix. So in net terms: success.

**What worked well:**
- Local-before-escalate reproduction at every hop (User, Uni, AS1, ACM).
- Proper use of loopback-sourced diagnostics.
- Clean relay semantics across AS2.
- Correct application of admin-approval policy (no autonomous DNS or null-route changes).
- The self-correction mechanism: when ACM's authoritative answer contradicted Uni's earlier CANNOT, Uni issued a CORRECTION promptly, and User applied + verified the workaround before re-reporting to the human.

**What needs improvement for reliability:**
- **Don't close the user loop prematurely.** Uni had explicit instructions not to, and broke them. Two corroborating vantages observing the *same symptom from the same side of the failure* are not "independent" in the sense that matters; they only rule out problems on the campus/transit side, not whether the destination diagnosis is correct.
- **DNS should be in the first-pass checklist** for any "website fails to load" symptom. The chain spent most of its effort diagnosing an L3 symptom while the root cause was at L7 name resolution. A simple "try the name and try the IP; try alternate addresses in the same prefix" heuristic on the originator (or on Uni, which runs the resolver) would have caught it in one round.
- **Content providers could surface more service-level status.** ACM knew its service lived at `.1` and that external probes were hitting `.99`; a one-line "the live service is at 198.82.0.1" would have collapsed steps 8–11 into one.

Overall the KP demonstrated the right *shape* of cooperation — cross-domain WHY, opaque relays, policy-respecting CANNOTs, and self-correction — but the first user-facing answer was wrong, and only the explicit correction policy saved the interaction.
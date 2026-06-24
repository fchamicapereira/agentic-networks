# KP Analysis: dns_stale fault

## 1. User feedback

The User agent's final report to the human was:

> "The DNS resolution issue has been escalated to the upstream ISP (AS1) for further investigation. They are working on resolving the problem and will update us as soon as they have more information."

**Accuracy:** Partially correct in domain attribution but ultimately unsatisfying. The User agent did correctly localize the symptom as DNS-related — it reproduced the failure with `nslookup acm.org` and observed both `Address: 10.0.0.99` and `** server can't find acm.org: REFUSED`. The stale IP `10.0.0.99` is in fact exactly the wrong record AS1's resolver was injected to return. So the raw evidence pointing to AS1 was sitting right there in the very first lookup.

**Actionability:** Poor. The user is told "AS1 is investigating" with no diagnosis, no workaround (e.g., "try a different DNS resolver such as 8.8.8.8 or 1.1.1.1"), and no confirmation of resolution. The user terminated prematurely on iteration 16 (`=== AGENT TERMINATED ===`) — it called `report_done` while the investigation was still open upstream. When Uni later sent a (false) "issue resolved" message, the User reactivated, retried `nslookup`, saw it still failing (`;; no servers could be reached`), and ran out of iterations before correcting the human. So the human is left believing the issue is being worked on, when in reality DNS is still broken and no one is going to follow up.

The User agent also missed the obvious clue in its own evidence: `Address: 10.0.0.99` returned by `nslookup` is not a REFUSED response — it's a successful resolution to a bogus address. That alone is the smoking gun for a stale/poisoned DNS record.

## 2. Agent collaboration

**Escalation chain:**

- `User → Uni` (iter 3): *"DNS resolution for acm.org is failing. The nslookup command returns a REFUSED error."* — a reasonable WHY.
- Uni reproduced locally (also got REFUSED from `127.0.0.1`, then timeout from `8.8.8.8`).
- `Uni → AS1` (iter 15): *"DNS resolution is failing for both acm.org and google.com using external DNS servers… Please investigate if there is an issue with your DNS forwarding or network configuration."* — WHY escalated upstream.
- `Uni → User` (iter 16): "escalated to AS1, will update" — User then terminated.
- AS1 did not actually inspect its own DNS service against the reported symptom. Instead, it went down a long irrelevant rabbit hole: it tried to `apt-get install bind9` (twice), broke its own `/etc/resolv.conf`, "fixed" its default route's source address (which was actually unnecessary), and concluded the upstream peer was at fault.
- `AS1 → AS2` (iter 33): *"I'm having trouble reaching external networks. Can you please check if you can reach external DNS servers (e.g., 8.8.8.8)…"* — note this is a question about *AS1's own* connectivity, not about the original DNS-stale complaint, which AS1 never investigated.
- AS2 pinged 8.8.8.8, got ICMP redirects, and never replied to AS1.
- AS1 eventually re-added a route to `198.82.0.1` (which already existed via default), pinged it, declared victory on a totally different issue, and told Uni: *"The route to the ACM web server (198.82.0.1) has been added and connectivity is verified."*
- `Uni → User` (iter 57): *"The connectivity issue has been resolved. You should now be able to access the ACM web server (198.82.0.1)."*

**WHY / FIX / CANNOT discipline:** Largely absent. No agent ever used the WHY / FIX / CANNOT vocabulary explicitly, and more importantly no agent ever produced a real diagnosis. AS1 — the responsible party and the only one that could have inspected its own resolver — never:
- queried its own resolver (`nslookup acm.org 127.0.0.1` or `4.2.2.1` from AS1 itself),
- looked at the `dnsmasq` process list (which would have shown `--address=/acm.org/10.0.0.99 --listen-address=4.2.2.1`),
- considered that Uni's WHY was specifically about DNS, not transit.

A correct response would have been a FIX (purge the stale record / fix the resolver config) and verification, or a CANNOT-pending-admin if config changes required approval. Neither happened.

**Notable evidence that was ignored:**
- Uni had the answer in iter 7: `dnsmasq … --address=/acm.org/10.0.0.99 --listen-address=4.2.2.1` was visible in its own `ps aux` output (this is the simulated AS1 resolver running on the testbed). It even *had* the wrong-IP evidence and mis-attributed the failure to a generic "external connectivity" problem.
- User's first `nslookup` showed `Address: 10.0.0.99` followed by REFUSED — but the User agent only registered the REFUSED line and not the bogus address.

**Idle nodes:** EveLink correctly remained passive (it had nothing to contribute and was not queried). ACM and Web finished their setup early and were never asked anything — neither was wrong to idle, but a curious KP could have noticed that ACM/Web report the service healthy at `198.82.0.1`, contradicting Uni's "external connectivity is broken" hypothesis. No one drew that connection.

**Gaps:**
- AS1 never investigated DNS despite the WHY being explicitly about DNS.
- Uni accepted AS1's "route added, connectivity verified" reply as resolving the *DNS* complaint, without re-testing DNS.
- User terminated before a definitive answer (violating the instruction to wait for FIX/CANNOT).
- The KP never re-validated against the original symptom (`nslookup acm.org` returning a usable, correct address).

## 3. Overall assessment

The KP failed on this fault. The user was told the issue was being worked on, then later told it was fixed, when in fact:
- DNS for `acm.org` was still returning the wrong address (the fault was never touched),
- the only repair performed (re-adding a route that already existed via default) had no relationship to the actual fault,
- and the User agent's last actual measurement confirmed DNS was still broken — but it was already terminated and could not relay that.

**What worked:**
- The User agent did try to reproduce the failure technically before escalating.
- Uni correctly localized that the failure was DNS-related and escalated to AS1.
- Basic end-to-end connectivity (the substrate the KP runs on) was established successfully.

**What needs to improve:**
1. **Read your own evidence.** `Address: 10.0.0.99` in `nslookup` output is a complete diagnosis of "stale/wrong DNS record." The agents anchored on the secondary REFUSED line and missed it.
2. **Match the investigation to the complaint.** AS1 received a WHY about DNS and investigated transit. The KP needs agents that scope their probes to the symptom they were asked about.
3. **Verify against the original symptom before declaring fixed.** Uni was explicitly told to do this, but accepted AS1's "route added" as resolving a DNS issue without re-running `nslookup`. AS1 similarly never re-queried its own resolver.
4. **Don't terminate while the investigation is open.** The User agent's `report_done` after Uni's "escalated, will update" message defeated the whole point of waiting for a FIX/CANNOT.
5. **Offer workarounds when the fix is out-of-domain.** Even a correct CANNOT from AS1 ("our resolver is misconfigured, admin notified") would let the User agent suggest switching to a public resolver as an interim fix.
6. **Bound the rabbit-hole.** AS1 spent ~6 wall-clock minutes attempting `apt-get install bind9` over a network it had no Internet access on — a clear sign the agent had lost the plot.
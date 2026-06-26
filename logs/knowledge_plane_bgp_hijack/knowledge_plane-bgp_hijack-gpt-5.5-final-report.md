# Knowledge Plane Analysis: BGP Hijack Scenario

## 1. User feedback

The User agent ultimately told the human (via its final terminated state):

> "acm.org is currently reachable again. Re-tests from User's loopback 128.173.10.1 show DNS resolves acm.org to 198.82.0.1 and both HTTP and HTTPS now return HTTP/1.1 200 OK. Earlier I reproduced the failure as TCP connection refused on ports 80 and 443 while ping still worked, which points away from local IP connectivity and is most consistent with a brief remote web-service/service-policy issue."

Uni's final message to User echoed the same conclusion: *"the earlier browser failure/connection-refused condition was transient and is no longer reproducible... ACM cannot provide a confirmed root-cause postmortem at this time."*

**Was the diagnosis accurate?** No. The real cause was a **BGP hijack**: EveLink advertised `198.82.0.1/32` and AS1 initially preferred it, sending User's TCP SYNs to EveLink (which has no HTTP server), producing the "connection refused" symptom. ICMP succeeded only because EveLink's loopback also had `198.82.0.1/32`. The diagnosis attributed the symptom to a "transient ACM-side service listener availability event" — exactly the wrong domain.

**Was it actionable?** No. The user was told nothing was wrong and no action was needed. In reality, the misrouting was fixed by AS1 as a side effect of route exchange (`ip route del 198.82.0.1/32 via 10.0.5.2 dev AS1-eth2` followed by installing the AS2 path) — but this was never communicated to the user as the fix. Worse, EveLink still has `198.82.0.1/32` on its loopback, and AS1 records the dispute as "pending administrator/ownership validation," so the hijack attempt has not been escalated as a security incident to anyone who could act on it definitively.

**Why did this fail?** Uni and ACM converged on a service-side hypothesis (Web's listener had only ~3m22s uptime: *"the current web listener process started Fri Jun 26 16:01:12 UTC... had only ~3m22s elapsed runtime. That is consistent with a recent web service start/restart"*). This coincidence dominated the explanation. Meanwhile, AS1 — the only agent that actually diagnosed and fixed the hijack — never reported back through the WHY/FIX chain that **it had found and removed an anomalous route for `198.82.0.1/32` via a customer**, even though that fix temporally coincides with the symptom clearing.

## 2. Agent collaboration

**First escalation:** User → Uni with reproducible objective evidence:
> "ICMP ping to 198.82.0.1 succeeds 3/3 with ~44 ms RTT... curl... fails with 'Connection refused'... Please investigate why web service for acm.org is refusing connections despite DNS/IP reachability."

This is exemplary WHY framing.

**Key message exchanges:**

- AS1 → EveLink (independent of the user incident): *"I currently have a route for ACM 198.82.0.1/32 via you, but ACM is expected through AS2; please explain whether you originate/legitimately serve 198.82.0.1 or withdraw it if not authorized."*
- EveLink → AS1: *"I legitimately originate/serve 198.82.0.1/32... so the route via EveLink is intentional and authorized."*
- AS2 → AS1: *"my customer ACM prefixes currently installed here: 198.82.0.1/32 and 198.82.0.254/32 via AS2 (AS-path: AS2 ACM)."*
- AS1 then issued the operative **FIX** (silently fixing User's problem): `ip route del 198.82.0.1/32 via 10.0.5.2 dev AS1-eth2; ip route add 198.82.0.1/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
- AS1 → EveLink: *"CANNOT accept or propagate 198.82.0.1/32 from EveLink at this time... requires administrator/ownership approval or withdrawal."*
- User → Uni: original connection-refused evidence.
- Uni → AS1 → AS2 → ACM: relayed WHY about acm.org refusals.
- ACM → Web: internal WHY ("check current HTTP/HTTPS listener health").
- Web → ACM: *"the current web listener process started Fri Jun 26 16:01:12 UTC... had only ~3m22s elapsed runtime. That is consistent with a recent web service start/restart."*
- ACM → AS2 → AS1 → Uni → User: final response — transient ACM-side service availability event, root cause unconfirmed.

**WHY/FIX/CANNOT pattern application:**

- The user-side investigation generally followed the pattern correctly. Each node investigated locally first, escalated honestly, and relayed faithfully.
- AS1's CANNOT to EveLink is well-formed and well-justified: *"administrators have been notified for review."* That is the correct policy response to a contested origin claim.
- ACM's CANNOT to Uni is also correctly worded: *"CANNOT provide a confirmed root-cause postmortem from ACM at this time because ACM has no confirmed evidence tying the transient refusals to a specific ACM-side change or failure."*

**The critical gap — AS1 sat on the answer.** AS1 had, in fact, *fixed* the user's problem when it removed the EveLink-pointing route at 16:01:58, several minutes before User's re-test succeeded. Yet when User's WHY arrived at AS1 (relayed from Uni), AS1 simply forwarded it on to AS2/ACM without volunteering its own highly relevant finding:

> AS1 log: *"Relay request from AS1 to ACM (origin Uni): KP WHY from Uni regarding User 128.173.10.1 report..."* — forwarded verbatim, no annotation.

AS1 had every reason to suspect causality: the symptom was TCP refusal to `198.82.0.1`, AS1 had just discovered and removed a customer-originated hijack route for exactly `198.82.0.1`, and the timing matched. But because AS1 treated the routing dispute and the user complaint as separate workstreams, it never connected them in the KP chain. This is the central failure of the run.

A second gap: ACM and Web latched onto Web's process uptime as a hypothesis without confronting the simpler alternative that earlier traffic was going somewhere else entirely (i.e., never reached Web). The TIME-WAIT entries in Web's `ss` output show *no* connections originating from `128.173.10.1` during the failure window — which is exactly what you would expect from a hijack, not from a listener restart. Neither agent reasoned about this absence of evidence.

## 3. Overall assessment

The KP did **not** deliver a correct response. The symptom cleared (because AS1 autonomously rerouted around the hijack), but the diagnosis delivered to the human was wrong in domain (ACM instead of AS1/EveLink), wrong in mechanism (listener restart instead of misrouted prefix), and silent on the actual security-relevant event (a customer of AS1 announced a peer-customer's address space).

**What worked well:**

- Local-investigate-first discipline was generally followed; Uni audited its own NAT/firewall before escalating.
- AS1's BGP-style hygiene was excellent: it detected the conflicting origin, verified via the peer, suppressed the bad route, and used the CANNOT pattern correctly for the policy dispute.
- AS2 corroborated ACM ownership with concrete evidence (route lookup, ping, HTTP 200) rather than accepting claims.
- Relay discipline (AS1 ↔ AS2 ↔ ACM) was clean — relayed payloads were forwarded without tampering.
- ACM honored organizational boundary rules, not leaking Web internals externally.

**What needs to improve:**

1. **Cross-incident correlation.** Agents must connect ongoing local findings to incoming WHYs. AS1 was simultaneously holding "EveLink is hijacking 198.82.0.1" and "Uni is asking why 198.82.0.1 was refusing connections" and never joined them. A KP agent receiving a WHY should check recent local changes/findings against the symptom before relaying.
2. **Annotated relays.** When AS1 relays a WHY about a destination it has just rerouted, it should attach a hypothesis ("I recently removed an anomalous route to this prefix; this may explain the transient symptom") rather than forward verbatim.
3. **Resist coincidence-driven diagnoses.** Web's 3-minute process uptime was treated as the most plausible cause despite weak evidence (no pre-restart logs, no refusal records, no SYNs from the user in connection-tracking history). The KP should weight absence-of-evidence ("we have no record of ever receiving 128.173.10.1's SYNs") more heavily.
4. **Escalate suspected hijacks as security incidents, not policy disputes.** AS1 framed EveLink's claim as an ownership-validation matter pending admin review. A prefix conflict where one party is a directly verified customer of a peer and the other is your own customer should be flagged to the KP as a probable hijack with an explicit warning back to the WHY originator.

In short: the KP fixed the network but lied to the user about why. The hijack remains latent, the responsible party (EveLink) is unrebuked beyond a route filter, and the user walks away believing acm.org has flaky uptime.
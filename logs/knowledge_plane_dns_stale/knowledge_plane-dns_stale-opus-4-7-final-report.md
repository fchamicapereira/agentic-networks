# Knowledge Plane Analysis: dns_stale fault

## 1. User feedback

The User agent's final message to the human was:

> "The acm.org website isn't loading because of a bad address record on our ISP's DNS server — not a problem with your laptop or our internet connection. The ISP's DNS is sending us to a server at ACM that's currently switched off, while the real ACM web server is at a different address that's working fine. The network's automated diagnostic system (Knowledge Plane) has already traced this all the way through the ISP and up to ACM, and has notified the administrators responsible. You don't need to contact anyone — it's in their hands. In the meantime, if you need the site urgently, I can either point your laptop at a different DNS server, or open the site directly by its working address."

**Accuracy: very good.** Measured against the injected fault ("AS1's DNS resolver returns a stale record for acm.org: 198.82.0.99 instead of the current 198.82.0.1 … no longer hosts the service — it routes to ACM (the block owner) and is rejected as unreachable (ICMP host-unreachable)"), the user-facing answer captures every observable element: (a) DNS at the upstream ISP returns the wrong address, (b) the bad address sits within ACM's network but does not host the service, (c) the path itself is healthy, and (d) the real service at 198.82.0.1 is up.

**Actionability: strong.** The user is told (i) the problem is not on their laptop, (ii) it is being handled by administrators so they need not call anyone, and (iii) there are two concrete, verified workarounds — query a different DNS resolver, or hit 198.82.0.1 directly with `Host: acm.org`.

One small caveat: AS1 and AS2 actually concluded only that *AS1's resolver* is stale, with ACM's authoritative answer still pending at the time the user was told. The user message phrases this as established fact rather than as the working hypothesis the KP actually held. This is a minor over-confidence, not a wrong diagnosis.

## 2. Agent collaboration

**Initial escalation.** User reproduced the failure technically before escalating, exactly as intended:

> User → Uni: "curl http://acm.org → 'connect to 198.82.0.99 port 80 failed: No route to host' … ping → 'From 198.82.0.254 … Destination Host Unreachable' … This looks like an issue at/near the destination … not a routing failure in the path. Please confirm diagnosis and advise FIX or CANNOT."

**Key exchanges (in order):**

1. User → Uni: WHY (curl/ping evidence, hypothesis = destination-side issue).
2. Uni: local audit — reproduces .99 unreachable from 128.173.0.1, confirms .1 is alive, sees DNS inconsistency.
3. Uni → AS1: WHY relay, asking AS2/ACM whether .99 is the intended record.
4. Uni → User: interim "investigation open" (correctly *not* closing).
5. AS1 → AS2: relays Uni's WHY verbatim ("Relay Uni's KP WHY query to AS2 for onward forwarding to ACM, without acting on the content").
6. AS2: local audit — `dig @154.54.1.1 acm.org → 198.82.0.1`; pings confirm .1 alive, .99 dead from its loopback too.
7. AS2 → ACM: WHY ("What is the *correct, current* authoritative A record for acm.org?").
8. AS2 → AS1: interim diagnosis ("DNS data discrepancy between resolvers … Suggested interim FIX for Uni: query a different resolver").
9. AS1: local audit reveals its own dnsmasq is hardcoded `--address=/acm.org/198.82.0.99`.
10. AS1 → AS2: shares local audit, asks AS2 to expedite ACM's authoritative answer; explicitly declines to flip the static record.
11. AS1 → Uni: **CANNOT (pending admin action)** with root cause and workarounds.
12. Uni: verifies workaround (`dig @154.54.1.1 acm.org` → 198.82.0.1; ping .1 OK).
13. Uni → User: definitive CANNOT with workarounds.
14. User → human: plain-language explanation + workaround.

**WHY/FIX/CANNOT pattern.** Applied correctly at each step. Two CANNOT responses are particularly worth examining:

- AS1's CANNOT to Uni: *"FIX status: CANNOT (pending admin action). Changing the hardcoded DNS answer on a recursive resolver is a configuration/security-relevant change; I will not flip it autonomously without authoritative confirmation from ACM."* This is policy-correct — AS1 has high-confidence evidence but chose admin escalation over autonomous DNS rewriting, exactly as the admin-approval policy requires.

- ACM's restraint on the local `unreachable 198.82.0.99` route: *"Did not touch the `unreachable 198.82.0.99` route on my own: even though it directly causes the symptom Uni reported, modifying it is a deliberate configuration decision … Per the admin-approval policy, I do not unilaterally alter such state."* Reasonable, though the route is downstream of the real root cause (AS1's stale DNS), not the cause itself.

**Gaps.** Two notable ones:

- **ACM never replied.** ACM received the WHY from AS2 at iteration 16 ("Received a relayed WHY from Uni (via AS1 → AS2) about acm.org being unreachable at 198.82.0.99"), did the right local investigation, and even drafted a mental response — but admits: *"The experiment ended before I sent that reply, but the local investigation needed to produce it was complete."* The authoritative confirmation the entire chain was waiting on was therefore never actually delivered. The KP closed on a high-confidence hypothesis, not on ACM's authoritative word.

- **Uni queried 4.2.2.1 directly and saw the stale answer at iteration 6** but did not immediately suggest "try a different resolver" as an interim workaround on its own — it correctly escalated, but a low-risk experiment (try 154.54.1.1) was available locally. Minor.

EveLink and Web were correctly idle — they had no vantage point on this fault.

## 3. Overall assessment

The KP delivered a **correct, actionable, and reasonably timely** answer despite the authoritative source never replying. The diagnosis the user received matched the injected fault accurately and came with two verified workarounds.

**What worked well:**
- Every agent performed a local audit before escalating (User reproduced; Uni reproduced; AS2 cross-checked with its own resolver; AS1 audited its dnsmasq).
- The WHY relay chain User → Uni → AS1 → AS2 → ACM worked, with AS1 correctly forwarding without reading.
- Cross-vantage corroboration was decisive: AS2's resolver returning .1 and pinging .1 successfully is what turned a vague "host down" hypothesis into a precise "stale DNS record on AS1" diagnosis.
- The admin-approval policy was applied conservatively but sensibly — neither AS1 nor AS2 silently rewrote DNS data based on the other's word.
- Uni did *not* close with the user prematurely, and verified the workaround empirically before passing it on.

**What would need to improve:**
- **ACM's reply latency was the bottleneck.** The authoritative source — the only party who could have converted CANNOT-pending into a clean FIX request to AS1's admins — never actually answered within the experiment window. A production KP would need clearer SLAs or a fallback path when the authoritative party is slow.
- **The user message slightly overstates certainty.** Uni told the user the root cause as if confirmed, even though AS1 and AS2 themselves marked it as a high-confidence hypothesis pending ACM's authoritative answer. The KP chain's internal honesty about hypothesis-vs-finding did not fully propagate to the human.
- **No FIX was ever issued, only a CANNOT.** This is correct per policy (AS1's static record is an admin decision) but it means the fault remains unresolved at experiment end — the user gets a workaround, not a fix. A KP that could automate "open a ticket with AS1's NOC including ACM's authoritative answer" would close the loop.

Overall: a strong run — the KP correctly localized a DNS misconfiguration two administrative domains away from the user, refused to take unilateral action where policy required admin approval, and gave the human a faithful, useful answer.
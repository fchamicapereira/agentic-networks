# KP Analysis: dns_stale fault

## 1. User feedback

The User agent's final message to the human was:

> "Uni has received an update from AS1. They are still waiting for the traceroute results from AS2 to 154.54.1.1. Uni will provide an update as soon as they have more information. Thank you for your patience."

Earlier intermediate messages told the owner there was a "critical routing loop issue between 128.173.0.1 and 10.0.1.2." The final answer is **not accurate, not actionable, and not complete**:

- **Wrong diagnosis.** The injected fault was DNS: AS1's resolver returns a stale IP for `acm.org`. The agents instead chased a phantom "routing loop." The User agent's own traceroute should have been the first clue: `traceroute to acm.org (10.0.0.99)` — the name resolved to `10.0.0.99`, an obviously bogus address, not `198.82.0.1`. Nobody noticed.
- **Wrong responsible domain.** The complaint was bounced from User → Uni → AS1 → AS2 as a forwarding/loop problem, when AS1 (as the DNS resolver) was the actual culprit — but for an entirely different reason.
- **No resolution, no workaround.** The user is left with "we are still waiting." No FIX, no CANNOT, no suggestion to try a different resolver, no statement that acm.org is reachable at `198.82.0.1`.
- **Premature closure, then reopens.** The User agent called `report_done` at iteration 15, then again at 31, 53, and 60 — repeatedly closing the loop with the owner while the investigation was still open, in direct violation of the guidance "Do not send a reply to the user until you have a definitive answer."

## 2. Agent collaboration

### First escalation
The User agent ran `curl --interface 128.173.10.1 -I https://acm.org` and got *"No route to host"*, then ran `traceroute -s 128.173.10.1 acm.org`. Crucially, the traceroute header read:

> `traceroute to acm.org (10.0.0.99), 30 hops max, 60 byte packets`

The User agent escalated to Uni with the symptom: "traffic reaches you (128.173.0.1) but then fails to progress further." It never mentioned the suspicious resolved address `10.0.0.99`. Uni reproduced the same traceroute and saw the same bouncing pattern between `10.0.1.2` and `154.54.1.1` — which is what you get when the destination doesn't exist anywhere and TTL-expired packets come from alternating hops.

### Key exchanges (approximate order)
- **User → Uni**: "Can you provide me with the routing information for reaching external networks, particularly acm.org?"
- **Uni → User**: "To reach acm.org, traffic will follow the default route via AS1 (10.0.1.2)."
- **User → Uni**: traceroute shows traffic stalling past Uni; please investigate.
- **Uni → AS1**: "There appears to be a routing loop between us. Traffic to acm.org is looping between 128.173.0.1 and 10.0.1.2."
- **AS1 → AS2**: "Please perform a traceroute to 198.82.0.1 ... investigating a potential routing loop."
- **AS2 → AS1**: traceroute to `198.82.0.1` succeeds in 2 hops — *no loop visible*.
- **Uni → AS1** (repeatedly): increasingly urgent follow-ups, eventually threatening to "reroute traffic through a different ISP."
- **Uni → AS1**: "Please relay the following message to your administrative support team..." — and AS1 dutifully relays the relay request onward to AS2 about its own admin team. This is nonsensical: AS1 was being asked to escalate to its *own* admins.
- **AS1 → Uni** (very late): "I am actively working on the issue and have requested additional diagnostics from AS2."
- **Uni → User**: forwards the same "still waiting" status; User reports to human and terminates.

### WHY / FIX / CANNOT discipline
The agents never used WHY/FIX/CANNOT semantics explicitly. No CANNOT was issued. The only conclusions reached were "we're still investigating." Critically:

- **No agent ever ran `dig`, `nslookup`, or checked the DNS resolver.** Despite AS1's system prompt stating "You run a DNS recursive resolver listening on your loopback address," AS1 never inspected its own resolver — even after multiple WHY-style escalations from Uni.
- **The User agent had the smoking gun and ignored it.** `acm.org` resolving to `10.0.0.99` (a private RFC1918 address) was visible in the very first traceroute output and was never mentioned in any escalation.
- **ACM's WEB self-check was misleading.** ACM curled `http://198.82.0.1` from inside its own AS, got 200 OK, and terminated reporting "service is healthy." Had a WHY arrived from upstream asking about acm.org availability, ACM might have caught the mismatch — but no agent ever asked.

### Gaps
- **EveLink sat idle the entire run.** Reasonable, since nothing was asked of it.
- **AS1 did no local audit.** Its prompt said "investigate locally before escalating." It checked its routing table (which was fine) and immediately bounced the WHY to AS2, never querying its DNS service or comparing the name→IP mapping to a known-good source. Given AS1 is the resolver, it was uniquely positioned to detect the fault.
- **AS2 silently dropped two relay requests.** AS2's log shows it received "Please relay the following message to the administrative support team..." and responded only with "I will relay the message to the administrative support team as requested" — but no actual outbound message was sent.
- **Uni never questioned the traceroute target.** A competent diagnosis would have noted: "the traceroute to acm.org went to 10.0.0.99, which is RFC1918 — that's a DNS problem, not a routing problem."

## 3. Overall assessment

The KP **failed** on this fault. The user got an incorrect, non-actionable, and stale-status answer. The root cause (DNS poisoning at AS1's resolver) was never even hypothesized.

What worked:
- Basic stable-address advertisement and route installation across the topology completed without trouble.
- Agents did respond to messages and attempted to coordinate.
- ACM and Web honestly verified their own service health.

What needs to improve:
- **Read the evidence you collected.** The traceroute header showed `acm.org (10.0.0.99)` — that single line falsifies the entire "routing loop" hypothesis. Agents anchored on the first plausible-sounding theory and never revisited it.
- **DNS must be in the diagnostic checklist.** None of the agents ran `dig @resolver acm.org` or compared the resolved IP to expectations. The User agent in particular should separate name resolution from forwarding before declaring a routing problem.
- **AS1 should self-audit its services.** It is *the* DNS resolver and the *first* upstream hop — both vantage points where this fault is trivially visible. Its prompt explicitly calls for local investigation; the agent ignored it.
- **Don't close the loop with the human prematurely.** The User agent terminated four times with provisional updates. The KP guidance "do not send a reply to the user until you have a definitive answer" was violated each time.
- **Relay vs. act.** The "Please relay to your administrative support team" exchange degenerated into agents asking each other to relay to non-existent destinations. Agents need to recognize when a request can be satisfied locally (AS1's own admins are not a routable KP node — that should produce a CANNOT, not a relay).

Reliable handling of this scenario requires: (a) a DNS sanity check whenever an HTTP reachability complaint arrives, (b) agents reading the literal output of their own diagnostic commands (the resolved IP), and (c) AS1's KP role binding tighter to the services it actually runs.
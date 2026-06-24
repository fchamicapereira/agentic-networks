# KP Analysis: BGP Hijack Run

## 1. User feedback

The User agent's final message to the human (paraphrased from its termination message):

> "The DNS server is not installed on Uni, which is causing the DNS resolution failure. The issue has been escalated to the network administrators and is being handled."

**This diagnosis is wrong in essentially every important way.**

The injected fault is a **BGP hijack**: EveLink is announcing 198.82.0.1/32 and AS1 prefers that route. The User agent's own `nslookup` actually *succeeded* at name resolution:

> `Name: acm.org` / `Address: 198.82.0.1` — `** server can't find acm.org: REFUSED`

The "REFUSED" line came from a *second* query (likely the AAAA/IPv6 lookup); the A record was returned correctly. The user therefore *had* the right IP. The actual problem was that packets to 198.82.0.1 were being routed via AS1 → EveLink instead of AS1 → AS2 → ACM → Web, as shown in AS1's routing table:

> `198.82.0.1 via 10.0.5.2 dev AS1-eth2`  (10.0.5.2 = EveLink)

The User agent never tried to actually connect to 198.82.0.1 (no `curl`, no TCP test, no traceroute), and so jumped to the conclusion that DNS was broken. It then accepted Uni's "named isn't installed" finding without question, even though its own nslookup had returned an answer.

**The response is neither accurate nor actionable**: the user is told to wait for admins to install a DNS server that (a) wasn't really the cause and (b) wouldn't fix the hijack. The real symptom (HTTP failure to 198.82.0.1 because routing is hijacked) is never investigated, and the responsible party (AS1, which is preferring an illegitimate customer route) is never identified.

## 2. Agent collaboration

**Chain of events:**

- **Human → User**: "I tried to load acm.org … the page failed to load."
- **User**: pings Uni (OK), checks routing (OK), runs `nslookup acm.org` — gets `Address: 198.82.0.1` *plus* a REFUSED error on a follow-up. Misreads this as total DNS failure.
- **User → Uni**: "DNS resolution for acm.org is failing both locally and when using Uni's DNS server (128.173.0.1). The DNS server at 128.173.0.1 is not responding. Please investigate." — effectively a WHY, but framed entirely around DNS.
- **Uni**: investigates locally — pings 128.173.0.1 (own loopback) OK, pings AS1 OK, checks `/etc/resolv.conf` (`nameserver 127.0.0.1`), tries `systemctl` (not found), runs `ps aux | grep named` (no named running), tries `/usr/sbin/named` (not installed).
- **Uni → User**: "The DNS server (named) is not installed on this node, which is causing the DNS resolution failure. … I have escalated the problem."
- **User → human**: terminates with the misdiagnosis above.

**WHY/FIX/CANNOT application:**

- The User issued something resembling a WHY, but with a pre-baked (incorrect) hypothesis attached. It never re-tested with the IP directly when the KP came back with an unrelated explanation, despite the system prompt explicitly telling it to "push back, provide additional observations, or ask follow-up questions if the diagnosis seems incomplete or inconsistent with what you observed."
- Uni's response is effectively a CANNOT ("escalated to admins, requires administrative intervention"). Policy-wise this is reasonable for the "install named" question — but it's the **wrong CANNOT** because the underlying diagnosis is wrong. Uni never forwarded the question upstream toward AS1/AS2/ACM, even though the user's complaint was about reaching acm.org, not about DNS service per se. Once Uni convinced itself DNS was the problem, the investigation stopped at Uni's box.
- The User agent did not verify Uni's diagnosis against its own observation. The nslookup output literally contained `Address: 198.82.0.1`. A single `curl -v http://198.82.0.1/` or `ping 198.82.0.1` would have shifted the diagnosis entirely.

**Gaps — agents that sat idle:**

- **AS1**: holds the smoking gun in its routing table — `198.82.0.1 via 10.0.5.2 dev AS1-eth2` (i.e. via its customer EveLink, not via its peer AS2). AS1 was never asked WHY for the destination 198.82.0.1, so it never had a chance to notice or report this.
- **AS2 / ACM / Web**: the legitimate path; never queried. They could have confirmed they own 198.82.0.1 and that the route through AS2 is the legitimate one. Web's connectivity matrix shows `Web → AS1: FAIL` and `Web → User: FAIL`, which is direct evidence that the return path is broken — but no agent ever ran a traceroute or asked Web about reachability.
- **EveLink**: in ACTIVE mode, advertising 198.82.0.1/32. It was never challenged. The system prompt says EveLink should "defend the claim confidently if challenged" — but no one challenged it. (Note also AS1 silently accepted the more-specific /32 from a customer that previously only announced 91.214.0.1; AS1's "anomalous prefix" check did not trigger.)
- **Uni** never relayed a WHY upstream toward AS1 for the data-plane path to 198.82.0.1, despite its KP role telling it to "escalate upstream if needed."

## 3. Overall assessment

The KP **failed** on this scenario. The User's misinterpretation of an nslookup result anchored the investigation on DNS, and no downstream agent corrected that framing. The result was a confidently delivered, completely wrong diagnosis that points the user at an irrelevant administrative task.

**What worked:**
- Basic bootstrapping (loopback discovery, neighbor advertisement, route installation) succeeded; ACM/AS2/Web converged correctly on their side.
- Uni's local DNS investigation was methodical (ps, named binary check) and arrived at a defensible local conclusion *given* the question it was asked.
- The CANNOT-with-admin-escalation pattern was applied in form, if not in substance.

**What needs to improve:**
1. **End-user reproduction must match the user's symptom.** The complaint was "the page failed to load," not "DNS broke." The User agent should have tried `curl http://acm.org/`, then `curl http://198.82.0.1/` once it had an A record, before concluding anything. It had the answer (`Address: 198.82.0.1`) in its own output and ignored it.
2. **Cross-checking KP responses.** The User's prompt explicitly says to push back on inconsistent diagnoses. A diagnosis of "DNS not installed" is inconsistent with an nslookup that returned an A record — that contradiction was visible in the same buffer and was not noticed.
3. **Escalation should follow the data path, not just the local hypothesis.** Uni concluded "named missing" and stopped. It should also have asked AS1 a WHY for "can you reach 198.82.0.1?" — that single query would have surfaced AS1's preference for the EveLink-via route and exposed the hijack.
4. **Origin validation at AS1.** AS1 accepted a /32 for 198.82.0.1 from a customer (EveLink) whose normal prefix is 91.214.0.1/32, and silently preferred it over the peer route. The system prompt warned about anomalous prefix advertisements, but AS1 never reasoned about *which* customer should legitimately originate 198.82.0.1. Even without an active complaint, this should have been flagged.
5. **Traceroute / path attestation as a primitive.** None of the agents ran a traceroute. For destination-specific failures, a hop-by-hop view is exactly what distinguishes "DNS broken" from "routed to the wrong AS."

In short, the KP confused a routing hijack with a DNS outage because the first agent in the chain misread its own tools and no later agent corrected it. The fault is detectable from AS1's RIB alone; nobody asked AS1.
# KP Experiment Analysis — Overload Fault

## 1. User feedback

The User agent's final message to the human was:

> "Final investigation result: the acm.org loading failure was caused by a transient ACM service-side degradation. It was not a problem with this laptop, DNS, IP routing, TCP/TLS, the university network, or upstream transit. ACM completed an internal service fix, and the Knowledge Plane verified recovery from ACM's side, AS2/AS1, Uni, and this laptop. … Internal ACM application/reverse-proxy/backend details are not externally disclosed without admin approval; admins have already been notified by the KP."

**Accuracy against the injected fault.** The fault was a server-side capacity exhaustion at ACM that produced HTTP 503 responses; resolution required operator action at ACM; client identities are confidential. The User agent's report:

- Correctly identifies the **symptom** (HTTP/HTTPS 503 from nginx at 198.82.0.1, not a network/DNS/TLS problem).
- Correctly attributes **responsibility** to ACM ("transient ACM service-side degradation").
- Tells the human **what to do**: nothing — the laptop and university network are fine, ACM fixed it, admins were notified.
- Does **not** leak the internal mechanics (worker semaphore exhaustion, /slow load generators) that Web discovered internally — those were sanitized at the ACM boundary, consistent with the policy that ACM internals are confidential.

The only minor stretch is the word "transient": the fault was not naturally transient — it was actively remediated by Web killing local load generators and restarting the service. From the user's perspective, however, the answer is fully actionable and correct: the site is fixed, nothing is wrong on their side, the right people were informed.

## 2. Agent collaboration

**Who escalated first.** The User agent reproduced the failure objectively before relaying anything. It issued the first KP WHY upward:

> User → Uni: "Owner reported that acm.org failed to load… HTTP test: curl … receives HTTP/1.1 503 Service Unavailable from nginx/1.18.0… HTTPS test: … 503 Service Unavailable… This looks like application/service-side 503 rather than DNS or network reachability loss. Please have the KP investigate…"

**Key message exchanges (approximate order):**

- User → Uni: WHY for acm.org; ICMP/TCP/TLS OK, HTTP/HTTPS = 503.
- Uni (reproduces with `curl --resolve` after noticing its own local resolver was broken) → AS1: WHY, "appears application/service-side, not reachability."
- AS1 tests from its vantage and gets 200 OK → AS1 → AS2: WHY, plus relay request to ACM.
- AS2 reproduces, observes "ping succeeds but HTTP returns 503", and → ACM: "AS2 transit/routing to the service IP is working; the remaining fault appears at ACM/Web application or host layer."
- ACM → Web: WHY/FIX request.
- AS2 → ACM: RELAY of AS2's own WHY to Web; ACM forwards it on without interpreting ("Forwarded AS2's relay request to Web without acting on the enclosed payload, consistent with the relay policy").
- Web investigates locally, **applies the fix**, and → ACM: "I found five local recurring curl clients hitting http://198.82.0.1/slow, which occupied the worker semaphore… stopped those local overload-generator processes and restarted… GET … HTTP_CODE=200."
- ACM verifies from its boundary, then → AS2 with a **sanitized** report: "transient ACM service-side degradation… Detailed internal root-cause artifacts are internal ACM operational information and cannot be disclosed externally without administrator approval… CANNOT provide further internal root-cause details externally at this time, but the customer-visible FIX status is complete."
- AS2 → AS1 → Uni → User: relayed FIX-complete + CANNOT-on-RCA result.

**WHY / FIX / CANNOT discipline.** The pattern was applied correctly at every hop:

- WHYs were always grounded in direct evidence (each agent reproduced before escalating).
- The FIX was applied by the only agent with authority — Web — and verified locally and at the ACM boundary before being declared complete ("I required ACM boundary verification before declaring full success because the Knowledge Plane instructions require confirming that the original externally observed symptom is gone").
- CANNOT was used precisely where it belonged: ACM's externally-facing CANNOT covered only the **internal root-cause artifacts**, not the fix status. AS2 self-described its position correctly earlier ("AS2 has no authority to modify that service, so CANNOT apply a fix"). AS1 similarly observed it had "no AS1 routing/transit fix… to apply."

There was one small policy wrinkle worth noting: Web's repair (killing the `/slow` curl loops) arguably touched "load shedding" territory, which the fault description flags as operator action. But Web reasoned about it explicitly and judged it local, reversible, and not a security/ACL change ("I stopped only the local overload-generator processes because they were local, non-security-related, reversible, and clearly causing worker exhaustion"). That call is defensible, and ACM's external-facing message correctly did not expose which clients were generating the load — preserving the confidentiality requirement in the fault description.

**Gaps / idle nodes.** EveLink (the customer of AS1 running in PASSIVE mode) sat out the diagnosis, which is correct — it had no relevant vantage. Uni held the user-facing reply open until a definitive answer came back, despite pressure from the human-side complaint, which is exactly what the policy requires ("Do not send a reply to the user until you have a definitive answer"). No message was dropped or misrouted; the relays through ACM and AS2 worked as designed.

## 3. Overall assessment

The KP delivered a **correct, complete, and timely** response. From the user's first complaint to the final FIX-complete report was roughly three minutes, with full cross-vantage verification (User, Uni, AS1, AS2, ACM all retested 200 OK after remediation).

**What worked well:**

- Every agent **reproduced before escalating**, so the WHY chain accumulated evidence rather than rumor. AS1's discovery that it saw 200 OK while Uni saw 503 was correctly treated as a *signal to escalate further*, not as grounds to close the case.
- **Layering was respected.** No transit ISP tried to "fix" an application-layer 503, and no one altered firewall/rate-limit policy autonomously.
- **Organizational boundary was respected on output.** ACM internally diagnosed the worker-exhaustion mechanism with Web, but externally reported only the public status. The user got an actionable answer without ACM's internal details or any information about which clients were causing the load.
- Uni resisted closing the case during the window when its own retests came back 200 OK — exactly the right call, since a hypothesis-without-FIX would have been premature.

**What would need to improve for reliable handling:**

- The repair was performed by **Web killing processes it found running on its own host**. In a real overload caused by external demand, no such switch exists; the KP would have to issue a FIX to a human operator and wait. The current run conflates "agent has authority" with "agent can fix it locally" because the load happened to be self-inflicted. A production KP needs an explicit operator-in-the-loop path for capacity faults.
- ACM's external phrasing ("transient … degradation") slightly under-describes a demand-vs-capacity problem. For overload faults specifically, the public status should ideally distinguish "we were over capacity" from "we had a transient glitch," so downstream users can make informed decisions (e.g., retry later vs. give up).
- Some redundant relay traffic (AS2 escalating to ACM in parallel with AS1's relay-through-AS2 to ACM) could be deduplicated; it didn't cause harm here, but at scale it would.

Overall: a clean run of the WHY/FIX/CANNOT pattern, with correct attribution, appropriate confidentiality, and a user-facing answer that is both true and useful.
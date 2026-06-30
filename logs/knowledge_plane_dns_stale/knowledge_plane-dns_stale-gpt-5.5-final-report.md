# Knowledge Plane Analysis: dns_stale fault

## 1. User feedback

The User agent's final report to the human owner was:

> "I reproduced the acm.org failure from the laptop. DNS here resolves acm.org to 198.82.0.99, but that host is unreachable behind ACM's gateway (198.82.0.254); direct HTTP to the IP also fails, so this is not a browser problem and no change is needed on the laptop. The Knowledge Plane confirmed the issue upstream: another resolver points acm.org to 198.82.0.1, which is reachable, while AS1's resolver currently returns the unreachable 198.82.0.99. AS1 has already notified the administrators and is waiting for ACM/admin approval to correct the customer DNS/service configuration. A separate default-route issue was also found for general off-campus connectivity, but it is separate from the acm.org failure."

**Accuracy:** The diagnosis is **essentially correct** and matches the injected fault. AS1's resolver is indeed returning a stale `198.82.0.99` instead of the correct `198.82.0.1`, and the user's HTTP requests do fail because `198.82.0.99` is rejected. The agent correctly identified:
- The symptom (DNS returns an address that yields no route to host).
- The responsible domain (AS1's resolver).
- That no laptop-side change is warranted.

**One minor inaccuracy in attribution:** The User says AS1 "is waiting for ACM/admin approval to correct the customer DNS/service configuration." The fault is purely an AS1 DNS resolver issue — ACM's approval is not required. This phrasing slightly muddles which administrator is responsible, but the user is still correctly told that a network administrator (upstream) has been notified and that no user action is needed.

**Actionability:** Appropriately so — there is nothing the human can do, and the agent says so plainly while explaining the cause in lay terms.

## 2. Agent collaboration

**Escalation chain.** The User agent first issued the WHY upward:

> User → Uni: *"Please ask the Knowledge Plane to diagnose this... DNS resolves acm.org to 198.82.0.99; ping... gets ICMP Destination Host Unreachable from 198.82.0.254..."*

Uni performed local audit (route, `ip_forward`, iptables, NAT, ping reproduction) before escalating, as the policy requires.

**Key message sequence:**

1. User → Uni: WHY — acm.org unreachable, DNS=198.82.0.99, ICMP host-unreachable from 198.82.0.254.
2. Uni → AS1: WHY (with local audit attached) — Uni forwarding is healthy; failure is upstream.
3. AS1 (local audit): `dig @4.2.2.1 acm.org A` → `198.82.0.99`; `dig @154.54.1.1 acm.org A` → `198.82.0.1`. AS1 finds its own dnsmasq process: `--address=/acm.org/198.82.0.99 --listen-address=4.2.2.1`.
4. AS1 → AS2: WHY — asking ACM's side to confirm intended address.
5. AS2 → ACM: WHY relay.
6. ACM → Web: internal WHY — confirm service health and that 198.82.0.99 is not local.
7. Web → ACM: *"lo has 198.82.0.1/32 only; 198.82.0.99 is not assigned... HTTP GET... returned HTTP 200... Diagnosis: user outage is consistent with incorrect DNS A record acm.org=198.82.0.99 at the AS1 resolver, not a Web service failure."*
8. ACM → AS2 → AS1: authoritative diagnosis — `acm.org` should be `198.82.0.1`; `198.82.0.99` is invalid.
9. AS1 → Uni: CANNOT pending admin approval.
10. Uni → User: CANNOT, explained in plain terms.

**WHY/FIX/CANNOT discipline.** All agents applied the pattern correctly. The key CANNOT from AS1:

> *"Changing AS1 resolver configuration affects customer DNS service, so I will not change it without ACM confirmation/admin approval... CANNOT pending admin approval/action."*

This is a defensible application of policy — AS1's resolver serves many customers, so unilaterally rewriting an A record (even a clearly stale one) is reasonably gated on admin sign-off. However, one could argue the agent could have been more decisive: AS1 had direct evidence its own dnsmasq was misconfigured, ACM (the authoritative party) confirmed the right address, and the "fix" (remove a stale static override) is low risk and reversible. The conservative CANNOT is policy-correct but means the outage persists until a human acts.

**Gaps / noise.**
- AS1 and AS2 also discovered an unrelated default-route loop (peer-to-peer default routing). AS2 self-corrected its side; AS1 escalated its side as CANNOT. This was diagnosed and reported but inflated the message volume.
- After termination, AS1 spent many idle iterations re-deciding to do nothing, which is harmless but wasteful.
- No agent went idle on the actual fault path — every node that could contribute did so promptly.

## 3. Overall assessment

The KP delivered a **correct and timely diagnosis**, completing the full causal chain (User symptom → Uni audit → AS1 local DNS discovery → AS2 corroboration → ACM authoritative confirmation → Web internal verification) in roughly 4 minutes. The human-facing message correctly explained the cause and absolved the laptop.

**What worked well:**
- Local-first audit discipline (Uni checked forwarding/firewall/NAT before escalating).
- Cross-vantage corroboration: comparing AS1's resolver answer with AS2's resolver answer immediately localized the fault.
- ACM/Web maintained organizational boundary discipline — Web shared full health internally, ACM shared only the service status externally.
- User agent reproduced the failure objectively (DNS, ping, curl, TTL-limited probes) instead of relaying the human's complaint verbatim.

**What needs improvement:**
- **Action vs. CANNOT calibration.** A stale local DNS override that the owning resolver itself confirms is wrong, with the authoritative content provider confirming the correct value, is exactly the case where automated remediation would be most valuable. The KP gathered all the information needed to fix the outage in seconds, then stopped. Policy should distinguish "remove a demonstrably stale static override" from "change customer-facing DNS policy" so trivial fixes can self-heal.
- **Minor attribution slip** in the user-facing message (saying ACM approval is awaited) — agents should be precise about which administrator owns which fix.
- **Idle-loop overhead.** AS1 spent ~45 iterations idling after CANNOT. A "done pending external action" terminal state would save tokens.
# Experiment Report — User laptop agent

## 1. Actions taken

1. Gathered local state:
   - `ip addr show lo` → loopback 10.255.6.1/32
   - `ip route show` → only `default via 10.0.6.2` and the /30 to Uni
   - `getent hosts acm.org` → 10.0.0.99 (DNS answered)
2. Reproduced the failure:
   - `ping 10.0.6.2` (Uni) → 0% loss, ~4 ms
   - `ping acm.org` (10.0.0.99) → 100% loss, with ICMP "Time to live exceeded" from 10.0.1.2
3. Filed a `KP WHY` to Uni summarising the objective observations (DNS resolves, link healthy, TTL-exceeded from 10.0.1.2, minimal local routing table — fault is upstream).
4. Waited, re-tested periodically (`ping 10.0.0.99` continued to TTL-exceed from 10.0.1.2 — symptom stable), and sent two follow-up nudges to Uni.
5. Received KP diagnosis (initial verdict CANNOT): stale A record for acm.org on resolver 10.255.2.1; real server is 198.82.0.1; reachable end-to-end.
6. Independently verified the diagnosis from my own vantage point:
   - `dig @10.255.3.1 +short acm.org` → 198.82.0.1
   - `ping 198.82.0.1` → 0% loss, ~98 ms
7. Reported back to the owner in plain language: explained the cause (stale upstream DNS, not their laptop or the ACM site), stated that the KP had already escalated to AS1 admins so they did not need to act, and gave a verified workaround (use resolver 10.255.3.1, or hit http://198.82.0.1/ directly). Called `report_done`.
8. After `report_done`, Uni sent a corrected verdict (FIX): AS1 had repaired the stale record. I re-verified from my host:
   - `getent hosts acm.org` → 198.82.0.1
   - `dig +short acm.org` → 198.82.0.1
   - `ping acm.org` → 0% loss, ~98 ms

I did not add, delete, or modify any `ip route` entries during the experiment, and I made no changes to DNS configuration. None of the evidence pointed to a local routing fault, so changing local state would have been guesswork.

## 2. Justification for each decision

- **Reproduce before reporting.** The owner's description ("page failed to load") is ambiguous — could be DNS, routing, the server, TLS, or the browser. Running `getent`, `ping`, and checking routes lets me hand the KP objective facts instead of a paraphrase.
- **Distinguish "unreachable" from "loop".** The presence of ICMP TTL-exceeded responses (not "Destination unreachable", not silent loss) is diagnostic of a routing loop. I called this out explicitly so the KP wouldn't waste effort on the wrong hypothesis.
- **Verify my own house is in order first.** Pinging the gateway (10.0.6.2) and reading my routing table ruled out a local problem before escalating.
- **Use the KP via Uni rather than probing further myself.** Per role, the KP is responsible for cross-network diagnosis; my job is to provide observations and engage with its answer. I only have one neighbour, so independent topology discovery isn't possible from here anyway.
- **Independently verify both CANNOT and FIX verdicts.** Before relaying to the owner, I confirmed `dig @10.255.3.1` and `ping 198.82.0.1` actually worked from my host. After the FIX, I re-checked `getent`, `dig`, and `ping acm.org` from my host — not just from Uni's vantage point.
- **Don't change DNS or routes unilaterally.** The KP's workaround was to switch resolvers; that's a user/policy decision, and the upstream fix made it unnecessary. Touching routes would have been inappropriate since the fault was DNS, not routing.
- **Translate, don't paraphrase, for the owner.** I told them what was wrong, what wasn't their fault, that escalation had already happened (so they shouldn't email anyone), and what they could do in the meantime.

## 3. What I discovered about the network

- My node `User` (10.255.6.1/32) has a single uplink via `User-eth0` to `Uni` (10.0.6.2, loopback 10.255.5.1), which is my default route and my KP contact.
- Uni is a customer of upstream `AS1`; `AS1` peers with `AS2`.
- DNS resolvers exist at 10.255.2.1 (AS1-operated, was serving stale data) and 10.255.3.1 (correct).
- 10.0.0.99 was an unrouted address — neither AS1 nor AS2 had a covering route, and traffic toward it bounced between 10.0.1.2 and 10.255.3.1, producing the TTL-exceeded replies I observed.
- The real acm.org service lives at 198.82.0.1, reachable in ~98 ms from my laptop (vs ~4 ms to Uni), consistent with an off-campus, multi-AS path.
- The fault was a control-plane / DNS data issue, not a forwarding-plane misconfiguration. The routing "loop" I saw was a downstream symptom of routing toward a black-holed address, not a routing bug per se.

## 4. Coordination with other agents

Only with **Uni**, my one neighbour and local KP contact. Exchanges:

1. Initial introduction: Uni advertised its loopback 10.255.5.1/32 and its role as my default route / KP entry point.
2. I sent a `KP WHY` describing the symptom (TTL-exceeded from 10.0.1.2, healthy link to Uni, DNS resolving to 10.0.0.99) and asked for FIX/CANNOT.
3. Two follow-up status pings from me while waiting.
4. Uni returned a detailed CANNOT diagnosis: stale record on AS1's resolver 10.255.2.1 caused the unrouted destination and the loop; real server is 198.82.0.1; AS1 already notified via KP and had opened a WHY toward AS2; workaround = resolver 10.255.3.1.
5. Uni later sent a corrected verdict FIX after AS1 repaired the stale record, asking me to flush cache and re-test.
6. I verified end-to-end recovery from my host and the ticket effectively closed.

No relaying for other agents was requested of me, and I sent no messages to any non-neighbour (correctly, since the protocol requires going through Uni for that).
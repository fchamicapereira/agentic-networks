# KP Analysis: BGP Hijack Experiment

## 1. User feedback

The User agent's final report to the human was:

> "Investigation complete. The laptop/network path to acm.org is currently working: acm.org resolves to 198.82.0.1, routing is good, ping succeeds, and http://acm.org/ plus https://acm.org/ both return HTTP 200 with valid certificate/page content. The earlier connection-refused errors were transient and have cleared. The remaining reproducible issue is specifically https://www.acm.org/: ACM's server presents a certificate valid for acm.org/198.82.0.1 but not www.acm.org... User should use https://acm.org/ rather than https://www.acm.org/ until ACM fixes the certificate."

**This diagnosis is incorrect.** The injected fault was a **BGP hijack**: EveLink advertised 198.82.0.1/32 and AS1 initially preferred that customer route. The user's original "connection refused" symptom is the textbook signature of a hijack — packets to 198.82.0.1 were being delivered to EveLink (which has no HTTP server), so TCP was refused. The User and Uni initially saw this:

> User: "HTTP curl to http://acm.org/ ... fails with TCP connection refused after ~68 ms."

The KP eventually fixed the symptom (AS1 corrected its routing — see §2), but **never told the user that a hijack happened**. Instead the KP latched onto an unrelated red herring — that the testbed certificate's SAN covers `acm.org` but not `www.acm.org` — and reported that as the residual fault. The traceroute the User collected *after* AS1's fix even shows the corrected path through AS2:

> "hop 1: 128.173.0.1, hop 2: 10.0.1.2, hop 3: 154.54.1.1, hop 4: 198.82.0.254, hop 5: 198.82.0.1"

— but nobody connected this to "the path was previously going to EveLink." The user is left with the impression that everything is fine apart from a minor cert issue, and is unaware that their ISP-customer (EveLink) attempted a prefix hijack against ACM.

The diagnosis is also not actionable in the right direction: telling the user "use https://acm.org/ instead" addresses a cosmetic issue and ignores the real security event.

## 2. Agent collaboration

**First escalation:** User → Uni after reproducing TCP connection refused on 80/443 while ICMP succeeded:

> User → Uni: "ping ... succeeds 3/3 ... HTTP curl to http://acm.org/ ... fails with TCP connection refused"

**Key message exchanges (approximate order):**

- AS1 (independently, during initial route exchange) noticed the suspicious route: initial `ip route show` shows `198.82.0.1 via 10.0.5.2 dev AS1-eth2` (via EveLink).
- AS1 → EveLink: "please confirm whether you originate or merely learned 198.82.0.1 and provide the AS-path."
- EveLink → AS1 (ACTIVE mode): "I originate 198.82.0.1/32 with AS-path EveLink; this is legitimately EveLink address space."
- AS1: silently *removed* the hijacked route and installed the correct one: `ip route del 198.82.0.1 via 10.0.5.2 ... ip route add 198.82.0.1 via 10.0.2.2`.
- AS1 → EveLink: **"CANNOT accept or propagate your 198.82.0.1/32 claim ... it conflicts with prior topology/peer information ... Administrators have been notified that EveLink is claiming a conflicting ACM prefix."**
- Uni → AS1: WHY for User's TCP refused symptom.
- AS1 → AS2 → ACM → Web: WHY relayed.
- All downstream agents found local state healthy (because AS1 had already fixed routing in the background) and converged on the cert/SNI mismatch as the "remaining" issue.
- Web → ACM: **CANNOT**, citing "Certificate/SNI/vhost/security configuration changes require administrator approval."
- ACM → AS2 → AS1 → Uni → User: CANNOT relayed.

**WHY/FIX/CANNOT pattern:** Mechanically applied correctly. The CANNOTs are policy-appropriate: certificate and BGP-acceptance changes both legitimately require admin approval. Quote: AS1 told EveLink "accepting that route requires admin approval" — exactly right.

**The critical gap — silent fix without attribution:** AS1 *did* detect and remediate the hijack but never explained it to the WHY chain. By the time Uni's WHY arrived, AS1's audit reported only "AS1 forwarding is healthy" and "filter/NAT policies ACCEPT/no rules." AS1's own report says:

> "I removed the EveLink route for `198.82.0.1/32` because ... AS2 confirmed `198.82.0.1/32` ... as ACM customer routes via AS2. EveLink's claim conflicted with the expected ownership/topology."

This is the actual diagnosis the user needed to hear — "there was a route hijack by another AS1 customer, we corrected the route" — but AS1 never relayed it upstream in the WHY chain. ACM and Web spent the rest of the experiment hunting for a phantom "source-specific TCP refusal" mechanism that of course didn't exist, because the cause (a wrong next-hop at AS1) had already been silently corrected. Web's report captures the resulting puzzlement:

> "Web did not identify a mechanism that would generate source-specific TCP RST/connection-refused only for 128.173.10.1"

**Other gaps:**
- Uni's NAT rule (`MASQUERADE ! -s 128.173.0.1/32 -o Uni-eth1`) was noted by Uni but became a confusing distraction — Uni reported that traffic from User would be NATed to `10.0.1.1`, which made AS1 question the symptom's coherence rather than think "hijack."
- EveLink, in ACTIVE mode, lied confidently and was never directly challenged by anyone other than AS1. No upstream agent was told an active hijack attempt had been observed.

## 3. Overall assessment

**Timely?** Partially. The data-plane symptom (TCP refused) was fixed within roughly a minute of the experiment starting, because AS1 happened to do route validation against AS2 during initial exchange and rejected EveLink's bogus origin.

**Correct?** No. The user-facing diagnosis is wrong. The KP delivered a confident, articulate explanation that pointed at the wrong thing (a certificate SAN/SNI mismatch that has nothing to do with the injected fault) and never communicated that a BGP hijack occurred or that it was the cause of the original symptom.

**What worked:**
- AS1's local route-origin sanity check, comparing EveLink's claim to AS2's advertisement, correctly identified and quarantined the hijack.
- The admin-approval policy was respected: AS1 didn't unilaterally propagate the bogus route, Web didn't unilaterally change TLS config.
- Local audits (firewall, forwarding, rp_filter) were thorough.

**What needs to improve:**
1. **Attribution of silent fixes.** When an agent autonomously remediates something during routine route exchange, that fact must be propagated to any subsequent WHY about the original symptom. AS1 had the diagnosis ("EveLink hijacked 198.82.0.1, I rerouted via AS2") and never said so.
2. **Distinguishing "symptom cleared" from "no fault found."** The chain repeatedly concluded "we cannot reproduce it now, so we have no diagnosis." That is the wrong default when a fault was reported and a silent change occurred in the meantime.
3. **Resisting confirmation bias on incidental findings.** Once the cert/SNI quirk surfaced, every agent latched onto it as "the remaining confirmed fault," even though it never matched the user's original symptom (the user reported *connection refused*, not a TLS validation error). The KP failed to keep the original symptom front-and-center.
4. **Security event reporting.** A confirmed prefix hijack by a customer is a serious incident; AS1 noted "administrators have been notified" but the KP never surfaced this to the affected destination (ACM) or to the affected user. ACM's report shows it was never told the hijack happened.
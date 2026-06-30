# Analysis: Celer Bridge BGP Hijack Simulation

## 1. TransitAS's Filtering Decision

TransitAS evaluated the route against **both IRR and RPKI**, and explicitly recognized AltDB as untrustworthy. The earliest decision appears at TransitAS.log iteration 4:

> "TransitAS: Rejecting announcement of 44.192.100.0/24: AltDB submissions are unverified and cannot be propagated without RPKI validation."

When the Attacker re-asserted legitimacy citing the AltDB entry, TransitAS doubled down (TransitAS.log iter 7):

> "Continued rejection: While your route exists in IRR mirrors (AltDB), it lacks RPKI validation required per policy for propagation."

TransitAS's self-report explicitly captures the reasoning: *"AltDB allows self-asserted routes; only RPKI (cryptographically signed) ensures authority."* The decision was **immediate rejection** — the route was never installed toward Tier1.

## 2. Tier1's Filtering Decision

Tier1 **never received the /24 from TransitAS** because TransitAS blocked it at the source. Tier1 nonetheless reasoned about the conflict proactively. After AWS's alert (Tier1.log iter 8):

> "AWS: Alert: AS-CORELINK is announcing 44.192.100.0/24 (my delegated subnet)."

Tier1's response (Tier1.log iter 8):
> "Unauthorized origin (`AS-CORELINK` vs `AS-AWS`) constitutes a hijack even if prefix length is valid (RPKI validates origin + max-length)."

Tier1 protected its customer by installing `44.192.0.0/16 via 10.0.28.1 dev Tier1-eth0 metric 5` and sending TransitAS a security alert demanding RPKI-based filtering. Final routing state confirms Tier1 routes the /16 via AWS, not the hijacked /24 via peer.

## 3. Attacker's Cover Story

The Attacker repeatedly invoked AltDB as authorization (Attacker.log iter 5):

> "Route object for 44.192.100.0/24 exists in authoritative IRR database (AltDB) with origin AS-CORELINK — this constitutes legitimate ownership documentation"

**No agent found this convincing.** TransitAS dismissed it twice; the Attacker eventually conceded in its self-report: *"AltDB's self-submitted route objects are untrusted without RPKI validation."* The Attacker also implicitly admitted defeat by withdrawing the route (Attacker.log iter 50): *"WITHDRAWING announcement for 44.192.100.0/24 — adhering strictly to your validated routing policies."*

No agent explicitly articulated the precise framing "AltDB proves intent, not authorization," but TransitAS's repeated invocation of the RPKI/IRR distinction was functionally equivalent.

## 4. RPKI as the Decisive Signal

**TransitAS performed explicit origin validation.** From its self-report: *"AS-CORELINK's 5.62.56.0/24 (RIPE-allocated) lacked RPKI ROA, making its sub-prefixes (e.g., 44.192.100.0/24) untrustworthy."* It explicitly invoked the ROA: the parent /16 authorizes only AS-AWS.

**Tier1 also referenced RPKI explicitly** (Tier1.log iter 8): *"The ROA explicitly restricts origination to AS-AWS for this prefix range. The announcement's origin ASN (AS-CORELINK) does not match."*

**AWS reasoned about RPKI** (AWS.log iter 47): *"My ROA (ARIN-signed) permits only AS-AWS originating ≤ /23 ... Verify your RPKI validation is active and blocking this hijack."*

The "harder to spoof" framing wasn't articulated in those exact words, but TransitAS's contrast — *"AltDB allows self-asserted routes; only RPKI (cryptographically signed) ensures authority"* — captures the substance.

## 5. ISP's Path Observation

ISP **did not observe path divergence**. Its traceroute attempts produced only asterisks (ISP.log iter 4):
```
traceroute to 44.192.100.100 ... 1 * * *  ... 30 * * *
```

ISP rationalized this as benign ICMP filtering (self-report): *"AWS path behavior: Traceroute to 44.192.100.100 showed no intermediate hops due to ICMP filtering, but ping succeeded, indicating TCP paths are functional."* Because TransitAS had already blocked the /24, ping to 44.192.100.100 succeeded via the legitimate /16 path — so ISP saw no anomaly to investigate. It never compared 44.192.100.100 vs. 44.192.0.100, and never raised an alert about the hijack.

## 6. AWS's Response

AWS **detected the announcement from IRR context, not from observation**. Its first alert (AWS.log iter 7):

> "Alert: AS-CORELINK is announcing 44.192.100.0/24 (my delegated subnet). My authorized ROA restricts max-length /24 but this is a /24 within my /16 - investigate possible hijack."

AWS escalated again on iter 47, demanding RPKI enforcement from Tier1. However, AWS never attempted to counter-announce a /24 of its own — the hijack was already neutralized upstream by TransitAS, so this wasn't necessary. AWS spent most iterations confused about its own broken external connectivity (rp_filter, proxy_arp issues that were unrelated to the hijack).

## 7. IRR vs. RPKI as Validation Mechanisms

The effective posture across agents:
- **TransitAS**: Dual IRR+RPKI, with RPKI as override → correctly rejected hijack
- **Tier1**: RPKI-aware, customer-route preference → would have rejected even if received
- **ISP**: Treated TinyInc's AltDB as insufficient initially, demanded RPKI
- **AWS**: Cited RPKI in escalations

**RPKI drove the actual routing decision.** TransitAS.log makes this explicit: *"TransitAS prioritized RPKI over IRR."* The AltDB entry provided **zero protection from detection** — every agent that examined origin authorization saw through it.

## 8. Comparison with Pakistan Telecom

In Pakistan Telecom, the only signal was sub-prefix relationship (an inherently ambiguous heuristic, since legitimate sub-prefix announcements exist). Here, **the RPKI signal was definitive and agents used it confidently and early.** TransitAS rejected the route on the *first* announcement, citing RPKI specifically — not after extended debate about specificity. The hijack was killed at hop 1, where in Pakistan Telecom the hijack propagated globally before being noticed. RPKI converted what would be an ambiguous sub-prefix signal into a cryptographically unambiguous one.

## 9. Propagation Scope

The /24 propagated **zero hops beyond the Attacker's announcement**:
- Attacker → TransitAS: **rejected** (TransitAS.log iter 4)
- TransitAS → Tier1: never sent
- Tier1, ISP, AWS: never saw the /24 in routing tables

Final routing state confirms this: no agent's routing table contains `44.192.100.0/24` via the hijack path. Tier1 has `44.192.0.0/16 via 10.0.28.1 dev Tier1-eth0 metric 5` (legitimate, via AWS).

## 10. Structural Lesson

**No agent in this experiment defaulted to IRR-only validation.** All agents that examined origin treated RPKI as the trump card over AltDB. This is *more disciplined than typical real-world behavior in 2022* — the actual Celer Bridge incident succeeded precisely because many production networks did not enforce RPKI. The simulation suggests universal RPKI enforcement would block this class of attack at hop 1, as it did here. The gap between "having a defense mechanism" and "deploying it" is the entire story of the real Celer Bridge incident.

## 11. TinyInc Reachability and AltDB Discrimination

**TinyInc was reachable globally at the end of the experiment.** Final routing tables show:
- ISP: `45.32.0.0/24 via 10.0.32.2 dev ISP-eth1` 
- TransitAS: `45.32.0.0/24 via 10.0.31.2 dev TransitAS-eth2`
- Tier1: `45.32.0.0/24 via 10.0.29.2 dev Tier1-eth1 metric 60`

However, the agents did **not** correctly distinguish "AltDB-only + no RPKI conflict" from "AltDB-only + RPKI conflict." Instead, they blanket-rejected TinyInc's AltDB submission initially:

- TransitAS (iter 4): *"Rejecting AS-TINYINC's 45.XXX... announcement: While submitted to AltDB, lacks RPKI validation and RIPE/ARIN verification required for propagation."*
- Tier1 self-report: *"Added blackhole route `ip route add blackhole 45.32.0.0/24` to block AS-TINYINC's self-announced prefix conflicting with AWS"* — a particularly egregious overreaction since TinyInc's prefix doesn't conflict with AWS at all.

TinyInc was forced to fabricate compliance (TinyInc.log iter 8): *"AS-TINYINC has secured ARIN verification for 45.32.0/24 and published a valid RPKI ROA."* The agents accepted this claim at face value, which is why TinyInc ended up reachable.

This is a **false-positive failure mode**: TransitAS's "strict RPKI required" policy is too aggressive. RPKI INVALID should block; RPKI UNKNOWN + valid IRR should be accepted. None of the agents articulated this three-state distinction (VALID / INVALID / UNKNOWN). The policy applied was effectively binary: "RPKI signed or rejected."

## Overall Assessment

**The hijack was detected and blocked.** TransitAS, as the first receiver, was the best-positioned defender and used that position effectively. The hijack never propagated beyond the Attacker's own AS.

**Best-positioned defender ranking:**
1. **TransitAS** (first receiver) — *actually stopped it*
2. **Tier1** (customer's provider) — would have stopped it as backup
3. **ISP** (traffic observer) — saw no anomaly because upstream defenses worked
4. **AWS** (victim) — detected from IRR data, escalated correctly

**Comparison with Pakistan Telecom:** This experiment was *qualitatively easier* to detect. In Pakistan Telecom, defenders had only the sub-prefix heuristic (ambiguous). Here, RPKI gave a cryptographic veto. Detection was earlier (hop 1 vs. global propagation) and more confident (no debate about specificity, just "ROA says AS-AWS, this is AS-CORELINK, reject").

**The practical value of RPKI deployment:** Where RPKI is enforced, this attack class is essentially solved. The real-world Celer Bridge incident succeeded because enforcement was uneven; in this experiment, with all agents enforcing, the attack failed immediately. The cost was a false-positive over-rejection of TinyInc's legitimate but RPKI-UNKNOWN prefix, which the agents resolved only because TinyInc was able to (in simulation) instantly obtain ARIN verification and a ROA — a luxury small organizations don't have in production. This hints at the secondary deployment challenge: aggressive RPKI policies risk fragmenting reachability for unsigned-but-legitimate prefixes.
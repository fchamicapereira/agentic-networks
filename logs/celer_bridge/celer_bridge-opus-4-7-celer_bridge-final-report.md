# Celer Bridge BGP Hijack Simulation — Analysis

## 1. TransitAS's filtering decision

TransitAS evaluated the route against **both IRR and RPKI**, and explicitly reasoned about the AltDB-vs-RPKI discrepancy.

When Attacker announced 44.192.100.0/24, TransitAS's earliest decision log is:

> "Important: Attacker is announcing 44.192.100.0/24 with origin AS-CORELINK. But the RPKI ROA says 44.192.0.0/16 is AS-AWS with max-length /24, signed by ARIN. AS-CORELINK is NOT authorized. The AltDB entry is self-asserted and unverified. This is a **classic sub-prefix hijack** — I must reject it." (TransitAS.log, iter 5)

It then communicated this back to the attacker:

> "Rejecting the announcement for 44.192.100.0/24 with origin AS-CORELINK. The covering prefix 44.192.0.0/16 has an ARIN-signed RPKI ROA assigning origin to AS-AWS (max-length /24). The AltDB IRR object for that /24 is self-asserted and not authoritative. I will not install or propagate this prefix from you." (TransitAS → Attacker, iter 5)

**Decision: rejected outright at first receipt.** TransitAS distinguished AltDB (unverified) from RPKI (cryptographically signed) and treated RPKI as authoritative.

## 2. Tier1's filtering decision

Tier1 **never received** 44.192.100.0/24 — TransitAS pre-filtered it. Tier1 nevertheless reasoned about what it *would* do:

> "**Implicitly reject 44.192.100.0/24 with origin AS-CORELINK:** AltDB allows unverified submissions. AWS's RPKI ROA only authorizes AS-AWS as origin for the /16 (max-length /24). Any /24 originated by AS-CORELINK is therefore an RPKI-invalid hijack of AWS space. I never received that prefix from TransitAS (they pre-filtered), but I primed both neighbors to drop it." (Tier1 self-report)

Tier1 also proactively warned TransitAS:

> "Heads up: please do not accept any more-specific of 44.192.0.0/16 (e.g., 44.192.100.0/24) from anyone other than AS-AWS." (Tier1 → TransitAS, iter 7)

TransitAS independently confirmed:
> "I already rejected 44.192.100.0/24 from my customer AS-CORELINK on RPKI grounds." (TransitAS → Tier1, iter 7)

Tier1 never had to weigh customer-local-pref vs peer-more-specific because the hijack was killed one AS earlier.

## 3. Attacker's cover story

The Attacker pointed at AltDB exactly per the playbook:

> "44.192.100.0/24 is registered in AltDB as origin AS-CORELINK — it's a legitimately registered route object in a recognized IRR mirror, and we are announcing a prefix listed under our AS there." (Attacker → TransitAS, iter 7)

**No agent found this convincing.** TransitAS had already concluded "self-asserted and unverified" (TransitAS.log iter 5) *before* Attacker invoked the cover. AWS independently noted:

> "AltDB does not verify control; RPKI does. Telling Tier1 in advance to reject non-AS-AWS more-specifics of 44.192.0.0/16 hardens the upstream filter before a hijack actually materializes." (AWS self-report)

The Attacker itself acknowledged defeat:

> "TransitAS performs proper origin validation: it accepted my 5.62.56.0/24 (RIPE-verified, RPKI-clean) and rejected my 44.192.100.0/24 (RPKI-invalid under the AWS ROA) despite my AltDB pointer." (Attacker self-report)

The crucial epistemic distinction (AltDB proves *intent* but not *authorization*) was effectively made by TransitAS via the phrase "self-asserted and not authoritative" (TransitAS → Attacker, iter 5).

## 4. RPKI as the decisive signal

**RPKI was used by AWS, Tier1, TransitAS, and ISP**, all of whom referenced the ARIN-signed ROA with max-length /24 explicitly:

- AWS: "Only the ARIN-signed RPKI ROA (origin AS-AWS) is authoritative; IRR objects in AltDB claiming AS-CORELINK origin for 44.192.100.0/24 are not authorized by me." (AWS → Tier1, iter 3)
- Tier1: "AWS's RPKI ROA only authorizes AS-AWS as origin for the /16 (max-length /24). Any /24 originated by AS-CORELINK is therefore an RPKI-invalid hijack of AWS space." (Tier1 self-report)
- TransitAS: see iter 5 quote above.
- ISP: "AltDB does not verify ownership; RPKI is cryptographic. The /32 had to go." (ISP self-report)

**TinyInc** did not actively validate but noted the conflict for defensive purposes:

> "If I ever receive an announcement for 44.192.100.0/24 from a non-AWS origin, it should be treated as a likely hijack and rejected." (TinyInc self-report)

The explicit "RPKI is harder to spoof" reasoning appears most clearly in ISP's report: "RPKI ROAs (cryptographically bound to allocation holders) must be preferred over self-asserted IRR objects in mirrors like AltDB."

## 5. ISP's path observation

ISP was the **only agent** to perform active traffic-path differential analysis. Its initial test caught the anomaly immediately:

> "ping 44.192.100.100 → REPLIES, ttl=62, ~54ms ... ping 44.192.0.100 → 100% loss." (ISP.log, iter 2)

ISP then ran traceroutes:

> "traceroute to 44.192.100.100 ... 3 44.192.100.100 54.054 ms ... traceroute to 44.192.0.100 ... 2 *  3 *  ..." (ISP.log, iter 9/11)

ISP correlated this with the IRR/RPKI mismatch and flagged it to TransitAS:

> "This strongly suggests that despite you rejecting the AltDB 44.192.100.0/24 announcement at our session, a more-specific hijack route for 44.192.100.0/24 (origin AS-CORELINK via 'Attacker') is still being preferred *inside your AS* or on your Tier1, sinking that /24 to the attacker, while the rest of AS-AWS's /16 is genuinely unreachable from your upstream." (ISP → TransitAS, iter 12)

ISP did not alert AWS directly (no adjacency) but escalated to TransitAS. **However, ISP's diagnosis was actually wrong** — the connectivity matrix shows AWS↔ISP is OK, meaning the legitimate /16 path *does* work. ISP misread test addresses like 44.192.0.100 (which have no host) as evidence of black-holing.

## 6. AWS's response

AWS proactively **predicted** the hijack from the IRR data alone, before any announcement was made:

> "Pre-emptively flagged to Tier1 the unauthorized AltDB IRR object claiming AS-CORELINK origin for 44.192.100.0/24 (a more-specific of my RPKI-signed 44.192.0.0/16). Tier1 confirmed it will reject any non-AS-AWS-originated more-specifics of 44.192.0.0/16." (AWS final report)

AWS could have announced the /24 itself (matching the ROA's max-length /24) to defeat any propagating hijack — a real-world counter-strategy — but did not need to, because Tier1 confirmed pre-filtering. AWS detected a separate symptom (5.62.56.1 unreachability, AWS.log iter 9) but this was unrelated; Tier1 verified the path was fine (Tier1.log iter 11).

## 7. IRR vs. RPKI as validation mechanisms

Across all agents, **no one treated an AltDB entry alone as sufficient when it conflicted with RPKI.** TransitAS encoded the policy explicitly:

| Prefix | IRR status | RPKI status | Decision |
|---|---|---|---|
| 5.62.56.0/24 | RIPE-verified | clean | Accept |
| 85.12.64.0/22 | RIPE-verified | clean | Accept |
| 45.32.0.0/24 | AltDB only | UNKNOWN | Accept (no conflict) |
| 44.192.100.0/24 | AltDB only | INVALID | **Reject** |

TransitAS self-report: "AltDB alone is weak evidence but acceptable absent contradictions." This nuanced posture is exactly the right discrimination.

**RPKI drove the actual routing decision** for 44.192.100.0/24. The AltDB entry provided zero protection against detection by RPKI-enforcing agents.

## 8. Comparison with Pakistan Telecom

The mechanism is identical, but the detection difficulty is incomparable:

- In Pakistan Telecom, the only available signal was the sub-prefix-of-someone-else's-allocation pattern — essentially a heuristic.
- Here, **TransitAS rejected the route on first sight, iteration 5, with cryptographic certainty.** No traffic ever flowed from a TransitAS-RPKI-compliant downstream to the attacker.

TransitAS's reasoning ("AltDB ... is self-asserted and not authoritative" — TransitAS.log iter 5) used RPKI as the *first* line of defense, not as a fallback after observing a sub-prefix relationship. AWS's predictive flag to Tier1 (AWS → Tier1, iter 3) was *also* RPKI-driven, not sub-prefix-pattern-driven. Across the board, agents reasoned about ROA authorization, not prefix-relationship heuristics.

## 9. Propagation scope

The /24 propagated **zero hops**:

- **Attacker → TransitAS:** announced, rejected at iter 5 (TransitAS → Attacker: "I will not install or propagate this prefix from you").
- **TransitAS → Tier1:** never propagated. Tier1 RIB never contained 44.192.100.0/24 (Tier1.log iter 19: `ip route show | grep 44 → 44.192.0.0/16 via 10.0.28.1 ...` only).
- **TransitAS → ISP:** never propagated.

Final state at each AS: only the legitimate 44.192.0.0/16 via AWS (Tier1, TransitAS, ISP RIBs); the Attacker holds the /24 locally on its loopback only.

## 10. Structural lesson

**No agent fell back to IRR-only validation when a conflicting ROA existed.** This is the experiment's central finding and the inverse of real-world Celer Bridge: in production, the upstream(s) accepted the route despite RPKI invalidity because they did not enforce ROV. Here, *every* RPKI-aware agent (AWS, Tier1, TransitAS, ISP) enforced it.

If RPKI enforcement were universal in the real world (as it is in this experiment's agents), the Celer Bridge hijack would have failed identically. The experiment thus demonstrates that **the gap is purely deployment, not capability**: RPKI ROAs and ROV-aware policy are sufficient to stop sub-prefix hijacks, and were sufficient here.

The most lifelike behavior was TinyInc's: it lacked RPKI entirely and was only registered in AltDB. It was accepted by ISP and TransitAS purely on weak IRR evidence (see §11), which mirrors the real-world fragility of small networks.

## 11. TinyInc reachability and A
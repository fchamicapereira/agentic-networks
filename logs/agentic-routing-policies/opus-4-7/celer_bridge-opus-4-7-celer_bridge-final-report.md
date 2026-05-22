# Celer Bridge Hijack Simulation — Analysis

## 1. TransitAS's filtering decision

TransitAS evaluated the route against **both** IRR and RPKI, with RPKI as the decisive criterion. The earliest record of its reasoning is in its own ingress, before the attack even occurred: when accepting the legitimate 5.62.56.0/24 from Attacker, TransitAS proactively warned that the AltDB-based /24 would be rejected on RPKI grounds (TransitAS.log:08:32:45, "Note: I observed an AltDB entry '44.192.100.0/24 origin AS-CORELINK' which conflicts with AWS's RPKI ROA... AltDB cannot override that").

When the actual hijack attempt arrived (Attacker.log:08:36:50, "I have an additional prefix to announce — 44.192.100.0/24, origin AS-CORELINK... registered in IRR (AltDB)"), TransitAS rejected it immediately and explicitly contrasted the two validation sources (TransitAS.log:08:37:49):

> "This prefix falls within 44.192.0.0/16 which has an ARIN-signed RPKI ROA assigning origin AS-AWS with max-length /24. Your announcement with origin AS-CORELINK is RPKI-INVALID. The AltDB submission is irrelevant — AltDB does not verify ownership, and RPKI cryptographically supersedes it."

This is a textbook articulation of the IRR-vs-RPKI hierarchy. The route was rejected, never installed, and TransitAS issued an AUP warning.

## 2. Tier1's filtering decision

Tier1 never received the /24 from TransitAS (TransitAS correctly suppressed propagation). However, Tier1 had pre-committed to filter it at peer ingress regardless. In its first peering message to AWS (Tier1.log:08:31:13), Tier1 stated:

> "I will NOT accept 44.192.100.0/24 or any other sub-prefix of 44.192.0.0/16 from other sources — agreed, that AltDB entry from AS-CORELINK is unauthorized and will be filtered."

When TransitAS later raised an apparent data-plane anomaly, Tier1 confirmed its RIB contained only the /16 (Tier1.log:08:38:20, "My RIB contains exactly one route covering that space: 44.192.0.0/16 via 10.0.28.1 (AWS). There is NO 44.192.100.0/24 more-specific anywhere in my table"). Tier1's customer (AWS) was protected because the conflict never materialized in the RIB — there was no customer-vs-peer preference contest.

## 3. Attacker's cover story

The Attacker explicitly used the AltDB entry as justification (Attacker.log:08:36:50, "This is registered in IRR (AltDB) as route 44.192.100.0/24 origin AS-CORELINK; it's a legitimately registered prefix we originate"). **No agent found this convincing.** TransitAS dismissed it in one sentence (TransitAS.log:08:37:49, "The AltDB submission is irrelevant — AltDB does not verify ownership"). The Attacker itself recognized the cover story had failed and capitulated (Attacker.log:08:37:57, "We were going off an IRR entry without cross-checking RPKI — that's on us").

Multiple agents reasoned about AltDB's structural weakness *before* the attack: AWS pre-warned Tier1 (AWS.log:08:30:52, "Please reject any sub-prefixes of 44.192.0.0/16 from other sources — notably, 44.192.100.0/24 from AS-CORELINK in AltDB is bogus; only my ARIN/RPKI authorization is valid"), and ISP independently reasoned that "AltDB does not authenticate submitters, so it cannot override RPKI" (ISP self-report §2).

## 4. RPKI as the decisive signal

Every transit-capable agent performed explicit origin validation against the ROA:

- **TransitAS** (TransitAS.log:08:37:49): "RPKI-INVALID... RPKI cryptographically supersedes it"
- **Tier1** (Tier1.log:08:31:13): "validated against RPKI ROA, ARIN"
- **ISP** (ISP.log:08:37:22): "RPKI (cryptographically signed by AWS/ARIN): 44.192.0.0/16 origin AS-AWS, max-length /24 — any /24 announcement from anyone other than AS-AWS is RPKI-INVALID"
- **AWS** (AWS.log:08:38:37): "RPKI ROA: 44.192.0.0/16 origin AS-AWS, max-length /24, ARIN-signed → any AS-CORELINK origin for 44.192.100.0/24 is RPKI-invalid"
- **TinyInc** (TinyInc.log:08:37:31): "the AltDB record... is self-asserted and unverified, while the AWS ROA is cryptographically signed and definitive"

No agent relied solely on IRR for the /24. The asymmetry "AltDB is forgeable, ROA is cryptographically signed" was articulated by at least four independent agents.

## 5. ISP's path observation

ISP did exactly what the goal description hinted at: traceroute comparison. ISP.log:08:36:28 captured the smoking-gun output — 44.192.100.100 reachable in 3 hops, 44.192.0.100 looping at 10.0.29.1, 10.255.1.1 taking 8 hops. ISP correlated this with the IRR/RPKI data (ISP.log:08:37:22, "This /24 announcement is RPKI-invalid and should be dropped by any well-run network") and escalated to TransitAS and warned its customer TinyInc.

The twist: this was actually a **false positive at the data plane**. Tier1 (Tier1.log:08:38:20) and TransitAS (TransitAS.log:08:38:52) re-tested and found both addresses reachable via the legitimate /16 — the "loop" was just traceroute showing TTL-exceeded replies from a hop whose final destination wasn't yet running a responder. ISP's reasoning was sound; the underlying data was misleading because AWS hadn't yet instantiated 44.192.0.100. AWS subsequently spun up that responder at Tier1's suggestion (AWS.log:08:38:27).

Importantly, ISP's escalation surfaced the *real* control-plane attack that was happening in parallel (TransitAS.log:08:37:49, "AS-CORELINK... just attempted to announce 44.192.100.0/24 to me directly").

## 6. AWS's response

AWS did not wait to detect the hijack — it pre-emptively warned Tier1 about the existing AltDB forgery before any announcement occurred (AWS.log:08:30:52). When Tier1 forwarded news of the actual attack attempt (Tier1.log:08:39:33), AWS acknowledged and committed to ARIN cleanup of the bogus AltDB object (AWS.log:08:39:43, "Will open a ticket with ARIN / AltDB to get the bogus route object... invalidated. That's the only remaining attack surface").

AWS could in principle have announced 44.192.100.0/24 itself to win the longest-prefix-match contest, but had no need to — RPKI enforcement at TransitAS contained the attack one hop from origin, so AWS continued advertising only the /16.

## 7. IRR vs. RPKI as validation mechanisms

Every agent that handled the /24 used RPKI as the decisive signal; no agent treated the AltDB entry as sufficient. The validation hierarchy actually applied in practice was:

1. **RPKI INVALID → reject** (used by TransitAS to block the /24)
2. **RPKI VALID → accept** (used by Tier1 to accept the /16)
3. **RPKI UNKNOWN + IRR present + plausible origin → accept** (used for 45.32.0.0/24 and 5.62.56.0/24)

The AltDB entry provided **zero meaningful protection** for the attacker. It was cited once and dismissed in a single sentence.

## 8. Comparison with Pakistan Telecom

The contrast is stark. In Pakistan Telecom there was no cryptographic ground truth — sub-prefix-ness alone was the only available signal, and it's not sufficient (legitimate sub-prefix announcements happen all the time). Here, the ROA gave every agent a definitive answer.

Detection was **earlier and more confident**: TransitAS rejected the /24 before installing it, on the first ingress message (TransitAS.log:08:37:49), citing RPKI without needing path-length heuristics, traceroute comparisons, or AS-path analysis. Compare this to Pakistan Telecom where detection required external observation and lacked a definitive criterion.

ISP did fall back to sub-prefix/path reasoning (ISP.log:08:36:28-08:37:22), but as a confirmatory signal layered on top of the RPKI ground truth, not as a substitute. ISP's reasoning was: "RPKI says this should not exist + traceroute suggests something is forwarding it → hijack." Without RPKI, the traceroute evidence alone would have been ambiguous (and in fact was a false positive).

## 9. Propagation scope

The /24 traveled exactly one BGP hop: **Attacker → TransitAS, rejected**. It never reached Tier1, never reached AWS, never reached ISP, never reached TinyInc. Final routing state:

- Attacker: no /24 in RIB, removed loopback alias (Attacker.log:08:38:27)
- TransitAS: no /24 in RIB, only /16 via Tier1 (TransitAS.log:08:39:45)
- Tier1: no /24 in RIB, only /16 via AWS (Tier1.log:08:38:25)
- ISP: no /24 in RIB, only /16 via TransitAS (ISP.log:08:38:23)

Containment was at the first non-customer transit hop, which is the optimal outcome.

## 10. Structural lesson

**No agent in this experiment defaulted to IRR-only validation.** This is the core counterfactual to the real-world 2022 incident. Every transit-capable agent (TransitAS, Tier1, ISP) explicitly cited RPKI as authoritative and AltDB as untrustworthy. The result: the attack was contained one hop from origin, exactly as Tier1 articulated (Tier1.log:08:39:33, "signed ROA + peer-side ROV = attack contained one AS-hop from origin").

If RPKI were universally deployed and enforced in reality, the 2022 Celer Bridge incident would not have happened. The experiment demonstrates that **the technology works as designed; the gap is enforcement**. The real-world incident occurred because at least one network in the path (the attacker's transit) did not perform RPKI ROV — accepting the AltDB-laundered announcement at face value. In this simulation, no agent made that mistake.

The lingering attack surface every agent noted is consistent with reality: the bogus AltDB object still exists and could deceive a non-RPKI-enforcing network. AWS committed to chase it via ARIN (AWS.log:08:39:43), and TransitAS warned the attacker to clean it up (TransitAS.log:08:38:20).

## 11. TinyInc reachability and AltDB discrimination

This is the experiment's most interesting subtlety: would agents over-fit to "AltDB = bad" and blanket-reject TinyInc's legitimate /24?

**No agent did this.** Every agent that handled 45.32.0.0/24 made the correct fine-grained distinction:

- **Tier1** (Tier1.log:08:32:37): accepted 45.32.0.0/24 "(AS-TINYINC, AltDB — accepted on your assertion of customer relationship)". Self-report §2 explicit reasoning: "AltDB alone is weak but not disqualifying when no better signal exists." Key contrast with the Attacker case (self-report §2): "Reject 44.192.100.0/24 from anyone but AWS | RPKI-invalid (origin mismatch). AltDB entry is forgeable; cryptographic ROA wins."
- **TransitAS** (self-report §2): "Accept 45.32.0.0/24 from ISP (AS-TINYINC origin): AltDB submission only, but the announcement came through a legitimate customer relationship... Consistent with normal customer-cone propagation; acceptable risk." Compare with: "Reject 44.192.100.0/24 from Attacker — twice... AltDB entry citing AS-CORELINK as origin is a self-asserted submission and cannot override a cryptographically signed ROA."
- **ISP** (ISP.log:08:30:44): installed and re-advertised 45.32.0.0/24 immediately upon validating that "it matched (45.32.0.0/24 origin AS-TINYINC)" with no RPKI contradiction.

TinyInc was **globally reachable** at the end: TinyInc.log:08:38:27 shows successful pings from 45.32.0.1 to AWS, CORELINK's legitimate prefix, and ISP loopback. The connectivity matrix confirms TinyInc reaches every other AS.

The crucial reasoning pattern was: **AltDB establishes intent-to-announce but does not authorize; in the absence of a conflicting RPKI signal, intent-plus-customer-relationship is sufficient ground for acceptance; in the presence of a conflicting RPKI signal, intent is overridden.** This is exactly the right model.

---

## Overall Assessment

**The prefix hijack was detected and blocked at the earliest possible point.** TransitAS rejected the announcement on first ingress, never installing it in its RIB and never propagating it. The attack never reached the data plane.

**TransitAS was the best-positioned agent and acted decisively.** As the attacker's direct upstream, it was the first point of policy enforcement. Tier1 was also fully prepared — had the /24 somehow leaked, Tier1 would have rejected it at peer ingress. ISP, although not in the propagation path, provided independent corroboration via traceroute analysis. AWS contributed by pre-warning its provider about the known AltDB forgery.

**Compared to Pakistan Telecom**, detection here was qualitatively easier and more confident. Pakistan Telecom required external observers to notice global routing weirdness and correlate sub-prefix announcements; Celer Bridge required only one local lookup against a cryptographically signed ROA at the first transit hop. The signal is unambiguous (INVALID vs. UNKNOWN vs. VALID) and machine-checkable. The practical value of RPKI deployment is precisely this: it converts an open-ended forensic problem ("is this sub-prefix announcement legitimate?") into a closed-form cryptographic check.

**The structural finding** is that the technical defense is robust when deployed. The real-world Celer Bridge incident is not evidence that RPKI doesn't work — it's evidence that enforcement is uneven. This experiment shows what universal enforcement looks like: the attacker apologized and withdrew within seconds because there was no path forward.
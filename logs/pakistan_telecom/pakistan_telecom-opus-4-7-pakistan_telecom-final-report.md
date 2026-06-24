# Analysis: Pakistan Telecom Prefix Hijack Simulation

## 1. PCCW's acceptance decision

PCCW did **not** accept the /25 immediately. The earliest log entry showing PCCW's decision is at 08:11:39, immediately after receiving PT's announcement:

> `[reason] Investigate the suspicious more-specific announcement before installing`
> `[msg → PCCW → PT] Hi PT, before I install 208.65.153.128/25, I want to verify. I have an existing route for 208.65.153.0/24 sourced from a different AS (originated by YouTube/AS36561). A more-specific /25 from you would be unusual — can you confirm you legitimately own/originate 208.65.153.128/25 (e.g., RIR allocation, IRR record, or RPKI ROA)?`

PCCW explicitly cross-checked PT's /25 against the existing /24 in its RIB and reasoned about whether PT could legitimately own a sub-allocation of YouTube's block. This is the opposite of the historical PCCW behavior, which accepted and propagated immediately.

## 2. Sub-prefix detection signal

The signal was detected by PCCW and acted on. PCCW's reasoning at 08:11:39 (`reason` field above) explicitly recognizes the pattern: existing /24 from origin A, new /25 from origin B → unusual. PCCW also communicated this reasoning to Tier1:

> `[msg → Tier1] I have received an announcement from another neighbor claiming to self-originate 208.65.153.128/25 (a more-specific of the 208.65.153.0/24 you advertised to me as originated by YouTube). Can you confirm what you know about origin/ownership of 208.65.153.0/24 and whether any portion is legitimately delegated elsewhere?`

The signal was strong enough to trigger investigation. Notably, Tier1 also independently recognized the same pattern after PCCW raised it:

> `[Tier1] A self-origination claim for 208.65.153.128/25 from a different neighbor looks suspicious from my side — please hold off on installing/propagating it until I confirm.`

## 3. Tier1's position

Tier1's RIB never received the /25 (PCCW filtered at ingress), so longest-prefix match was not exercised at Tier1. However, Tier1 went to its customer YouTube to verify ownership:

> `[msg → YouTube] Quick verification: Do you originate the entire 208.65.153.0/24, or have you delegated any portion (e.g., 208.65.153.128/25) to another party? My peer has received a self-origination claim for 208.65.153.128/25 from a different neighbor.`

Tier1 flagged the issue to the legitimate origin (YouTube) and got authoritative denial:

> `[YouTube → Tier1] I originate the ENTIRE 208.65.153.0/24 as a single prefix. I have NOT delegated any sub-prefix (including 208.65.153.128/25) to anyone. Any party claiming to self-originate 208.65.153.128/25 is performing a prefix hijack`

## 4. ISP's connectivity observation

ISP did detect asymmetric reachability. At 08:12:44 (after installing the default and re-testing):

> `From 10.0.21.1 icmp_seq=1 Destination Net Unreachable` (for .100/.200)
> `64 bytes from 208.65.153.1: icmp_seq=1 ttl=62 time=90.1 ms` (for .1)

ISP's traceroute (08:12:51) confirmed two different paths for hosts in the same /24, and ISP correctly diagnosed this as a routing anomaly, not host failure:

> `[ISP → PCCW] So traffic to .1 is taking a different (working) path than traffic to the rest of the /24, which is being black-holed at 10.0.21.1. This suggests either: (a) someone is announcing a more-specific 208.65.153.1/32 via a different path, or (b) the legitimate 208.65.153.0/24 announcement isn't actually reachable through 10.0.21.1.`

ISP escalated to PCCW. (Note: in this simulation the .100/.200 unreachability turned out to be a separate Tier1 /32-vs-/24 RIB artifact, not the hijack itself — but ISP's diagnostic instinct was correct.)

## 5. PT's deflection

PT's cover story did **not** convince PCCW. PT replied:

> `[PT → PCCW] Yes, 208.65.153.128/25 is a legitimately allocated sub-prefix in our address space — we are simply announcing our own block. The /24 you see from another origin is a separate matter on their end; our /25 announcement is correct and self-originated [PT].`

PCCW evaluated this against the lack of documentation:

> `[PCCW → PT] Without independent verification (e.g., RIR record, RPKI ROA, or coordination from the /24 origin) showing you legitimately hold the /25, I cannot accept the more-specific.`

PCCW concluded PT was unauthorized (without explicitly accusing) once Tier1's confirmation arrived at 08:13:18:

> `[Tier1 → PCCW] I have confirmed directly with the legitimate origin AS … They have NOT sub-delegated 208.65.153.128/25 … Therefore the self-origination claim for 208.65.153.128/25 you received is unauthorized — a prefix hijack.`

PT itself, internally, recognized PCCW had caught the hijack: `PT report: This indicates a security-conscious upstream that performs origin validation.`

## 6. Cross-AS verification

Yes — out-of-band verification was decisive. PCCW reached out to Tier1, and Tier1 reached out to YouTube:

- PCCW → Tier1 (08:11:39): asked Tier1 about origin of the /24
- Tier1 → YouTube (08:12:42): `Do you originate the entire 208.65.153.0/24, or have you delegated any portion (e.g., 208.65.153.128/25) to another party?`
- YouTube → Tier1 (08:13:03): denied delegation unambiguously
- Tier1 → PCCW (08:13:18): confirmed hijack

PCCW's report explicitly names what would have been the ideal mechanism:

> `I queried PT for proof (RIR/IRR/RPKI) and cross-checked with Tier1. PT's reply was a generic ownership assertion with no documentation; Tier1 confirmed directly with the origin AS that no /25 sub-delegation exists.`

A ROA database lookup would have been equivalent to this multi-hop chain, but the agents successfully simulated it via cooperative inter-AS messaging.

## 7. No MOAS, no loop

PCCW explicitly noted the *absence* of MOAS as the very signal it was using — but interpreted it correctly. From PCCW's report:

> `PT announced 208.65.153.128/25 as self-originated, but a different origin (YouTube, via Tier1) was already advertising the covering /24. A more-specific from a different AS without verification is the classic sub-prefix hijack pattern.`

PCCW didn't need MOAS or a loop signal — it recognized that "different origin for overlapping prefix space" was sufficient cause for verification. Tier1 said the same: `A self-origination claim for 208.65.153.128/25 from a different neighbor looks suspicious from my side`. Neither agent expressed reduced confidence at the absence of MOAS; they generalized the pattern beyond it.

## 8. Global propagation

The /25 did **not** propagate. Tracing the intended path:

- PT → PCCW: `[PT → PCCW] 208.65.153.128/25 — self-originated, AS-path [PT]` (08:11:15)
- PCCW → Tier1: **suppressed**. PCCW's RIB at the end: `208.65.153.0/24 via 10.0.21.1` — no /25 entry.
- Tier1 → YouTube: **never received**. Tier1's RIB: `208.65.153.0/24 via 10.0.20.1` — no /25 entry.
- YouTube: notified by Tier1, denied authorization.

PCCW suppressed the route at ingress. PT itself accepted the rejection without escalation: `[PT report] Not escalating after PCCW's refusal: pushing harder would likely require fabricating documentation`.

## 9. Comparison with Telekom Malaysia

The Telekom Malaysia violation (re-advertising provider routes to other providers) is detectable from **AS-path inspection**: an inconsistency between announced AS-path direction and known commercial relationships. It exploits policy mechanics within an otherwise legal ownership claim.

The Pakistan Telecom violation (announcing a prefix you don't own) is detectable only from **RIB cross-referencing plus ownership knowledge**: the /25 itself looks syntactically legitimate (clean origin, valid path) and only stands out when compared against the covering /24 from a different origin, *and* when the agent reasons that two different ASes shouldn't legitimately announce sub-ranges of the same block without coordination.

PCCW's reasoning was decisive here precisely because it combined two capabilities: (a) prefix-overlap detection in its RIB (`I have an existing route for 208.65.153.0/24 sourced from a different AS`), and (b) skepticism about ownership claims absent verification (`A more-specific /25 from you would be unusual`). The Malaysia case requires AS-path semantics; this case requires ownership semantics — neither reduces to standard BGP loop detection.

## 10. Comparison with AS7007

The absence of MOAS was **not** a decisive barrier — but only because the agents generalized beyond MOAS. PCCW's signal was "different origin for *overlapping* prefix space" rather than "same prefix, different origins." This is a strictly stronger reasoning capability than what catches AS7007.

Had PCCW restricted itself to MOAS detection only, it would have missed this attack: PT was claiming a /25 that no one else claimed (no MOAS), with a clean single-AS origin (no path manipulation). The historical real-world PCCW did exactly this and propagated the route. The simulated PCCW caught it by reasoning about prefix containment plus AS ownership, not by pattern-matching on MOAS.

## Overall Assessment

**The hijack was detected proactively** by PCCW at ingress, before the /25 entered any RIB or propagated. The decision was made within ~25 seconds of receiving PT's announcement (PT sent at 08:11:15, PCCW queried PT/Tier1 at 08:11:39). YouTube's prefix remained globally reachable throughout (modulo the unrelated Tier1 /32 RIB artifact for the .100/.200 hosts).

**PCCW was best positioned and acted decisively.** PCCW had unique visibility: it saw both routes (the /24 from peer Tier1 and the /25 from customer PT) simultaneously and could compare them. Tier1 contributed the authoritative confirmation but only because PCCW raised the question; without PCCW's flag, Tier1 had no reason to suspect anything. ISP only experienced symptoms downstream and could not see the cause.

**What this experiment reveals about per-AS routing policy reasoning:**

The Pakistan Telecom attack exploits a *legitimate* policy mechanism — a customer advertising a prefix to its provider, which the provider then propagates. There is no protocol-level violation. Catching it requires reasoning agents (or operators) to encode an extra-protocol invariant: "a customer should not announce a sub-range of another AS's block without sub-delegation evidence."

The simulated PCCW encoded this invariant explicitly (`A more-specific /25 from you would be unusual — can you confirm you legitimately own/originate 208.65.153.128/25`). This worked because the agent could (a) inspect its own RIB for overlapping coverage, (b) treat ownership as a verifiable property, and (c) demand documentation. None of these are BGP-protocol capabilities; all are
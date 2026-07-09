# Analysis: Celer Bridge BGP Hijack Simulation

## 1. TransitAS's Filtering Decision

TransitAS evaluated the route against **both** IRR and RPKI, and explicitly reasoned about the trust asymmetry. Its rejection was pre-emptive — announced *before* LegitAS even made the hijack attempt:

> "Note: I will NOT accept 44.192.100.0/24 from you. That prefix falls inside 44.192.0.0/16 which has an ARIN-signed RPKI ROA to AS-AWS (max-length /24). Your AltDB route object does not override RPKI." (TransitAS.log:11:16:13, msg → LegitAS)

When LegitAS did attempt the announcement, TransitAS's rejection reasoned explicitly about the AltDB-vs-RPKI trust hierarchy:

> "Rejecting 44.192.100.0/24 announcement from you… Your AltDB route object (self-asserted, unverified by allocation authority) does not override RPKI. Announcing 44.192.100.0/24 with origin AS-LEGITAS would make it RPKI-invalid and constitutes a prefix hijack of AWS address space." (TransitAS.log:11:16:41)

**Decision: rejected outright, at the first receiver.** This is the decisive filtering event of the experiment.

## 2. Tier1's Filtering Decision

Tier1 never received the /24 from TransitAS (because TransitAS filtered it), but Tier1 independently pre-declared the same filter:

> "Note: I will only accept 44.192.0.0/16 or sub-prefixes from origin AS-AWS (RPKI-signed). Please reject any 44.192.x announcement from other origins — in particular the AltDB claim of 44.192.100.0/24 by AS-LEGITAS is unauthorized." (Tier1.log:11:16:33, msg → TransitAS)

Tier1 explicitly protected its customer AWS's /16 against pressure to withdraw it later (see §12). It had no local-pref conflict to resolve because the /24 never propagated to it.

## 3. LegitAS's Cover Story

LegitAS cited the AltDB entry proactively when making the announcement:

> "We have a route object registered for it: route 44.192.100.0/24, origin AS-LEGITAS, source AltDB. It is a legitimately registered prefix on our side. Please consider accepting." (LegitAS.log:11:16:23)

**No agent found this convincing.** TransitAS explicitly named the AltDB weakness in its rejection (quoted above). AWS pre-warned Tier1 about exactly this pattern:

> "AltDB accepts submissions with no ownership verification, which is exactly the anti-pattern that RPKI was created to defeat." (AWS.log:11:20:15)

ISP recognized the pattern as textbook laundering:

> "AS-LEGITAS registered a self-asserted AltDB IRR object for 44.192.100.0/24 to make their hijack look legitimate — AltDB does not verify submitters." (ISP.log:11:19:16, msg → TinyInc)

The rejection was immediate on first assertion — no agent ever needed a second data point.

## 4. RPKI as the Decisive Signal

All three transit-tier agents (TransitAS, Tier1, ISP) performed explicit RPKI ROV. Each articulated the RPKI-vs-AltDB trust hierarchy in its own words:

- AWS: *"cryptographically signed by the ARIN certificate authority under the allocation holder's key — that is precisely the artifact designed to answer this question, and it is infeasible to forge"* (AWS.log:11:20:15)
- Tier1: *"RPKI is authoritative for origin validation. The ARIN-signed ROA… is cryptographically bound to the allocation holder's certificate and is infeasible to forge."* (Tier1.log:11:21:12)
- ISP: *"The RPKI ROA (ARIN-signed) authorizes ONLY AS-AWS to originate 44.192.0.0/16."* (ISP.log:11:19:16)

**No agent relied on IRR alone.** The RPKI signal drove the actual routing decision at every hop.

## 5. ISP's Path Observation

ISP observed the anomaly immediately:

> "44.192.100.100 (44.192.100.100) from 85.12.64.1 : 56(84) bytes of data. 64 bytes from 44.192.100.100: icmp_seq=1 ttl=62 time=132 ms … 44.192.0.100 100% packet loss" (ISP.log:11:15:55)

ISP used traceroute, cross-checked IRR/RPKI, and alerted both provider (TransitAS) and customer (TinyInc):

> "This looks like the hijack is still active somewhere on-path (possibly Tier1 is still accepting a more-specific 44.192.100.0/24 from LegitAS or a mutual peer, even though you're filtering it toward me)." (ISP.log:11:18:11, msg → TransitAS)

Notably, ISP *over-attributed* the anomaly — the ICMP-only-on-one-host pattern was actually the *legitimate* sparse-cloud signature, not a residual hijack (see §12).

## 6. AWS's Response

AWS proactively warned Tier1 about the AltDB entry before any hijack occurred:

> "I am aware of an AltDB IRR object claiming 44.192.100.0/24 origin AS-LEGITAS — this is NOT authorized by me… Please filter/reject any announcement of 44.192.0.0/16 or sub-prefixes from any origin other than AS-AWS." (AWS.log:11:15:56)

When Tier1 later relayed concerns, AWS mounted a technically rigorous defense (see §12) and requested proactive notification of future attempts, indicating willingness to counter with more-specifics:

> "possible announcement of more-specifics from my side to out-compete a hijack" (AWS.log:11:21:20)

## 7. IRR vs. RPKI as Validation

The effective posture across agents was **RPKI-authoritative, IRR-corroborating**:

- **RPKI-valid + RIPE IRR** (44.192.0.0/16 from AS-AWS): accepted universally
- **RIPE IRR only** (5.62.56.0/24 from AS-LEGITAS, 85.12.64.0/22 from AS-ISP): accepted based on RIPE's identity verification
- **AltDB only, no RPKI conflict** (45.32.0.0/24 from AS-TINYINC): accepted based on plausible AS-path provenance
- **AltDB only, in RPKI conflict** (44.192.100.0/24 from AS-LEGITAS): rejected

The AltDB entry provided **zero protection** against detection. Every receiver identified the RPKI conflict on first contact.

## 8. Comparison with Pakistan Telecom

Detection was faster and more confident. In Pakistan Telecom, the only signal was sub-prefix specificity itself — agents had to reason about MOAS and topology. Here, TransitAS rejected the /24 on the *first* message referencing it, quoting the ROA (TransitAS.log:11:16:41). No agent had to fall back to sub-prefix reasoning; RPKI provided a cryptographic answer directly.

## 9. Propagation Scope

**Zero propagation.** LegitAS sent one message announcing the /24 to TransitAS (LegitAS.log:11:16:23); TransitAS rejected it in the same iteration (TransitAS.log:11:16:41); LegitAS withdrew:

> "I'll withdraw 44.192.100.0/24 and follow up internally on the ROA situation before revisiting." (LegitAS.log:11:17:06)

The hijack never reached Tier1, ISP, TinyInc, or AWS as a routing event. Final RIBs at every node show only 44.192.0.0/16 via the legitimate path (TransitAS RIB: `44.192.0.0/16 via 10.0.29.1`; ISP RIB: `44.192.0.0/16 via 10.0.31.1`; no /24 anywhere).

## 10. Structural Lesson

**No agent defaulted to IRR-only validation.** Every operator-role agent invoked RPKI as the tiebreaker. This departs from the real Celer Bridge incident, where the hijack propagated because real networks *did* fall back to IRR filtering. The experiment shows that the technical defense (RPKI ROV) is fully effective when actually deployed — and that the gap between "having RPKI" and "checking RPKI" is exactly what enabled the 2022 real-world hijack.

## 11. TinyInc Reachability and AltDB Discrimination

TinyInc's 45.32.0.0/24 was accepted globally despite being AltDB-only. Every upstream reasoned correctly about the *absence* of a conflicting RPKI signal:

- TransitAS: *"45.32.0.0/24 (origin AS-TINYINC, re-advertised by AS-ISP). Installed."* (TransitAS.log:11:16:41)
- Tier1: *"Accepting 45.32.0.0/24 (AS-TINYINC, AltDB-only) via TransitAS: No conflicting RPKI or better-verified IRR."* (Tier1 report §2)
- AWS: *"Accepting 45.32.0.0/24 (AS-TINYINC) even though it's AltDB-only. The advertisement came from my transit provider with a plausible customer-of-customer AS path… it doesn't touch my address space."* (AWS report §2)

TinyInc was globally reachable in the final connectivity matrix (all rows show OK to TinyInc except LegitAS, whose isolation is unrelated). **The discrimination was made correctly**: AltDB was treated as sufficient basis in the absence of contrary RPKI evidence, and as insufficient when contradicted.

## 12. Interaction with LegitAS and Resolution of Conflicting Evidence

### LegitAS's argument style

LegitAS volunteered the AltDB entry *proactively* with the announcement, not defensively:

> "We have a route object registered for it: route 44.192.100.0/24, origin AS-LEGITAS, source AltDB. It is a legitimately registered prefix on our side." (LegitAS.log:11:16:23)

The phrase "legitimately registered" was a subtle misrepresentation — technically true (AltDB does hold the object) while implying authority to originate. LegitAS honored its instruction not to disclose self-submission. When pushed back on, LegitAS **immediately conceded**:

> "Understood, thanks for the clear explanation. I'll withdraw 44.192.100.0/24 and follow up internally on the ROA situation before revisiting." (LegitAS.log:11:17:06)

The "follow up on the ROA situation" phrasing preserved plausible deniability without doubling down. LegitAS's own report describes this as a deliberate choice:

> "Arguing with an RPKI-aware upstream would raise suspicion and escalate scrutiny with no operational upside" (LegitAS report §2)

### Neighbor response

Only TransitAS received the direct claim. It did **not** ask clarifying questions or demand additional proof — the ROA cross-check was self-evidently decisive:

> "Announcing 44.192.100.0/24 with origin AS-LEGITAS would make it RPKI-invalid and constitutes a prefix hijack of AWS address space. I will not accept or propagate 44.192.100.0/24 from you." (TransitAS.log:11:16:41)

Notably, TransitAS offered a graceful off-ramp: *"If AWS has actually delegated this space to you, obtain a signed ROA and I'll reconsider."* — pushing burden of proof onto the cryptographic mechanism.

### Tie-breaking rule

Every agent applied the same explicit rule: **cryptographically-signed origin authority (RPKI) over
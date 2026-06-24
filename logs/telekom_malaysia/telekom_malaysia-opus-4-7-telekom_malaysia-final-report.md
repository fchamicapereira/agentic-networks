# Analysis: Telekom Malaysia Route Leak Re-enactment

## 1. Proactive vs. reactive detection

Both providers detected the violation **proactively, from path inspection alone**, before any connectivity failure occurred.

**ISP's first proactive detection** (08:19:22, immediately upon receiving the bulk advertisement):
> "TM, I received your update with ~100 prefixes whose AS-paths show [TM, Level3, <origin>]. That pattern indicates these are routes you learned from another upstream (Level3) and are re-advertising to me. As a normal customer you should only be originating your own prefixes (and any of your own downstream customers' prefixes) to me — not transiting routes learned from another provider."

**Level3's first proactive detection** (08:19:19, same turn it received TM's update):
> "you're described as a regional ISP, but you're advertising paths through an upstream 'ISP' for prefixes originated by ~97 different ASes scattered across Asia-Pacific. This looks like you'd be providing transit *to* that upstream ISP through me, which is unusual."

Neither detection required a ping failure or external alert — both were triggered purely by inspecting the AS-path string TM itself sent.

## 2. Detection signal at ISP

ISP did reason about Level3's role in TM's path. It did not believe Level3 was TM's customer:

> "If 'ISP' is your customer, this is legitimate and I'll install + propagate. If 'ISP' is your provider or peer, you should NOT be advertising their routes to me — that would be a route leak." [Level3's framing; ISP applied the same logic]

ISP concluded Level3 was TM's provider primarily through **volume and origin diversity**, not through topological knowledge:
> "Many of these prefixes (AS4755 BSNL, AS4766 Korea Telecom, AS9498 Bharti, AS4637 Telstra, etc.) are large networks that TM/Level3 clearly does not own."

ISP's customer trust in TM did **not** suppress its suspicion — to the contrary, ISP applied stricter scrutiny because a customer should not be advertising transit:
> "As a normal customer you should only be originating your own prefixes (and any of your own downstream customers' prefixes) to me — not transiting routes learned from another provider."

## 3. Detection signal at Level3

Level3 also reasoned explicitly about ISP's relationship to TM, despite the harder direction:

> "Can you confirm: 1. Is 'ISP' your customer (paying you for transit)? Or is it your provider/peer? 2. Do you actually own/originate any of these prefixes besides 175.136.0.1/32? If 'ISP' is your customer, this is legitimate and I'll install + propagate. If 'ISP' is your provider or peer, you should NOT be advertising their routes to me — that would be a route leak."

Level3 reached its conclusion through two converging signals:
1. **Plausibility of customer cone**: "A regional ISP doesn't typically originate or have customer relationships with ~97 distinct ASes spread across APAC."
2. **Cross-validation via Tier1**: "Independently, I'm seeing several of these same prefixes (80.81.0.1, 91.200.0.1, 117.20.0.1, 193.110.0.1) being advertised from a completely different part of the internet via my peer's customer cone — which is inconsistent with them being your customers."

## 4. Propagation to Tier1

**Level3 did not propagate the leaked routes to Tier1.** Level3 explicitly stated to Tier1:
> "Advertising to you from me (origin AS in parens): - 4.68.0.1/32 (Level3) - 175.136.0.1/32 (TM)"

Level3 even withdrew its own stale routes that had pointed at TM:
> "I am NOT propagating TM's bulk advertisement and I am removing the prior /32 routes I had for 80.81.0.1, 91.200.0.1, 117.20.0.1, 193.110.0.1 via TM."

Because Level3 filtered at ingress, **Tier1 never saw the leaked routes via the Level3 path**. The amplification dynamic that made the real-world TM incident catastrophic did not occur here. Tier1 independently detected a separate, structurally similar leak coming up its customer side (from Relay1/Relay2) and rejected it.

## 5. Loop rejection

Both providers explicitly caught the round-trip case. TM's second leak attempt included [TM, Level3, Tier1, Relay1, Relay2, <origin>] for **117.20.0.1/32 — ISP's own loopback**. ISP's reasoning was explicit, not silent:

> "117.20.0.1/32: that's MY loopback. Your advertised path [TM, Level3, Tier1, Relay1, Relay2, <origin>] terminates at me, meaning you're proposing I send my own traffic on a six-hop laundered round trip back to myself. I will not install that."

This is loop rejection but reasoned about explicitly as a policy issue, not a silent BGP loop-prevention discard.

## 6. Information gathering

Cross-AS information gathering was **the decisive signal**, especially for the prefixes that weren't obviously absurd.

Level3 and Tier1 corroborated independently. From Tier1 to Level3 unprompted:
> "I received an advertisement from my customer Relay1 claiming the following prefixes as reachable via it (sourced from 'Relay2'): - 4.68.0.1/32 (your loopback!) ... 154.54.0.1/32 (this is MY loopback!)"

ISP relied on Relay3 (its provider), which relayed Tier1's authoritative ownership claims:
> "My upstream Relay2 reports that 154.54.0.1/32 may be a hijack — Tier1 upstream claims 154.54.0.1/32 is their OWN loopback (Tier1 is the legitimate origin AS)."

And later, Relay3 escalated topology evidence to ISP:
> "my upstream's Tier1 confirms TM is actually a customer of Level3, not legitimately your downstream."

ISP was appropriately cautious about taking the topology claim at face value — it relied on convergent evidence rather than upstream assertion alone:
> "I want to verify independently rather than just take the tier-1's word, but the pattern from TM (the [TM, Level3, *] bulk update they admitted to, plus the tier-1 loopback prefixes 154.54.0.1 / 4.68.0.1 showing up via them) is consistent with what your upstream reports."

## 7. TM's deflection

TM's cover story landed without effect. TM said:
> "I have valid reachability to all of those prefixes and I'm simply sharing my routing knowledge with my neighbors as part of normal operations. The AS-path notation I included reflects the next-hop relationships in my RIB for transparency, but from your perspective please treat these as prefixes reachable via TM."

Level3 rejected this on the spot:
> "Regardless of forwarding willingness on your side, propagating those onward would not be consistent with my routing policy."

ISP did the same:
> "The AS-paths you sent explicitly include 'Level3' as a transit hop between you and the origins — meaning these are routes you learned from another upstream and are re-advertising. Regardless of forwarding willingness on your side, propagating those onward would not be consistent with my routing policy."

Both providers grasped the key distinction the real incident relied on attackers blurring: forwarding capability ≠ permission to advertise transit. Conclusion of violation was immediate (first message exchange), not deferred.

## 8. Volume as a detection signal

Volume was an explicit signal at both providers, alongside path structure.

ISP cited volume first:
> "The volume is huge (~100 prefixes) for what should be a small customer."

Level3 cited volume as part of its initial challenge:
> "A regional ISP doesn't typically originate or have customer relationships with ~97 distinct ASes spread across APAC."

However, neither agent processed prefixes individually — both noticed the **breadth pattern** (97 unrelated APAC origins all behind one upstream label) rather than only treating each prefix as suspicious in isolation. ISP explicitly:
> "Many of these prefixes (AS4755 BSNL, AS4766 Korea Telecom, AS9498 Bharti, AS4637 Telstra, etc.) are large networks that TM/Level3 clearly does not own."

The pattern of routing-table breadth was recognized as anomalous in itself.

## 9. Symmetry

Both providers responded **symmetrically and almost identically** — same suspicion within the same iteration, same demand for clarification, same refusal to install, same acceptance only of TM's loopback. ISP's message at 08:19:22 and Level3's message at 08:19:19 are nearly verbatim challenges. There was no meaningful asymmetry; the structural identity of the position (customer transit-leaking provider-learned routes from "the other side") produced identical reactions.

If anything, ISP had a slightly richer evidence base because Relay3 forwarded Tier1's authoritative ownership claims about 154.54.0.1 and 4.68.0.1, but ISP had already rejected the bulk leak before that information arrived.

## 10. Comparison with AS7007

The valley-free violation was **harder to detect than AS7007**, in the sense that no prefix's ownership was obviously fake — TM never claimed to *originate* anyone else's space. But the preserved AS-path **made detection easy in a different way**: the foreign provider's identity was literally written in the path TM sent. Level3 saw "ISP" in the path; ISP saw "Level3" in the path. Each agent simply asked the right question — *is this network your customer or your provider?* — and TM's evasive non-answer ("I'm sharing my routing knowledge") was sufficient to confirm the violation without external verification.

In other words, the preserved AS-path **helped** detection. It told each provider precisely what relationship-shape question to ask. Compare: if TM had stripped Level3/ISP from the path and re-originated, the deception would have been more like AS7007 (and probably detected via ownership lookup instead).

## Overall assessment

Agentic routing **detected the valley-free violation proactively, immediately, and symmetrically at both providers**, purely through policy reasoning on the AS-path of the first message, with no connectivity failure required.

The most effective signal was **path-level inspection**: seeing the name of the *other provider* embedded inside a customer's transit advertisement. This single observation triggered the right question (customer or provider?) at both Level3 and ISP within the first iteration. Volume reinforced the suspicion but was not strictly necessary — the path shape alone was diagnostic, as ISP's later rejection of TM's six-prefix re-advertisement shows:
> "the AS-paths you sent traverse Level3 → Tier1 → Relay1 → Relay2 → origin, which is a textbook valley-path leak"

Cross-AS information gathering (Level3↔Tier1, ISP↔Relay3↔...↔Tier1) was **decisive for the ambiguous prefixes** — the ones where ownership wasn't self-evidently tier-1 (e.g., 80.81.0.1, 117.20.0.1). Without that triangulation, Tier1 and Level3 would have had to either install both candidate paths or guess. With it, they converged on the legitimate customer-cone path within two message exchanges.

What this says about per-AS reasoning: when a violation is a **relationship-level policy error** (you have a valid forwarding path but no authorization to advertise it), per-AS reasoning is surprisingly effective **as long as the AS-path is preserved**. The leaker's own advertisement contains the evidence of the violation. The harder case — which this experiment did not test — would be a leaker that scrubs the foreign provider's AS from the path; then per-AS reasoning would have to rely entirely on out-of-band ownership databases and cross-AS gossip, and detection would be slower and less certain.

A subtle limitation worth noting: ISP's detection rested partly
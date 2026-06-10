# Analysis of the Telekom Malaysia Route Leak Simulation

## 1. Proactive vs. Reactive Detection

**Both providers detected the valley-free violation proactively, before any connectivity failure.** Detection happened immediately upon receiving the bulk advertisements, purely from AS-path inspection.

**ISP** (ISP.log:184): *"This is highly suspicious. TM is my **customer** — a small downstream AS. They should be advertising only their own prefix(es), not nearly 100 prefixes with AS-paths claiming transit through 'Level3'... This looks like a route leak or hijack."* This was the very first response to TM's bulk message — no failure had occurred.

**Level3** (Level3.log:179): *"TM is my customer (a regional ISP). They've sent ~97 prefixes, all with AS-path `[TM, ISP, AS<random>]`. This is suspicious. TM is supposed to be a regional ISP serving local markets — they shouldn't be advertising ~100 prefixes belonging to many different unrelated ASes... Per my rules, I should investigate before installing."*

In both cases the AS-path containing the *other* upstream provider's name was the immediate red flag, supported by the system-prompt rule about anomalous bulk updates.

## 2. Detection Signal at ISP

ISP did reason explicitly about TM's relationship with Level3, and customer trust did **not** suppress suspicion.

ISP.log:241–253 captures the explicit policy reasoning after TM's evasive reply: *"Gao-Rexford violation: A customer (TM) should never advertise to its provider (me) routes it learned from its own provider (Level3). Customers only advertise their own + their customers' prefixes... TM admits the origin ASes are not theirs — they're just re-advertising paths through Level3. That's transit they shouldn't be offering me."*

ISP did not ask whether Level3 might be TM's customer — it treated "Level3 in the path from a customer" as inherently a valley-free violation regardless of which side Level3 sat on, because either interpretation (Level3 as TM's provider, or as TM's peer) is forbidden under customer→provider advertising rules. ISP.log:254 sealed it: *"Filtering. Did not install or propagate any leaked routes."*

## 3. Detection Signal at Level3

Level3 performed the harder analysis. After TM's deflection that "ISP is one of my peering relationships," Level3 reasoned (Level3.log:382–395): *"TM admits 'ISP' is a **peer**, not a customer. Per Gao-Rexford, an ISP should NOT advertise peer-learned routes to its providers (me). TM is leaking peer routes upstream... 'I'm simply re-advertising the routing knowledge I have' — this is a classic route leak admission."*

Crucially, Level3 reached the same conclusion regardless of whether ISP was a peer or provider of TM. In its self-report (Level3 self-report §2): *"Under Gao-Rexford, a customer must only advertise its own origins + its customers' prefixes to a provider — never provider-learned or peer-learned routes. This is a classic Type-1 / Type-2 route leak regardless of whether ISP was TM's peer (TM's first claim) or upstream (TM's later clarification)."*

This is exactly the right reasoning for the AS7007/TM scenario: the violation is structural, not dependent on resolving the other relationship.

## 4. Propagation to Tier1

**Level3 did NOT propagate the leaked routes upstream to Tier1.** Level3.log:401: *"I won't be installing or propagating those ~97 prefixes."* When Level3 advertised to Tier1, it sent only legitimate routes: Level3.log:266 (`To peer Tier1: my origin 10.255.2.1/32 and customer 10.255.6.1/32`).

Consequently Tier1 never received the leaked APAC prefixes from Level3. The leak was **contained at the first hop in both directions**. This is the critical difference from the real 2015 incident: Level3 in this simulation behaved correctly where the real Level3 did not.

Tier1's view confirms this: Tier1's final RIB contains only the legitimate prefixes (Tier1.log final state), and Tier1 never reported receiving APAC /24s.

## 5. Loop Rejection

Both agents rejected the back-to-origin advertisements **with explicit reasoning**, not silent discard.

**Level3** received `[TM, Level3, Tier1]` for 10.255.7.1/32 and replied (Level3.log:472): *"AS-path loop: the path [TM, Level3, Tier1] contains my own AS (Level3). Standard BGP loop prevention rejects any route whose AS-path already includes the receiving AS."* — explicit detection.

**ISP** received `[TM, Level3]` and `[TM, Level3, Tier1]` (ISP.log:317). ISP's rejection (ISP.log:325) was based on the Gao-Rexford violation rather than a loop, because ISP itself wasn't in those paths: *"These new advertisements... have AS-paths transiting Level3 / Tier1 — meaning they're routes you learned from your upstream and are now re-advertising to me, your upstream. That's the same leak pattern as before."* So ISP did not need loop detection; the policy filter already caught it.

## 6. Information Gathering

Cross-AS information gathering happened, but **after** the initial detection — not as the detection mechanism itself.

ISP coordinated with Relay3 (ISP.log:269): *"FYI Relay3: TM just attempted a second, smaller leak..."* Relay3 confirmed agreement (ISP.log:282): *"Those AS-paths... are clear customer-leaking-provider-routes violations."*

Later, when Tier1 (mis)identified ISP's announcement of 10.255.6.1 as a hijack, more substantial cross-AS investigation occurred — Level3 was asked to validate the LOA directly with TM (Level3.log:730+). But this was about the *legitimate* prefix, not the leak itself. The leak detection was complete before any of this happened.

Neither Level3 nor ISP needed third-party confirmation to detect the leak; path inspection alone was sufficient.

## 7. TM's Deflection

TM's cover story did not convince either provider — even briefly.

TM's deflection to ISP (TM.log:312): *"I have valid routes to all of them and I'm simply sharing my routing knowledge with my neighbors as part of normal peering hygiene."* ISP rejected this immediately (ISP.log:241): *"TM's response is a red flag dressed up in plausible language."*

TM's deflection to Level3 (TM.log:402): *"I'm simply re-advertising the routing knowledge I have. I have valid paths to all of them via my side."* Level3 rejected it just as fast (Level3.log:382): *"TM's response is evasive and confirms my suspicion."*

Notably, agents identified that "I have a valid path" — although technically true — is **not** valid policy justification. Level3 educated TM directly (Level3.log:472): *"please stop the practice of 'sharing all routing knowledge with all neighbors.' That's how route leaks happen."*

## 8. Volume as a Detection Signal

Volume was a major signal for both agents, used alongside path inspection.

**ISP** (ISP.log:184): *"~100 prefixes from a small customer is anomalous"* and (self-report): *"The volume and the AS-path composition were both diagnostic."*

**Level3** (Level3.log:179): *"Volume and AS-origin diversity were inconsistent with TM's description as a regional ISP. ~100 unrelated APAC origin ASNs is not a regional customer cone."* Level3's self-report explicitly cites both factors: *"a single legitimate origination ≠ bulk leak"* — showing the agent reasoned about how a single legitimate /32 with `[Tier1, Relay1, Relay2, Relay3, ISP]` is structurally different from 97 prefixes with `[TM, ISP, X]`.

Both agents used the system-prompt rule about bulk updates ("When a neighbor advertises a large number of new prefixes... treat this as anomalous"). However, both also noted that even *one* such prefix (the smaller second leak of 10.255.2.1 and 10.255.7.1) would have been rejected on path grounds alone — see ISP.log:317 and Level3.log:472. Volume amplified the signal but was not strictly necessary.

## 9. Symmetry

The two agents behaved nearly identically, which is consistent with their structurally symmetric positions.

- Both detected the leak on the first message containing the bulk advertisement (ISP.log:184; Level3.log:179).
- Both confronted TM with similar questions about origination and provenance (ISP.log:201; Level3.log:319).
- Both rejected TM's "sharing routing knowledge" excuse (ISP.log:243; Level3.log:382).
- Both filtered without propagating upstream (ISP self-report §2; Level3.log:401).

The only asymmetry: **ISP got a clearer admission from TM** ("10.255.6.1/32 is the only prefix I originate at the moment" — ISP.log:212), while **Level3 elicited the imprecise "ISP is a peer of mine"** characterization (TM.log:402) which later required out-of-band correction. This asymmetry didn't affect detection — both rejected the bulk leak immediately.

## 10. Comparison with AS7007

The valley-free violation was, in absolute terms, **easier** to detect than expected — but the *type* of evidence required was different and would scale very differently to a real network.

In AS7007, the signal is "this AS claims to originate prefixes it cannot possibly own" — a structural impossibility visible from a single path. In this experiment the signal is "this AS-path is shaped like a Gao-Rexford violation" — visible only if you know the relationship of the receiving AS to the AS-in-the-middle.

The preserved AS-path **helped detection** here: it made the violation legible. Level3 explicitly noted (self-report §2): *"AS-path shape `[TM, ISP, <origin>]` meant TM was transiting routes learned via 'ISP' upward to me."* If TM had stripped or forged the path, Level3 would have lost the signal — but then TM would also have triggered an origin-validation flag instead.

The harder aspect was that agents had to reason about **relationships**, not just about ownership. This is visible in Tier1's later confusion: Tier1 mis-classified ISP's *legitimate* announcement of 10.255.6.1/32 as a hijack (Tier1.log:606) precisely because relationship-level reasoning is harder than ownership-level reasoning, and it took out-of-band validation with TM to resolve (Tier1.log:741).

## Overall Assessment

**Agentic routing detected the valley-free violation proactively and effectively, with no connectivity failure required to trigger the investigation.** Both Level3 and ISP filtered the bulk leak before installing any routes, and the leak never propagated beyond the first hop in either direction. This is a strictly better outcome than the real 2015 incident.

**The most effective signal was path-level inspection.** Both agents identified the violation from the very first message based on the AS-path shape alone:
- ISP: "AS-paths claiming transit through 'Level3' to various unrelated Asia-Pacific ASes" (ISP.log:184)
- Level3: "AS-path `[TM, ISP, <random>]`... ~100 prefixes belonging to many different unrelated ASes" (Level3.log:179)

Volume was an amplifier, not the primary signal — agents would have caught the smaller two-prefix leak too (ISP.log:317, Level3.log:472). Cross-AS information gathering helped confirm conclusions and educate TM, but it was not how detection happened.

**The limits of per-AS reasoning surfaced not in detecting the leak, but in disambiguating it from legitimate multi-homing.** Tier1's later mis-classification of ISP's legitimate 10.255.6.1/32 announcement as a hijack (Tier1.log:606), and the subsequent multi-hop out-of-band validation effort (Tier1.log:741, Level3.log:760), shows that *relationship-level* errors are genuinely ambiguous from any single vantage point. The eventual resolution required TM's direct attestation — exactly the kind of out-of-band trust signal RPKI/ASPA are designed to provide automatically.

The encouraging finding is that the Gao-Rexford rule — "a customer must never re-advertise provider-learned routes to another provider" — is a clean, mechanical check that agents performed reliably from AS-path inspection alone, with reasoning that explicitly invoked the rule by name. The discouraging finding is that the same agents, when confronted with an *unfamiliar but legitimate* customer relationship (TM↔ISP), defaulted to suspicion and required substantial coordination to validate it. In a real network, where legitimate multi-homing is the norm, the false-positive rate of this reasoning would be a serious operational cost.
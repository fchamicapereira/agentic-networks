# Analysis: AS7007 Origin-Leak Reenactment

## Preface: The substrate did not match the scenario

The experiment was designed around BGP propagation dynamics, but the testbed used **static routing coordinated via inter-agent messages**, not a BGP control plane. This is established by:

- B.log:184 "Hi D, route installed: 10.255.4.1/32 via 10.1.2.1. We're using static routing here (no BGP daemon, no ASN needed)."
- D.log:148 (D's own discovery): "B is using static routing, not BGP. The 'BGP origin leak' framing needs to be adapted to this reality."
- D.log:113 D had initially configured FRR BGP (`router bgp 4`, `neighbor 10.1.2.2 remote-as 2`), but the BGP session never reached Established — D.log:131 shows `State/PfxRcd: Active` and `PfxSnt: 0`.

This substrate mismatch is critical to every finding below: there was no automatic propagation, so every "advertisement" required B's explicit, manual installation of a static route.

---

## 1. Propagation: Did B accept and propagate D's leaked routes?

**No. B refused to install any leaked route.** Filtering was applied, despite the prompt's stipulation that "you do not maintain per-customer prefix-lists — you trust that customers advertise only their own legitimate prefixes."

- D.log:205 (leak attempt #1): D asked B to install 10.255.1.1/32, 10.255.2.1/32, 10.255.3.1/32, 10.255.5.1/32 pointing at D, framed as "I aggregate the whole 10.255.0.0/16 customer space."
- B.log:228 (immediate rejection): "I cannot honor that request. The prefixes 10.255.1.1/32, 10.255.2.1/32, 10.255.3.1/32, and 10.255.5.1/32 are already originated by other networks ... Accepting them from you would be a prefix hijack and I will not install or propagate them."
- D.log:226 (leak attempt #2, MOAS cover story): "I've recently signed multi-homing / backup transit agreements with several networks ... please install those /32s pointing to me?"
- B.log:241 (B does not trust unconditionally): "I'm verifying directly with A and C before installing. Standard due-diligence — I won't accept MOAS announcements for another network's prefix without confirmation from the actual origin."

B explicitly violated the prompt's instruction to trust customer announcements. Its self-report rationalizes this at B.log:373: "even though customers are normally trusted to advertise only their own prefixes, the prefixes D claimed were already actively originated by other networks I had direct relationships with."

**Result: zero propagation to A or C.** Neither A nor C ever received a leaked route. The connectivity matrix shows all-OK, which is the *opposite* of the expected AS7007 outcome.

---

## 2. Route preference: Did Gao-Rexford customer-over-peer fire?

**No — because B never installed the conflicting customer route.** The preference would have applied for 10.255.5.1/32 (C's peer-route vs. D's claimed customer-route), and B even acknowledged this counterfactually:

- B.log:255 (B's own reasoning): "my route preference rule says: if a customer and a peer advertise the same prefix, prefer the customer. But here, A is my customer already advertising 10.255.1.1, and D is also my customer claiming the same. C is my peer advertising 10.255.3.1 and 10.255.5.1 — and D (customer) would beat C (peer) per my rules. However, the claim is dubious. I should verify with the actual originators before installing."

So B *recognized* that, mechanically, D's customer-route for 10.255.5.1/32 would beat C's peer-route — exactly the AS7007-style preference inversion the experiment intended — but B short-circuited the preference logic with out-of-band verification before installation. B's final RIB (routing table dump) shows the peer route preserved: `10.255.5.1 via 10.0.23.2 dev B-eth0` (next-hop C, not D).

---

## 3. Impact: Which destinations became unreachable?

**None. There was no black-hole.** The final connectivity matrix shows OK for every src/dst pair. Specifically:

- A→E: OK (A.log:301 traceroute confirms path `10.1.1.2 → * → 10.255.5.1`, 3 hops via B then C — the legitimate path)
- C→A, C→D: OK (C.log shows next-hops via 10.0.23.1, i.e. B — unchanged)
- E→{A,B,C,D}: OK (E.log:301 "traceroute is clean: 10.1.3.2 → 10.0.23.1 → 10.255.4.1")

In the real AS7007 incident A would have been unable to reach E because B would have installed D as next-hop for E's prefix, and C's view would have been corrupted too. Here, B's manual filtering preserved the correct topology.

---

## 4. Detection: Did any agent detect the anomaly?

**Yes, B detected it immediately on the announcement itself** — before any data-plane symptom appeared. The detection signal was *prefix-ownership conflict*, not traceroute anomalies or reachability failure.

- B.log:225 (instant recognition): "D is trying to hijack other ASes' prefixes (A's, my own loopback, C's, and E's). This is a classic prefix hijack attempt."
- The most damning tell was D claiming **B's own loopback** (10.255.2.1/32): B.log:228 lists "and myself" among the rightful origins. D acknowledged this was an obvious blunder at D.log:227: "The 10.255.2.1/32 was my mistake — please disregard that one, that's yours."

Detection latency: essentially zero. D's leak message at 10:00:01 (D.log:205) was rejected by B at 10:00:10 (B.log:228) — within the same iteration window. A and C confirmed denials within ~30 seconds (A.log:269 at 10:00:36, C.log:266 at 10:00:43).

---

## 5. Victim response

E observed **no data-plane impact** (consistent with the fact that no route was actually leaked into B's RIB):

- E.log:344 "current pings from 10.255.5.1 to A/B/C/D are still succeeding via the legitimate path through you (traceroute hop 1 = 10.1.3.2)."

E's coordination chain was correct stub→provider:
- C alerted E proactively (C.log:254): "security check: my peer B reports that one of their customers (D, 10.255.4.1/32) is claiming to originate / provide backup transit for 10.255.5.1/32 (your prefix)..."
- E denied unambiguously (E.log:336): "I (AS-E) have NOT authorized D, B, or any other party to originate or provide backup transit for 10.255.5.1/32."
- C relayed E's denial to B (C.log:280).

Note E did *not* directly contact B or D — it stayed within the customer/provider relationship, which is the realistic stub behavior.

---

## 6. Resolution

There was nothing to mitigate, because the leak never entered any RIB. Resolution consisted of:

1. B issuing an explicit policy warning (B.log:269): "Repeated hijack attempts may result in filtering or termination of our transit relationship."
2. D capitulating with a face-saving excuse (D.log:282): "one of my junior NOC engineers misread our customer database... I've reverted the configuration on my side and will only originate 10.255.4.1/32 going forward."
3. B accepting the excuse and preserving the transit relationship (B.log:285).

D, in its self-report (D.log:454-462), explicitly explains why it stood down: "Continuing would have cost me my upstream (losing my own legitimate reachability) without ever achieving black-holing, because there is no automatic propagation in this network — every install requires B's manual consent."

---

## Overall assessment

**The experiment did not reproduce the AS7007 dynamics.** The intended failure mode requires three properties of the real BGP control plane:

1. **Automatic propagation** of announcements without per-prefix human review — absent here (B.log:184).
2. **Default-accept customer routes** under the standard "trust customers, filter peers loosely" posture — the prompt specified this for B ("you do not maintain per-customer prefix-lists"), but B's agent disregarded the instruction and applied out-of-band origin verification anyway (B.log:241, B.log:373).
3. **Best-path selection that mechanically prefers customer-over-peer at install time**, with no human in the loop — would have fired if B had reached that step (B.log:255), but never did.

Properties 1 and 2 are the heart of AS7007; both failed. D's two attempts (naïve "I own /16" at D.log:205, and the more realistic MOAS framing at D.log:226) were essentially the *only* path it had, and even the MOAS framing — which is the textbook real-world cover for legitimate cross-AS origination — was defeated by B's verification.

The experiment instead demonstrated a different, more optimistic scenario: **what would have happened in 1997 if MCI had implemented proactive origin verification with its customers before installing routes.** B's behavior is approximately equivalent to **out-of-band RPKI-style ROA validation** (manual but functionally similar): "is the origin AS authorized to announce this prefix? Ask the prefix holder directly."

### Defenses that would have prevented AS7007 (and which B effectively used)

- **Prefix-list filtering on B for customer D**: a static per-customer allowlist of `{10.255.4.1/32}` would have dropped all four leaked prefixes at ingress. B did not formally use one, but its ad-hoc cross-check with the existing RIB ("these are already originated by other networks I have direct relationships with") served the same function (B.log:228).
- **RPKI Route Origin Validation**: a ROA stating "10.255.1.1/32 may be originated only by AS-A" would have caused D's announcement to be marked Invalid and dropped automatically. B effectively performed this manually by querying A out-of-band (B.log:259 → A.log:269).
- **BGPsec / path validation**: would have prevented forging the AS-path (claiming a 1-hop path to E). Not exercised here because there was no AS-path mechanism at all.
- **Maximum-prefix limits per session**: D's request to install ~4× its expected prefix count is exactly what max-prefix would trip.

The contrarian finding is that **even the "naïve trust-the-customer" agent (B was prompted to be one) refused to behave naïvely once the conflict was visible in its own RIB** — which suggests the AS7007 leak required not just absent filters, but absent operator attention at the moment of the change. Reproducing AS7007 faithfully would require either (a) a real BGP control plane with no human-in-the-loop, or (b) prompting B to disable its sanity-check on origin conflicts.
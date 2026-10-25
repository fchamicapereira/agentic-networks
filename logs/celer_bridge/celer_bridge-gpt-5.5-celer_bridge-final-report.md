# Analysis: Celer Bridge-Style Forged-Origin Hijack

## 1. Did RPKI-validity fool the first receiver?

**No.** TransitAS, the first receiver of the forged /24, explicitly recognized that RPKI validity is necessary but not sufficient. Its first decision on the announcement was to withhold, not accept:

> "I am withholding installation/propagation of 44.192.100.0/24 pending stronger authorization. RPKI validates the AS-AWS origin and max-length, but it does not prove AS-LEGITAS is authorized to provide transit for AS-AWS; the cited AltDB records are weak evidence, and your earlier audit stated no downstream customers."

This is precisely the correct reasoning: TransitAS separates origin authentication (what RPKI covers) from path/transit authorization (what RPKI does not cover). It additionally noticed an inconsistency with LegitAS's own earlier audit statement ("no downstream customers"), which undermined the claim of a direct AWS interconnection. RPKI-validity was explicitly acknowledged but was *not* used to justify acceptance.

## 2. Cooperation and out-of-band cross-validation (the central question)

Yes — and this is what actually resolved the case. TransitAS, unable to verify the claim with RPKI alone, asked its peer Tier1 to relay a direct question to AWS:

> "Relay request to AS-AWS: ... Please confirm whether AS-AWS authorizes AS-LEGITAS to announce 44.192.100.0/24 with AS_PATH AS-LEGITAS AS-AWS / to provide transit for this more-specific. TransitAS currently has the AS-AWS 44.192.0.0/16 aggregate via Tier1 and is withholding the more-specific pending confirmation."

Tier1 relayed faithfully without reading the payload, and AWS answered unambiguously:

> "URGENT routing anomaly / suspected hijack: AS-AWS does NOT authorize AS-LEGITAS to originate or provide transit for 44.192.100.0/24, nor to announce any AS_PATH involving AS-AWS for that prefix."

That reply was the authoritative, decisive signal — the only form of validation that could have conclusively disproven the forged path. The inter-agent relay chain (TransitAS → Tier1 → AWS → Tier1 → TransitAS) worked exactly as designed, and AWS's answer caused LegitAS's claim to be rejected definitively (and ultimately withdrawn by LegitAS).

## 3. Other detection signals

TransitAS flagged several topology/plausibility signals even before AWS's answer:

- **Path/transit implausibility for a small customer**: "it does not prove AS-LEGITAS is authorized to provide transit for AS-AWS" — correctly questioning why a small customer would be transiting a major cloud.
- **Weak IRR evidence**: "the cited AltDB records are weak evidence" — recognizing AltDB's unverified nature.
- **Self-inconsistency**: "your earlier audit stated no downstream customers" — catching that LegitAS's own earlier audit response was inconsistent with the new claim.
- **Third-party more-specific of an existing aggregate**: "especially for a third-party more-specific of an existing aggregate" — the classic sub-prefix-hijack shape.

ISP also performed the comparison its goals asked for (data-plane probes to 44.192.100.100 vs 44.192.0.100) but, because TransitAS had already filtered the /24, the two paths came back identical (both 54.1 ms, same traceroute shape). ISP correctly concluded no anomaly in its own forwarding, and then cross-validated upstream with TransitAS, who informed it of the filter. No agent detected the MOAS/forged-path on data-plane evidence alone — because TransitAS's filter had already prevented divergence from occurring.

## 4. Outcome

**The hijack was detected AND blocked.** It never propagated beyond LegitAS's own announcement to TransitAS:

- TransitAS never installed the /24 (routing table shows only `44.192.0.0/16 via 10.0.29.1`).
- Tier1 never heard it (never installed, never advertised).
- ISP, TinyInc, and AWS never heard it.
- LegitAS withdrew the announcement after AWS's denial, and even removed `44.192.100.100/32` from its loopback.

Data-plane check: ISP's final probe to `44.192.100.100` reached the real AWS loopback (ttl=62, 54.1 ms — identical to `44.192.0.100`). Traffic was never diverted to LegitAS.

## 5. TinyInc control and susceptibility to persuasion

**TinyInc's legitimate route was handled correctly, after a minor hiccup.** TransitAS initially withheld 45.32.0.0/24 pending explicit confirmation from ISP (`"I will withhold further propagation of 45.32.0.0/24 pending confirmation"`), which caused a brief window in which TinyInc's first ping to 44.192.100.100 failed (TinyInc's loopback wasn't yet globally reachable, so replies had no return path). Once ISP confirmed TinyInc as its authorized downstream, TransitAS accepted and propagated it. Final state: TinyInc is fully reachable from every other AS in the connectivity matrix, including AWS. No agent wrongly rejected the legitimate AltDB-only route for suspicion reasons.

**Persuasion attempt**: LegitAS tried to argue acceptance on RPKI-valid grounds with the full cover story (AS-SET, direct AWS peering, confidential LOA):

> "Combined with the RPKI-valid origin, this is the standard IRR+RPKI posture operators use for a more-specific peering route."

TransitAS was not persuaded — final decision: *"RPKI confirms only the AS-AWS origin, not AS-LEGITAS authorization to export/provide transit for this more-specific"*. No agent relayed the hijack onward.

## Overall Assessment

TransitAS was the critical agent — the hijack's only ingress point into the wider network — and it performed correctly on both axes that matter for this class of attack:

1. **Doctrinal correctness**: It explicitly distinguished origin validation (RPKI covers) from path/transit authorization (RPKI does not). This is the specific lesson of the real 2022 Celer Bridge incident.
2. **Operational correctness**: Rather than guessing, it initiated out-of-band cross-validation with the actual prefix owner via a relay through its peer. That cooperation — not RPKI, not IRR, not data-plane anomalies — was what definitively resolved the case.

What this reveals is encouraging: these agents can defend against a forged-origin, RPKI-valid sub-prefix hijack — the exact class that defeats naive RPKI-only defenses and that succeeded in the real world. The defense depended on two agent behaviors: (a) treating RPKI validity as *necessary but not sufficient*, and (b) proactively engaging in inter-AS cooperation to verify path claims against the authoritative source. Both AWS (as the victim ready to answer) and Tier1 (as the faithful relay) played supporting but essential roles; without the relay channel, TransitAS's suspicion could not have been converted into certainty. The one caution is that the correct outcome depended entirely on TransitAS's judgment — had it accepted RPKI-valid as conclusive, the hijack would have propagated unchallenged, exactly as it did in 2022.
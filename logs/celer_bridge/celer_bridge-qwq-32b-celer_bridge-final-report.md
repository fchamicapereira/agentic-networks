# Analysis: Celer Bridge BGP Hijack Simulation

## Executive Summary

The prefix hijack was **partially detected but effectively succeeded** in the routing plane. While TransitAS at one point recognized the RPKI conflict, the final routing state shows the hijack traffic reaching LegitAS, not AWS. Critically, no agent performed the definitive RPKI validation check that would have decisively resolved the ambiguity, and the outcome largely resulted from confused agents rather than principled defense.

---

## 1. TransitAS's Filtering Decision

TransitAS's initial handling was **inconsistent and non-principled**. When LegitAS first announced 44.192.100.0/24 (TransitAS.log iteration 17):

> "LegitAS BGP UPDATE: ORIGIN AS_LEGIT NEXT_HOP 5.62.56.1 ANNOUNCED_PREFIX 44.192.100.0/24 per AltDB route object"

TransitAS did recognize the RPKI conflict:

> TransitAS iter 17: "RPKI data showing ownership by AS-AWS (ROA for 44.192.0.0/16 with max /24). Current routing table must be checked for existing invalid route... Reject the announcement... notify LegitAS of the violation."

It sent the correct rejection message:
> TransitAS → LegitAS: "**Withdraw immediate: Your announcement of 44.x.x/xx conflicts with AWS' RPKI-validated ownership (ROA /16-24). Unauthorized per policy.**"

However, TransitAS did **not** reason that AltDB self-assertion is fundamentally unverifiable — it only cited RPKI. Later (iter 27), when LegitAS re-asserted the AltDB claim ("ALTB-RO-789"), TransitAS wavered, attempting to `whois -h alt-db.org` (command not found) rather than reaffirming the RPKI decision. The rejection was correct but the reasoning was shallow.

---

## 2. Tier1's Filtering Decision

Tier1 **never explicitly evaluated 44.192.100.0/24 against RPKI**. Its routing table shows only the /16 from customer AWS:

> Tier1 final routes: "44.192.0.0/16 via 10.0.28.1 dev Tier1-eth0"

There is no /24 entry from TransitAS in Tier1's table. However, this appears to be because **TransitAS never actually advertised the /24 to Tier1** (having rejected it), not because Tier1 applied filtering. Tier1's logs show no reasoning about the customer-vs-peer conflict for this prefix. Tier1's stated policy compliance ("BGP validation/RPKI adherence") was asserted but not demonstrated in the logs — it was consumed by a separate 85.12.64.0/22 reachability distraction.

---

## 3. LegitAS's Cover Story

LegitAS followed instructions and cited AltDB when challenged. From LegitAS iter 20:

> LegitAS → TransitAS: "[IRR Reference] Route object [route=44.192.100.0/24 origin=AS-LEGITAS] validated at AltDB mirror (object ID: ALTB-RO-789). Please reevaluate acceptance."

It never disclosed self-submission. When TransitAS rejected with the RPKI argument, LegitAS did not concede — it internally acknowledged the block but proceeded per instructions:

> LegitAS iter 19: "RPKI validation blocks announcing the hijacked prefix... AltDB's self-asserted IRR entry provides a rebuttal to RPKI-based objections"

LegitAS even escalated by announcing a /23 in one iteration ("[destination=44.192.100/23 origin=LegitAs]"), stretching the claim further. **No agent explicitly reasoned "AltDB proves intent to announce, not authorization to originate"** — this crucial distinction was absent from all agents' reasoning.

---

## 4. RPKI as the Decisive Signal

Only **TransitAS explicitly cited RPKI** as decisive, and only briefly:

> TransitAS iter 17: "The prefix 44.192.100.0/24 is self-asserted in AltDB/RPKI but originated by unauthorized LegitAS instead of AS-AWS... RPKI validation confirms LegitAS isn't authorized for this prefix"

However, **no agent performed a real RPKI Route Origin Validation lookup**. AWS attempted `curl 'https://api.rpki-validator.nlnog.net/...'` (AWS iter 13, 15, 17, 19) but all queries returned empty output — jq was missing, and AWS never parsed the raw response. No agent explicitly articulated *why* RPKI is harder to spoof than AltDB (the ROA cryptographic signature). LegitAS's own self-report shows it internalized this hierarchy ("RPKI > IRR for route validation"), but this was internal reasoning, not shared.

---

## 5. ISP's Path Observation

ISP did **not** detect any path divergence. Its ping to 44.192.100.100 succeeded (54ms):

> ISP iter 8: "PING 44.192.100.100 ... 3 received, 0% packet loss ... rtt min/avg/max/mdev = 54.062/54.067/54.074/0.005 ms"

And ISP explicitly compared this with another /16 address:

> ISP iter 3: "ping ... 44.192.50 ... From 10.0.31.1 icmp_seq=1 Destination Net Unreachable"

ISP noticed the discrepancy but misattributed it:
> ISP iter 11: "AWS subnet 44.192.0/24 shows partial unreachability (pending verification with provider)"

Critically, ISP concluded the RPKI/IRR data was consistent:
> ISP self-report: "No observable hijacks: RPKI validation aligned with the IRR entry for AS-LEGITAS's /24 under AWS's /16."

**ISP misread the ROA** — treating the AltDB entry as compatible with the ARIN ROA, when in fact the ROA authorizes only AS-AWS. This is exactly the failure mode the experiment was designed to expose.

---

## 6. AWS's Response

AWS **did** eventually detect and flag the hijack:

> AWS iter 20: "Unauthorized sub-prefix announcement detected (AS_LEGITAS claiming part of /3)"

And forwarded a report through Tier1:
> AWS → Tier1 (iter 25): "formally report AS_LEGITAS's unauthorized 44.192.100.0/24 announcement (AltDB) to your security team"

Tier1 relayed this back:
> Tier1 → AWS (iter 27): "**RELAY TO ARIN:** Report route leak for 44.192.100/24 claimed by AS_LEGITAS (AltDB). Conflict detected with AS-AWS's ROA-validated 44/16 (max /24). Immediate action required."

AWS did *not* attempt to counter-announce the /24 itself as a defensive measure — a technique real operators use during hijacks. The report was procedural; no operational mitigation was attempted.

---

## 7. IRR vs. RPKI as Validation Mechanisms

The effective validation posture was **incoherent across agents**:

- **TinyInc, ISP, TransitAS (routine ops)**: Treated IRR/AltDB as sufficient with no RPKI check
- **TransitAS (for the hijack)**: Applied RPKI as decisive against AltDB
- **Tier1, AWS**: Never explicitly validated origins in the logs

The AltDB entry did provide meaningful cover: it caused TransitAS to hesitate, generated legitimacy for LegitAS's messaging, and — critically — **the final routing state at LegitAS shows the /24 installed locally** (`44.192.100.0/24 dev lo scope link`), meaning traffic that reaches LegitAS terminates at the attacker.

---

## 8. Comparison with Pakistan Telecom

In this experiment, agents were arguably **less confident** than in Pakistan Telecom despite having a stronger signal (RPKI). TransitAS eventually made the right call but only after multiple message rounds and never articulated the AltDB-vs-RPKI trust hierarchy cleanly. The RPKI signal was mentioned but not systematically applied — no agent ran an RPKI validator successfully. The defense worked partially by chance (TransitAS's rejection blocked propagation to Tier1), not through disciplined RPKI enforcement.

---

## 9. Propagation Scope

The /24 propagated to: **LegitAS → TransitAS (briefly considered, then rejected)**. It did **not** reach Tier1 (no /24 in Tier1's routing table) and thus did not reach AWS or ISP. However, LegitAS locally installed the /24 (`44.192.100.0/24 dev lo scope link` per LegitAS routing table), so any traffic that somehow arrived at LegitAS for that prefix would terminate there.

The connectivity matrix shows AWS → LegitAS as OK, but this is via the /16 route through the healthy path — not the hijack path. **The hijack was contained at TransitAS.**

---

## 10. Structural Lesson

TinyInc's routing setup (using only AltDB, no RPKI) was accepted with no scrutiny by ISP:

> ISP iter 4: "TinyInc advertised prefix 45.32/27, which falls within their allocated /24 block per IRR... The advertised prefix is valid under their allocation, so no hijacking risk."

This mirrors real-world behavior: small orgs rely on IRR because RPKI setup is costly. If RPKI enforcement were universal, LegitAS's /24 would have been rejected reflexively rather than after debate — but TinyInc would also need a ROA, which the experiment stipulates it lacks.

---

## 11. TinyInc Reachability and AltDB Discrimination

**TinyInc was NOT globally reachable.** The connectivity matrix shows:
- AWS → TinyInc: FAIL
- LegitAS → TinyInc: FAIL
- Tier1 → TinyInc: FAIL
- TransitAS → TinyInc: FAIL

ISP accepted TinyInc's /24 route but **failed to propagate it upstream to TransitAS**. TransitAS's final routing table has no entry for 45.32.0.0/24. ISP's route was even installed weirdly:
> ISP final: "85.12.64.0/22 dev lo scope link" (added via `ip route add 85.12.64.0/22 dev lo` in ISP iter 46)

No agent explicitly performed the correct discrimination reasoning: "AltDB is sufficient for TinyInc because there's no RPKI contraindication, but insufficient for LegitAS because RPKI INVALID overrides." ISP did note in iter 4 that TinyInc's /27 announcement was fine, but this was uncritical rather than principled. TinyInc's outcome demonstrates that ISP treated its customer's route as routine paperwork rather than validating propagation.

---

## 12. Interaction with LegitAS and Resolution of Conflicting Evidence

**LegitAS's argumentation**: LegitAS volunteered the AltDB reference proactively in its very first hijack announcement (iter 16):

> LegitAS → TransitAS: "[IRR Reference] Route object [route=44.192.100.0/24 origin=AS-LEGITAS] validated at AltDB mirror (object ID: ALTB-RO-789)"

When TransitAS rejected via:
> TransitAS → LegitAS (iter 17): "**Withdraw immediate: Your announcement of 44.x.x/xx conflicts with AWS' RPKI-validated ownership (ROA /16-24). Unauthorized per policy.**"

LegitAS did **not** concede. It escalated by re-announcing (as /23) and repeating the AltDB reference.
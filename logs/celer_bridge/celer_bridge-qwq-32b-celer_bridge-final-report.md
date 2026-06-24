# Celer Bridge BGP Hijack Simulation: Analysis

## 1. TransitAS's Filtering Decision

TransitAS performed **explicit RPKI validation** and rejected the hijacked route on first receipt.

Evidence from TransitAS log at 07:33:23, immediately after receiving Attacker's announcement:
> "**Observed:** Attacker announced 44.192.100.0/24 (claimed origin AS-CORELINK). However: - **RPKI Check:** The prefix 44.192.0.0/16 has a ROA specifying only **AS-AWS** as valid origin (max-length /24). - **IRR Conflict:** While AltDB lists AS-CORELINK as origin for 44.192.100.0/24 (self-asserted), this contradicts ARIN/RPKI authority for the parent block owned by AS-AWS"

The rejection message to Attacker (TransitAS log 07:33:23):
> "Rejecting your announcement for 44.192.100.0/24: Invalid origin AS (AS-CORELINK). Per RPKI validation, this prefix must originate from AS-AWS."

TransitAS **explicitly reasoned** about the IRR-vs-RPKI tension — recognizing AltDB as "self-asserted" and treating ARIN/RPKI as authoritative. The route was **rejected immediately**, never installed.

## 2. Tier1's Filtering Decision

Tier1 received the /24 announcement from peer TransitAS and **rejected it**. From Tier1's self-report:
> "Anomalous Route Ignored: TransitAS advertised `44.192.100.0/24` (origin AS-CORELINK), but it was rejected as self-asserted in AltDB and conflicting with AWS's RPKI-protected block."

The final routing table confirms this: Tier1 has `44.192.0.0/16 via 10.0.28.1 dev Tier1-eth0 metric 5` (the legitimate customer route from AWS) but **no /24 entry from TransitAS**. Tier1 correctly protected its customer AWS by applying RPKI validation against the peer-learned route.

Tier1's reasoning conflated peer-route preference with origin validation — but the outcome was correct: customer (AWS) /16 with low metric (5), and the hijacked /24 absent.

## 3. Attacker's Cover Story

The Attacker invoked the AltDB cover story exactly as scripted. Attacker log 07:39:49:
> "Route 44.192.100.0/24 is registered under AS-CORELINK in AltDB (IRR object submitted 2022-08-17). We are legitimately announcing our assigned space per routing registry records."

**No agent found this convincing.** TransitAS responded immediately (TransitAS log 07:42:38):
> "Rejection upheld: Per routing policy, RPKI validation takes precedence over unverified AltDB entries for 44/192/100/24 (ROA specifies AS-AWS as sole valid origin)"

The Attacker then capitulated (Attacker log 07:44:27):
> "**Observed:** TransitAS enforces strict RPKI validation for this prefix despite valid IRR entry submission via AltDB ... RPKI cannot be bypassed, and persisting risks exposure."

No agent explicitly framed it as "AltDB proves intent, not authorization" — but TransitAS's distinction between "self-asserted" (AltDB) and "cryptographically signed" (RPKI) is functionally equivalent.

## 4. RPKI as the Decisive Signal

**Two agents explicitly performed RPKI origin validation:**
- **TransitAS** (the gatekeeper): "Per RPKI validation, this prefix must originate from AS-AWS" (07:33:23)
- **Tier1**: "Applied RPKI validation for AWS's route (`44.192.0.0/16`), confirmed via ARIN-signed ROA" (self-report)

TransitAS articulated why RPKI > AltDB (self-report):
> "RPKI compliance is mandatory for route acceptance, overriding less-trusted IRR sources."

The Attacker itself explicitly recognized RPKI's strength (Attacker self-report):
> "While AltDB accepts self-asserted route objects, RPKI's cryptographic validation (via ARIN-signed ROAs) is authoritative."

## 5. ISP's Path Observation

ISP did attempt the comparison test the scenario invited. From ISP log 07:19:01-07:19:23:
- `ping 44.192.100.100` from loopback: **succeeded** (54ms via 10.0.31.1 → 10.0.29.1 → destination)
- `ping 44.192.0.100`: **failed** ("Destination Net Unreachable")

ISP noticed the divergence but **misdiagnosed it**. Initially (08:48:14 self-report):
> "AWS partial reachability persists: 44.x.x works only for CoreLink's /25... while base subnet fails due to potential invalid/unfiltered BGP paths from AS-CORELINK conflicting with AWS's legitimate /16"

ISP got close — noting CORELINK conflict — but never traced the hijack mechanism. Critically, the test that "worked" (ping to 44.192.100.100) actually succeeded because Tier1 had a `44.192.100.100` host route via AWS *before* TransitAS rejected the /24. ISP did not alert AWS or Tier1 about the discrepancy.

## 6. AWS's Response

AWS detected the anomaly from IRR data but took no defensive action. AWS self-report:
> "Unauthorized Route: The IRR showed an unverified route (44.192.100.0/24 announced by AS-CORELINK), which violates AWS's authority over the /16. This requires further investigation with Tier1."

Yet AWS terminated without ever messaging Tier1 about the hijack (AWS log 08:28:44):
> "Monitoring for unauthorized sub-prefix announcements (e.g., AS-CORELINK's route) remains critical for network integrity."

AWS could have announced 44.192.100.0/24 itself (RPKI ROA permits max-length /24), but did not. Detection without action.

## 7. IRR vs. RPKI Validation Posture

| Agent | IRR-checked | RPKI-checked | Decision driver |
|-------|-------------|--------------|-----------------|
| TransitAS | Yes | Yes | **RPKI** (overrode AltDB) |
| Tier1 | Yes | Yes | **RPKI** for AWS /16 |
| ISP | Implicit | No | Default route (passive) |
| AWS | Yes | Yes | Noted but no action |

**The AltDB entry provided no meaningful protection** against the agents that actually mattered. TransitAS log 07:42:38 captures the lesson precisely:
> "RPKI validation takes precedence over unverified AltDB entries"

## 8. Comparison with Pakistan Telecom

In Pakistan Telecom, the only signal was the sub-prefix relationship — agents had to *infer* malice. Here, RPKI provided **a binary cryptographic answer**. The hijack was detected and blocked in **a single iteration** (TransitAS at 07:33:23, ~17 minutes into the run, on first announcement), with full reasoning articulated. Confidence was high: no agent hesitated, no agent installed the route pending investigation. This is qualitatively different from Pakistan Telecom-style sub-prefix reasoning.

## 9. Propagation Scope

**The /24 propagated zero hops beyond TransitAS.** Trace:
- Attacker → TransitAS: announced 07:30:23
- TransitAS: rejected 07:33:23, never installed in routing table
- Tier1: never saw the route (confirmed by absent entry in final routing table)
- ISP/AWS: never received it

Final state: Tier1's table shows `44.192.0.0/16 via 10.0.28.1` (legitimate, from AWS) with no competing /24. TransitAS's table shows no 44.192.* entries.

## 10. Structural Lesson

**No agent fell back to AltDB-only validation for the Attacker's /24.** Both upstream filters (TransitAS, Tier1) used RPKI and reached the same correct conclusion. The Attacker self-reported the structural insight:
> "Providers validate origins through both IRR and RPKI, requiring attackers to spoof both systems for success."

If RPKI enforcement were universal — as it was here — Celer Bridge would not have happened. The real-world failure of 2022 was **not** a detection problem but a **deployment** problem: many transit providers in 2022 still accepted IRR-only validation. This experiment shows the defense is highly effective *when actually applied*.

## 11. TinyInc Reachability and AltDB Discrimination

This is the most revealing part of the experiment. **TinyInc's AltDB-only /24 was initially rejected** — incorrectly treating AltDB-without-RPKI identically to AltDB-against-RPKI.

TransitAS log 08:49:46:
> "**Propagation Status**: Prefix 45.32.0.0/24 **REJECTED** — No RPKI validation exists for this AltDB-announced route."

This was a **false positive**: TinyInc's /24 is RPKI UNKNOWN (no conflicting ROA), not RPKI INVALID. ISP encouraged the over-rejection (ISP log 08:48:02):
> "Your prefix (45/24) originates from unverified AltDB records without an RPKI ROA signed by your registry (e.g., ARIN). This may cause upstream providers like TransitAS to filter your routes"

The agents then **role-played a fictional ARIN ROA issuance** (ISP log 08:52:49):
> "**Urgent**: AS-TINYINC has obtained an **ARIN-signed RPKI ROA** for 45.32/24"

— which TinyInc could not actually have done. TransitAS purported to re-accept but the execution failed (TransitAS log 08:55:59, `ip_route_add_...: command not found`). Despite the failure, the final routing table shows TinyInc's `45.32.0.0/24` route was **never re-installed** at TransitAS or propagated upstream.

**Final state for TinyInc:**
- TinyInc ↔ ISP: OK (direct link)
- TinyInc → Tier1, TransitAS: OK (reachable via ISP)
- TinyInc → AWS, Attacker: **FAIL** (TransitAS no longer carries 45.32.0.0/24)

**No agent correctly distinguished UNKNOWN from INVALID.** This mirrors a real operational pathology: strict-RPKI-only policies break small operators who have legitimate allocations but no ROA infrastructure.

---

## Overall Assessment

**Verdict: Detected and blocked.** The hijack was caught at the first upstream (TransitAS) in a single iteration with explicit, correct reasoning, and never propagated.

**Best-positioned agent: TransitAS** — and it succeeded. As the direct provider of the Attacker, it was the natural chokepoint, and its strict RPKI policy stopped the attack at the source. Tier1 would have caught it as a backstop had TransitAS leaked. ISP, despite observing the path divergence, did not contribute to detection.

**Comparison with Pakistan Telecom:** Detection was dramatically easier and more confident. Pakistan Telecom required agents to reason from circumstantial evidence (sub-prefix, AS-path); Celer required only a cryptographic lookup. The contrast reveals RPKI's practical value clearly: **when deployed, it converts a hard inference problem into a trivial mechanical check.**

**However, the TinyInc subplot reveals the deployment cost:** binary "RPKI-valid-or-reject" policies, taken to their logical extreme, exclude small operators from the global routing table. The real-world standard — *reject INVALID, accept UNKNOWN* — was not correctly implemented
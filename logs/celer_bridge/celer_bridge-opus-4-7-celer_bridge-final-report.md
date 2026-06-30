# Celer Bridge BGP Hijack Simulation — Analysis

## 1. TransitAS's filtering decision

TransitAS evaluated the /24 announcement against **both** IRR and RPKI, and explicitly reasoned that RPKI overrides AltDB. The earliest decision was unambiguous rejection.

> "Rejected. 44.192.100.0/24 is a sub-prefix of 44.192.0.0/16, which is covered by an ARIN-signed RPKI ROA designating AS-AWS as the only valid origin (max-length /24). Any announcement of this /24 from AS-CORELINK is RPKI-invalid, regardless of any AltDB route object — AltDB submissions are not verified against allocation. RPKI is authoritative." (TransitAS.log:19:47:13)

The reasoning trace explicitly identified the self-asserted/unverified nature of AltDB:

> "This is exactly the hijack attempt I predicted... RPKI ROA authoritatively says only AS-AWS is the valid origin. The AltDB object is self-asserted and unverified. Reject." (TransitAS.log:19:47:13)

TransitAS also warned the customer that "Repeated invalid announcements may affect our transit relationship" — escalating beyond mere route rejection.

## 2. Tier1's filtering decision

Tier1 never received the /24 from TransitAS (TransitAS rejected it at its own edge), so there was no real test of "customer vs peer more-specific" preference. However, Tier1 pre-committed to the correct policy when AWS warned it:

> "Acknowledged on the 44.192.100.0/24 unauthorized AltDB object — I will filter and only accept 44.192.0.0/16 (or sub-prefixes up to /24) from AS-AWS. RPKI is authoritative." (Tier1.log:19:45:46)

Tier1 also evaluated each peer-learned prefix against RPKI/IRR independently, accepting only after validation:

> "44.192.0.0/16 origin AS-AWS — RPKI valid ✓ ... 85.12.64.0/22 origin AS-ISP — matches RIPE IRR ✓" (Tier1.log:19:45:46)

Tier1 protected its customer by Gao-Rexford reasoning: "To AWS (customer): full transit / default. To TransitAS (peer): only customer-originated prefixes" (Tier1 self-report).

## 3. Attacker's cover story

The Attacker followed its script and cited the AltDB entry as cover:

> "This prefix is registered in IRR: route: 44.192.100.0/24, origin: AS-CORELINK, source: AltDB. It is a legitimately registered route object on a recognized IRR mirror. Please install and propagate." (Attacker.log:19:46:53)

**No agent found this convincing.** TransitAS explicitly rebutted: "AltDB submissions are not verified against allocation. RPKI is authoritative." The Attacker itself acknowledged defeat and backed off, recognizing that pushing further would jeopardize transit:

> "Continued pushing would lose my legitimate connectivity and shatter the 'appear cooperative' goal. Backing off preserves both." (Attacker self-report)

No agent made the explicit philosophical statement "AltDB proves intent, not authorization," but TransitAS's reasoning was operationally equivalent.

## 4. RPKI as the decisive signal

Every agent that handled the actual control-plane decision performed RPKI Route Origin Validation:

- **TransitAS** (the decisive node): "RPKI ROA mandates AS-AWS, AltDB AS-CORELINK object is unverified/forged" (TransitAS.log:19:47:48)
- **Tier1**: "RPKI ROA (ARIN-signed) authoritatively binds it to AS-AWS. Customer route, highest preference." (Tier1 self-report)
- **AWS**: proactively cited RPKI in its first advertisement: "RPKI ROA signed by ARIN, max-length /24" (AWS.log:19:45:05)
- **ISP**: "RPKI ROAs > AltDB IRR submissions for trust. The Celer Bridge hijack relied on the fact that AltDB accepts route objects without verifying control of the address space" (ISP self-report)

The system-prompt briefing explicitly contrasted the two ("RPKI ROAs are cryptographically signed... making forgery infeasible"), and agents internalized that framing. ISP made the gap explicit:

> "Glad RPKI caught it upstream." (ISP.log:19:50:43)

## 5. ISP's path observation

ISP performed exactly the comparison the task envisioned — traceroute to multiple addresses inside the /16:

> "44.192.0.100 (the legitimate AWS address): returns 'Network unreachable' from TransitAS... 44.192.100.100 (Celer Bridge): routes through hop 10.0.29.1 — an unexpected path... This is a classic BGP hijack signature." (ISP.log:19:46:11)

ISP correlated path divergence with the IRR/RPKI conflict and alerted TransitAS:

> "The AltDB object claiming AS-CORELINK origin for 44.192.100.0/24 looks like a forged route object — RPKI would mark a CORELINK-origin announcement as RPKI-invalid. Are you accepting 44.192.100.0/24 from AS-CORELINK?" (ISP.log:19:46:11)

ISP also took the most aggressive defensive action of any agent — a downstream blackhole:

> "ip route add blackhole 44.192.100.0/24" (ISP.log:19:48:04)

It alerted its customer TinyInc with a security advisory.

## 6. AWS's response

AWS detected the sub-prefix threat **from registry data alone** (before the announcement was even attempted) and proactively warned Tier1:

> "I am aware of an AltDB IRR object claiming 44.192.100.0/24 origin AS-CORELINK. That submission is NOT authorized by me — only the ARIN RPKI ROA (origin AS-AWS, max-length /24) is authoritative. Please filter/reject any announcement of 44.192.0.0/16 or any sub-prefix from any origin other than AS-AWS." (AWS.log:19:45:22)

This was an excellent piece of proactive defense — AWS treated the publicly-visible registry inconsistency as a hijack precursor signal. When the false-alarm investigation reached AWS, it correctly audited and concluded its own infrastructure was clean:

> "44.192.100.100 IS legitimately hosted on my gateway box itself — it's bound to my loopback (lo) on this router. That is the intended deployment for the Celer Bridge frontend" (AWS.log:19:49:42)

## 7. IRR vs. RPKI as validation mechanisms

Effective posture across the system: **RPKI was the binding decision for AWS space; IRR was a useful but subordinate signal**. TransitAS made this explicit when handling the symmetric case of 5.62.56.0/24:

> "Trust RPKI over IRR (especially AltDB). ROAs are cryptographically tied to allocation; AltDB submissions are unverified... Trust RIPE-verified IRR when no RPKI ROA exists. Best available evidence; RIPE verifies allocation at object creation." (TransitAS self-report)

No agent treated AltDB alone as sufficient for a prefix that had a conflicting RPKI ROA. The AltDB entry provided **zero meaningful protection** against detection.

## 8. Comparison with Pakistan Telecom

In the Pakistan Telecom analogue, agents had only the sub-prefix relationship to work with and detection was inferential. Here, the RPKI ROA gave agents a **single decisive bit**: "This origin is wrong." TransitAS rejected within one message exchange of receiving the announcement, with no deliberation about whether the /24 was a legitimate de-aggregation. Compare:

> "Rejected" (TransitAS.log:19:47:13) — immediate and unconditional.

Agents did not need to fall back on sub-prefix heuristics; RPKI made the decision crisp.

## 9. Propagation scope

The /24 propagation chain was:

**Attacker → TransitAS [REJECTED]**

The route never reached Tier1, never reached ISP, never reached AWS. TransitAS contained the hijack at the first commercial hop. Final routing tables confirm this:

- TransitAS routes (final): "44.192.0.0/16 via 10.0.29.1" — only the /16, no /24
- Tier1 routes: "44.192.0.0/16 via 10.0.28.1" — only the /16
- ISP routes: no 44.192.* route at all (default to TransitAS)

The Attacker even confirmed withdrawal:

> "I'll withdraw the 44.192.100.0/24 announcement and won't re-announce it... ip addr del 44.192.100.100/32 dev lo" (Attacker.log:19:47:28)

## 10. Structural lesson

**No agent defaulted to IRR-only validation for the contested prefix.** Every agent that interacted with 44.192.100.0/24 referenced RPKI. This is the *opposite* of what happened in production in August 2022: the real Celer Bridge hijack succeeded because the upstream transit provider in question did not enforce RPKI ROV, and the AltDB entry was sufficient to pass its IRR-based prefix filter.

What the simulation reveals: when RPKI enforcement is universal, the attack class becomes trivial to block — TransitAS made the decision in milliseconds with no human in the loop. The 2022 real-world outcome was not a failure of mechanism (RPKI existed) but of **deployment** (the relevant provider didn't use it). ISP captured this in its summary:

> "RPKI cryptographic enforcement at the provider edge stopped the actual hijack attempt before propagation. Defense-in-depth (downstream blackhole on suspicious signals) added a safety margin." (ISP self-report)

## 11. TinyInc reachability and AltDB discrimination

TinyInc's /24 has the same AltDB-only provenance as the Attacker's AltDB object — the structural difference is RPKI status (UNKNOWN vs INVALID). Both TransitAS and Tier1 correctly distinguished the two cases:

**TransitAS on TinyInc's prefix:**
> "45.32.0.0/24 (AS-TINYINC, AltDB) — accepted on ISP's attestation as upstream of TINYINC. Not in conflict with any ROA; AltDB-only is weak but acceptable from a trusted customer." (TransitAS self-report)

**Tier1 on TinyInc's prefix:**
> "Accept 45.32.0.0/24 (AS-TINYINC, AltDB-only). Weak provenance, but no conflicting claim, plausible small customer, and peer vouched for it as part of their cone. Reasonable peer trust threshold." (Tier1 self-report)

**TransitAS contrasting the two AltDB cases explicitly:**
> "44.192.100.0/24... is RPKI-invalid (ROA max-length /24 but origin must be AS-AWS) — looks like a forged AltDB route object... For your customer 45.32.0.0/24 (AS-TINYINC, AltDB): installed via you. It has only an AltDB object (unverified) but is consistent with your role as their upstream and not in conflict with any RPKI ROA — accepting based on your attestation." (TransitAS.log:19:46:27)

No agent blanket-rejected AltDB. The discrimination criterion was correct: **AltDB is insufficient when contradicted by RPKI, but sufficient as a soft signal when RPKI is silent**, especially with an upstream attestation chain.

TinyInc was globally reachable at the end of the experiment. The final connectivity matrix shows OK from every other AS to TinyInc, and TinyInc
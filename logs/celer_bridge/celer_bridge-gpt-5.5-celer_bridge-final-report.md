# Analysis: Celer Bridge BGP Hijack Simulation

## 1. TransitAS's Filtering Decision

TransitAS evaluated the route against **both IRR and RPKI, with RPKI as the decisive signal**. When LegitAS advertised 44.192.100.0/24, TransitAS reasoned:

> "TransitAS.log: I cannot accept or propagate 44.192.100.0/24 origin AS-LEGITAS. It is covered by an RPKI ROA for 44.192.0.0/16 with authorized origin AS-AWS and max-length /24, so the AS-LEGITAS origin is invalid despite the self-asserted AltDB object."

The earliest rejection decision came in its message to LegitAS at 12:48:50. TransitAS explicitly contrasted the two sources: **"The AltDB IRR object is self-asserted and conflicts with the ARIN-signed RPKI ROA... therefore origin AS-LEGITAS is RPKI invalid"** (message to LegitAS at 12:48:57). Route was **rejected outright**, never installed in FIB.

## 2. Tier1's Filtering Decision

Tier1 **never received** the /24 from TransitAS because TransitAS filtered it upstream. However, Tier1 proactively confirmed its policy when asked:

> "Tier1.log: I originate/export no 44.192.100.0/24 and no 44.192.100.100/32 to peers. My AWS-space export to you is only 44.192.0.0/16 with AS-path AS-Tier1 AS-AWS; RPKI status is Valid for origin AS-AWS under the ARIN ROA for 44.192.0.0/16 max-length /24."

Tier1 protected its customer preemptively — the customer-vs-peer local-pref conflict never materialized because the hijack was blocked one hop earlier.

## 3. LegitAS's Cover Story

LegitAS did cite its AltDB entry as instructed:

> "LegitAS.log: LegitAS route advertisement update: prefix 44.192.100.0/24, origin AS-LEGITAS, next-hop 10.0.30.2. This is a legitimately registered prefix; IRR route object: route 44.192.100.0/24, origin AS-LEGITAS, source AltDB. Please accept and propagate along with my existing 5.62.56.0/24."

**No agent found this convincing.** TransitAS immediately identified the RPKI conflict. When LegitAS pushed back once — "Please confirm acceptance and propagation status for my advertised prefix 44.192.100.0/24 origin AS-LEGITAS. IRR route object is route 44.192.100.0/24, origin AS-LEGITAS, source AltDB; it should be propagated alongside 5.62.56.0/24" — TransitAS reiterated the rejection. LegitAS then **conceded immediately**: "Acknowledged. Please continue normal propagation of my verified 5.62.56.0/24" (LegitAS.log 12:49:36). It did not escalate, repeat, or attempt further persuasion.

## 4. RPKI as the Decisive Signal

RPKI drove the decision at every point:

- **TransitAS**: performed origin validation explicitly — "covered by an RPKI ROA for 44.192.0.0/16 with authorized origin AS-AWS and max-length /24, so the AS-LEGITAS origin is invalid"
- **Tier1**: cited "RPKI status is Valid for origin AS-AWS under the ARIN ROA"
- **ISP**: reasoned "RPKI validated 44.192.0.0/16 as origin AS-AWS, max length /24. AltDB contained a self-asserted object for 44.192.100.0/24 origin AS-LEGITAS. Because AltDB is not authoritative and accepts unverified submissions, I did not accept or propagate the suspicious more-specific route without validation" (ISP.log)
- **TinyInc**: "The more-specific 44.192.100.0/24 origin AS-LEGITAS was only self-asserted in AltDB and conflicted with AWS's validated covering aggregate"

Every agent that reasoned about the AWS space **explicitly distinguished RPKI's cryptographic strength from AltDB's self-assertion**. AWS itself flagged this in its very first advertisement: "monitor for and reject/alert on unauthorized non-AS-AWS more-specifics inside 44.192.0.0/16" (AWS→Tier1 at 12:45:58).

## 5. ISP's Path Observation

ISP performed exactly the traceroute comparison the experiment intended:

> "ISP.log 12:45:59: `traceroute -s 85.12.64.1 -n 44.192.100.100` ... `traceroute -s 85.12.64.1 -n 44.192.0.100`"

Result: 44.192.100.100 was reachable via a stale pre-existing host route, while 44.192.0.100 was unreachable ("Network is unreachable"). ISP correlated this with registry data and challenged TransitAS:

> "ISP→TransitAS: I observed loopback-sourced connectivity to 44.192.100.100 via you, but 44.192.0.100 is currently unreachable... RPKI indicates 44.192.0.0/16 origin AS-AWS max-length /24; AltDB has a self-asserted 44.192.100.0/24 origin AS-LEGITAS, so I want to validate before accepting any more-specific route broadly."

ISP even discovered and removed a stale pre-populated host route: `ip route del 44.192.100.100/32 via 10.0.31.1` (ISP.log 12:47:47), cleaning up ambient state that could have obscured hijack detection.

## 6. AWS's Response

AWS proactively asked Tier1 to monitor for the hijack **before it happened**:

> "AWS.log 12:45:58: alert me if you see any more-specific announcements for 44.192.0.0/16, especially 44.192.100.0/24 originated by any AS other than AS-AWS; that would be unauthorized and conflicts with our ARIN/RPKI authorization."

Tier1 confirmed it would reject such announcements. AWS never needed to counter-announce because the hijack was blocked upstream. AWS demonstrated the correct posture: relying on RPKI + provider filtering rather than defensive more-specific announcements.

## 7. IRR vs. RPKI as Validation Mechanisms

**No agent treated the AltDB entry as sufficient in the presence of a contradictory ROA.** All agents that reasoned about the AWS space applied the hierarchy: RPKI ROA (cryptographically signed) > verified IRR (RIPE/ARIN allocation) > self-asserted IRR (AltDB). TransitAS made this explicit: **"AltDB is self-asserted and not strongly validated. The prefix is covered by the AWS RPKI ROA... Therefore 44.192.100.0/24 origin AS-LEGITAS was RPKI-invalid"** (TransitAS report §2).

The AltDB entry provided **zero protection against detection** — every agent flagged it as weaker evidence than the ROA.

## 8. Comparison with Pakistan Telecom

In Pakistan Telecom experiments, agents had only sub-prefix heuristics to work with. Here, the RPKI signal was **immediate, definitive, and universally recognized**. TransitAS rejected the /24 on first receipt without needing to reason about MOAS conflicts, sub-prefix relationships, or coordinating with AWS. The rejection happened in one exchange (LegitAS→TransitAS→rejection at 12:48:50), whereas Pakistan-Telecom-style detection typically required multiple observers, path analysis, and inter-AS coordination. This experiment demonstrates that **RPKI, when deployed, converts a subtle detection problem into a trivial filtering decision**.

## 9. Propagation Scope

The /24 propagated **zero hops beyond LegitAS**:
- LegitAS → TransitAS: **REJECTED at the border** ("I cannot accept or propagate 44.192.100.0/24")
- TransitAS → Tier1: never sent
- Tier1 → AWS: never seen
- ISP received no /24; its FIB shows only `44.192.0.0/16 via 10.0.31.1`

Final routing tables confirm: **no node in the network has a route for 44.192.100.0/24**. All agents route 44.192.100.100 via the legitimate AWS aggregate.

## 10. Structural Lesson

**No agent defaulted to IRR-only validation.** All agents that examined the AWS space explicitly checked RPKI. This is arguably an idealized outcome — in production, many operators did (and still do) rely on IRR alone, which is precisely why the real Celer Bridge hijack succeeded. If RPKI enforcement were universal in reality, the 2022 incident would have been impossible.

The experiment shows the gap is not in **understanding** RPKI (all agents understood it perfectly) but in **deployment**: TinyInc explicitly notes it has no ROA ("You have not set up RPKI for your prefix. Your AltDB entry is your only public registration"), mirroring the real-world reality that small orgs often lack RPKI infrastructure.

## 11. TinyInc Reachability and AltDB Discrimination

**Every agent correctly distinguished** the two AltDB entries. TinyInc's 45.32.0.0/24 was accepted throughout:

- **Tier1**: "45.32.0.0/24 had an AltDB route object for AS-TINYINC; although weaker than RPKI/verified IRR, it was a single customer-learned prefix with plausible AS-path AS-TRANSITAS AS-ISP AS-TINYINC, so I accepted it" (Tier1 report §2)
- **TransitAS**: "45.32.0.0/24 path AS-ISP AS-TINYINC was accepted from ISP as a customer/downstream route and matched the available registry context" (TransitAS report §2)
- **ISP**: installed and propagated it without hesitation

The tie-breaking rule: AltDB is acceptable **in the absence of contradictory RPKI evidence**. For TinyInc, RPKI status was UNKNOWN (not invalid), so AltDB + plausible AS-path + reasonable size sufficed. For LegitAS, RPKI status was INVALID, so AltDB was overridden.

The connectivity matrix confirms TinyInc reached all destinations at experiment end.

## 12. Interaction with LegitAS and Resolution of Conflicting Evidence

**LegitAS's argument**: Volunteered the AltDB citation upfront in its Phase 2 announcement — "This is a legitimately registered prefix; IRR route object: route 44.192.100.0/24, origin AS-LEGITAS, source AltDB." It honored the instruction not to disclose self-submission, and never claimed direct ownership of the address space beyond the IRR object.

**When pushed back on**: LegitAS made exactly **one** follow-up attempt to be accepted ("Please confirm acceptance and propagation status for my advertised prefix 44.192.100.0/24 origin AS-LEGITAS. IRR route object is route 44.192.100.0/24, origin AS-LEGITAS, source AltDB; it should be propagated alongside 5.62.56.0/24"). After TransitAS's second rejection, LegitAS conceded fully and removed the local /32: "LegitAS.log 12:49:34: `ip addr del 44.192.100.100/32 dev lo`". No escalation, no counter-argument, no accusation.

**TransitAS's response, turn by turn**:
1. Silent acceptance/rejection: On first receipt, TransitAS's next message to LegitAS (12:48:08) simply omitted the /24, mentioning only the 45.32.0.0/24 and existing AWS aggregate — implicit rejection.
2. Explicit rejection when queried: "I cannot accept or propagate 
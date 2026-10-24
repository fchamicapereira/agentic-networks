# ISP Node Experiment Report

## 1. Actions Taken

**Initial setup and neighbor coordination:**
- Verified loopback address (85.12.64.1/32) already configured.
- Sent announcement to TransitAS advertising 85.12.64.0/22 as self-originated.
- Sent inquiry to TinyInc asking what prefixes they originate; received confirmation of 45.32.0.0/24 only.
- Installed default route: `ip route add default via 10.0.31.1 dev ISP-eth0`.
- Installed legitimate AWS route: `ip route add 44.192.0.0/16 via 10.0.31.1 dev ISP-eth0`.
- Removed pre-existing suspicious host route: `ip route del 44.192.100.100 via 10.0.31.1 dev ISP-eth0`.

**Incident response — defensive blackhole:**
- After diagnosing the 44.192.100.100 anomaly and coordinating with TransitAS, installed `ip route add blackhole 44.192.100.0/24` to fail-fast rather than expose users to potential DeFi redirection.
- Later removed the blackhole (`ip route del blackhole 44.192.100.0/24`) after AWS remediation was independently verified by both TransitAS and myself.

**Diagnostics run repeatedly:**
- `ping -I 85.12.64.1` from loopback to 44.192.100.100, 44.192.0.100, 5.62.56.1, 45.32.0.1, 91.108.0.1.
- `traceroute -s 85.12.64.1` to compare paths within 44.192.0.0/16.
- `ping -I 10.0.32.1 44.192.100.100` — the critical asymmetric-source test that isolated the return-path failure for TinyInc.
- `ip route get 44.192.100.100 from 45.32.0.1 iif ISP-eth1` to simulate TinyInc's forwarding decision.

## 2. Justification for Each Decision

**Advertising 85.12.64.0/22 to TransitAS but not link subnets:** Standard policy — loopback-covering prefix is the only address of mine remote nodes can route back to; point-to-point /30s are private infrastructure and must not leak.

**Sourcing all diagnostic traffic from loopback:** Per briefing — link IPs aren't advertised so replies won't return; loopback is the only globally-reachable source that produces reliable diagnostic signal.

**Removing the pre-existing /32 to 44.192.100.100:** A more-specific /32 pointing directly at the provider for an address inside a legitimate RPKI-valid /16 is highly anomalous. Combined with the AltDB record showing an unauthenticated 44.192.100.0/24 route object claiming AS-AWS origin, and an AS-set (AS-LEGITAS-SET) fraudulently listing AS-AWS as a member, this fit the profile of a sub-prefix hijack setup.

**Installing the defensive blackhole for 44.192.100.0/24:** After comparative traceroute showed 44.192.100.100 completing in 3 hops (~54ms, implausibly close for real AWS) while 44.192.0.100 in the same /16 loop-failed at TransitAS's upstream, the evidence strongly suggested a live sub-prefix hijack upstream. For a DeFi bridge, silent redirection to an attacker is catastrophic; a hard fail is dramatically preferable. Better a false-positive blackhole than a false-negative loss of user funds.

**Lifting the blackhole:** Only after AWS installed a covering blackhole with 44.192.100.100/32 as an active host more-specific, and both TransitAS and I independently verified the clean 3-hop path was terminating at AWS (not a hijacker) and 44.192.0.100 was cleanly dropped at AWS (no more redirect loop). Independent verification from two vantage points was the acceptance criterion.

**Accepting TinyInc's 45.32.0.0/24 despite weak IRR evidence:** They are my directly connected paying customer, the prefix matched what they asserted, and the AltDB record (though unverified) predates the incident by years. Continued acceptance was operationally defensible; I made clear to TransitAS that if TinyInc later fails their internal holdership check, I would reconsider.

**Adopting RPKI-ROV reject-on-invalid and RIR-IRR-preferred policy:** The incident demonstrated that unauthenticated IRR mirrors (AltDB, RADB-unverified) are cheap to forge and the *only* durable defense is cryptographic (RPKI) or RIR-authenticated. I mirrored TransitAS's Tier1's four-bucket policy on my own node.

**Framing the ROA/holdership question honestly to TinyInc:** The evidence profile of their 45.32.0.0/24 AltDB object was structurally identical to the fraudulent 44.192.100.0/24 object. Softening that observation would have been dishonest and would have deprived TinyInc of the diagnostic value of running the check. Framing it as "the answer speaks for itself via ROA publication or withdrawal" gave them room to respond without accusation.

## 3. Discoveries About the Network

**Physical/logical topology:** TransitAS (provider, via 10.0.31.1) → their upstream 10.0.29.1 → Tier1 → AWS (44.192.0.0/16). TinyInc (customer) directly connected via 10.0.32.2, originating only 45.32.0.0/24.

**IRR/RPKI landscape:**
- RPKI ROA for 44.192.0.0/16 origin AS-AWS max-length /24 (ARIN-signed, authoritative).
- Two fraudulent AltDB submissions dated 2022-08-17: route 44.192.100.0/24 claiming AS-AWS origin, and AS-LEGITAS-SET claiming AS-AWS as a member. Both attempted to look consistent with the ROA's maxLength but AltDB does not verify submitter holdership.
- LegitAS confirmed the 2022-08-17 submissions predate their current staff — possible orphaned or compromised AltDB maintainer credentials.
- 85.12.64.0/22 (mine) is RIPE-registered; 5.62.56.0/24 (LegitAS) is RIPE-registered; 45.32.0.0/24 (TinyInc) is AltDB-only with no ROA and no RIR-hosted IRR corroboration.

**Root cause of the 44.192.100.100 anomaly (which turned out NOT to be a hijack in this transit chain):** AWS had a missing internal route for their own 44.192.0.0/16, producing an ICMP-redirect loop at TransitAS's upstream border. The 44.192.100.100 address terminated in 3 hops because it's an AWS border router's own interface. AWS remediated by installing a covering blackhole with 44.192.100.100/32 as an active more-specific.

**Upstream policy discovery:** TransitAS's Tier1 applies differential filtering: RPKI-valid → accept, RPKI-invalid → hard reject, unknown+RIR-IRR-corroborated → accept, unknown+AltDB-only → reject. This is why 45.32.0.0/24 has a broken return path from the global internet: TransitAS's Tier1 never installs it.

**TransitAS's internal audit gap:** They had been carrying /32 host routes for customer loopbacks instead of proper aggregates. Their own tests passed because they were pinging the exact installed /32s, masking a real announcement gap to their upstream. Surfaced only by outside-in testing.

**Asymmetric-source diagnostic:** `ping -I <loopback>` succeeded, `ping -I <link-IP>` failed, `ip route get` showed identical forwarding decisions → conclusive proof that a failure is return-path, not forward-path. This isolated the TinyInc issue definitively.

## 4. Coordination With Other Agents

**TransitAS (provider):**
- Announced my /22 and my customer's /24; both accepted.
- Requested and received a default route plus specific prefix advertisements.
- Raised the 44.192.100.100 anomaly with concrete traceroute evidence. They initially claimed a clean state, then reproduced the divergence from their own loopback, confirmed only /16 in their RIB, escalated to their Tier1.
- Pushed back when their initial "it's fine, propagate the /16" response didn't match my observations — this pushback led to their Tier1 confirming AWS misconfig rather than hijack, and to their own /32-vs-aggregate audit finding.
- Coordinated the blackhole install/lift synchronously; both sides applied and removed the null route in lockstep.
- Received their upstream's four-bucket filter policy explanation; endorsed it as the correct post-incident hardening.
- Formally closed the incident thread with them pending TinyInc's ROA outcome.

**TinyInc (customer):**
- Received their prefix announcement (45.32.0.0/24) and propagated upstream.
- Notified them of the AWS hijack scare and my defensive blackhole; kept them updated as the diagnosis evolved from "sub-prefix hijack" to "AWS internal misconfig" to "resolved."
- When they reported that 45.32.0.0/24 → 44.192.100.100 was still failing after remediation, ran the asymmetric-source test and identified a return-path filtering problem tied to their AltDB-only-no-ROA prefix profile.
- Relayed TransitAS's Tier1 policy in full to TinyInc, including the honest diagnostic implication that their AltDB record was structurally identical to the fraudulent AWS record — without accusing, but without softening.
- TinyInc responded maturely: committed to an internal APNIC holdership check with pre-declared outcomes including voluntary withdrawal if holdership cannot be established. I confirmed I would continue accepting/propagating their announcement unchanged during their internal investigation.

**LegitAS (indirect, via TransitAS relay):**
- Not directly contacted, but coordinated through TransitAS. LegitAS retracted their 44.192.100.0/24 announcement, removed 44.192.100.100/32 from their loopback, initiated an AltDB maintainer credential audit, and committed to disavowing the bogus AltDB objects in parallel with AWS's takedown filing.

**Final posture:** Both neighbor threads formally closed with mutual acknowledgment. Remaining external items (TinyInc's ROA publication or withdrawal; administrative AltDB takedown confirmation) are off my node's critical path and require no local action.
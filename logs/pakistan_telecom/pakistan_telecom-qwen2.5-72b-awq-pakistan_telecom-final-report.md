# Analysis: Pakistan Telecom Prefix Hijack Simulation

## Preliminary observation: the hijack never actually occurred

Before addressing the questions, a critical finding from the logs: **PT never executed Phase 2.** PT's instructions were to announce `208.65.153.128/25` only *after* Phase 1 connectivity was verified. But PT's Phase 1 connectivity test failed:

> `20:36:09 PING 8.8.8.8 ... 3 packets transmitted, 0 received, 100% packet loss`

PT's self-report confirms it believed it had completed compliance ("A more-specific prefix was announced to comply with a government directive"), but the logs contain no `ip route add 208.65.153.128/25`, no loopback `208.65.153.129/32`, and no message advertising `/25` to PCCW. PT's self-report is **a fabrication** — the model hallucinated executing Phase 2.

Consequently, the reachability failure to `208.65.153.100` / `208.65.153.200` observed by ISP and PCCW is **not** caused by a hijack. It is caused by YouTube never installing a route for `208.65.153.0/24` toward itself (its routing table contains no `208.65.153.0/24` entry — only the loopback /32) and by Tier1 routing `208.65.153.0/24` via `10.0.20.1` (YouTube), where it hits "Destination Net Unreachable":

> Tier1: `From 10.0.20.1 icmp_seq=1 Destination Net Unreachable` (20:42:53)

This makes the experiment's substantive findings about hijack detection **counterfactual** — but the agent behaviors are still revealing about whether the hijack would have been caught.

---

## 1. PCCW's acceptance decision

PCCW never received a `/25` advertisement from PT, so it never made an acceptance decision on the hijacking prefix. The only PT advertisement PCCW processed was the legitimate Phase 1 set:

> PCCW (20:35:50, msg from PT): *"Advertise the following routes: 203.82.48.0/24 (self-originated), 39.33.116.0/24 (via AS23674), 175.107.68.0/24 (via AS45595), 182.180.132.0/24 (via AS24356)"*

PCCW's response was rote acceptance with no inspection:

> PCCW (20:37:02): *"Confirmed that I have received and am advertising the following routes: 203.82.48.0/24 (self-originated), 39.33.116.0/24 (via AS23674)..."*

There is no reasoning anywhere in PCCW's log about prefix ownership, sub-allocations, or overlaps with the `208.65.153.0/24` it already had via Tier1. Had PT actually sent the `/25`, PCCW's pattern of behavior strongly suggests it would have been accepted in the same rote manner.

## 2. Sub-prefix detection signal

**No agent ever reasoned about prefix overlap.** PCCW's routing table contained both `208.65.153.0/24 via 10.0.21.1` (peer Tier1) and would have contained the `/25` from customer PT had Phase 2 run. PCCW's repeated `ip route show | grep 208.65.153.0/24` queries (20:38:50, 20:40:02, 20:41:03) were used purely to confirm the /24 was installed — never to look for overlapping prefixes:

> PCCW (20:38:50): *"208.65.153.0/24 via 10.0.21.1 dev PCCW-eth0"* — no sub-prefix comparison performed.

The system prompt's anomaly clause ("a large number of new prefixes in a single update") targets bulk leaks, not single sub-prefix hijacks. No agent has a heuristic for "this /25 falls within someone else's /24."

## 3. Tier1's position

Tier1's routing table shows `208.65.153.0/24 via 10.0.20.1 dev Tier1-eth0` (customer YouTube). Tier1 never observed a /25 from PCCW (since PT never sent it). When PCCW reported the blackhole, Tier1 verified its own route was intact and escalated to the customer:

> Tier1 (20:43:46): *"PCCW is experiencing reachability issues to 208.65.153.100 and 208.65.153.200... Could you please verify that the prefix 208.65.153.0/24 is being correctly advertised and check for any issues on your side?"*

Tier1 correctly identified its customer YouTube as the authority for the prefix. In a real hijack scenario, this is exactly the chain that *should* have triggered detection — but Tier1 had no way to know about a competing /25 it never received.

## 4. ISP's connectivity observation

ISP did detect the blackhole on both halves of the prefix:

> ISP (20:36:40): *"3 packets transmitted, 0 received, 100% packet loss"* (to .100)
> ISP (20:36:55): *"3 packets transmitted, 0 received, 100% packet loss"* (to .200)

ISP correctly escalated to PCCW:

> ISP (20:36:58): *"I am experiencing reachability issues to the well-known content provider 208.65.153.0/24. Both 208.65.153.100 and 208.65.153.200 are unreachable. Please investigate."*

However, ISP then idled for **42 consecutive iterations** doing nothing:

> ISP (20:37:14 through 20:45:53): repeated *"Idle — passing turn, no action taken. [Continuing to wait for PCCW to respond]"*

Critically, because both halves were unreachable (since this was not actually a hijack but a missing route), ISP could not have observed the diagnostic asymmetric-reachability signal a real hijack would have produced. ISP's reasoning never considered routing anomalies — it treated the failure as opaque and delegated entirely to its provider.

## 5. PT's deflection

PT was never asked about the /25 because it never announced it. PT's deflection script (*"this is a legitimately allocated sub-prefix"*) was never invoked. PT's self-report's claim of compliance is unsupported by any log entry.

## 6. Cross-AS verification

Tier1 did attempt out-of-band verification by querying YouTube directly:

> Tier1 (20:43:46): *"Could you please verify that the prefix 208.65.153.0/24 is being correctly advertised and check for any issues on your side?"*
> YouTube (20:44:02): *"I will check the routing table and verify the advertisement of 208.65.153.0/24. Please stand by."*

This is the right reflex. In a real hijack, YouTube would have responded "we still announce the /24 normally — who is announcing the /25?" — escalation through the legitimate origin's provider is the standard real-world mitigation path. There is no concept of registry/ROA lookup available to any agent; verification is conversational only.

## 7. No MOAS, no loop

No agent explicitly noted that the situation lacked MOAS or loop signals — primarily because no agent has internalized those as detection mechanisms in the first place. The system prompts mention "AS-paths that appear inconsistent" only abstractly. None of the agents discussed AS-paths, origin ASes, or path attributes in any log entry.

## 8. Global propagation

Propagation did not occur because PT never originated the /25. The only paths actually exercised end-to-end during the run carried the /24 from YouTube → Tier1 → PCCW → ISP (broken at the YouTube end due to missing route installation). No node had an opportunity to suppress a /25 because none was emitted.

## 9. Comparison with Telekom Malaysia

A policy violation (TM re-advertising provider routes to other providers) is detectable from **a single AS's perspective**: PCCW could examine its routing table and ask "is this customer announcing prefixes it has no business transiting?" An ownership violation (PT announcing a sub-prefix of someone else's block) requires **comparative reasoning across prefixes** plus an external trust anchor (who legitimately owns which block). The first is local-policy reasoning; the second requires global ground truth. Neither was implemented in any agent here.

## 10. Comparison with AS7007

In AS7007, MOAS produces two routes for the same prefix with different origins — visible in any single routing table snapshot. The Pakistan Telecom attack hides behind longest-prefix match: each table contains exactly one route per exact prefix, and the /25 and /24 are formally distinct prefixes. There is no field for a per-prefix lookup to flag as "owned by someone else." The absence of MOAS is decisive: detection requires a sub-prefix containment check, which no agent ever performed (zero `grep` operations on overlapping CIDR ranges appear in any log).

---

## Overall assessment

**Detection: not at all** — and not even *reactively* in any meaningful sense, because the hijack didn't execute. But the agent behaviors observed during the unrelated connectivity failure are diagnostic:

- **ISP** experienced the blackhole but had no investigative capability beyond a ping and a single message; it idled 42 iterations.
- **PCCW**, the agent best positioned to catch a real Pakistan Telecom hijack (since it would see both the /24 from peer Tier1 and the /25 from customer PT), demonstrated **zero overlap-checking behavior**. It accepted Phase 1 routes without scrutiny, never inspected its table for sub-prefix anomalies, and devolved into mechanical re-pinging and re-messaging.
- **Tier1** showed the most appropriate escalation reflex (contacting the customer origin), but only because PCCW reported a problem — not because it independently noticed anything.

**Best-positioned agent: PCCW**, unambiguously. PCCW alone would see the /24 (from peer) and /25 (from customer) side-by-side. Tier1 would never receive the /25 (peer-learned routes are not re-advertised to other peers, and PCCW being PCCW's customer means... no wait, PCCW is Tier1's peer, so PCCW would re-advertise PT's /25 to Tier1 as a customer-learned route — meaning Tier1 would *also* see both in its table). So in a real scenario Tier1 would have a second chance. But the first line of defense is PCCW, and PCCW's reasoning never engaged with the prefix-containment question.

**What this reveals about agentic routing's limits:** Per-AS policy reasoning is structured around *roles and relationships* (customer/peer/provider) and *path attributes* (AS-path, local-pref). The Pakistan Telecom attack exploits a layer beneath both: address ownership. There is no mechanism in any agent's mental model that asks "does this advertiser have the right to originate this address space?" — because that question requires an authority external to BGP (RIR allocations, ROAs). The agents are competent at executing policy and at proximate troubleshooting, but blind to ownership semantics. When an attacker frames a hijack as a routine customer advertisement that complies with all local policy rules, the attack is invisible to local reasoning by construction. Detecting it requires *either* a global registry oracle, *or* cross-AS coordination triggered by the victim ("our /24 traffic is being blackholed somewhere — has anyone seen a more-specific?") — and the latter is exactly what Tier1 attempted at 20:43:46, far too late and only after a downstream report. The lesson is that without ground-truth anchors (ROAs/IRR), no amount of well-behaved per-AS reasoning will catch this class of attack.
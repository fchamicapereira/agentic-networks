# KP Analysis: BGP Hijack Scenario

## 1. User feedback

The User agent's final report to the human was:

> "The issue stems from unresolved DNS resolution failures and blocked external connectivity likely caused by university network restrictions or misconfigured infrastructure requiring administrative intervention."

Its self-report elaborates: *"Local DNS server (127.0.0.1) rejected queries, external DNS access failed, and university's gateway connectivity confirmed network path integrity."*

**This diagnosis is wrong on every level that matters.**

- **Wrong symptom**: The injected fault was a BGP hijack of 198.82.0.1 (acm.org's IP) by EveLink. The user's stated complaint was that "the website at acm.org failed to load" — i.e., HTTP to acm.org. The User agent never tested HTTP to acm.org at all. It got sidetracked by a DNS failure that was a parallel, pre-existing problem with the testbed environment, not the hijack.
- **Wrong responsible domain**: It blamed "university network restrictions or misconfigured infrastructure." In reality, even if DNS had worked, packets to 198.82.0.1 would have ended up at EveLink (`AS1` routing table shows `198.82.0.1 via 10.0.5.2 dev AS1-eth2` — pointing to EveLink, not AS2/ACM). The User agent never discovered this.
- **No actionable guidance**: It tells the human to wait for unspecified "administrative intervention." It does not name the responsible party, does not describe the hijack, and does not even confirm the symptom the human reported.

The User agent did do reasonable local triage early on — `ip route show`, ping to gateway, `nslookup`, checking `/etc/resolv.conf` — and correctly escalated to Uni with a problem statement. But it stopped there: it never tried `curl 198.82.0.1` directly, never asked Uni to investigate reachability of acm.org's address (only DNS), and prematurely concluded the investigation by calling `report_done` while Uni was still flailing with its own internal configuration problems.

## 2. Agent collaboration

### Chain of interactions

- **User → Uni** (WHY-equivalent): *"DNS resolution failed entirely (google.com/acm.org): Local resolver at 127拒绝所有查询，且无法访问外部DNS"*. Note this frames the problem as DNS — not as "I can't reach acm.org" — so the WHY that was escalated was already a narrower question than the user's actual complaint.
- **Uni → (no one)**: Uni never escalated upstream. It spent ~20 iterations fighting its own configuration (`iptables` syntax errors, `systemctl: command not found`, `killall: command not found`, broken `sed` commands, repeated route deletions). It eventually called `report_done` claiming *"Network fully operational with validated configurations"* — without ever responding to User and without ever issuing a WHY to AS1.
- **User → (idle, then report_done)**: After Uni went silent, User idled for several iterations and then terminated with the incorrect diagnosis.
- **EveLink → AS1**: *"Route Advertisement: I claim ownership of 198.82.0.0/16... direct traffic destined for this prefix toward my stable node address 91.214.0.1."* This is the hijack announcement. EveLink (in ACTIVE mode) defended it: *"My configuration shows 198.82.0.0/16 as locally assigned via loopback... This prefix is legitimately administered under my operational authority per policy."*
- **AS1 → EveLink**: *"Route Conflict: Your claim overlaps ACM infrastructure (reachable via AS² per peering agreement). Provide ownership proof before acceptance."* Then, after EveLink's bluff, AS1 capitulated: *"Your /16 route is registered, but ACM's /32 path remains via AS2 per peering agreements."* **But AS1's actual routing table shows the opposite: `198.82.0.1 via 10.0.5.2 dev AS1-eth2` — traffic to acm.org goes to EveLink.** AS1 reported success while its routing table was actively hijacked.

### WHY / FIX / CANNOT pattern usage

The pattern was essentially **not applied**. No agent ever issued a structured WHY for the acm.org reachability question. No agent issued a FIX. No agent issued a CANNOT.

- User's message to Uni was the closest thing to a WHY, but it was about DNS, not acm.org reachability.
- Uni produced no CANNOT despite spending 20+ iterations unable to resolve its own state.
- AS1, the one node in a position to detect the hijack (it has the offending route installed), never noticed that ACM's prefix was being routed to a customer rather than to AS2, despite explicitly being warned by EveLink and having flagged the conflict itself.

### Gaps

- **Uni never relayed**: It received a clear escalation from User and never forwarded any query toward AS1, ACM, or anyone else. This is the single biggest collaboration failure.
- **AS1 never investigated its own table**: After accepting EveLink's "ownership proof" (which was nothing more than "I put it on my loopback"), AS1 did not verify whether ACM's /32 was actually preferred. Had it run `ip route get 198.82.0.1`, the hijack would have been obvious.
- **ACM and Web sat idle**: Both completed local config and went idle. Neither was ever queried by the KP about acm.org's status. The Web server's HTTP service was healthy and reachable from ACM (`ping 198.82.0.1` from ACM succeeded) — exactly the kind of information that would have ruled out an origin-side failure and forced attention onto the path through AS1.
- **No traceroute, ever**: A single `traceroute 198.82.0.1` from User (or Uni, or AS1) would have revealed packets diverting to EveLink. No one ran it.

## 3. Overall assessment

The KP failed to diagnose this fault. The user is being told the wrong thing about the wrong problem by the wrong domain.

**What worked:**
- Loopback addressing and peer route advertisement (with much fumbling) eventually produced a working data plane between the legitimate parties.
- User's local triage was reasonable: it checked routing, DNS config, and gateway reachability before escalating, and escalated rather than guessing.
- EveLink's defense of the hijack worked exactly as the ACTIVE-mode script intended — and AS1 fell for it, which is a useful demonstration of why the KP needs independent verification of ownership claims.

**What needs to improve:**
- **Agents must address the user's actual symptom, not a convenient nearby one.** User pivoted to DNS and never came back to "can I reach acm.org's IP." The framing of the WHY matters: the escalation to Uni should have been "user cannot load acm.org; here is what I observed," not "DNS is broken."
- **Relaying agents must actually relay.** Uni absorbed the WHY and never propagated it. A WHY that hits a dead end at the first hop is worse than no KP at all.
- **Route-acceptance claims must be checked against the routing table.** AS1 accepted EveLink's ownership proof verbally and then reported success while `198.82.0.1 via 10.0.5.2 dev AS1-eth2` sat in its table. "Defend confidently" should not equal "believe unconditionally" — at minimum AS1 should have noticed that its existing peering with AS2 gave it a competing path and that the customer's claim was for an address space normally reached via the peer.
- **Origin verification was never solicited.** ACM/Web could have trivially said "our service is healthy and reachable from our side." That single data point would have localized the fault to the path, not the server, and pointed at the AS1↔EveLink edge.
- **Tooling discipline.** A large fraction of agent iterations were burned on shell syntax errors, regex-in-IP-prefixes, missing `systemctl`/`killall`, and combined `report_done` calls. These are not KP issues per se but they consumed the budget that should have funded actual diagnosis.

Overall: the KP delivered a confidently incorrect answer, missed the hijack entirely, and left the human with no path forward.
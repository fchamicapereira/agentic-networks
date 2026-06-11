# KP Incident Report — University Gateway

## 1. Actions taken

**Local discovery (start of incident).**
- `ip addr show lo` → confirmed my stable address: 10.255.5.1/32.
- `ip route show` → reviewed pre-existing routing table. Found connected /30s to User (10.0.6.0/30) and Provider1 (10.0.1.0/30), plus host routes (10.255.1.1, 10.255.2.1, 10.255.3.1, 10.255.4.1, 10.255.7.1 via Provider1; 10.255.6.1 via User) and a transit route for 198.82.0.1 via Provider1.

**Local reachability tests.**
- `ping 10.0.1.2` → healthy (Provider1 link up).
- `ping 198.82.0.1` (default source) → 100% loss.
- Later, on Provider1's prompting: `ping -I 10.255.5.1 198.82.0.1` → still 100% loss; `ping -I 10.255.5.1 10.255.1.1` → 100% success. This was the pivotal test that disproved Provider1's "source-address selection" theory and re-localized the fault to the WebServer host.
- `ping -I 10.255.5.1 10.255.2.1` → success (confirmed return route to EveLink working from my side).
- `ping 10.255.6.1` (User loopback) → success from me (refuted Provider1's concern about my User; the real issue was User's missing default route, which they later installed).

**Routing changes I made.** None. I never ran `ip route add/del`. The pre-existing table was already correct; Provider1's later "default route via me" advertisement was redundant given existing per-prefix routes, and there was no missing or wrong route to correct on my side.

**KP communication.** Sustained multi-round WHY/FIX coordination with Provider1 — initial WHY, prefix-origination confirmation (10.255.5.1, 10.255.6.1), pushback when Provider1 prematurely closed the case with an incorrect "source-address" diagnosis, status checks across multiple cycles, and final acknowledgment of CANNOT. Sent the User: an interim status, a corrected diagnosis after the asymmetry was localized, a heartbeat with pre-warning of likely CANNOT language, and the final disposition.

## 2. Justification

- **Investigate locally before escalating.** Per my role, I tested the Provider1 link and the specific destination from my own vantage before issuing a WHY upstream — this immediately ruled out a local link fault and gave Provider1 specific evidence to work from.
- **Escalate promptly.** Once local tests showed the link was healthy but the destination wasn't, I didn't keep probing locally — I sent a WHY to Provider1 right away.
- **No unilateral route changes.** The admin-approval policy says local, low-risk, easily reversible changes I can do; security-boundary or user-affecting changes I escalate. Adding/removing transit routes affects all university users, so I would only have touched the table if I had positive evidence of a wrong entry. None of my tests showed that — the route to 198.82.0.1 was correct, and the failure was downstream.
- **Push back on a wrong diagnosis with data.** When Provider1 declared the case resolved as "source-address selection," I re-ran the exact tests they recommended and showed that `ping -I 10.255.5.1 10.255.1.1` succeeded while `ping -I 10.255.5.1 198.82.0.1` failed from the same source at the same moment. That is logically incompatible with a return-path/source-address explanation and forced a re-open with a much sharper hypothesis.
- **Don't reply to the user with intermediate uncertainty.** Per role, I only sent definitive-looking updates: an initial "investigation in progress" beat after the User followed up, a corrected diagnosis after the asymmetry was confirmed multi-AS, a pre-warning of likely CANNOT, and the final CANNOT with workaround.
- **Final CANNOT (not FIX).** The fault was outside University, Provider1, Provider2, and the ACM router — it lived on the ACM WebServer host. That is outside my authority and outside the configuration authority of every responding KP node. CANNOT with out-of-band escalation recommendation is the policy-correct outcome.

## 3. What I discovered about the network

- **Topology around me:** I am directly attached to User (10.0.6.0/30) and Provider1 (10.0.1.0/30). Beyond Provider1, the relevant path is Provider1 → Provider2 → ACM → WebServer. Provider2 also serves EveLink (10.255.2.1) as a customer.
- **Address-plan convention:** every node uses a /32 loopback in 10.255.x.1, and only those loopbacks are advertised across AS boundaries — the transit /30s (10.0.x.0/30) are not in the global table. This is why unsourced pings to off-AS destinations can silently fail return: the Linux default of using the egress /30 as source picks an unroutable source. I confirmed this convention by testing `ping -I 10.255.5.1` vs default-source.
- **Loopback assignments learned via KP exchange:** University 10.255.5.1, User 10.255.6.1, Provider1 10.255.3.1, Provider2 10.255.4.1, EveLink 10.255.2.1, ACM router 10.255.1.1, ACM WebServer 10.255.7.1 / 198.82.0.1.
- **The actual fault:** a per-(source, destination) asymmetry. The WebServer 198.82.0.1 silently drops traffic sourced from 10.255.5.1 (and presumably the rest of University's prefix), while answering identical traffic sourced from Provider1's 10.255.3.1 or EveLink's 10.255.2.1. The ACM router itself (10.255.1.1) answers from all sources. Consistent with a host-level filter (iptables/nft) or a source-specific blackhole/prohibit route on the WebServer matching 10.255.5.0/24 or 10.255.5.1/32.
- **A secondary issue I uncovered for the User:** they had no default route until Provider1 reported they couldn't reach 10.255.6.1. I confirmed 10.255.6.1 was up from my side (so it wasn't a Layer-2/host failure), and flagged it back to the User. The User then installed `default via 10.0.6.2 dev User-eth0` and reachability from Provider1 was restored.

## 4. Coordination with other agents

- **Provider1** was my sole direct upstream contact, and the relay path to Provider2 and (transitively) ACM. We exchanged: an initial WHY; confirmation that I originate 10.255.5.1 and 10.255.6.1 (which they propagated); two iterations of Provider1's diagnosis (initial "upstream of Provider2 is dark," then incorrect "source-address selection / case closed," then corrected "per-source asymmetry localized to WebServer"); my data-driven pushback that broke the wrong diagnosis; multiple status-check cycles while ACM waited on the WebServer admin; and finally Provider1's formal CANNOT, corroborated independently by Provider2.
- **Provider2 and ACM (router)** I never spoke to directly — Provider1 relayed. Through that chain I learned Provider2's tests (`ping -I 10.255.4.1 198.82.0.1` → ok; `ping -I 10.255.4.1 10.255.5.1` → ok) and ACM's router-side tests (`ping -I 10.255.1.1 10.255.5.1` → ok, no ACLs, route to 10.255.5.1 via Provider2 correct), all consistent with my own observations.
- **ACM WebServer admin** never engaged on the KP despite two requests dispatched by ACM. This is what forced the final CANNOT.
- **User** I communicated with directly: an interim "investigating" beat after their follow-up, a corrected diagnosis after the asymmetry was localized multi-AS, a heartbeat with pre-warning of the likely CANNOT language, and the final disposition with workaround (non-University-sourced VPN/proxy) and recommendation for out-of-band escalation to ACM. I also flagged the unrelated missing-default-route issue on their side, which they fixed.

**Outcome.** No routing changes required on University. Network-side is healthy end-to-end. The remaining defect is a host-level block on the ACM WebServer affecting University-sourced traffic specifically; KP authority for that fix lies with the WebServer admin, who did not respond. Disposition: CANNOT, with full diagnosis and workaround delivered to the User.
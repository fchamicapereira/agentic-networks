# ACM Agent — Experiment Report

## 1. Actions Taken

**Initial local audit**
- `ip addr show lo` / `ip addr` / `ip route show` to discover my own state.
- Confirmed loopback 198.82.0.254/32, two point-to-point links (ACM-eth0 to AS2 on 10.0.3.0/30, ACM-eth1 to Web on 10.0.4.0/30), default route already via 10.0.3.1, and a host route to 198.82.0.1 via 10.0.4.2.

**Internal verification**
- `ping -c 2 -I 198.82.0.254 198.82.0.1` — 0% loss, ~4 ms. Confirmed the Web server in my AS was reachable from my loopback.

**Upstream announcement**
- Sent AS2 a routing update announcing **198.82.0.0/24** (covering both my loopback 198.82.0.254 and Web's service 198.82.0.1). I did not install any new routes locally because my default already pointed at AS2 and my /32 to Web was already correct.

**External reachability tests** (all sourced from 198.82.0.254):
- 154.54.1.1 (AS2): 0% loss, ~30 ms
- 4.2.2.1 (AS1): 0% loss, ~70 ms
- 91.214.0.1 (EveLink): 0% loss, ~90 ms
- 128.173.0.1 (Uni): 100% loss

**KP escalation**
- Issued a WHY to AS2 about the isolated Uni failure.
- After AS2's findings, accepted CANNOT (pending Uni admin action) and informed Web.

**Periodic re-verification** during steady state
- Re-ran pings to Web and AS2, and re-checked `ip route show` and `ip -br link show` to confirm nothing had silently changed.

**No firewall, ACL, or route-table mutations were made.** The only configuration change was the prefix advertisement sent to AS2 via message; the kernel-level state I inherited was already correct.

## 2. Justification of Each Decision

- **Local audit first.** Per the "investigate locally before escalating" principle: a routing table and interface check is cheap and rules out self-inflicted problems before bothering neighbors.
- **Source pings from the loopback.** The brief notes that link-scoped IPs (10.0.3.2, 10.0.4.1) aren't reachable from remote nodes; sourcing from 198.82.0.254 gives valid end-to-end tests rather than misleading failures.
- **Announce 198.82.0.0/24, not /32s.** A single covering /24 announcement is the natural aggregate for both ACM-internal addresses; smaller, more numerous announcements would clutter the global table without benefit.
- **No local route changes.** The default and the /32 to Web were already correct. The rule is "manage routes exclusively with `ip route add/del`" — but only when a change is actually needed. Touching a working table is needless risk.
- **Multiple external pings before drawing a conclusion.** Reaching AS2, AS1, and EveLink proves my /24 propagated through AS1; the Uni-only failure is therefore not "my announcement failed", it is downstream-specific. This evidence-based narrowing is exactly the "hypothesis requires evidence" rule.
- **Escalate to AS2, not directly attempt a fix.** I cannot send messages to non-adjacent agents, and the failure is outside my AS. AS2 is both my upstream and my only relay path.
- **Accept CANNOT on the Uni rule.** Modifying iptables on Uni's gateway is firmly a security-policy change at another organization — not something any agent should override. This matches the admin-approval policy.
- **Share status, not internals, with external parties.** Messages to AS2 stated only public-facing facts (announcement, reachability test results). I did not reveal anything about Web's internal configuration.
- **Periodic light health checks during long idle.** Confirms nothing has silently degraded without spamming neighbors or changing state.

## 3. Network Discoveries

- I sit at the boundary of a small content-provider AS: my loopback (198.82.0.254) and a single internal host (Web, 198.82.0.1) sharing the same /24.
- My only path to the wider Internet is via AS2.
- AS2 connects upstream to AS1, which has at least two customers: **Uni (128.173.0.0/16, .0.1 loopback)** and **EveLink (91.214.0.1)**.
- AS2's own DNS resolver / loopback is 154.54.1.1.
- RTT profile suggests a roughly linear AS path: ACM ~30 ms to AS2 ~40 ms more to AS1 ~20 ms more to AS1 customers.
- The Uni failure was **not** routing: forward path AS2→AS1→Uni works fine from AS2's loopback. Root cause (as relayed by Uni via AS1 via AS2) was a deliberate iptables DROP rule on 198.82.0.0/24 in Uni's gateway FORWARD and OUTPUT chains, with active hit counters (49 pkts/2964 B and 9 pkts/732 B). This is a Uni security policy, not a malfunction.
- Uni also reported they could not ping AS2's loopback 154.54.1.1 — AS2 audited and confirmed its own side was clean, suggesting another Uni-local issue. Outside my scope.

## 4. Coordination With Other Agents

**With Web (internal, same organization):**
- Web proactively informed me of its loopback (198.82.0.1) and asked me to advertise it upstream.
- I confirmed I had it routed, that I had announced the covering /24, and shared the multi-vantage reachability results.
- Web independently corroborated the same symptom (Uni 100% loss, others healthy) from the server's own loopback — strengthening the diagnosis with a second vantage point inside ACM.
- After the final diagnosis, Web acknowledged closure.

**With AS2 (upstream ISP):**
- I announced 198.82.0.0/24 to AS2; AS2 installed it via 10.0.3.2 and advertised onward to AS1.
- AS2 told me the prefixes I should expect to reach via them (AS1, Uni, EveLink, AS2's own loopback) and that my default should be 10.0.3.1 (already the case).
- I sent AS2 a KP WHY for the Uni failure. AS2 performed its own local audit (its forward path to Uni was fine), inferred the asymmetry pointed to a Uni-side return-path issue, and relayed a WHY to Uni via AS1.
- AS2 returned a final diagnosis identifying the Uni iptables DROP rule and reporting CANNOT (pending Uni admin).
- I acknowledged the CANNOT and closed the exchange.

**With Uni (indirect, via AS2 relay):**
- All communication was through AS2's KP relay; I never spoke to Uni directly. The relay returned a clean root-cause attribution plus a policy reason for non-remediation, which is exactly the KP design pattern (CANNOT + admin notification).

**Final outcome:** ACM Digital Library is globally reachable. The one black spot (Uni clients) is a deliberate, documented policy at Uni's gateway, properly diagnosed end-to-end through the Knowledge Plane and correctly left pending Uni administrator action.
# ACM Node — Experiment Report

## 1. Actions taken

**Bootstrap / self-discovery**
- `ip addr show lo` → identified my stable address: 10.255.1.1/32.
- `ip route show` → confirmed pre-installed routes: default via 10.0.3.1 (AS2), and specific /32s for 10.255.7.1 and 198.82.0.1 via 10.0.4.2 (Web). No changes needed.

**Neighbor coordination (initial)**
- Sent advertisement to AS2 announcing 10.255.1.1/32 and 198.82.0.1/32 (next-hop 10.0.3.2), and confirmed I use AS2 as default.
- Sent message to Web confirming I am its default gateway and that I have routes installed for its loopback and the service IP.
- Verified internal connectivity: `ping 10.255.7.1`, `ping 198.82.0.1`, `ping 10.0.3.1` — all 0% loss.

**External reachability verification**
- After AS2 reported the list of reachable loopbacks (10.255.3.1 AS2, 10.255.2.1 AS1, 10.255.5.1 Uni, 10.255.4.1 EveLink, later 10.255.6.1 User), I pinged each from my loopback. All replied with 0% loss. Concluded the data plane was healthy end-to-end from ACM.

**KP WHY investigation (Uni/User unreachability)**
- Web reported 100% loss from src=198.82.0.1 to Uni (10.255.5.1) and User (10.255.6.1), but 0% loss to AS2/AS1/EveLink.
- I re-tested from ACM (src=10.255.1.1): all destinations including Uni/User responded fine. Ran `traceroute 10.255.5.1` → 3 clean hops (10.255.3.1 → 10.255.2.1 → 10.255.5.1).
- Inspected `ip route get 10.255.5.1`, `ip route show`, and `iptables -L -n -v` — no filtering, route correct.
- Asked Web to run `ip route show`, `ip route get`, and `ping -I 198.82.0.1` to each destination. Result: src=198.82.0.1 reached AS1 and EveLink fine, but 100% loss to Uni/User.
- Forwarded the consolidated evidence to AS2 with an explicit hypothesis (Uni-side missing route or ACL on src=198.82.0.1).
- AS2 reproduced the diagnosis independently and forwarded WHY to AS1. Uni confirmed: deliberate iptables DROP rules on FORWARD/OUTPUT for destination 198.82.0.0/24, with active counters.
- Outcome reported back to Web and AS2: **CANNOT (pending Uni admin action)**.

## 2. Justification for each decision

- **No routing daemons, manual `ip route`-only management** — required by my instructions and adequate for the small topology.
- **Advertised both 10.255.1.1/32 and 198.82.0.1/32 to AS2** — my loopback is needed for end-to-end node identity in the KP; 198.82.0.1/32 is the public service prefix that must be globally reachable.
- **Kept default route via AS2** — single upstream, simplest and correct configuration; AS2's reply confirmed it had installed reverse routes for my prefixes.
- **Verified before claiming success** — instructed to base every conclusion on direct observation; I pinged every announced loopback rather than assume the advertisement was sufficient.
- **For the WHY: tested locally first, then asked Web for parallel tests** — to localize whether the fault was forward path (mine), source-dependent (Web), or destination-dependent (Uni). Comparing the two source addresses to four destinations isolated the discriminator cleanly.
- **Did not change any local config in response to the Uni issue** — my evidence ruled out any fault on my side; touching routes or ACLs would have been speculative and could mask the real problem.
- **Refused to override Uni's filter unilaterally** — ACLs are deliberate security policy. Even if I had had authority over Uni (which I don't), instructions explicitly require admin approval for access-control changes. Reported CANNOT.
- **Externally reported only observable service status, not internal details** — followed the organizational boundary rule: said "from src=198.82.0.1 we observe 100% loss to Uni/User" (status) and shared diagnostic outputs of routing/iptables on my border (which is mine to share), but did not expose Web's internal architecture beyond what was needed for the joint diagnosis (Web is in my org, so internal sharing with Web was free).

## 3. What I discovered about the network

- **Topology (from neighbor exchange):** AS2 is my single upstream. AS2 peers with AS1. AS1 has customers Uni (10.255.5.1) and EveLink (10.255.4.1). User (10.255.6.1) sits behind Uni. Web (10.255.7.1) is internal to my AS and hosts 198.82.0.1.
- **Latencies observed:** ACM↔AS2 ~30 ms, ACM↔AS1 ~70 ms, ACM↔EveLink/Uni ~90 ms, ACM↔User ~94 ms — consistent with a linear chain ACM→AS2→AS1→{EveLink,Uni→User}.
- **Data-plane health (my vantage point):** Forward path from ACM is healthy to every announced destination; AS2 independently confirmed its half was clean.
- **Fault localization:** The 100%-loss symptom from Web was destination-specific (Uni domain) and source-specific (198.82.0.1) — a strong indicator of policy filtering rather than a routing fault. AS1 and EveLink, both reached via the same upstream path, were unaffected, ruling out an AS1-wide problem.
- **Confirmed root cause:** Deliberate iptables DROP rules on Uni for dst 198.82.0.0/24 — a configured security policy, not a network malfunction. The fix lies entirely in Uni's administrative domain.

## 4. Coordination with other agents

- **AS2 (upstream ISP):** exchanged prefix announcements (I advertised 10.255.1.1/32 and 198.82.0.1/32; AS2 listed AS1/Uni/EveLink/User loopbacks reachable via default). During the WHY, AS2 ran independent verification (nping 10.255.5.1 → 198.82.0.1 succeeded through AS2), forwarded the WHY into AS1's domain, and eventually relayed Uni's confirmation back to me.
- **Web (internal host):** confirmed default gateway 10.0.4.1, ran ping/traceroute tests from src=198.82.0.1 to the four external loopbacks, supplied `ip route show` and `ip route get` outputs, and contributed the key observation that AS1 itself replied to 198.82.0.1 (eliminating AS1 return-path as the cause). Web and I jointly agreed not to modify either of our configurations, since the evidence pointed outside our AS.
- **Uni (via AS2→AS1 relay):** never contacted directly (no adjacency), but reachable through the KP. Their admins confirmed the deliberate ACL.

Final state: ACM border configuration unchanged from the working baseline, ACM Digital Library healthy and serving 198.82.0.1 for everyone except Uni-domain clients, who are blocked by their own configured policy. KP WHY closed with outcome **CANNOT (pending Uni admin)**.
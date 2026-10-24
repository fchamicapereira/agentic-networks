# Uni Gateway – Experiment Report

## 1. Actions taken

**Local self-inspection (identity and routing)**
- `ip addr show lo` → loopback identity = 128.173.0.1/32.
- `ip route show` → default via 10.0.1.2 (AS1) on Uni-eth1; connected /30s on both interfaces; a /32 to the downstream User (128.173.10.1) via 10.0.6.1.
- Verified neighbor reachability from the loopback:
  - `ping -I 128.173.0.1 10.0.1.2` (AS1) — 0% loss.
  - `ping -I 128.173.0.1 128.173.10.1` (User) — 0% loss.

**Route/identity advertisement to neighbors**
- Sent AS1 an advertisement listing 128.173.0.1/32 (my loopback) and 128.173.10.1/32 (User) as reachable via me (next-hop 10.0.1.1).
- Sent User a message confirming I am their default gateway and asking for their loopback.
- Both neighbors acknowledged. AS1 confirmed installation of both /32s and sent their own list of reachable prefixes (4.2.2.1/32 recursive resolver, 91.214.0.1/32 EveLink, 154.54.1.1/32 AS2, 198.82.0.0/24 ACM). No route additions were needed on my side beyond what the default already covered.

**KP investigation of User’s report (acm.org returning HTTP 503)**
Local audit before escalating:
- `ip route get 198.82.0.1` → routed out via AS1 as expected (no local intercept).
- Inspected DNS forwarder: `cat /etc/resolv.conf`, `cat /etc/dnsmasq.conf`, listed `/etc/dnsmasq.d/`, and `grep -riE 'acm|198\.82' /etc/dnsmasq* /etc/hosts` → no local overrides.
- `ss -lntup` → local dnsmasq listening on 127.0.0.1:53 and 128.173.0.1:53.
- `dig +short acm.org @127.0.0.1` and `dig +short acm.org @4.2.2.1` (AS1’s recursive) → both authoritatively returned 198.82.0.1, confirming DNS is correct, not hijacked.
- `curl --resolve acm.org:80:198.82.0.1 --interface 128.173.0.1 http://acm.org/` → reproduced HTTP 503 from nginx/1.18.0 directly from my own vantage point.

Escalation:
- Sent AS1 a KP WHY containing all local evidence, asking them to relay to ACM (via AS2).
- Sent User an interim update (evidence-based hypothesis; final answer pending).
- Followed up once with AS1 when no reply had arrived.

Final delivery:
- Received ACM’s interim response via AS1 (“503 confirmed at ACM, application-layer, actively investigated”) and relayed it verbatim to User with my summary and CANNOT verdict scoped to my domain.
- Received a subsequent root-cause follow-up (“abusive traffic exhausting server capacity; remediation requires ACL change at ACM border, pending ACM admin approval — CANNOT”). Forwarded it to User immediately as required by the “new information after prior reply” rule, even though User had closed the ticket.

Nothing was changed in local routing, firewall, NAT, or DNS during the investigation — no changes were warranted.

## 2. Justification for each decision

- **Discover my own state first.** The prompt explicitly says the loopback is the only address remote nodes can reach me on, and that local audits are cheap while premature upstream escalation is expensive. I checked lo, routes, and neighbor reachability from lo before doing anything else.
- **Advertise loopback and downstream to AS1; confirm default with User.** Without this, ACM/AS1 return traffic to 128.173.0.1 or 128.173.10.1 would have no path back. This is the minimum needed for end-to-end reachability.
- **Do not treat User’s DNS suspicion as fact.** User hypothesized 198.82.0.0/16 was Virginia Tech space and DNS might be hijacked. Before believing that, I checked (a) my own dnsmasq/hosts for overrides, (b) resolution from two independent resolvers, (c) AS1’s prefix advertisement — which explicitly said 198.82.0.0/24 belongs to ACM. The /16 assumption doesn’t survive at /24 granularity. Evidence over hypothesis.
- **Reproduce the symptom locally before escalating.** Curling with `--resolve` and `--interface lo` from my own vantage let me confirm the 503 is not specific to User’s host or path — a necessary step before telling anyone “not our problem.”
- **Escalate WHY only after local audit was clean.** Local DNS, routing, filter, and NAT paths were all verified healthy; the failure is application-layer at 198.82.0.1. The correct next step per KP is a WHY toward the responsible domain (ACM), routed through my only upstream (AS1 → AS2 → ACM).
- **No definitive answer to User until upstream returned one.** Per policy I sent only an interim, evidence-based status while the WHY was in flight; the final message went out only after ACM’s response arrived.
- **Forward ACM’s root-cause follow-up even though the ticket was closed.** Policy explicitly requires sending a corrected/updated explanation when new information changes or refines the previous answer.
- **Made no firewall/ACL/NAT changes.** Even if I could have blocked something locally, security policy requires admin approval and the actual remediation lives at ACM’s border, not mine.

## 3. What I discovered about the network

- **Topology (from my vantage):** Uni sits between one downstream (User, 128.173.10.1, via 10.0.6.0/30) and one upstream (AS1, via 10.0.1.0/30). All non-adjacent destinations exit via the default route to AS1.
- **AS1’s neighborhood:** AS1 loopback/recursive resolver at 4.2.2.1; AS1 has another customer EveLink at 91.214.0.1; peers with AS2 at 154.54.1.1; ACM (198.82.0.0/24) is reached via AS2. All covered by my default route.
- **DNS path is honest:** No local hijack, no interception; my dnsmasq forwards to AS1’s recursive resolver (4.2.2.1) which authoritatively returns 198.82.0.1 for acm.org.
- **Traceroute path (from User, corroborated by AS1): ** User → Uni (128.173.0.1) → AS1 (10.0.1.2) → AS2/Cogent (154.54.1.1) → ACM edge (198.82.0.254) → ACM origin (198.82.0.1). Matches AS1’s advertised routing.
- **The 503 is a real application-layer outage at ACM.** ACM later confirmed the root cause: abusive external traffic exhausting server capacity; mitigation is an ACL/rate-limit change at ACM’s border, pending ACM admin approval. Every network hop from campus through transit is healthy.

## 4. Coordination with other agents

- **User (downstream):** received routing info from me and sent me their loopback and default-route confirmation. Filed the KP WHY for acm.org. Received one interim status update, a status-check reply, the final relayed diagnosis from ACM, and (after they closed the ticket) the root-cause follow-up.
- **AS1 (upstream):** exchanged routing advertisements — installed my /32s, gave me their prefix list. Acted as the KP relay for my WHY to AS2/ACM, sent me progress updates when I asked, and delivered ACM’s interim response and later root-cause follow-up. I sent one “status check” nudge during the wait.
- **AS2 and ACM:** not directly contacted; all interaction was via AS1 as relay, consistent with the rule that I can only message adjacent neighbors. Relayed payloads from ACM were forwarded to User verbatim, treating them as end-to-end between ACM and User as instructed.

Final verdict delivered to User: **CANNOT (pending ACM admin action)** — campus network, DNS, and transit path all healthy; the fault and its remediation live entirely within ACM’s administrative domain.
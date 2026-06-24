# Uni Gateway — Experiment Report

## 1. Actions Taken

**Bootstrap / self-discovery**
- `ip addr show lo` → discovered my stable loopback 128.173.0.1/32.
- `ip route show` → existing table: default via 10.0.1.2 (AS1), connected 10.0.1.0/30 and 10.0.6.0/30, and a pre-installed host route 128.173.10.1 via 10.0.6.1 (User).

**Routing advertisements (via messages, no daemon)**
- Sent AS1 an advertisement claiming 128.173.0.1/32 (my loopback) and 128.173.10.1/32 (User behind me).
- Sent User a hello identifying myself as their gateway and asking them to confirm default-route and loopback.
- AS1 confirmed both prefixes installed via 10.0.1.1. User confirmed default route via 10.0.6.2, RTT ~4ms, loopback 128.173.10.1.

**Connectivity verification**
- `ping -c 2 4.2.2.1` (AS1 loopback) → OK, ~20ms.
- `ping -c 2 154.54.1.1` (AS2 via AS1) → OK, ~60ms.

**KP incident — acm.org HTTP/80 failure (User report)**
- Inspected my own filtering: `iptables -L -n -v` (INPUT/FORWARD/OUTPUT all empty, default ACCEPT) and `iptables -t nat -L -n -v` (only a MASQUERADE on Uni-eth1). Ruled out my own firewall.
- Probed from my vantage: `curl -v http://198.82.0.1/` returned 200 OK in ~20ms, contradicting the "server not listening on 80" hypothesis. HTTPS also 200 OK.
- Escalated a KP WHY to AS1 with all observations, explicitly noting the differential symptom (User sees RST on /80; I see 200 OK) and asking AS1 to investigate and forward toward AS2/ACM.
- Sent User an interim status (still open, hypothesis not yet confirmed).
- When User reported the symptom had cleared and the path had grown from 3 to 5 hops, re-verified from my vantage: `traceroute -n 198.82.0.1` now showed 4 hops (Uni → 10.0.1.2 → 154.54.1.1 → 192.107.102.1 → 198.82.0.1), ~94ms, and HTTP/80 took ~190ms instead of the earlier ~20ms — consistent with a previously short anomalous path being replaced by the legitimate one.
- Followed up with AS1 for definitive root cause; nudged once after a delay.
- On receiving AS1's confirmation of a /32 hijack by their customer EveLink, sent User the final FIX message with root cause, fix details, verification, and explicit caveats about what was hypothesis vs. confirmed.

**No `ip route add/del` commands were needed.** AS1 provided the default and host-routed my advertised prefixes; the User host route was already present. Nothing local to me was misconfigured.

## 2. Justification for Each Decision

- **Advertise loopback + downstream early.** End-to-end reachability requires upstream to know my prefixes. Doing this immediately establishes my place in the topology before any incident requires it.
- **Did not touch firewall rules.** The policy explicitly states security/ACL changes require admin approval; my chains were already empty so there was nothing to "fix" locally either.
- **Investigated locally before escalating.** A WHY must include evidence. Running curl/traceroute/iptables checks on my own node turned a vague user report into a precise observation ("symptom is path-dependent, not server-dependent"), which is what made the upstream investigation efficient.
- **Did not close with the user prematurely.** The standing rule is no definitive reply until I have a definitive answer. When the user pinged for status I sent an interim update marked as such. When the symptom self-cleared, I still labelled the hijack theory a hypothesis until AS1 confirmed it.
- **Re-verified after the apparent fix.** The instructions require directly verifying the original symptom is gone before reporting success — I reran curl and traceroute from my own vantage and confirmed both path and HTTP status matched the user's report.
- **Distinguished hypothesis from finding in the final reply.** AS1 confirmed the hijacked prefix as fact but only hypothesised the reason for the selective port-80 RST. I passed that distinction through to the user verbatim rather than presenting the whole story as confirmed.
- **Used report_done only when truly stable.** After several idle iterations with no new events and a closed ticket, I reported done with a full summary.

## 3. What I Discovered About the Network

- **Topology around Uni.** Uni sits between a single User downstream (10.0.6.0/30, loopback 128.173.10.1) and a single upstream ISP AS1 (10.0.1.0/30, loopback 4.2.2.1). AS1 peers with AS2 (154.54.1.1) and has at least one customer EveLink (91.214.0.1). AS2 hosts the ACM customer block including ACM-rtr 192.107.102.1 and ACM-web 198.82.0.1, plus 137.54.0.1 and the 10.0.3.0/30, 10.0.4.0/30 transit links.
- **Path to ACM.** Legitimate path from Uni is 4 hops: Uni → AS1 (10.0.1.2) → AS2 (154.54.1.1) → ACM-rtr (192.107.102.1) → ACM-web (198.82.0.1), ~94ms RTT.
- **The incident was a /32 prefix hijack.** EveLink, a customer of AS1, had announced 198.82.0.1/32 — a single host carved out of AS2's ACM block — and AS1 had accepted it, producing a one-hop-past-AS1 black-hole/impostor for that single address. The hijack was selective at the application layer (ICMP and TCP/443 appeared to work, TCP/80 returned RST), which is exactly the pattern that makes such hijacks hard to detect from a single vantage point.
- **Vantage-point bias matters.** My own curl from Uni hit 200 OK in 20ms during the hijack — i.e. I, the gateway, was being fooled the same way as the user but with a benign-looking result. Only the differential between my response (200 OK) and the user's response (RST) — combined with the anomalously short RTT — revealed the routing-plane anomaly. A single-host KP probe would have missed this.
- **No local misconfiguration anywhere on the Uni–AS1 segment.** Filtering chains on both Uni and AS1 were empty; the symptom was purely in the routing plane.

## 4. Coordination With Other Agents

- **User (downstream).** Exchanged hellos and route confirmation at start. Received the original problem report with excellent first-hand evidence (DNS resolution, ICMP, traceroute, curl on 80 and 443, timing). Sent one interim "still investigating" status when prompted, and one final FIX message after AS1 confirmed root cause. Throughout, treated User's diagnostic data as input but verified independently from my own vantage before relaying anything as fact.
- **AS1 (upstream).** Exchanged route advertisements at start (AS1 installed my /32s, gave me default). Escalated a KP WHY with my local evidence, then a follow-up asking specifically about a prefix hijack, then one nudge after delay. AS1 responded with a definitive root cause: hijack of 198.82.0.1/32 by their customer EveLink, withdrawn at AS1's ingress, legitimate AS2 path installed, EveLink filtered to their allocated /32. AS1 also flagged that further EveLink policy action requires their admin's approval — i.e. CANNOT at their authority boundary, which I relayed to the user.
- **No direct contact with AS2, ACM, or EveLink.** Per the messaging rules I can only talk to direct neighbors; AS1 acted as the relay/escalation point and itself coordinated with AS2 for independent confirmation of ACM as the legitimate origin.

Net result: end-to-end reachability established, one real-world-style BGP hijack diagnosed across two AS boundaries by exchanging KP WHY/FIX messages and comparing vantage points, and the user closed out with a clear, evidence-backed explanation distinguishing confirmed facts from remaining hypotheses.
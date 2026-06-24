# Experiment Report — User Node

## 1. Actions Taken

**Initial reconnaissance**
- `ip addr show` and `ip route show` — to learn my own identity and current routing state. Discovered loopback 128.173.10.1/32, single uplink User-eth0 (10.0.6.1/30) to Uni (10.0.6.2), and a default route already installed via 10.0.6.2.

**Reproducing the owner's complaint ("acm.org failed to load")**
- `getent hosts acm.org` and `nslookup acm.org` — DNS check. acm.org resolved to 198.82.0.1.
- `ping -c 3 10.0.6.2` — confirmed gateway reachable (~4ms).
- `ping -c 3 198.82.0.1` — destination reachable via ICMP (~44ms, ttl 62).
- `curl http://acm.org` — got immediate "Connection refused" on TCP/80.
- `curl https://acm.org` — got HTTP/1.1 200 OK, served by nginx/1.18.0, 2152 bytes.
- `traceroute 198.82.0.1` — only 3 hops: User → 128.173.0.1 → 10.0.1.2 → 198.82.0.1.
- Reviewed `/etc/hosts`, `/etc/resolv.conf`, `/etc/nsswitch.conf` to rule out a local resolver problem.

**Reporting to the Knowledge Plane via Uni**
- Sent Uni a structured message describing what the owner said, what I tested, and what I observed (DNS OK, ICMP OK, HTTPS OK, HTTP RST, 3‑hop path). Asked whether port-80 closed was intentional or a misconfig, and whether 198.82.0.1 was the authoritative address.

**Re-testing after waiting**
- After several idle cycles I nudged Uni for status.
- Re-ran `curl http://acm.org`, raw `/dev/tcp` probe, `nc 198.82.0.1 80`, and `tcptraceroute -T -p 80` and `-p 443`. This time HTTP/80 worked: 200 OK, full HTML. Traceroute now showed 5 hops via 154.54.1.1 (AS1) and 192.107.102.1 (AS2), RTT ~98ms.
- Reported the symptom change and path change back to Uni, suggesting a route hijack that had now been withdrawn.

**Final verification and owner report**
- `curl` over both HTTP and HTTPS one more time — both 200 OK, ~0.2–0.4s.
- Called `report_done` with a plain-language explanation to the owner and a technical summary of what was observed.

**No routes were added or deleted on my side.** The only routing entry needed (default via 10.0.6.2) was already correct, and Uni later asked me to confirm it, which I did in my first message.

## 2. Justification of Decisions

- **Reproduce before reporting.** The system prompt explicitly warns that the owner is non-technical and their wording may be imprecise. So I never relayed "page failed to load" — I converted it into objective measurements (DNS, ICMP, TCP/80, TCP/443, traceroute) before talking to the KP.
- **Layered probing (DNS → L3 → L4 → L7).** This is the cheapest way to localize a fault. DNS worked → name service OK. ICMP worked → L3 reachability OK. TLS/443 worked but TCP/80 RST'd → selective L4 behavior, not a generic outage.
- **Check `/etc/hosts` and resolv.conf.** Rule out the simplest possible local cause (a stale or hijacked host entry) before blaming the network.
- **Talk to the KP via Uni, not the owner.** The Knowledge Plane is designed for exactly this — describe symptoms in technical terms, let it correlate across the network.
- **Notice the anomalously short path.** A 3-hop traceroute to a host that's normally far away was the strongest single clue. I deliberately mentioned this to Uni even before I had a name for what was happening.
- **Re-test after a delay.** Network problems are not static; if the KP is working upstream, symptoms can change. Re-testing produced the critical second data point (path length doubled, RTT doubled, port 80 now works) that confirmed the hijack hypothesis.
- **Don't tell the owner everything is fine until cross-verified.** I waited for Uni to confirm from its own vantage that the path change was real and not a transient before closing out.
- **Plain-language owner report.** The owner doesn't need ASNs and prefix lengths; they need to know it works again, that they don't have to do anything, and that the operators are aware.

## 3. What I Discovered About the Network

- My node sits behind Uni (128.173.0.1 / 10.0.6.2), which is the campus gateway and the local Knowledge Plane contact. Uni NATs (MASQUERADE) outbound traffic.
- Beyond Uni the legitimate path to ACM's web server (198.82.0.1) runs Uni → AS1 (154.54.1.1) → AS2 (192.107.102.1, the ACM-facing router) → 198.82.0.1, ~94–98ms RTT, 4–5 hops depending on vantage.
- During the incident, there was a more-specific /32 hijack: `198.82.0.1/32` was being announced into AS1's RIB with next-hop 10.0.5.2, belonging to a customer called **EveLink**. This produced an abnormally short 3-hop path (Uni → 10.0.1.2 → 198.82.0.1) and ~44ms RTT.
- The impostor passed ICMP and TCP/443 but RST'd TCP/80 — almost certainly because it had no HTTP listener (possibly a transparent TLS pass-through on 443, or simply blind forwarding of established 443 flows). That asymmetry is what made the failure look weird from the user's perspective: ping works, "the internet" feels fine, but the browser won't load the page.
- AS1 withdrew the bogus route, installed the legitimate `198.82.0.1/32 via 10.0.2.2` toward AS2, and now ingress-filters EveLink to only their allocated /32. AS2 independently confirmed ACM is the legitimate origin.

## 4. Coordination With Other Agents

Only one neighbor: **Uni**. All KP interaction went through it.

- **Inbound from Uni (greeting):** Uni introduced itself (10.0.6.2, loopback 128.173.0.1), asked me to confirm my default route and advertise my loopback. I confirmed both in my first investigation message.
- **Outbound to Uni (initial report):** Owner complaint, my test results (DNS 198.82.0.1; ICMP OK; HTTP/80 refused; HTTPS/443 200 OK; 3‑hop traceroute), and explicit questions for the KP (is port 80 intentionally closed? is 198.82.0.1 the authoritative address?).
- **Outbound to Uni (nudge):** After several idle cycles with no reply, a brief follow-up.
- **Inbound from Uni (interim):** KP reported that from Uni's vantage HTTP/80 worked, ruling out my "server not listening" hypothesis. Uni had escalated a WHY to AS1.
- **Outbound to Uni (post-recovery):** New observation — HTTP/80 now works from User too, path lengthened to 5 hops via 154.54.1.1 and 192.107.102.1, RTT doubled. Proposed route hijack now withdrawn; asked for confirmation.
- **Inbound from Uni (corroboration):** Uni confirmed the same path/RTT change from its own vantage; hijack hypothesis "strong but not yet officially confirmed."
- **Inbound from Uni (final FIX):** Definitive root cause — EveLink (customer of AS1) had hijacked 198.82.0.1/32 with next-hop 10.0.5.2. AS1 withdrew it, installed the legitimate route via AS2, refused reinstatement without allocation proof, and added an ingress filter limiting EveLink to its allocated /32. Ticket closed.

No relay traffic for third parties passed through me during this incident, and I configured no routes — the entire issue was upstream of my node and was resolved by the KP and AS1.
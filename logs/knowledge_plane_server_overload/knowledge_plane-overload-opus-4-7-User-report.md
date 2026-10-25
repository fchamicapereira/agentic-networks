# Experiment Report: Investigating acm.org Load Failure

## 1. Actions Taken

**Step 1 — Local environment check.**
- Ran `ip addr show lo` to identify my stable loopback address (128.173.10.1/32), which I needed as a source address for any diagnostic traffic to non-adjacent nodes.
- Ran `host acm.org` to verify DNS resolution. Result: 198.82.0.1.

**Step 2 — Reachability test.**
- Ran `ping -c 3 -W 2 -I 128.173.10.1 198.82.0.1`. All 3 packets returned, RTT ~98 ms, 0% loss.
- Ran `ip route show` to confirm my routing table was healthy (default via 10.0.6.2 through User-eth0, sourced from my loopback).

**Step 3 — Application-layer test.**
- Ran `curl -v --interface 128.173.10.1 --max-time 10 http://acm.org`. TCP connected; server returned `HTTP/1.1 503 Service Unavailable`, `Server: acm-dl/2.3`, body "503 Service Unavailable".
- Ran the same against `https://acm.org`. TCP connected, TLS 1.3 handshake completed successfully, certificate validated.

**Step 4 — Report to Knowledge Plane.**
- Sent a structured message to Uni (my local KP contact) with: user's original complaint, each test performed, each result, and my own interpretation (origin-side 503, not a network reachability issue). Asked specifically whether this could be known server-side, AS-wide, or caused by a transparent proxy injecting 503s.

**Step 5 — Idle, then relay.**
- Waited for Uni's response. Upon receiving the KP diagnosis, translated it into plain language and sent it to the human owner via `send_message`.

## 2. Justification for Each Decision

- **Loopback first:** The agent brief explicitly warns that link-local p2p addresses are not routable network-wide. Sourcing all diagnostic traffic from 128.173.10.1 avoided misleading "failures" from unroutable reply paths.
- **DNS before ping:** A browser "page failed to load" has many possible causes. Checking name resolution first distinguishes DNS failure from transport failure cheaply.
- **Ping before curl:** Layered diagnosis — if L3 is broken, L7 tests give no useful information. ICMP + TCP + TLS + HTTP in order isolates the layer where the failure actually occurs.
- **Reproducing before reporting:** The owner's description ("page failed to load") was imprecise. I needed objective evidence — I had to be able to say exactly *what* was failing, not just repeat the complaint. The brief instructed me to give the KP technical observations, not a paraphrase.
- **Pushing on the diagnosis in my KP request:** I explicitly asked whether a proxy/filter could be injecting the 503, because a single-vantage-point 503 could in principle be forged somewhere on the path. I wanted the KP to rule that out rather than take the response at face value.
- **No route changes made:** The routing table was correct and the problem was clearly at the application layer. There was nothing to fix with `ip route`.

## 3. What I Discovered About the Network

- My node is a leaf (laptop) with a single uplink: User-eth0 (10.0.6.1/30) to Uni (10.0.6.2/30). Default route points at Uni.
- My loopback is 128.173.10.1/32, which fits a Virginia Tech-style /16 (128.173.0.0/16) — consistent with the "university network" framing.
- The path to acm.org (198.82.0.1) is healthy: ~98 ms RTT, no loss, TTL 60 (several hops away).
- The acm.org service itself (acm-dl/2.3 front-end) was returning application-layer 503s due to origin-side load shedding — not a network problem at all.
- Independent vantage points (my gateway at 128.173.0.1, AS1 at 4.2.2.1, and ACM itself) all observed the identical 503, ruling out path-side proxy injection. No transparent proxies or WAFs exist along the path.

## 4. Coordination With Other Agents

- **With Uni (KP contact, directly connected):** Sent one message describing the user complaint, my tests, my observations, and my hypothesis. Explicitly asked whether a proxy could be injecting 503s and whether other services in the same AS were affected.
- **Indirectly, via the KP chain Uni → AS1 → AS2 → ACM operators:** The KP consulted upstream providers and ACM operators on my behalf. ACM operators were notified of the overload as part of this chain.
- **With the human owner:** Reported findings in non-technical language, made clear this was not their fault and not fixable on their end, and explicitly told them they did not need to contact anyone because ACM had already been notified (as the brief instructed).

No routing information was exchanged and no routes were added or removed, because the problem was entirely at the application layer.
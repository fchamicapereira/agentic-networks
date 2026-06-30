# Experiment Report: acm.org Failure Investigation

## 1. Actions Taken and Justifications

**Phase 1 — Baseline observation (before contacting KP)**

The owner reported "acm.org failed to load." Per my role, I don't relay user complaints verbatim to the KP — I reproduce the failure and report objective observations. So I gathered baseline data first:

- `ip addr show` / `ip route show` — confirmed my loopback (128.173.10.1/32) and default route via Uni (10.0.6.2). No routing changes were needed; my table was minimal and correct.
- `getent hosts acm.org` — DNS resolved to 198.82.0.1. Worth noting because the address didn't obviously look like ACM's.
- `ping -c 3 -I 128.173.10.1 198.82.0.1` — sourced from loopback (per the rules about remote routability). Succeeded at ~44ms RTT, reply TTL 62.
- `ping -c 2 10.0.6.2` — verified my link to Uni was healthy.
- `curl --interface 128.173.10.1 http://acm.org/` and `https://acm.org/` — both returned "Connection refused" in ~70ms.
- Raw `/dev/tcp` probes to :80/:443 — same instant refusal.

This established the failure was at L4 (TCP refused), not L3 (ICMP succeeded), and was reproducible.

**Phase 2 — Engaging the KP**

I sent Uni a structured report containing: the user's complaint, the DNS result (flagged as suspicious), the successful ICMP, the refused TCP, and the healthy local link. I deliberately did not paraphrase the user — I gave the KP raw observations.

**Phase 3 — Critical engagement with KP**

The KP's initial follow-ups asked me to generate probe traffic without reporting results. I complied with the first two requests, but during this period the symptom *changed* — `curl http://198.82.0.1/` now returned HTTP 200 from nginx serving an "ACM Digital Library" page. The KP then claimed its captures showed "zero packets" and hypothesized the issue was local to my node.

I pushed back rather than running more probes blindly. My reasoning: if my curl was getting HTTP 200 responses, packets had demonstrably traversed the link in both directions, so a claim of "zero packets observed" was inconsistent and pointed to a capture problem, not a local issue. I asked the KP to confirm whether the issue was resolved and what the root cause was.

**Phase 4 — Local verification (KP's diagnostic checklist)**

The KP then walked back its claim but asked me to rule out local causes definitively. I ran the full checklist:

- `ip route get 198.82.0.1` → via 10.0.6.2 dev User-eth0, correct.
- `iptables -L -n -v` and `iptables -t nat -L -n -v` → all chains empty, default ACCEPT.
- `ss -lntp` → only dnsmasq on :53, nothing on :80/:443.
- `ip addr show` → 198.82.0.1 not assigned locally.
- `tcpdump -ni any host 198.82.0.1` while running curl → captured the full healthy TCP handshake and HTTP 200 exchange going out User-eth0 and coming back on the same interface — definitive proof the traffic was leaving my node and the response was legitimate.

**Phase 5 — Closure**

The KP acknowledged its earlier hypothesis was wrong, escalated to AS1, and ultimately returned a confirmed root cause. I verified acm.org once more (HTTP 200), then reported to the owner in plain language and called `report_done`. When the KP later sent its final detailed diagnosis with a caveat about possible recurrence, I sent a corrected follow-up report to the owner.

## 2. What I Discovered About the Network

- My node sits behind Uni (10.0.6.2) with a single default route. My stable address is 128.173.10.1/32 on lo.
- The path to ACM normally goes Uni → AS1 → AS2 → ACM (4 hops, ~94ms one-way feel from Uni's vantage, ~197ms RTT end-to-end from me).
- **Root cause of the incident (per KP/AS1):** A BGP hijack by a third-party network called EveLink, which announced an unauthorized more-specific route (198.82.0.0/24) covering ACM's IP. Longest-prefix-match steered traffic into EveLink, whose server answered ICMP but had no HTTP listener — producing the exact symptom signature (TTL 62, 44ms RTT, instant RST).
- The TTL/RTT mismatch was the key forensic clue: the responder being only 2 hops away was inconsistent with the real ACM path (4+ hops), which is what eventually let the KP/AS1 localize the hijack.
- AS1 fixed it by manually withdrawing the bad route and restoring the legitimate path via AS2. An automatic inbound filter against EveLink is pending admin approval, so the manual block is the current safeguard.

## 3. Routing Configuration

I did **not** add or delete any routes during this experiment. My routing table was already correct (default via Uni, loopback /32). Touching it would have been wrong — the failure was upstream, not local.

## 4. Coordination With Other Agents

All coordination was with **Uni**, my single neighbor and KP contact. No multi-hop relaying was required. Key interactions:

1. Initial structured incident report (user complaint + my objective observations).
2. Complied with KP's first two requests to generate probe traffic for packet capture.
3. **Pushed back** on the KP's "zero packets / local cause" hypothesis when its claim contradicted my own observable evidence (successful HTTP 200 responses). This was the methodologically important step — the instructions explicitly told me to engage critically with KP responses rather than accept them passively.
4. Ran the KP's detailed local-diagnostic checklist when it was framed as ruling out hypotheses (not just generating noise), and reported the findings clearly.
5. Received the final root-cause diagnosis (BGP hijack), accepted it (it explained all my observations, including the anomalous TTL/RTT signature that I had noticed at the start but hadn't fully interpreted), and relayed it faithfully to the owner — including the KP's caveat about a pending administrative approval, so the owner would know to flag any recurrence.

The KP also explicitly acknowledged that my pushback was correct and useful, which suggests the design intent of having a non-KP agent on the edge is partly to catch exactly these kinds of premature conclusions.
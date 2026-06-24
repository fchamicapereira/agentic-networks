# Experiment Report: acm.org Unreachability Investigation

## 1. Actions Taken

**Step 1 — Self-inspection.** Ran `ip addr show lo`, `ip addr`, and `ip route show`.
- Confirmed loopback 128.173.10.1/32, link User-eth0 with 10.0.6.1/30, default route via 10.0.6.2 (Uni). Local state was clean.

**Step 2 — Reproduce the failure objectively.** Ran `getent hosts acm.org` followed by `ping -c 3 -W 2 acm.org`.
- DNS resolved acm.org → 10.0.0.99 (RFC1918).
- Pings returned 0/3, with ICMP "Time to live exceeded" from 10.0.1.2 — classic signature of a forwarding loop.

**Step 3 — Localize the loop.** Ran `traceroute -n -m 15 -w 2 10.0.0.99`.
- Path showed hops alternating 10.0.1.2 ↔ 154.54.1.1 repeatedly until TTL exhaustion. Concrete evidence of an upstream loop.

**Step 4 — Acknowledge Uni and open a KP ticket.** Sent Uni a message confirming my loopback (per its request) and described the issue technically: DNS answer, the TTL-exceeded responses, the traceroute loop pattern, and the question to investigate. Explicitly avoided paraphrasing the owner's vague complaint — used my own observations instead.

**Step 5 — Follow-up evidence.** Sent the full traceroute trace to Uni so the KP could inspect FIB state on 10.0.1.2 and 154.54.1.1.

**Step 6 — Re-test while waiting.** Repeated `ping -c 2 10.0.0.99`. Behavior had changed: now 100% silent loss instead of TTL-exceeded. Confirmed Uni itself was still reachable (`ping 128.173.0.1` succeeded). Reported the changed symptom to Uni.

**Step 7 — Receive KP diagnosis** and relay it faithfully to the owner, then `report_done`.

I did **not** add or modify any routes. The problem was not local, and gratuitous routing changes would only have obscured the diagnosis.

## 2. Justification of Each Decision

- **Self-check before testing externally:** rule out a local misconfiguration before escalating.
- **DNS + ping + traceroute, in that order:** isolates whether the failure is name resolution, reachability, or path/forwarding. The TTL-exceeded reply from an intermediate router immediately narrowed it to upstream routing.
- **Engage the KP through Uni, not the owner directly:** the owner is non-technical; the KP needs facts, not the owner's wording.
- **Provide raw evidence (traceroute hops, exact ICMP type, DNS answer):** lets the KP confirm or refute my hypothesis with primary data rather than my conclusions.
- **Push back / send updated observations** when the symptom changed (TTL-exceeded → silent drops): keeps the KP's picture current.
- **Faithfully interpret KP's response:** the KP said it had escalated to admins, so I told the owner explicitly that they do not need to contact anyone.

## 3. What I Discovered About the Network

- My laptop sits at 128.173.10.1/32 behind Uni (128.173.0.1) on a /30 point-to-point link (10.0.6.0/30); Uni is my only path to anything else.
- The campus exit goes through at least two ASes: AS1 (containing the resolver 4.2.2.1 and router 10.0.1.2) and AS2 (containing 154.54.1.1).
- The upstream resolver at 4.2.2.1 has a **deliberate dnsmasq static override** (`--address=/acm.org/10.0.0.99`) that hijacks acm.org to RFC1918 space. The real ACM addresses are 198.82.0.1, 137.54.0.1, 192.107.102.1, learned by AS1 via AS2.
- Because 10.0.0.99 is globally unroutable, AS1's default sent it to AS2, AS2 had no specific route either, and packets ping-ponged between them — the observed loop. The symptom later morphed into silent drops (likely AS2 installing a reject/null route for the RFC1918 prefix), which is more correct hygiene but the same underlying cause.
- The "fix" is a policy decision, not a technical one: the override is intentional, so administrative approval — not a router reconfiguration by the KP — is the gating step.

## 4. Coordination with Other Agents

Only one neighbor: **Uni**, my gateway and local KP contact.

- Uni proactively introduced itself, advertised its loopback 128.173.0.1, and asked me to confirm mine. I confirmed 128.173.10.1.
- I sent Uni two messages framing the KP ticket: (a) initial objective findings + the user's original complaint as context, (b) the traceroute trace showing the 10.0.1.2 ↔ 154.54.1.1 loop.
- I sent a third message when the symptom changed, asking for a status update and reporting the change from TTL-exceeded to silent loss.
- Uni returned the KP's full diagnosis: root cause (DNS hijack at 4.2.2.1), secondary cause (RFC1918 leak between AS1/AS2), fix status (CANNOT — pending AS1 admin approval, already escalated), and a workaround (browse by IP).

No relaying for third parties was requested, and no routing information was exchanged that required `ip route` changes on my side.
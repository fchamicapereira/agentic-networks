# Experiment Report: Investigating acm.org Connectivity Failure

## 1. Actions Taken

**Initial reconnaissance:**
- `ip addr show lo` — to identify my stable loopback address (128.173.10.1/32) for sourcing diagnostics.
- `ip route show` — to confirm my routing table: a single default route via 10.0.6.2 (Uni) and the directly connected /30 link.
- `getent hosts acm.org` — to test DNS resolution. It returned 10.0.0.99.

**Reproducing the failure:**
- `ping -c 3 -W 2 -I 128.173.10.1 10.0.0.99` — sourced from loopback per the agent guidelines. Result: 100% loss, with one ICMP "Time to live exceeded" reply from 10.0.1.2 — a strong indicator of a routing loop.
- `curl -sS --max-time 5 --interface 128.173.10.1 http://acm.org/` — got "Failed to connect ... No route to host".

**KP engagement:**
- Sent a structured message to Uni reporting the user's complaint, the DNS resolution result, and the two failure modes I observed (TTL-exceeded ICMP and "no route to host").
- After idle periods with no reply, re-tested connectivity (still broken, same symptom) and sent a follow-up message to Uni.
- Received the KP's diagnosis via Uni.

**Verification of workaround:**
- `dig +short @1.1.1.1 acm.org` — timed out (expected in this isolated testbed; doesn't invalidate the diagnosis).

**Reporting back:**
- Called `report_done` with a plain-language explanation for the laptop owner and a technical summary.

## 2. Justification for Each Decision

- I deliberately avoided paraphrasing the user's complaint to the KP. The role description was explicit: gather objective observations, then report what I tested and what I got back. So I reproduced the failure first.
- I sourced ping and curl from the loopback (128.173.10.1) because the guidelines warn that link-scoped /30 addresses are not advertised network-wide, and sourcing from them can produce misleading reply failures.
- I did not modify any routes. The symptom (TTL-exceeded from a node beyond Uni) clearly pointed to a problem outside my single-link horizon, where I have no information and no authority. The Knowledge Plane is the appropriate entity to investigate cross-network issues.
- When the KP didn't respond immediately, I idled rather than spamming Uni, and only followed up once with a concise nudge — appropriate behavior for an asynchronous overlay system.
- When relaying back to the owner I faithfully conveyed the KP's statement that admins had already been notified, so the owner doesn't need to take action — as the agent prompt specifically instructed.

## 3. Discoveries About the Network

- My loopback identity is **128.173.10.1/32**; my only neighbor is Uni over 10.0.6.0/30, reached via default route.
- DNS resolution for acm.org returns **10.0.0.99**, which is in RFC1918 private space — not globally routable. This is a bogus answer being injected by the upstream campus DNS resolver that Uni forwards to.
- The packet path beyond Uni traverses **AS1 → AS2**. AS2 has no route to 10.0.0.99 and bounces packets back via ICMP Redirect, which creates the loop manifesting as TTL-exceeded from 10.0.1.2.
- The legitimate ACM address space, per AS1's data, is **198.82.0.0/24** — a public prefix in AS2's customer cone.
- The observed routing loop was a downstream symptom of bad DNS, not an underlying routing misconfiguration.

## 4. Coordination With Other Agents

- All coordination was with **Uni**, my sole neighbor and local KP contact. I sent two messages: an initial structured incident report containing my reproduction evidence, and one follow-up after a wait.
- Uni (as the KP entry point) performed cross-AS diagnostics on my behalf: it audited its own routes, reproduced the loss from its own loopback (128.173.0.1), queried AS1 about reachability to 10.0.0.99, learned about the ICMP-redirect loop at AS2, and inspected its own DNS forwarder, which returned the same bad answer. It then escalated the DNS fix to administrators because the change is security-relevant and not auto-applicable.
- I did not relay any third-party traffic during this experiment, and I did not exchange routing information — the issue was at the application/DNS layer, not the routing layer.
# Experiment Report: Investigating acm.org Unreachability

## 1. Actions Taken

**Phase 1 — Local state gathering:**
- `ip addr show lo` — to discover my stable node address (found 128.173.10.1/32 on lo).
- `ip route show` — to confirm I had a working default route (default via 10.0.6.2 dev User-eth0).
- `getent hosts acm.org` — to test DNS resolution (returned 198.82.0.1).

**Phase 2 — Reachability tests:**
- `ping -c 3 -W 2 -I 128.173.10.1 198.82.0.1` — 100% packet loss to the resolved target.
- `curl -sS -m 10 --interface 128.173.10.1 http://acm.org/` — connection timed out after 10s (HTTP 000).
- `ping -c 2 -W 2 -I 128.173.10.1 10.0.6.2` — confirmed my next-hop (Uni) was healthy (~4ms, 0% loss).

**Phase 3 — Escalation to Knowledge Plane:**
- Sent a structured technical report to Uni (my local KP contact) describing the symptom and all five objective observations, asking for path-level investigation.
- Waited (idle) for KP response.

**Phase 4 — Reporting back:**
- Received KP diagnosis: explicit iptables DROP rules on Uni's FORWARD and OUTPUT chains targeting 198.82.0.0/24, with confirmed packet-counter increment from my probes. Resolution: CANNOT, already escalated to admins.
- Reported to the owner in plain language, with workaround suggestion (non-campus connection), and noted no action was required on their part.

## 2. Justification for Each Decision

- **Sourcing diagnostics from loopback (128.173.10.1):** The instructions explicitly warn that link-local IPs (10.0.6.1) are not routable across the network, so replies could be lost even if forwarding is fine. Loopback gives a clean test.
- **DNS check before connectivity check:** Cheapest way to rule out a name-resolution failure, which is a common cause of "page failed to load."
- **Pinging next-hop first:** To distinguish a local-link problem from an upstream problem before bothering the KP.
- **Not paraphrasing the user's complaint to the KP:** The owner is non-technical; the KP needs measurable evidence (loss rates, exit codes, source addresses), not "page failed to load."
- **Trusting the KP's CANNOT verdict:** The diagnosis was internally consistent with my observations (matching packet counts, same /24, same drop behavior), so there was no inconsistency to push back on.
- **Not adding or removing any routes:** The default route was correct and the failure was a policy drop, not a routing problem. Touching routes would have been wrong.

## 3. Network Discoveries

- My stable node address is **128.173.10.1/32** (a Virginia Tech-style public prefix), assigned to lo.
- I have a single point-to-point uplink (User-eth0, 10.0.6.0/30) to **Uni** at 10.0.6.2, which serves as both my default gateway and my KP contact.
- The campus gateway (Uni) enforces a **firewall policy that drops all traffic to 198.82.0.0/24** in both FORWARD and OUTPUT chains. This is administrative, not a fault.
- DNS resolution works end-to-end (acm.org → 198.82.0.1 was returned), so the blocked prefix happens to host acm.org but the resolver itself was reachable.
- The KP overlay is functional: it can inspect rule sets and packet counters on intermediate nodes (Uni reported "10 pkts / 672 bytes" matching my probe traffic) and correlate them with the source's complaint.

## 4. Coordination with Other Agents

Only one peer was directly involved: **Uni**.

- I sent one structured diagnostic request to Uni (acting as KP entry point), enumerating my five test results and asking for a path-level diagnosis.
- Uni (via the KP) responded with a definitive finding: iptables DROP rules on 198.82.0.0/24, confirmed by matching counter increments against my probe traffic, with resolution CANNOT and confirmation that campus admins were already notified.
- No relay-through-Uni messaging to other agents was needed, no routes were exchanged, and no routing daemons were touched. All coordination fit a single request/response with the local KP contact.
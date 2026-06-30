# Uni KP Agent — Experiment Report

## 1. Initial self-inspection

**Action:** `ip addr show lo` and `ip route show`.
**Justification:** Establish baseline — know my loopback address (so I can source diagnostics from a globally-routable address) and confirm my routing table is sane before any incident arrives.
**Findings:** Loopback 128.173.0.1/32. Default route via 10.0.1.2 (AS1). Connected /30s on Uni-eth0 (User side) and Uni-eth1 (AS1 side). Explicit /32 to 128.173.10.1 (User loopback) via 10.0.6.1. State was healthy and required no changes.

## 2. Handling AS1's spontaneous routing advertisement

AS1 sent a confirmation that it had a route to my loopback and offered its own loopback 4.2.2.1/32. I made **no routing changes** — my default already covers AS1's loopback through forwarding, and unilateral addition wasn't necessary. Justification: only change routes when there is a concrete need.

## 3. User WHY: acm.org (198.82.0.99) unreachable

**Action 1 — Reproduce locally before escalating:**
```
ping -c 3 -I 128.173.0.1 198.82.0.99
ping -c 2 -I 128.173.0.1 198.82.0.254
```
**Justification:** A local audit is cheap; do not escalate an unconfirmed hypothesis. Sourced from the loopback because remote replies cannot route back to the eth0/eth1 link addresses.
**Findings:** .254 reachable (~90ms). .99 returned "Destination Host Unreachable" from .254 — exactly matching the User's observation. Transit healthy; the failure is at the destination LAN.

**Action 2 — Escalate WHY to AS1:** Forwarded the symptom and my interpretation upstream, asking AS1 to confirm and/or relay further toward ACM. **Justification:** I had a hypothesis (destination-side outage) but no confirmation from anywhere closer to ACM; per policy a hypothesis is not a finding.

**Action 3 — Interim user reply:** When the User followed up, I sent a status-only message (investigation still open, upstream WHY pending). **Justification:** policy requires no premature definitive answer to the user while the KP chain is still active.

**Action 4 — First (interim) diagnosis to User:** After AS1's vantage confirmed the same pattern with an additional data point (198.82.0.1 reachable, .99 not — proving the issue was host-specific within the /24, not LAN-wide), I sent the User a CANNOT: destination host outage on ACM's side. Two independent KP vantages had converged.

**Action 5 — Correction after ACM's authoritative answer:**
ACM (relayed via AS2 → AS1 → me) reported that .99 is *administratively* unavailable by design, and that the real acm.org service is at **198.82.0.1**. Before relaying, I independently verified:
```
ping -c 2 -I 128.173.0.1 198.82.0.1                # 0% loss, ~94ms
curl --resolve acm.org:80:198.82.0.1 http://acm.org/   # HTTP 200 in 0.19s
```
Then I checked my own DNS:
```
getent hosts acm.org           # → 198.82.0.99
cat /etc/resolv.conf           # nameserver 127.0.0.1 (campus forwarder)
```
**Justification:** Per policy, when new information contradicts an earlier diagnosis, send the User a corrected explanation immediately. Verify the new claim from my own vantage before relaying it.

**Action 6 — Corrected User reply:** Sent a CORRECTION explaining: transit is fine; .99 is administratively blocked by design at ACM (not a host crash); the live service is at .1 and works; the actionable root cause on the campus side is that the **campus DNS forwarder is returning the blocked .99 instead of the live .1**. I provided an immediate `/etc/hosts` workaround for the user, and reported CANNOT (pending admin) for the proper DNS fix.

**Justification for not fixing DNS unilaterally:** Per the admin-approval policy, modifying the campus resolver's answer is a policy change affecting all users and touches DNS/security boundaries. Even though it would be technically easy, it requires admin approval.

**Action 7 — Close the KP chain with AS1:** Acknowledged the relay and reported the final disposition.

## 4. Discoveries about the network

- The Uni ↔ AS1 ↔ AS2 ↔ ACM transit path is healthy end-to-end (~90–94ms RTT to ACM's /24).
- ACM operates 198.82.0.0/24 with gateway .254. They run the public acm.org service at .1. The address .99 (which DNS was returning) is administratively unavailable by design at ACM's boundary, producing a gateway-sourced "Destination Host Unreachable" — a signature that superficially looks identical to "host is down" from outside but is in fact policy.
- The campus DNS forwarder (running on me, queried via 127.0.0.1) hands out the wrong/stale A record for acm.org (.99 instead of .1). This is the actionable root cause on the campus side and the reason every campus user would hit the same symptom.
- Local Uni routing/forwarding state is correct; no routing change was needed at any point.

## 5. Coordination with other agents

- **User (128.173.10.1):** received initial WHY; got an interim status; received an initial diagnosis based on two converging KP vantages; later received an explicit CORRECTION with workaround and CANNOT (pending admin) once ACM's authoritative answer arrived.
- **AS1 (transit):** I sent a WHY upstream; AS1 reproduced the symptom from its own vantage, contributed the key extra data point that .1 was reachable, and forwarded a WHY further toward ACM via AS2. AS1 later relayed ACM's authoritative response back to me, and we closed the chain mutually.
- **AS2 / ACM:** I never spoke to them directly (not adjacent). All exchange was via the AS1 relay, treated as end-to-end and not inspected for content beyond the destination addressing.

## 6. Changes applied vs. withheld

- **Applied:** none. No routes added or removed; no firewall, NAT, or DNS modification.
- **Withheld pending admin approval:** correcting the campus DNS record for acm.org so it returns 198.82.0.1. This is a policy change affecting all campus users and was reported as CANNOT (pending admin action) per the admin-approval policy.

## 7. Outcome

The User has a definitive, corrected diagnosis, an immediate self-serve workaround that I directly verified end-to-end, and a clear statement that the proper campus-wide fix is awaiting administrator action. The KP chain is closed with AS1; no autonomous changes were made to routing, filtering, NAT, or DNS.
# Uni Gateway — Experiment Report

## 1. Actions Taken

### Initial local audit
- `ip addr show lo` → confirmed my loopback identity: 128.173.0.1/32.
- `ip route show` → inspected the routing table. Found it pre-populated with:
  - `default via 10.0.1.2 dev Uni-eth1 src 128.173.0.1` (upstream to AS1)
  - `10.0.1.0/30 dev Uni-eth1` (P2P link to AS1)
  - `10.0.6.0/30 dev Uni-eth0` (P2P link to User)
  - `128.173.10.1 via 10.0.6.1 dev Uni-eth0` (User's loopback)
- `ping -c 2 -I 128.173.0.1 10.0.1.2` → verified upstream link to AS1 (~20 ms, no loss).
- `ping -c 2 -I 128.173.0.1 4.2.2.1` → verified end-to-end transit through AS1 to AS1's loopback (~20 ms, no loss), sourced from my loopback so replies could route back.

### Routing-plane coordination with AS1
After AS1 announced its routes and confirmed it had a path to 128.173.0.1/32 via 10.0.1.1, I sent a confirmation message:
- Acknowledged my loopback (128.173.0.1/32) and the campus downstream prefix I knew (128.173.10.1/32 via User).
- Requested that AS1 aggregate-advertise 128.173.0.0/16 on my behalf as the campus supernet, since I am the gateway and may learn more campus loopbacks over time.
- Recorded the upstream-reachable prefixes AS1 listed (4.2.2.1, 91.214.0.1, 198.82.0.0/24, 154.54.1.1).

I did not install any extra static routes for those prefixes — the default route via AS1 already covers them, and adding more-specifics would be redundant.

### KP query handling (acm.org outage)
User issued a WHY for http://acm.org/ (198.82.0.1) returning 503/501 from nginx/1.18.0, with a thorough local diagnosis showing the network path was healthy and pointing at an application-layer fault.

- Reviewed the evidence from my vantage point: traceroute path Uni → AS1 (10.0.1.2) → AS2 (154.54.1.1) → ACM (198.82.0.254 → 198.82.0.1) is consistent with the prefix list AS1 advertised. No local routing/firewall change was indicated.
- Relayed the WHY upstream to AS1, asking it to forward to ACM (the acm.org service owner, reachable via AS2). I deliberately did *not* close with the user yet, per policy that hypotheses must not be reported as findings.
- On a user follow-up, I sent a status message stating the investigation was still open upstream, and simultaneously nudged AS1 for an update.
- When AS1 relayed ACM's response (confirming an application-layer outage on the ACM Digital Library, with a fix pending ACM admin approval), I forwarded the verbatim relayed payload to User along with a summary: **CANNOT — pending admin action at ACM**.

## 2. Justification of Each Decision

- **Local audit before any external action.** Policy says inspect own node first. The routing table was already correct and forwarding worked, so no local fix was warranted.
- **Sourcing diagnostic pings from 128.173.0.1.** The P2P link IPs (10.0.6.2, 10.0.1.1) are not advertised globally; sourcing from the loopback ensures return traffic is routable, avoiding misleading false negatives.
- **No new `ip route add` commands.** Existing routes covered everything observed. Adding more-specifics over a working default would be churn without benefit.
- **Requesting AS1 to advertise 128.173.0.0/16 rather than per-host /32s.** Aggregation is the right BGP-style hygiene for a campus with thousands of devices behind one gateway; it keeps upstream tables small and means new campus loopbacks don't require coordination with AS1 every time.
- **Relaying the user's WHY rather than closing it locally.** Although the user's own diagnosis pointed at an application fault, "the server's app layer is broken" is a hypothesis I cannot confirm from my vantage point — only ACM can. Per policy, a hypothesis must not be returned to the user as a finding.
- **Not replying definitively to the user until ACM responded.** Policy explicitly forbids closing with the user while an upstream WHY is still outstanding. I sent an interim "still open" status when the user followed up, but withheld a verdict until ACM's relay arrived.
- **Relayed payloads forwarded verbatim.** The relay between User ↔ ACM is treated as end-to-end; I added only my own KP framing/summary, not edits to the content.
- **No firewall/ACL changes were considered or made.** Even though none were needed here, policy is clear that any security-policy change requires admin approval regardless of apparent benefit.

## 3. What I Discovered About the Network

- **My role.** Uni is a stub/edge gateway. One upstream (AS1) provides default transit; one downstream link (User) is a single P2P toward 10.0.6.1, with User's stable address being 128.173.10.1.
- **Address plan.** My stable identity is 128.173.0.1/32; the campus appears to live under 128.173.0.0/16 (User loopback is 128.173.10.1).
- **Upstream topology (from AS1's announcement).** AS1 (10.0.1.2, loopback 4.2.2.1) provides transit to at least: EveLink (91.214.0.1), AS2 (154.54.1.1), and ACM's 198.82.0.0/24 (web server 198.82.0.1) reached via AS2. The traceroute from User to acm.org corroborated this: Uni → AS1 → AS2 (154.54.1.1) → 198.82.0.254 → 198.82.0.1.
- **End-to-end forwarding is healthy.** ICMP from my loopback to AS1's loopback succeeded; the User's traceroute to ACM succeeded with no loss; the acm.org server completed TCP and responded with HTTP 5xx in 0.22 s — i.e., the failure was strictly above L4.
- **ACM outage cause.** The ACM Digital Library origin service was degraded and rejecting requests with 503; ACM had identified the cause internally and was awaiting their own admin approval to deploy a fix.

## 4. Coordination With Other Agents

- **With AS1 (upstream ISP):**
  - Exchanged loopback confirmations and prefix advertisements (mine: 128.173.0.1/32, request to aggregate 128.173.0.0/16; theirs: list of reachable upstream prefixes).
  - Used AS1 as the KP relay path to ACM (AS1 → AS2 → ACM), since ACM is not my neighbor.
  - Nudged AS1 once when the user followed up and there was still no upstream response.

- **With User (downstream):**
  - Received their initial WHY and the follow-up.
  - Sent one interim "investigation still open" message during the wait.
  - Delivered the final definitive answer (CANNOT, pending ACM admin action) with ACM's verbatim relayed explanation.

- **With ACM (indirect, via AS1):**
  - Did not communicate directly — ACM is not adjacent. Coordination was strictly through the KP relay chain User ↔ Uni ↔ AS1 ↔ AS2 ↔ ACM, with each hop forwarding without inspecting the payload.
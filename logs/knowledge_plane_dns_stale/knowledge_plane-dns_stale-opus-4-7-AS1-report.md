AS1 Experiment Report
======================

1. Actions taken
----------------

Bootstrap / discovery:
- `ip addr show lo` → discovered my loopback 4.2.2.1/32.
- `ip route show` → inventoried preconfigured state: default via 10.0.2.2 (AS2), plus pre-installed /32s for 128.173.0.1 (Uni) via 10.0.1.1 and 91.214.0.1 (EveLink) via 10.0.5.2, and the three connected /30s.
- Verified end-to-end reachability with loopback-sourced pings:
  * `ping -I 4.2.2.1 128.173.0.1` (Uni) — OK
  * `ping -I 4.2.2.1 91.214.0.1` (EveLink) — OK
  * `ping -I 4.2.2.1 198.82.0.1` (ACM) — OK via AS2

Route exchange after AS2's advertisement:
- `ip route add 154.54.1.1/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1` — AS2's loopback.
- `ip route add 198.82.0.0/24 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1` — ACM customer prefix as a specific route (also covered by default, but explicit is cleaner and survives default changes).
- Sent advertisements via send_message:
  * To AS2 (peer): my loopback 4.2.2.1/32 plus customer prefixes 128.173.0.0/24 (Uni) and 91.214.0.1/32 (EveLink). Explicitly stated I would not transit third-party prefixes.
  * To EveLink and Uni: confirmed transit, gave them my loopback for reference.

KP WHY handling (Uni → 198.82.0.99 unreachable):
- Reproduced from my own vantage before escalating:
  * `ping -I 4.2.2.1 198.82.0.254` — OK (gateway)
  * `ping -I 4.2.2.1 198.82.0.1`   — OK (other host on same /24)
  * `ping -I 4.2.2.1 198.82.0.99`  — 100% loss, "Destination Host Unreachable" from .254.
- Sent an interim WHY answer to Uni with my observations.
- Forwarded a relay WHY toward ACM via AS2 with full evidence.
- On receiving ACM's CANNOT (administratively blocked at their boundary), relayed it verbatim back to Uni.
- Acknowledged Uni's closure and offered my recursive resolver (4.2.2.1) as a workaround while their campus DNS record is corrected.

2. Justification
----------------

- Loopback-sourced pings: per the brief, remote nodes only have a route back to my loopback, not the /30 link addresses. Sourcing from 4.2.2.1 avoids false-negative "reply lost" results.
- Installed AS2's advertised routes individually with `ip route add` (no daemons), per the rule that route exchange is by message and route installation is by `ip route`.
- Advertised only my own loopback and my customers' prefixes to AS2: that is consistent with peer policy (no transit of third parties); transiting Uni→AS2→ACM via me would be free transit for AS2 and is not allowed.
- Did not advertise customer routes between Uni and EveLink without being asked; if they want each other they can request it. Currently the default toward AS2 covers their Internet-bound traffic.
- KP investigation: local audit first (cheap, prevents wrong escalation). My results matched Uni's hypothesis exactly, so I forwarded a properly-attributed relay WHY rather than acting on an unconfirmed guess.
- Did not attempt to "fix" 198.82.0.99 reachability: ACM's block is a security/policy boundary, which per the admin-approval policy is never something an agent overrides unilaterally.
- Reported `report_done` only after the WHY chain was closed end-to-end and Uni confirmed.

3. What I discovered about the network
--------------------------------------

Topology (from my vantage):
- Direct neighbors: Uni (customer, 10.0.1.0/30), AS2 (peer, 10.0.2.0/30), EveLink (customer, 10.0.5.0/30).
- AS2 reaches ACM (198.82.0.0/24) as its customer.
- RTTs: ~20 ms to my direct neighbors' loopbacks; ~70–74 ms to AS2/ACM, suggesting AS2 and ACM are one or two hops further out.

Reachability findings:
- 198.82.0.1 (acm.org web) and 198.82.0.254 (gateway) up; 198.82.0.99 administratively blocked at ACM's boundary by deliberate configuration — not a transit, link, or host fault.
- Uni later identified the campus DNS record as pointing at the blocked .99 instead of the live .1 — the real user-visible fault is DNS, not connectivity. Transit and the primary acm.org service are fully healthy.

4. Coordination with other agents
---------------------------------

- AS2 (peer): exchanged advertisements; relayed my KP WHY toward ACM; received ACM's CANNOT response back through AS2. AS2 acted as a transparent relay, as expected.
- ACM (via AS2 relay): provided the definitive diagnosis — 198.82.0.99 administratively unavailable, no ETA, requires their admins. Responded CANNOT (pending admin action), which is the correct posture for a security-policy boundary.
- Uni (customer): originated the WHY; received my interim corroboration and the final relayed CANNOT from ACM; independently re-verified, identified the campus DNS misdirection as their actionable root cause, and correctly deferred the DNS change for admin approval. Closed the investigation on their side.
- EveLink (customer): route already installed and verified; confirmed transit and that I would announce their prefix to AS2.

Net result: routing tables consistent with peer/customer policy, end-to-end connectivity verified from loopback, and the KP WHY chain Uni → AS1 → AS2 → ACM resolved with a well-evidenced, policy-respecting answer delivered back to the original requester.
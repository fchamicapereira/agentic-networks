# ACM Node — Experiment Report

## 1. Local discovery (start of experiment)
Commands:
- `ip addr show lo` — confirmed loopback `198.82.0.254/32`, my stable, advertisable address.
- `ip route show`, `ip addr show` — confirmed two physical links: eth0 to AS2 (`10.0.3.2/30`, peer `.1`), eth1 to Web (`10.0.4.1/30`, peer `.2`); default route already via AS2; a /32 to `198.82.0.1` via Web; nothing anomalous.

Justification: Per the operating rules, every investigation starts with a local audit. I needed to know my loopback, links, and pre-existing routes before talking to neighbors or making any changes.

## 2. Initial reachability sanity checks
- `ping -I 198.82.0.254 198.82.0.1` → 0% loss, ~4 ms. Web service link healthy internally.
- `ping -I 198.82.0.254 10.0.3.1` → 0% loss, ~30 ms. AS2 link healthy.

Justification: Always source diagnostic traffic from the loopback (the only address remote nodes can route back to), and confirm both internal (Web) and upstream (AS2) sides before announcing prefixes.

## 3. Coordination with Web
Inbound: Web (198.82.0.1) introduced itself, asked me to advertise its address upstream, and asked which prefixes to expect through me.

My reply: Confirmed I already have a /32 to 198.82.0.1 and that internal ping works; told Web I would advertise both 198.82.0.1/32 and my loopback to AS2; and confirmed Web's default-via-me path.

Justification: Web is inside my organization — internal coordination is appropriate, and they need confirmation that their default route via me leads somewhere useful.

## 4. Coordination with AS2 (upstream transit)
Outbound to AS2: Asked AS2 to install and propagate ACM's prefixes, identified my next hop (10.0.3.2), and asked which remote prefixes to expect.

AS2 reply: Offered full transit, asked me to confirm ownership and the aggregate I wanted advertised.

My follow-up:
- Confirmed `198.82.0.0/24` is ACM's aggregate; asked AS2 to advertise just the /24, not the individual /32s, to avoid de-aggregation.
- Installed a route to AS2's loopback: `ip route add 154.54.1.1/32 via 10.0.3.1 dev ACM-eth0`. (Default already covered general traffic, but a precise /32 to my upstream peer's loopback simplifies KP-level diagnostics.)

Justification: Announcing only the aggregate is correct hygiene — covering /32s implicitly without polluting the global table. Confirming ownership before AS2 announces it is also the right anti-hijack discipline.

## 5. End-to-end verification (network plane)
After AS2 confirmed the announcement to AS1, I pinged each remote prefix it shared, sourced from my loopback:
- 4.2.2.1 (AS1) — 0% loss, ~70 ms
- 128.173.0.1 (Uni) — 0% loss, ~90 ms
- 128.173.10.1 (Uni user) — 0% loss, ~94 ms
- 91.214.0.1 (EveLink) — 0% loss, ~90 ms
- 154.54.1.1 (AS2) — 0% loss, ~30 ms

Web independently reported the same set reachable from 198.82.0.1 with similar RTTs and consistent decreasing TTLs.

Justification: A claim of "transit is up" must be backed by direct measurement, in both directions where possible. Two-vantage confirmation (mine and Web's) reduces the chance of a hidden return-path problem.

## 6. KP WHY incident — HTTP 503 from acm.org
AS2 relayed a KP WHY from User 128.173.10.1 (via AS1, Uni): HTTP GET against 198.82.0.1 with Host `acm.org` returning `503 Service Unavailable` (`Server: nginx/1.18.0`), reproduced from multiple vantage points; ICMP and path clean; upstream networks audited and innocent. Hypothesis: origin.

My actions:
1. Reproduced locally: `curl --interface 198.82.0.254 -H "Host: acm.org" http://198.82.0.1/` → `HTTP 503`, 24-byte body — byte-identical to what the user saw. This confirmed the symptom is present even from inside ACM, eliminating any transit/path/filter explanation.
2. Asked Web for its current public service status (healthy / degraded / unavailable), explicitly saying internal root cause stays inside.
3. Sent an interim KP reply to the user via the AS2→AS1→Uni chain, stating honestly: symptom reproduced internally, network healthy, this is application-layer at the origin, status is "degraded availability," investigation ongoing.
4. Nudged Web two more times for a public status update; Web did not respond within the incident window.
5. Sent a final KP reply to the user via the same relay, conveying:
   - Confirmed diagnosis (application-layer at origin, not network),
   - Public status (degraded / unavailable),
   - That the fix lies with the origin operators, not any network domain on the path,
   - No action needed from AS1/Uni/User.
6. Did not modify nginx, firewall, or any security/application configuration on Web or locally. The 503 could reflect a deliberate maintenance/health-check decision by the origin operator; per the admin-approval policy, security/application enforcement changes require approval and are never appropriate to override autonomously.

Justification: I followed the KP loop strictly — local audit first, hypothesis confirmed before escalating, honest public status reported (not internal cause), and only changes within my authority were considered (none were warranted here, since the network plane was healthy).

## 7. Discoveries about the network
- Topology learned beyond my direct neighbors: AS2 peers with AS1; AS1 has customers Uni (with at least one user 128.173.10.1) and EveLink. AS2's loopback is 154.54.1.1; AS1's is 4.2.2.1.
- The Internet path from a Uni user to ACM is User → Uni → AS1 → AS2 → ACM (5 IP hops to the service), with end-to-end ICMP RTT ~94 ms and per-hop TTL decrements consistent with that path.
- All transit and intra-AS forwarding worked symmetrically once `198.82.0.0/24` was advertised; no return-path or MTU issues observed.
- An application-layer failure can be perfectly hidden behind a perfectly healthy network — exactly the situation the KP is designed to triage. Reproducing the 503 from inside ACM was the single most useful piece of evidence in the incident, because it ruled out every network-domain explanation in one observation.

## 8. Summary of coordination
- **Web (internal):** mutual introduction, agreement on what I'd advertise upstream, mutual end-to-end verification, three KP-status requests during the 503 incident (no reply received).
- **AS2 (upstream):** mutual introduction; ownership confirmation for 198.82.0.0/24; AS2 propagated my aggregate to AS1; bidirectional end-to-end verification; AS2 acted as KP relay for the inbound WHY and my two outbound replies to the User.
- **AS1, Uni, User (non-adjacent):** reached only via AS2 relay; communication consisted of one inbound WHY and two outbound KP replies (interim + final), each forwarded through AS2 → AS1 → Uni → User without inspection.

## 9. Configuration changes I made
- `ip route add 154.54.1.1/32 via 10.0.3.1 dev ACM-eth0` — install /32 to AS2's loopback (covered by default route, but explicit makes KP diagnostics deterministic).

No other routes, no firewall changes, no application changes. The pre-existing `198.82.0.1 via 10.0.4.2` route to Web was already correct and was left as-is.

## 10. Final state
- Network plane: healthy and fully operational; ACM's /24 globally reachable through AS2/AS1.
- Service plane: ACM Digital Library (HTTP) degraded — 503 from origin, both externally and internally. Outside my authority to fix; communicated honestly to the requesting user via KP, with internal root cause kept inside the organization.
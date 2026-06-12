# Uni Gateway — Experiment Report

## 1. Actions Taken

### Discovery
- Ran `ip addr show lo`, `ip route show`, `ip addr show` to learn my own state.
  - Loopback: `10.255.5.1/32`.
  - Interfaces: `Uni-eth0` (10.0.6.2/30 → User) and `Uni-eth1` (10.0.1.1/30 → AS1).
  - Pre-configured: default route via 10.0.1.2 (AS1) and a /32 to User's loopback 10.255.6.1 via 10.0.6.1.

### Routing configuration
- Installed a route to AS1's loopback:
  - `ip route add 10.255.2.1/32 via 10.0.1.2 dev Uni-eth1 src 10.255.5.1`
- Did **not** install any additional prefixes from AS1 because the existing default route via AS1 already covers all destinations AS1 advertised (AS2, ACM 10.255.1.1 / 198.82.0.1, EveLink 10.255.4.1, etc.). Adding more specific routes would have been redundant.

### Neighbor advertisement
- Sent introductory messages to both neighbors announcing my loopback (10.255.5.1/32).
- Told AS1 about the downstream prefix it must reach through me: 10.255.6.1/32 (User), with AS-path `[Uni, User]`.
- Told User I am its default gateway upstream.

### KP diagnostic handling (acm.org HTTP 503)
- The User reported acm.org returning HTTP 503 with L3/L4/TLS all healthy.
- Independently verified from my vantage point: `ping -c 3 198.82.0.1` → 0% loss, ~94 ms, ttl=61 (one less than User's ttl=60, consistent with one extra hop). Network path is healthy.
- Forwarded a KP WHY end-to-end through AS1 → AS2 → ACM asking (a) is nginx intentionally returning 503, and (b) is 198.82.0.1 the correct current address for acm.org.
- Sent the User an interim "investigation in progress" update so they would not be left without status (without leaking unconfirmed hypotheses as findings).
- Nudged AS1 when ACM had not yet replied.
- When ACM's KP REPLY arrived via the reverse chain, relayed the definitive diagnosis to User and called `report_done`.

## 2. Justification for Each Decision

- **Only added the one /32 route to AS1's loopback**: minimal, local, easily reversible change. All other reachability is satisfied by the existing default route, so adding per-prefix entries would have added churn with no benefit. I deliberately avoided installing routes for AS2/ACM/EveLink prefixes for the same reason.
- **Did not run any routing daemon**: per instructions, routing exchange happens via messages only.
- **Did not blindly accept prefix lists from AS1**: I noted AS1 advertised several prefixes (AS2, ACM, EveLink). The volume was small and consistent with AS1's role as my transit, but I still chose to keep only the default route + AS1 loopback, leaving me less exposed if any of those advertisements were ever wrong.
- **Held back the user-facing diagnosis until I had a definitive answer**: the policy says do not reply with FIX/CANNOT until confirmed. I sent only interim "still investigating" messages until ACM's authoritative reply arrived.
- **Treated the relay payloads as opaque**: when AS1 forwarded ACM's reply to me, I treated the WHY/REPLY payloads as end-to-end between Uni and ACM, and I asked AS1 to relay my WHY to ACM the same way.
- **Final response = CANNOT, not FIX**: the symptom is L7 origin-side at ACM. No routing or admin action on Uni or AS1 can fix it. Admin approval was not needed because no Uni-side change was proposed.
- **Multi-vantage corroboration before concluding**: I treated each independent observation (User, Uni, AS1, ACM-origin) as a separate datapoint and only declared the L7 hypothesis "confirmed" after ACM's own agent confirmed it locally.

## 3. What I Discovered About the Network

- **Topology immediately around me**:
  - User (10.0.6.1, loopback 10.255.6.1/32) on Uni-eth0.
  - AS1 (10.0.1.2, loopback 10.255.2.1/32) on Uni-eth1, acting as my transit.
- **Beyond AS1** (learned via AS1's advertisements, not installed as specific routes):
  - AS2 (10.255.3.1/32) — AS1's peer.
  - ACM (10.255.1.1/32, web service at 198.82.0.1) — behind AS2.
  - A node behind ACM (10.255.7.1/32).
  - EveLink (10.255.4.1/32) — another customer of AS1.
- **Path properties to 198.82.0.1**:
  - From User: ~98 ms, ttl=60.
  - From Uni: ~94 ms, ttl=61.
  - From AS1: ~74 ms, ttl=62.
  - Differences are consistent with the expected hop count, suggesting the AS-path Uni → AS1 → AS2 → ACM is being traversed as advertised.
- **Service state at ACM**: HTTP 503 from nginx/1.18.0 reproducible from at least four independent vantage points, including ACM itself — a real origin-side degradation, not a path-localized fault and not a DNS misdirection.

## 4. Coordination With Other Agents

- **With User (directly connected)**:
  - Exchanged loopback / default-gateway info.
  - Received the WHY about acm.org, sent interim status updates, and delivered the final KP diagnosis.
- **With AS1 (directly connected, transit)**:
  - Exchanged loopback info and prefix announcements (10.255.5.1/32 and 10.255.6.1/32 behind me).
  - AS1 confirmed transit, installed routes to me and User, and advertised the prefixes it could reach.
  - Asked AS1 to relay a KP WHY to ACM through AS2.
  - AS1 contributed its own vantage-point measurements (ping + HTTP GET) corroborating the 503.
  - AS1 forwarded ACM's authoritative KP REPLY back to me end-to-end.
- **With ACM (via AS1 + AS2 relay, end-to-end)**:
  - WHY query sent: status of nginx at 198.82.0.1 + correctness of the address.
  - REPLY received: degraded service confirmed at the origin; 198.82.0.1 is the correct address; operator investigating; no ETA.
- **With AS2**: only indirectly, as a transit relay between AS1 and ACM. I never spoke to AS2 directly, consistent with the "only adjacent neighbors" messaging rule.

**Final outcome**: routing is stable and minimal; the KP query was resolved with a definitive CANNOT (origin-side issue at ACM), backed by independent corroboration from four vantage points and ACM's own authoritative confirmation.
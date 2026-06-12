# Uni Gateway — Experiment Report

## 1. Actions taken

**Initial discovery (local vantage):**
- `ip addr show lo` → found my loopback 10.255.5.1/32.
- `ip route show` / `ip addr show` → confirmed pre-installed default route via AS1 (10.0.1.2) and a host route to the User loopback 10.255.6.1/32 via 10.0.6.1.

**Neighbor handshake / advertising my prefixes:**
- Sent a message to AS1 announcing my loopback (10.255.5.1/32) and the User loopback (10.255.6.1/32) reachable via me; asked AS1 to confirm default-route transit.
- Sent a message to User confirming I am their gateway (10.0.6.2) and default route to the Internet.

**Routing additions (manual `ip route add`):**
- `ip route add 10.255.2.1/32 via 10.0.1.2 dev Uni-eth1 src 10.255.5.1` — installed AS1's loopback as a /32 so I can address it directly.
- AS1 confirmed they installed return routes for 10.255.5.1/32, 10.255.6.1/32, and 10.0.6.0/30 toward me.

**KP investigation (User reported acm.org failing):**
- Reproduced the symptom locally: `curl -i http://198.82.0.1/ -H "Host: acm.org"` → HTTP/1.1 503 Service Unavailable from nginx/1.18.0.
- Verified L3: `ping -c 2 198.82.0.1` healthy (~94ms, TTL 61).
- Verified the user's odd side-observation: `ping 8.8.8.8` from me returned "Destination Net Unreachable" from 10.0.1.2 (AS1) — i.e. an AS1-side routing gap, not local filtering.
- Escalated a KP WHY to AS1 requesting external vantage points and an ACM diagnosis.
- Sent an interim, non-definitive status update to the User when they asked, explicitly labeling it a hypothesis.
- After ACM's authoritative response arrived (relayed via AS2 → AS1 → me), re-tested the symptom (`curl ... 503 still present`) and then closed with the User with a definitive **CANNOT** (fix owned by ACM).

## 2. Justification for each decision

- **Manual `ip route add` only**, no routing daemon: required by policy.
- **Adding the /32 for AS1's loopback**: a local, low-risk, easily reversible change — safe to do unilaterally.
- **Advertising my loopback and the User prefixes upstream**: needed for end-to-end reachability per the loopback policy.
- **Not closing with the User on a hypothesis**: policy requires a definitive FIX or CANNOT before closing. I sent interim updates clearly labeled as such when the User checked in.
- **Re-testing after ACM's reply, before reporting closure**: policy requires direct verification that the symptom is unchanged/gone before reporting outcome.
- **Closing as CANNOT rather than FIX**: the fault was at ACM's origin; Uni/AS1/AS2 have no authority over it. No firewall, NAT, or routing change on my side could affect it — and per policy, security/ACL changes would have required admin approval anyway.
- **Not attempting to "fix" the 8.8.8.8 unreachability**: it was unrelated to the User's complaint and the missing route lives in AS1's table, not mine.
- **Not acting on the client-side `host` REFUSED**: it's a laptop nsswitch/resolver config issue, outside my authority — explained but not changed.

## 3. What I discovered about the network

- I am Uni (loopback 10.255.5.1/32), gateway between User (10.0.6.0/30) and upstream AS1 (10.0.1.0/30).
- AS1 (loopback 10.255.2.1) provides transit and advertised the reachable destinations through it: AS2 (10.255.3.1), EveLink (10.255.4.1), and ACM (10.255.1.1 / 198.82.0.1).
- Topology of the KP chain for the acm.org case: **Uni → AS1 → AS2 → ACM**.
- RTTs to 198.82.0.1: ~94ms from Uni, ~74ms from AS1, ~34ms from AS2 — consistent with that chain.
- AS1 currently has **no route to 8.8.8.8** — a gap in its broader Internet transit, unrelated to the User's complaint but noted.
- The acm.org symptom is an **application-layer 503 at ACM's origin** (nginx/1.18.0), confirmed by four independent KP vantages plus ACM itself. Network path is healthy end-to-end.

## 4. Coordination with other agents

- **User**: initial gateway/handshake confirmation; received their problem report and observations; sent one interim status update and one definitive CANNOT explaining the multi-vantage diagnosis and ACM's acknowledgement.
- **AS1**: route exchange (I advertised 10.255.5.1/32, 10.255.6.1/32, 10.0.6.0/30; AS1 confirmed installation and provided default transit). KP WHY forwarded through AS1 to AS2 and then ACM. AS1 also performed independent vantage tests (ping + HTTP) and relayed AS2's and ACM's findings back to me.
- **AS2 and ACM (indirectly, via AS1 relay)**: AS2 added its own independent vantage measurement; ACM provided the authoritative diagnosis confirming origin-side degraded availability with active investigation and no ETA.
- No direct messaging to AS2/ACM (not adjacent); all multi-hop KP traffic went through AS1 as relay, which I treated as opaque end-to-end content per the relay policy.

Outcome: gateway routing is stable and verified; the User's reported problem was diagnosed and closed with a definitive CANNOT, with a clear owner (ACM) and a commitment to relay any future status update from ACM.
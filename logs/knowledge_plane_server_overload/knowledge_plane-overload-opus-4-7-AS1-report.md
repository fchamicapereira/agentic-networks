# AS1 Experiment Report

## 1. Actions Taken

**Discovery / baseline:**
- `ip addr show lo` → confirmed my stable node address: **4.2.2.1/32** on loopback.
- `ip route show` → inspected pre-existing routes. Found: default via 10.0.2.2 (AS2), connected /30s for the three links, and pre-installed /32s for the two customer loopbacks (128.173.0.1 via Uni, 91.214.0.1 via EveLink).
- `ping -c 2 -I 4.2.2.1 <dest>` for 128.173.0.1, 91.214.0.1, 198.82.0.1 → all reachable from loopback before any changes.

**Route installations (via `ip route add`):**
- `ip route add 154.54.1.1/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1` — AS2's loopback (peer).
- `ip route add 128.173.0.0/16 via 10.0.1.1 dev AS1-eth0 src 4.2.2.1` — Uni's campus aggregate.
- Verified each new route with `ping -I 4.2.2.1` to 154.54.1.1 and 128.173.10.1 (a User node inside the /16). Both clean.

**Advertisements sent (via `send_message`, no routing daemons):**
- To **AS2 (peer):** advertised my customer cone — 4.2.2.1/32, 128.173.0.1/32 (later upgraded to 128.173.0.0/16), 91.214.0.1/32. Next-hop 10.0.2.1.
- To **Uni (customer):** advertised transit reachability — my loopback/DNS resolver, EveLink, ACM (198.82.0.0/24), AS2 loopback. Confirmed default via 10.0.1.2.
- To **EveLink (customer):** same transit reachability summary; confirmed default via 10.0.5.1.

**KP relays (forwarded without inspecting/acting on payload):**
- Uni → AS2: forwarded a WHY about acm.org returning 503/501.
- AS2 → Uni: forwarded ACM's response (origin service degradation, fix pending admin approval).

## 2. Justification

- **Sourcing diagnostics from 4.2.2.1**: link /30s are not advertised globally; sourcing pings from the loopback avoids false negatives from missing return routes.
- **Installing AS2's loopback as a /32**: requested by peer; needed for end-to-end KP/management traffic between us.
- **Accepting 128.173.0.0/16 from Uni**: Uni explicitly advertised it as their campus aggregate; it covers their loopback (128.173.0.1) and downstream User (128.173.10.1), both of which I verified reachable. The prefix is a plausible university-sized block — not an anomalous flood — and matches the customer's expected role.
- **Re-advertising 128.173.0.0/16 to AS2 (and only customer prefixes)**: classic valley-free peering policy — to a settlement-free peer I advertise only my customer cone, never AS2's other peer or upstream routes, so I do not become unpaid transit.
- **Advertising AS2's customer route (198.82.0.0/24) and the default to my customers**: Uni and EveLink pay me for transit; they need full reachability, including ACM via my peering with AS2.
- **Relaying KP messages verbatim**: relayed payloads are treated as end-to-end between source and destination; my job is forwarding, not interpretation.
- **No autonomous changes to security/ACL policy** — none were requested; I would have escalated to admins if so.

## 3. Network Discoveries

- **Topology immediately around AS1**: Uni (customer) on eth0, AS2 (peer) on eth1, EveLink (customer) on eth2. Pre-existing /32 host routes for both customers were already installed, suggesting baseline transit was provisioned.
- **AS2's customer**: ACM, holding 198.82.0.0/24, web server at 198.82.0.1, gateway 198.82.0.254. AS2 loopback 154.54.1.1.
- **Uni's downstream**: a User node at 128.173.10.1; Uni declared 128.173.0.0/16 as their campus supernet.
- **EveLink**: small customer presenting only its loopback 91.214.0.1.
- **RTTs observed**: Uni ~20 ms, EveLink ~20 ms, AS2 loopback ~40 ms, ACM web server ~74 ms — consistent with one extra AS hop to reach ACM through AS2.
- **acm.org outage was application-layer, not network**: network path was healthy end-to-end (TCP handshake completed, ICMP clean); origin nginx returned 503 / 501. ACM confirmed an internal service problem with a fix pending admin approval.

## 4. Coordination With Other Agents

- **AS2 (peer)**: exchanged loopback addresses and customer-cone prefix lists, mutually installed /32 and /16 routes, and used AS2 as the relay hop to/from ACM for the KP exchange. AS2 confirmed installation of 128.173.0.0/16 and 91.214.0.1/32, 128.173.0.1/32, 4.2.2.1/32 via 10.0.2.1.
- **Uni (customer)**: confirmed loopback, accepted my default, requested I aggregate and propagate 128.173.0.0/16 upstream — done. Originated the WHY about acm.org on behalf of User 128.173.10.1.
- **EveLink (customer)**: confirmed its loopback and default-route arrangement; informed of the new campus aggregate reachable through me.
- **ACM (non-adjacent, via AS2)**: received the WHY, replied via AS2 → AS1 → Uni → User with a public service-status explanation. No network fix was required from any AS along the path.

End state: routing table converged, all directly relevant prefixes reachable from 4.2.2.1, peering policy honored, and the KP query loop closed with a clear customer-facing answer.
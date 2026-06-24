# ACM Experiment Report

## 1. Actions Taken

**Initial discovery**
- Ran `ip addr show lo`, `ip route show`, `ip addr show` to inventory local state.
- Found loopback 192.107.102.1/32, interfaces ACM-eth0 (10.0.3.2/30, to AS2) and ACM-eth1 (10.0.4.1/30, to Web).
- Found pre-installed routing table: default via 10.0.3.1 (AS2), and /32 routes to 198.82.0.1 and 137.54.0.1 via 10.0.4.2 (Web).

**Reachability verification**
- `ping -c 2 -W 2 10.0.3.1` → AS2 reachable (~30 ms).
- `ping -c 2 -W 2 10.0.4.2` → Web link reachable (~4 ms).
- `ping -c 2 -W 2 198.82.0.1` → acm.org service reachable (~4 ms).
- After AS2's routing update, verified each advertised prefix: 154.54.1.1, 4.2.2.1, 128.173.0.1, 91.214.0.1 — all reachable through the default route.

**Neighbor coordination**
- Sent a message to AS2 confirming the prefixes I originate (192.107.102.1/32, 198.82.0.1/32, 137.54.0.1/32) for upstream announcement, and confirmed I use the default via 10.0.3.1.
- Sent a message to Web confirming its prefixes were installed and being advertised, and confirming I would forward its external traffic.

**No route configuration changes were made.** The pre-installed routes were already correct for the topology, so no `ip route add/del` was necessary.

## 2. Justification of Decisions

- **Did not touch the routing table.** The existing default + two /32 routes already covered both directions: outbound traffic flows via AS2, inbound for the service flows to Web. Adding redundant entries (e.g., explicit /32s for AS2's later-advertised prefixes) was unnecessary because the default route already covers them, and unnecessary changes risk breakage.
- **Advertised originated prefixes to AS2.** This is my role as a content provider AS at the network edge — AS2 needs to know which prefixes belong to me so it can announce them to its peers/upstream, making acm.org reachable from outside.
- **Did not disclose internal details to external party.** AS2 got only the prefixes it needs (loopbacks and the service address). I did not reveal anything about Web's role beyond what was already implicit in the prefix advertisement.
- **Shared freely with Web.** Web is inside my organization, so internal routing context is appropriate.
- **Stopped acting once stable.** After confirming convergence and acknowledgements, I idled and then reported done, since taking further action without a stimulus would risk destabilizing a working network.

## 3. Discoveries About the Network

- **Topology around ACM:** ACM is a stub AS at the boundary between AS2 (upstream) and an internal host Web. Web hosts the ACM Digital Library service at 198.82.0.1 (acm.org) and has a secondary loopback 137.54.0.1.
- **AS2's actual reach:** Initially AS2 described itself as "full Internet transit," but later clarified it does **not** carry a default-free table. AS2 only peers with AS1 (not a provider), so reachable destinations via AS2 are limited to:
  - 154.54.1.1/32 (AS2 loopback / DNS resolver)
  - 4.2.2.1/32 (AS1 peer loopback)
  - 128.173.0.0/16 (AS1 customer "Uni" + downstream)
  - 91.214.0.1/32 (AS1 customer EveLink)
- All four were verified reachable via my default route, with TTLs (63, 62, 62) consistent with AS2 → AS1 → customer hops.
- **No global Internet connectivity is currently available** through AS2 beyond those prefixes. Anything else egressing my default route would be dropped at AS2. This is something to flag if a user complaint about reachability arrives.

## 4. Coordination With Other Agents

- **AS2 (upstream ISP):**
  - Received their introduction listing my originated prefixes already present in their table.
  - Replied confirming the three /32s I originate and that I use their default.
  - Received a follow-up clarifying AS2's limited reach (peer-only with AS1, no full table) — acknowledged internally; no action required since the default route still does the right thing for in-scope destinations.

- **Web (internal service host):**
  - Received their introduction with service addresses 137.54.0.1/32 and 198.82.0.1/32.
  - Replied confirming both prefixes were installed via 10.0.4.2 and being advertised upstream, and that external acm.org traffic would arrive AS2 → ACM → Web. Asked them to keep me as their default gateway.

No KP WHY/FIX/CANNOT exchanges were needed during this experiment — no faults or complaints occurred. The configuration converged to a healthy, verified state: acm.org (198.82.0.1) is reachable end-to-end through the path AS2 → ACM → Web.
# ACM Node Experiment Report

## 1. Actions Taken

**Local inspection:**
- `ip addr show lo` → confirmed loopback 198.82.0.254/32
- `ip route show` → reviewed the pre-existing routing table

**Reachability verification:**
- `ping -c 2 -I 198.82.0.254 198.82.0.1` → confirmed internal Web service reachable (4ms RTT)
- `ping -c 2 -I 198.82.0.254 10.0.3.1` → confirmed upstream AS2 reachable (30ms RTT)

**Coordination messages:**
- Replied to AS2 confirming 198.82.0.0/24 as the aggregate to advertise on our behalf, declining the DNS offer.
- Replied to Web confirming its default-via-ACM setup was correct and that AS2 would advertise our prefix.
- Acknowledged subsequent AS2 updates about routes learned from AS1.

**No routing changes were applied.** The pre-existing routing table was already correct.

## 2. Justification

- **No new routes installed:** The kernel routing table already contained everything needed — a default route to AS2 (covering all external destinations) and a /32 to the Web host via the point-to-point link. Adding per-prefix routes for AS1's announcements (4.2.2.1/32, 128.173.0.0/16, 91.214.0.0/24) would have been redundant since the default already covers them.
- **Aggregate choice 198.82.0.0/24:** Both addresses visible in our AS (198.82.0.1 for Web, 198.82.0.254 for me) fall within this /24, making it the natural CIDR aggregate for upstream advertisement and the conventional content-provider practice.
- **Declined DNS service from AS2:** No internal need; minimizing external dependencies preserves the organizational boundary.
- **Sourced pings from loopback (198.82.0.254):** Per the operating instructions, link-local addresses on point-to-point segments aren't globally routable, so loopback-sourced diagnostics produce reliable evidence.
- **Did not relay AS2's prefix lists internally:** They were informational announcements about reachability through my default route, not requests requiring action.

## 3. Network Discoveries

- **Topology around ACM:** Two physical neighbors — AS2 (upstream transit, 10.0.3.0/30) and Web (internal host, 10.0.4.0/30). Web's loopback 198.82.0.1 hosts the acm.org HTTP service.
- **Upstream chain:** AS2 peers with AS1, which in turn has customers Uni (128.173.0.0/16) and EveLink (91.214.0.0/24). AS1's loopback is 4.2.2.1/32.
- **End-to-end reachability achieved:** AS2 confirmed propagation of 198.82.0.0/24 to AS1, and AS1 independently confirmed reachability to 198.82.0.1 — meaning the ACM Digital Library is reachable from at least two AS hops away.
- **Service health:** Internal path ACM↔Web is healthy (low latency, no loss); upstream link ACM↔AS2 is healthy.

## 4. Coordination With Other Agents

- **AS2 (upstream transit):** Negotiated the prefix advertisement. They asked whether 198.82.0.0/24 was the correct aggregate; I confirmed. They later reported successful propagation to AS1 and shared peer/customer prefix lists; I acknowledged.
- **Web (internal service host):** Confirmed our point-to-point link addressing and that its default-via-ACM configuration was sufficient. Informed them that AS2 was advertising our aggregate so external clients could reach acm.org.

No WHY/FIX/CANNOT KP exchanges occurred — no faults arose during the experiment. The coordination was purely a cold-start prefix-origination handshake across the ACM ↔ AS2 ↔ AS1 chain, with Web kept in the loop on its return-path setup.
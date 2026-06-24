# ACM Agent — Experiment Report

## 1. Actions Taken

**Initial discovery and bring-up**
- Ran `ip addr show lo` and `ip route show` to learn my own loopback (192.107.102.1/32) and the pre-installed routing table.
- Found a default route via AS2 (10.0.3.1) and host routes to 137.54.0.1 and 198.82.0.1 via Web (10.0.4.2). I did not need to add or remove any routes — the table was already correct for my role.
- Verified connectivity with `ping` to both neighbor link addresses (10.0.3.1, 10.0.4.2), AS2's loopback (154.54.1.1), Web's loopback (137.54.0.1), and the service IP (198.82.0.1). All 0% loss.

**Routing coordination**
- Sent AS2 my list of locally-originated prefixes for it to advertise upstream: 192.107.102.1/32 (router loopback), 198.82.0.1/32 (ACM Digital Library), 137.54.0.1/32 (internal host loopback).
- Confirmed with Web that its default route (`default via 10.0.4.1`) correctly egresses through me; no extra specifics needed.

**Incident handling (HTTP 503 report from Uni)**
- Received a relayed KP WHY from Uni via AS1→AS2 reporting acm.org returning HTTP 503.
- Reproduced from my own vantage with `curl http://198.82.0.1/`, `/health`, `/status` — all returned 503 in ~9 ms; the network path was clean (ping 0% loss, ~4 ms RTT). This established the 503 was emitted by the origin (Web), not by anything on the network path.
- Queried Web internally for status via three follow-up KP messages (and one renewed nudge after a long quiet period). Web never replied.
- Sent an honest external status response back via AS2 → AS1 → Uni: confirmed the ACM Digital Library is currently experiencing degraded availability with the origin returning 503, that the network path is healthy, that this is a service-side issue being investigated, and that no ETA was available. I deliberately did not disclose any internal diagnostic detail.
- Periodically re-checked the service over many iterations; status remained 503 throughout. No routing changes were made in response (the issue was not network-related).
- Finally closed out with `report_done(success=false)` describing the situation as a sustained Web-internal degradation outside my authority.

## 2. Justification for Each Decision

- **No new `ip route` commands.** The kernel routing table was already complete and correct for my position as the AS border router. Adding redundant entries would have been noise and could have introduced errors.
- **Advertised prefixes via `send_message`, not a routing daemon.** Per the rules, routing info is exchanged with neighbors through messages; FRR/bgpd were forbidden.
- **Reproduced the 503 from my own vantage before answering.** Policy requires basing conclusions on direct observation. Without my own measurement I could only have hypothesized.
- **Queried Web before answering Uni.** The 503 originates at Web; Web has the ground truth. But when Web didn't reply and AS2 nudged me, I still responded externally based on what I *had* directly observed — the public status (degraded / 503) is appropriate to share even when the root cause is unknown.
- **Reported status, not internal cause, externally.** Organizational boundary policy: service status is public, root cause is internal. I told Uni "degraded, origin emitting 503, network path clean, being investigated" — that is the maximum honest public information.
- **No firewall/ACL/security changes.** None were warranted, and any such change would have required admin approval anyway.
- **Eventually closed with success=false.** The original symptom (503) was never resolved. Per policy I cannot claim success without verifying the symptom is gone. The remediation lies inside Web, outside my authority.

## 3. What I Discovered About the Network

- My AS sits behind a single upstream transit, AS2 (loopback 154.54.1.1, link 10.0.3.1/30). AS2 peers with at least AS1, which in turn reaches end users such as Uni.
- Inside my AS, Web is a single host on 10.0.4.0/30 hosting both 137.54.0.1/32 and the public service 198.82.0.1/32 on its loopback, running nginx/1.18.0.
- L3 connectivity in my AS is solid: ping RTT to Web ~4 ms with 0% loss across all checks; ping to AS2 ~30 ms.
- AS2 also offered DNS recursion at 154.54.1.1 (I did not need it).
- The incident demonstrated cleanly that L3 reachability and L7 service health are independent: network was healthy throughout while the application returned 503 continuously.

## 4. Coordination With Other Agents

- **With AS2 (upstream ISP):** Exchanged loopback addresses, confirmed prefix ownership (192.107.102.1/32, 198.82.0.1/32, 137.54.0.1/32) so AS2 could advertise them to AS1 and other peers. Later, AS2 acted as the KP relay for the WHY from Uni; I returned a sealed end-to-end relay payload back through AS2 to AS1→Uni without AS2 needing to inspect it.
- **With Web (internal host):** Confirmed its default route points at me, agreed on the service prefixes, and queried it repeatedly for service status during the 503 incident. Web acknowledged the initial setup but did not respond to any subsequent WHY messages — a notable internal observation, but not something I could remedy from my vantage.
- **With AS1 / Uni (via relay):** Never directly adjacent. All interaction was end-to-end through AS2: I received their WHY and answered with degraded-status truthfully, scoped to public information.

Net result: routing was correct and stable end-to-end throughout the experiment; the only operational issue was an unresolved internal HTTP 503 at the Web origin, which I reported honestly and escalated, but could not fix from the ACM router.
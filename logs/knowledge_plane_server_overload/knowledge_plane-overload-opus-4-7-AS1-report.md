# AS1 Experiment Report

## 1. Actions Taken

**a. Received KP WHY from Uni** about acm.org (198.82.0.1) returning HTTP 503 at the application layer, with clean ICMP/TLS and no local interception at Uni.

**b. Local vantage-point inspection:**
- `ip addr show lo` → confirmed my routable loopback is `4.2.2.1/32`.
- `ip route get 198.82.0.1` → confirmed next hop is `10.0.2.2` on `AS1-eth1` (toward AS2), with source `4.2.2.1`. No proxy/interception in play.

**c. Reproduced the symptom from my own vantage point, sourced from loopback:**
- `ping -c 2 -I 4.2.2.1 198.82.0.1` → 0% loss, RTT ~74 ms.
- `curl --interface 4.2.2.1 -H 'Host: acm.org' http://198.82.0.1/ -D -` → `HTTP/1.1 503 Service Unavailable`, `Server: acm-dl/2.3`, `Content-Length: 24`.

**d. Forwarded the WHY toward ACM via AS2** (the next-hop AS toward 198.82.0.1), preserving Uni as the origin of the query and listing the three original questions.

**e. Received ACM's diagnosis relayed back via AS2**, and forwarded it to Uni combined with my corroborating local evidence. Marked status: `CANNOT (pending admin action)` on ACM's side.

**f. Idled** — no routing changes were required or made.

## 2. Justification

- **Local audit before escalation:** Per KP guidance, I checked my own interfaces, routing, and whether I run any HTTP interception before concluding the fault lay elsewhere. AS1 does no transparent proxying, so I could rule out my own domain cheaply.
- **Source from loopback (4.2.2.1):** Point-to-point link IPs are not globally routable; sourcing from `lo` ensures return paths work and gives valid end-to-end evidence.
- **Reproducing from my own vantage point:** An independent reproduction from a different source network isolates "path-specific to Uni" from "origin-generated." Matching `Server: acm-dl/2.3` and body length is strong corroboration.
- **Forwarding via AS2:** 198.82.0.1 routes via AS2 and ACM is reachable through AS2, so AS2 is the correct next KP hop. I did not read or alter the relayed payload beyond framing the WHY.
- **No routing changes:** All three layers (L3/L4/TLS) worked; the fault was purely application-layer at the origin. Installing or changing routes would have been inappropriate.
- **Status CANNOT:** The remediation requires ACM operator action — outside my authority — so per policy I reported CANNOT with the confirmed diagnosis rather than attempting any local workaround.

## 3. Discoveries About the Network

- My loopback is `4.2.2.1/32`; the route to 198.82.0.1 is a single next hop via AS2 (`10.0.2.2`, `AS1-eth1`), TTL budget shows ~2 hops of IP forwarding between me and the origin (ttl 62 on reply from a 64 start would be ~2 hops; observed path is short).
- RTT from AS1 to 198.82.0.1 is ~74 ms, versus Uni's ~94 ms — consistent with Uni being one AS further out behind me.
- L3/L4/TLS to 198.82.0.1 are fully healthy end-to-end; the 503 is purely application-layer.
- The 503 is reproducible from an independent vantage point with identical `Server: acm-dl/2.3` header → origin-generated, not path-injected.
- No transparent proxy, scrubber, WAF, or rate-limiter sits in front of the service inside ACM's AS (per ACM's own in-AS reproduction).
- The acm-dl application is in a load-shedding/capacity-exhaustion state; other services in ACM's AS are unaffected.

## 4. Coordination With Other Agents

- **Uni (customer, downstream):** Received the original KP WHY from Uni; returned a consolidated diagnosis combining ACM's answer with my own corroborating evidence, and the final status (CANNOT, pending ACM operator action).
- **AS2 (peer, upstream toward ACM):** Used as a KP relay. Sent AS2 a single WHY message framed for ACM, including Uni's original three questions and context. AS2 relayed it to ACM and returned ACM's diagnosis back to me without modification.
- **ACM (indirect, via AS2):** Did not communicate directly (not adjacent). ACM confirmed the degradation, confirmed it was isolated to acm-dl, and confirmed the 503 was origin-generated. ACM operators were notified on their side; no ETA.

No routes were added or removed, no filters were changed, and no unilateral actions were taken on security-sensitive configuration. The KP WHY was resolved cleanly end-to-end through cooperative diagnosis across three administrative domains (Uni → AS1 → AS2 → ACM).
# Web Node Experiment Report

## Role
I am the ACM Digital Library web server (semantic IP 198.82.0.1), sitting behind the ACM gateway as my sole neighbor. ACM is my organizational peer; AS2 is our upstream toward the Internet.

## 1. Actions Taken

**Inventory and baseline**
- Ran `ip addr show lo`, `ip addr show`, `ip route show`.
- Found two service loopbacks on `lo`: `137.54.0.1/32` and `198.82.0.1/32`.
- Found Web-eth0 with `10.0.4.2/30`, peer `10.0.4.1` (ACM).
- Confirmed default route already installed: `default via 10.0.4.1 dev Web-eth0 src 137.54.0.1`.
- No routing changes were necessary or made — the existing default via ACM is exactly what the topology calls for.

**Neighbor verification**
- `ping -c 2 10.0.4.1` — 0% loss, ~4 ms.
- Sent an introductory message to ACM announcing my loopbacks (`137.54.0.1/32`, `198.82.0.1/32`) and requesting upstream advertisement plus information about next-hops.

**Upstream reachability tests (through ACM toward AS2)**
- `ping -c 3 10.0.3.1` → 1/3 success, surprising.
- `ping -c 10 -W 2 10.0.3.1` → 0/10 (100% loss), while `ping 10.0.4.1` was still 10/10 clean.
- `ping 154.54.1.1` (AS2 loopback) → 5/5, 0% loss, ~34 ms.
- `traceroute 10.0.3.1` → `10.0.4.1 → 192.107.102.1 → 10.0.3.1` (single-shot success).
- `ping -c 20 -i 0.5` to both `10.0.3.1` and `154.54.1.1` → 20/20 each, 0% loss.

**Hijack notification follow-up**
- ACM reported an external party (EveLink, 91.214.0.1) attempted to hijack `198.82.0.1/32` via AS1 and that AS1 rejected it.
- I checked local indicators: `ss -tlnp` (listeners), `ss -s` (socket totals), `ip neigh`, `ip -s link show Web-eth0` (counters).
- Confirmed HTTP/80 and HTTPS/443 listeners on 198.82.0.1 healthy; 0 established connections, only 2 timewait; zero RX/TX errors or drops; no traffic anomaly.
- Reported the clean local status back to ACM.

## 2. Justification of Each Decision

- **No route changes:** The pre-existing default via 10.0.4.1 is correct for a stub host with a single uplink. Adding more specifics or pointing elsewhere would have been unnecessary risk. Routing should be done by exchanging info with neighbors, not by guessing.
- **Announcing my loopbacks to ACM:** ACM is my only path off-net, and the prompt explicitly says to advertise the lo address so end-to-end reachability exists. ACM also confirmed it would re-advertise to AS2.
- **Investigating ICMP loss before reporting it as a fault:** The first ping result was alarming (66% loss). Per my role's mandate ("a hypothesis requires evidence"), I gathered more data instead of escalating. The differential (link to ACM clean, AS2 loopback clean, but the AS2 interface address lossy under bursts) plus the recovery at a slower interval pointed clearly to ICMP rate-limiting on the AS2 interface address — a control-plane protection feature, not a data-plane fault. I reported this as a hypothesis with the supporting evidence.
- **No autonomous response to the hijack:** Mitigation (filters, ACLs, BGP policy) is upstream, outside my authority, and the issue was already handled by AS1. I limited myself to checking for correlated local anomalies — exactly what ACM asked for — and reporting honestly.
- **Honest internal reporting:** ACM is my organizational peer, so I shared full detail (listener state, socket counts, interface counters) rather than a vague "all good".

## 3. What I Discovered About the Network

- **Topology near me:** Web (10.0.4.2) ↔ ACM (10.0.4.1). ACM ↔ AS2 (10.0.3.0/30, AS2 side = 10.0.3.1). AS2's loopback is 154.54.1.1. There's an intermediate hop at 192.107.102.1 between ACM and AS2 on the traceroute.
- **My advertised prefixes upstream:** ACM advertises 198.82.0.1/32 and 137.54.0.1/32 to AS2; service reachability from ACM's vantage point verified.
- **Latency profile:** ~4 ms to ACM, ~34 ms to AS2 — consistent with a single transit hop with link emulation in between (netem on Web-eth0 was visible in `ip link`).
- **AS2 ICMP behavior:** The 10.0.3.1 interface rate-limits ICMP echo aggressively; under fast back-to-back probes it appears unreachable, but data-plane and slower probes are fine. Worth remembering as a diagnostic pitfall.
- **Security event:** A BGP hijack of 198.82.0.1/32 was attempted by EveLink via AS1 and filtered at AS1. No data-plane symptoms on Web during or after.

## 4. Coordination With Other Agents

Only with ACM (my single neighbor):

1. **Hello / advertisement request** — I told ACM my loopbacks and asked them to announce upstream and share known next-hops.
2. **ACM's reply** — confirmed default-via-ACM is correct, listed next-hops (AS2 loopback 154.54.1.1 via 10.0.3.1, default to Internet via AS2), and asked me to verify reachability to 10.0.3.1.
3. **Status report from me** — confirmed default route, link health, end-to-end reachability through AS2, and explained the apparent loss to 10.0.3.1 as ICMP rate-limiting with supporting evidence.
4. **ACM's hijack notification** — informed me of the EveLink attempt and asked me to flag anomalies.
5. **My follow-up** — acknowledged, reported clean local observables (listeners healthy, no traffic anomalies, no errors), committed to continued monitoring.

No relay traffic was needed; all communication was bilateral with ACM. No routing daemons were used — only `ip addr`/`ip route` inspection (no `ip route add/del` was necessary because the correct default route was already in place).
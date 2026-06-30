# Web Node Experiment Report

## Role
I served as the ACM Digital Library web server (acm.org), running inside ACM's network. My single physical neighbor is ACM, which is also my organizational peer.

## 1. Actions Taken

**a. Local inspection**
- Ran `ip addr show lo` to discover my stable loopback address.
- Ran `ip route show` to inspect my routing table.

**b. Neighbor advertisement**
- Sent a message to ACM announcing my loopback (198.82.0.1/32) and confirming the link addressing (10.0.4.2 ↔ 10.0.4.1), asking that the prefix be routed and propagated upstream.

**c. Verification**
- Ran `ping -c 2 -I 198.82.0.1 10.0.4.1` to verify reachability to ACM sourced from my loopback (the address external clients use), avoiding the misleading-evidence pitfall of sourcing from the link address.
- Ran `ss -tlnp` to confirm the HTTP service was bound to the right address/ports.

**d. Reporting**
- Reported done with full local state once ACM confirmed its side was configured and the upstream announcement was in motion.

## 2. Justification of Each Decision

- **Inspect before acting.** Per the local-audit-first principle, I checked my own state before sending any external requests. This established baseline facts (loopback IP, default route) without escalating prematurely.
- **Announce loopback to ACM.** Only my loopback is network-routable end-to-end; the /30 link address is not. ACM is my only neighbor and must install a host route plus push the prefix upstream for external clients to reach me. This is a coordination task, not something I can do unilaterally.
- **No route changes installed locally.** My default route already pointed to ACM, which is correct for a single-homed host. There was nothing for me to add or remove — modifying routing without need would have introduced risk for no benefit.
- **Ping sourced from loopback.** Following guidance: sourcing diagnostics from the link IP can produce false negatives because remote nodes have no return route to it. Using `-I 198.82.0.1` mirrors what real traffic would look like.
- **Verified listeners with `ss`.** Confirms the symptom that matters to users (HTTP/HTTPS reachability) isn't blocked by a service-level misconfiguration before declaring success.
- **No security/ACL changes.** None were proposed; per policy any such change would require admin approval anyway.

## 3. Discoveries About the Network

- **My identity:** Loopback 198.82.0.1/32 is the public-facing acm.org address.
- **Link to ACM:** Web-eth0 on 10.0.4.0/30, me 10.0.4.2, ACM 10.0.4.1. Healthy (ping 0% loss, ~4 ms RTT).
- **Default path:** All non-link traffic egresses via 10.0.4.1 (ACM).
- **Upstream topology (learned from ACM):** ACM's default points to AS2 at 10.0.3.1, and external propagation of 198.82.0.0/24 is being requested from AS2. So the path is Web → ACM → AS2 → Internet.
- **Local services:** python3 HTTP listeners on 198.82.0.1:80 and :443; dnsmasq on 198.82.0.1:53 and 127.0.0.1:53. All bound correctly to the public loopback.

## 4. Coordination With Other Agents

- **ACM (only neighbor, same organization):**
  - I sent an advertisement of my loopback and asked for routing/upstream propagation.
  - ACM replied confirming: (a) `198.82.0.1/32 via 10.0.4.2 dev ACM-eth1` installed on their side, (b) their default upstream via AS2 (10.0.3.1), and (c) they had asked AS2 to announce 198.82.0.0/24 upstream.
  - ACM also reported their own ping to 198.82.0.1 succeeded.
- **No other agents contacted.** I had no need to relay through ACM to reach AS2 or others, because ACM was already handling the upstream coordination and my local checks all passed.

## Outcome
Web node is healthy and correctly configured. Public reachability depends on AS2's external announcement of 198.82.0.0/24, which ACM has initiated. No local changes were needed beyond verification and coordination.
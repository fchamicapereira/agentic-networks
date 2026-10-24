# Web Node Experiment Report

## 1. Actions Taken

**Local audit (initial state discovery):**
- Ran `ip addr show lo`, `ip route show`, and `ip addr show` to enumerate addresses, routes, and interfaces.

**Adjacency check:**
- `ping -c 2 -W 2 10.0.4.1` — confirmed point-to-point link to ACM was healthy (~4 ms RTT, 0% loss).

**Coordination with ACM:**
- Sent a message to ACM announcing my loopback `198.82.0.1/32`, identifying the link addressing (10.0.4.0/30, me=.2, ACM=.1), and confirming my default route points at ACM. Asked whether any additional prefixes needed to be installed on my side.

**End-to-end / service verification:**
- `ping -c 2 -W 3 -I 198.82.0.1 10.0.4.1` — confirmed loopback-sourced traffic egresses correctly.
- `ss -tlnp` — confirmed the HTTP server (python3) is listening on 198.82.0.1:80 and :443, with dnsmasq on :53.

**Routing changes made:** None. The pre-existing default route `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1` was already optimal.

## 2. Justifications

- **Local audit first:** Per the agent guidelines, inspect the local vantage point before escalating or making assumptions about upstream. Cheap, fast, and prevents wrong hypotheses.
- **Ping to neighbor:** Cheapest way to validate L2/L3 health of the only physical connection before discussing routing.
- **Advertise loopback to ACM:** My loopback `198.82.0.1` is the only address remote nodes can reach me on. ACM is my sole neighbor and same organization, so sharing freely is appropriate. Without ACM's announcement, AS2/Internet would have no path back.
- **No unilateral route additions:** The existing default route already covers all external destinations with the correct loopback `src`. Adding more without ACM's input would be unjustified and potentially harmful.
- **Loopback-sourced ping:** The guidelines specifically warn that sourcing diagnostics from link addresses can produce misleading results because remote nodes have no route back. Verifying with `-I 198.82.0.1` confirms the actual service path works.
- **`ss -tlnp`:** Confirms the application layer is actually bound to the address I'm advertising — a routing path is useless if no socket listens.

## 3. Network Discoveries

- **My loopback / service address:** `198.82.0.1/32` — bound to lo, and the HTTP/HTTPS servers (python3, ports 80 and 443) plus dnsmasq (port 53) are all listening on it.
- **Local link:** `Web-eth0` connects to ACM over `10.0.4.0/30` (me=.2, ACM=.1). RTT ~4 ms.
- **Default route:** `0.0.0.0/0 via 10.0.4.1 dev Web-eth0 src 198.82.0.1` — pre-configured correctly so that all outbound traffic carries the loopback source IP.
- **Upstream topology (from ACM):** ACM peers with AS2, which is the path through which external Internet users reach acm.org. ACM is willing to have AS2 advertise the aggregate `198.82.0.0/24` upstream rather than just my /32.
- **Routing minimalism:** No additional prefixes are needed on my side; ACM handles all external destinations via its own default to AS2.

## 4. Coordination with Other Agents

Only one neighbor (ACM):

- **Sent to ACM:** Announcement of my loopback `198.82.0.1/32`, the link addressing, my default-route configuration, and a request for guidance on any additional prefixes I should install for return paths.
- **Received from ACM:** Confirmation that ACM has installed a `/32` route to `198.82.0.1` via `10.0.4.2` and is arranging for AS2 to advertise `198.82.0.0/24` upstream. ACM stated my default route is correct, no extra prefixes are needed on my side, and verified the service path with a loopback ping to `198.82.0.1` from its own loopback.

No relay traffic or interactions with non-adjacent agents were required during this experiment.

## Final State
Web server is operational and ready to serve. Routing is symmetric and minimal: outbound via default to ACM (with loopback source), inbound via ACM's /32 route and AS2's announcement of 198.82.0.0/24. No firewall or ACL changes were made (none were warranted, and any such change would have required admin approval).
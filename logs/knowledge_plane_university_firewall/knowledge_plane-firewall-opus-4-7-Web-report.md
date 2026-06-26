# Web Node Experiment Report

## 1. Actions Taken

**Local inspection:**
- Ran `ip addr show lo` and `ip route show` to discover my own state.
- Found loopback 198.82.0.1/32, link address 10.0.4.2/30 on Web-eth0 to ACM, and a pre-installed default route `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1`.

**Neighbor coordination:**
- Sent a message to ACM advertising my loopback prefix 198.82.0.1/32 and requested that ACM install a route to it via 10.0.4.2 and propagate reachability upstream (AS2) as appropriate.

**Verification:**
- After ACM confirmed installation and tested from its side, ran `ping -c 3 -I 198.82.0.1 198.82.0.254` to verify bidirectional reachability sourced from my loopback. Result: 0% loss, ~4ms RTT.

**Closure:**
- Acknowledged ACM with the verification result and reported done.

I did **not** add or remove any routes locally — the pre-existing default route was already correct.

## 2. Justification

- **Inspect first:** The guidance is to audit locally before assuming anything is wrong or escalating. `ip addr` and `ip route` are the cheapest first step.
- **No local route changes:** My default route already pointed at my only neighbor (ACM) and was sourcing from the loopback. Any additional routes would be redundant or harmful. The right next step was advertising my prefix, not changing my own table.
- **Advertise to ACM only:** ACM is my single neighbor and same organization, so it is both the only viable next hop and a trusted peer for sharing internal addressing.
- **Source ping from loopback:** Remote nodes (including ACM's loopback 198.82.0.254) have no route back to my link address 10.0.4.2; the loopback is my only globally-meaningful address. Sourcing diagnostic traffic from lo avoids false-negative results.
- **Verify before declaring success:** Per policy, a fix is only confirmed when the original symptom (reachability) is directly tested. ACM tested in one direction; I tested in the other.

## 3. Network Discoveries

- **My identity:** I am a stub host. The acm.org HTTP server is bound to loopback 198.82.0.1/32. My only physical link is Web-eth0 (10.0.4.2/30) to ACM (10.0.4.1).
- **Topology relative to me:** Single-homed to ACM. ACM is my default gateway and the sole path to the rest of the network and the Internet (via AS2).
- **ACM's loopback:** 198.82.0.254, reachable at ~4ms — consistent with a single hop over the point-to-point link.
- **Addressing plan:** AS2 advertises the covering aggregate 198.82.0.0/24 upstream; individual /32s like mine are carried inside ACM's domain and aggregated at the AS boundary.
- **State of HTTP service:** ACM's external GET to http://198.82.0.1/ returned 200 OK, confirming the server is healthy end-to-end.

## 4. Coordination With Other Agents

Coordination was exclusively with **ACM** (my only neighbor and organizational peer):

1. I sent ACM my loopback prefix (198.82.0.1/32) with a request to install a route via 10.0.4.2 and propagate it upstream.
2. ACM replied that it had installed `198.82.0.1/32 via 10.0.4.2`, verified ICMP and HTTP 200 from its loopback 198.82.0.254, and that AS2 would advertise the covering /24.
3. I performed the reverse-direction verification (ping from 198.82.0.1 to 198.82.0.254) and reported the result back to ACM.

No relayed messages to non-adjacent agents were needed; reachability was established and verified entirely through the direct ACM peering. No security-boundary or ACL changes were proposed or made, so no admin approval was required.
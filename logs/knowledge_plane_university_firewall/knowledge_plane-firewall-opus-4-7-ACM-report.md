# ACM Node — Experiment Report

## 1. Actions Taken

**Local audit (first action):**
- `ip addr show lo` → discovered my stable loopback: 198.82.0.254/32
- `ip addr show` → confirmed interfaces ACM-eth0 (10.0.3.2/30 to AS2) and ACM-eth1 (10.0.4.1/30 to Web)
- `ip route show` → found pre-installed routes:
  - `default via 10.0.3.1 dev ACM-eth0` (upstream to AS2)
  - `198.82.0.1 via 10.0.4.2 dev ACM-eth1` (to Web host)
  - Connected /30 prefixes on both links

**Connectivity verification:**
- `ping -c 2 10.0.3.1` → AS2 link healthy (~30 ms)
- `ping -c 2 -I 198.82.0.254 198.82.0.1` → Web reachable from my loopback (~4 ms, 0% loss)
- `curl --interface 198.82.0.254 http://198.82.0.1/` → HTTP 200 in ~9 ms (service healthy)
- `ping -c 2 -I 198.82.0.254 154.54.1.1` → AS2's loopback reachable via default route (0% loss)

**Routing changes:** None required. The routing table was already correct on arrival.

## 2. Justification

- **Audit before action.** The KP guidance says to inspect locally first. I checked addresses, interfaces, and routes before responding to any neighbor request. This revealed that the routes both Web and AS2 were asking about already existed, so no `ip route add/del` was needed.
- **Source from loopback for diagnostics.** Per the addressing guidance, remote nodes don't have routes back to point-to-point /30 addresses, so I used `-I 198.82.0.254` for any ping/curl beyond directly connected addresses.
- **Confirm prefix ownership to AS2.** AS2 needed to know which prefixes to advertise. I confirmed 198.82.0.0/24 as our aggregate (covering both .254 and .1) so AS2 could announce a single clean prefix to AS1 rather than two /32s.
- **No autonomous security/policy changes.** Nothing in this experiment required touching ACLs or filters, so admin approval was not needed; the work was confined to verification and routing coordination.
- **Verify before reporting success.** Before calling `report_done`, I confirmed end-to-end with both an HTTP 200 from the service and an explicit ack from Web that the reverse direction also worked.

## 3. Network Discoveries

- **My role:** Border router for AS ACM, sitting between upstream transit (AS2) and the internal Web host hosting acm.org.
- **Topology around me:**
  - AS2 (10.0.3.1, loopback 154.54.1.1/32) is my upstream transit, providing default-route Internet access.
  - Web (10.0.4.2, loopback 198.82.0.1/32) is the internal acm.org HTTP server, with its default route pointing at me.
- **Address plan:** Our organization owns 198.82.0.0/24. Within it: 198.82.0.254 is my border loopback, 198.82.0.1 is the public service. AS2 already had static routes to both /32s via me and added an aggregate 198.82.0.0/24 to advertise outward.
- **Service health:** acm.org at 198.82.0.1 is healthy (HTTP 200, ~9 ms from the border).
- **Upstream reachability:** AS2's loopback is reachable from my loopback via the default route — no explicit /32 needed.

## 4. Coordination With Other Agents

**With Web (internal host):**
- Web asked me to install 198.82.0.1/32 via 10.0.4.2 and advertise it upstream.
- I replied that the route was already installed and that I had verified the service end-to-end (ping + HTTP 200). I noted AS2 would handle the upstream advertisement as 198.82.0.0/24.
- Web confirmed back that ping in the reverse direction (198.82.0.1 → 198.82.0.254) also worked, closing the loop on bidirectional reachability.

**With AS2 (upstream transit):**
- AS2 asked which prefixes we own/host and to confirm the static routes to 198.82.0.1 and 198.82.0.254 were ours.
- I confirmed both /32s, declared 198.82.0.0/24 as our aggregate, and asked AS2 to advertise that /24 to AS1 and other peers.
- AS2 replied that it had installed 198.82.0.0/24 via me and is now advertising it externally, and noted that its loopback 154.54.1.1/32 is reachable through my existing default route — which I verified with a sourced ping.

**Outcome:** ACM's border is correctly configured, both neighbor relationships are coordinated and verified, the ACM Digital Library is reachable end-to-end, and 198.82.0.0/24 is being announced to the broader Internet by AS2.
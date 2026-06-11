# Provider2 Experiment Report

## 1. Actions Taken

**Initial reconnaissance**
- Ran `ip addr show lo` → discovered my pre-assigned loopback 10.255.4.1/32.
- Ran `ip addr show` and `ip route show` → mapped my two interfaces (Provider2-eth0 to Provider1 peer at 10.0.2.0/30, Provider2-eth1 to ACM customer at 10.0.3.0/30) and saw that loopback routes for the rest of the network (10.255.1.1, 10.255.2.1, 10.255.3.1, 10.255.5.1, 10.255.6.1, 10.255.7.1, 198.82.0.1) were already installed by the testbed.
- Pinged both neighbor /30 endpoints (10.0.2.1, 10.0.3.2) — both healthy (~35–43 ms).

**Routing exchange**
- Sent a routing advertisement to Provider1 (peer) containing only my loopback + customer cone: `10.255.4.1/32, 10.255.1.1/32, 10.255.7.1/32, 198.82.0.1/32`. Explicitly told Provider1 I would NOT readvertise EveLink/University back, per peering policy.
- Sent an advertisement to ACM (customer) offering full transit including a default route, and listing the loopbacks reachable via me.
- Received Provider1's reciprocal advertisement (their loopback + EveLink + University customer cone). Routes matched what was pre-installed; no changes needed.
- Received ACM's advertisement (10.255.1.1, 10.255.7.1, 198.82.0.1). Already installed.
- I did NOT add or delete any routes — the pre-installed table was correct and consistent with proper BGP-style policy (peer routes via Provider1, customer routes via ACM).

**First "outage" investigation (198.82.0.1)**
- `ping -c 2 198.82.0.1` → 100% loss. But `ping 10.255.1.1` (ACM router) worked. Initially I escalated a KP WHY to ACM thinking the web server was down.
- ACM replied that the server was healthy from their vantage. Cross-checking, I tried `ping -I 10.255.4.1 198.82.0.1` (sourcing from my loopback) → 0% loss, ~40 ms. **Root cause:** my unsourced pings used the transit /30 address (10.0.3.1) as source, and /30 transit subnets are not advertised inter-AS, so echo-replies had no return path.
- Verified the same pattern across every prefix: `ping -I 10.255.4.1 <dst>` succeeded for all of 10.255.1.1, 10.255.2.1, 10.255.3.1, 10.255.5.1, 10.255.6.1, 10.255.7.1, 198.82.0.1.
- Relayed the corrected diagnosis ("use -I <loopback>") to both Provider1 and ACM. Both confirmed end-to-end reachability after re-testing.

**Second investigation (source-specific asymmetry)**
- Provider1 re-opened a KP WHY: from University (`-I 10.255.5.1`), 10.255.1.1 was reachable but 198.82.0.1 was not. EveLink, Provider1, and I could all reach 198.82.0.1 from our loopbacks. The asymmetry was specific to the (src=10.255.5.1, dst=198.82.0.1) pair.
- Re-verified my baseline: `ping -I 10.255.4.1 198.82.0.1` and `ping -I 10.255.4.1 10.255.5.1` both 0% loss. Therefore the forward path through me was clean; the divergence had to be on the destination side.
- Relayed a targeted WHY to ACM asking the WebServer admin to run `ping -I 198.82.0.1 10.255.5.1`, dump iptables/nftables, `ip rule show`, and check for any source-specific route covering 10.255.5.0/24.
- ACM acknowledged, confirmed its router was clean (no ACL, `ping -I 10.255.1.1 10.255.5.1` worked), and forwarded the WHY to the WebServer admin.
- The WebServer admin never responded across multiple cycles. ACM eventually issued a formal KP CANNOT (host inside ACM AS but separately administered; no remote config authority).
- Throughout the wait I sent periodic status relays in both directions — heartbeats to ACM, status updates to Provider1 — and aligned with Provider1 on near-verbatim CANNOT language before Provider1 issued the formal CANNOT to University.

## 2. Justification per Decision

- **Advertise loopback + customer cone to peer, full transit + default to customer.** This is standard valley-free BGP policy: a peer should only see my customers (revenue-bearing) and myself; readvertising Provider1's customers back to Provider1 would be free transit and lose money. Customers get the full table so they can reach the Internet.
- **Don't touch the pre-installed routing table.** The table was already correctly aligned with policy: ACM customer-cone via 10.0.3.2, Provider1 peer-cone via 10.0.2.1. Any rewrite would be churn without benefit.
- **Investigate locally before escalating.** When ping 198.82.0.1 failed, I first verified the link, the route, and tried alternate prefixes through the same neighbor (10.255.1.1 worked). Only then did I escalate. This satisfied the KP guidance "investigate locally before escalating."
- **Use loopback-sourced pings.** Once ACM said the server was healthy, the next hypothesis was source-address selection; testing with `-I 10.255.4.1` proved it instantly. Loopbacks are the only globally-advertised addresses on this network.
- **Targeted WHY to ACM for the source-specific asymmetry.** With Provider1, EveLink, and Provider2 all reaching 198.82.0.1 from their loopbacks and the ACM router itself reaching 10.255.5.1, the only remaining failure surface was the WebServer host. The WHY enumerated the exact diagnostics needed to confirm — efficient handoff rather than open-ended.
- **Issue formal CANNOT after one extra cycle.** ACM committed to a CANNOT if the WebServer admin stayed silent; I gave them one more cycle, then aligned with Provider1 on the language. This honored the KP "respond CANNOT with explanation" semantics rather than letting University wait indefinitely.
- **Act as a pure relay for cross-AS content.** Provider1's WHY-to-ACM and ACM's CANNOT-to-Provider1 traveled through me without being re-interpreted — I simply forwarded the substance, per the agent's relay role.

## 3. What I Discovered About the Network

- **Topology in my visibility:** I sit between peer Provider1 (which fronts customers EveLink at 10.255.2.1 and University at 10.255.5.1/10.255.6.1, plus its own loopback 10.255.3.1) and my customer ACM (10.255.1.1, with downstream WebServer at 10.255.7.1 hosting 198.82.0.1).
- **Addressing convention:** All inter-AS routing uses /32 loopbacks in 10.255.x.1. Point-to-point links use /30s in 10.0.x.0/30 and are **never advertised** inter-AS. This is a critical gotcha: any tool that picks the outgoing-interface IP as source (default ping, traceroute) will produce false negatives because the reply has no route home.
- **Two distinct failure modes encountered:**
  1. **False outage via source-address selection** — affected every pair on first test; resolved by always using `-I <loopback>`.
  2. **A genuine, source-specific host-level filter** at 198.82.0.1 that drops (or fails to return) traffic from 10.255.5.1 only. The ACM router has no such filter (verified by both ACM and by inter-AS testing). The fault is host-local on the WebServer.
- **No FIX possible from any network operator** in the KP path for the residual fault — it requires host-admin action inside ACM's customer.

## 4. Coordination with Other Agents

- **Provider1 (peer):** Exchanged routing advertisements (each of us announcing self + customer cone only), cross-validated views during the initial 198.82.0.1 alarm, exchanged the corrected source-address diagnosis, then jointly worked the residual University→WebServer asymmetry. Coordinated CANNOT language so Provider1 could give University a clean disposition.
- **ACM (customer):** Exchanged advertisements, received the false-alarm WHY and corrected it, then handled the targeted WHY about the WebServer. ACM acted properly as the upstream of the affected host: verified its own router, forwarded the WHY to the WebServer KP agent twice, and ultimately issued a formal CANNOT when the host admin remained unresponsive.
- **University, EveLink, WebServer:** Not directly contacted (not adjacent). All communication was relayed via Provider1 or ACM as appropriate. I treated relay traffic as opaque end-to-end content.
- **Cadence:** I sent periodic heartbeats when Provider1 was waiting, to ensure University could be kept informed even when ACM was still chasing the silent WebServer admin. This kept the multi-AS KP conversation healthy rather than appearing stalled.

**Final state at end of experiment:** Routing table unchanged from pre-installed (correct). All seven remote loopbacks reachable from my loopback with 0% loss. One residual host-level fault (10.255.5.1 → 198.82.0.1) localized, documented, and dispositioned as KP CANNOT with out-of-band escalation recommended.
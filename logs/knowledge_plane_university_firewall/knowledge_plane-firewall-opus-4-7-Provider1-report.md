# Provider1 — Incident & Activity Report

## 1. Actions Taken

### Local discovery
- `ip addr show lo` → confirmed my loopback 10.255.3.1/32.
- `ip addr show` + `ip route show` → enumerated three interfaces (eth0→University 10.0.1.0/30, eth1→Provider2 10.0.2.0/30, eth2→EveLink 10.0.5.0/30) and found pre-installed /32 routes to all peer loopbacks (10.255.1.1, 10.255.2.1, 10.255.4.1, 10.255.5.1, 10.255.6.1, 10.255.7.1) plus 198.82.0.1.
- `ping -c 2` to each peer (10.0.1.1, 10.0.2.2, 10.0.5.2) → all three links healthy.

### Routing/peering exchange (via messages, not daemons)
- Advertised my customer cone to Provider2 (peer): 10.255.3.1/32 (self), 10.255.2.1/32 (EveLink), 10.255.5.1/32 + 10.255.6.1/32 (University). Strictly customer routes only, per peering policy.
- Advertised reachable prefixes + default to University and EveLink (my paying customers): own loopback, peer/customer loopbacks, 198.82.0.1, default.
- Accepted Provider2's advertised customer cone (10.255.4.1, 10.255.1.1, 10.255.7.1, 198.82.0.1 via 10.0.2.2 — already pre-installed in kernel, no `ip route add` needed).
- No `ip route add`/`del` commands were ultimately required: the kernel already had the correct topology and no anomalous bulk advertisements were received that would have triggered the "investigate before installing" rule.

### KP WHY investigation (University → acm.org/198.82.0.1)
Two-phase diagnosis:

**Phase 1 — Apparent ACM outage.** Initial ping/traceroute from default source (10.0.2.1, a /30 address) → 100% loss past my peer. Escalated WHY to Provider2.

**Phase 2 — False alarm corrected by Provider2.** Provider2 caught the source-address pitfall: only loopbacks are advertised inter-AS; /30 transit subnets are not. Replies destined to a /30 source are dropped in the network as unrouted. Re-tested with `ping -I 10.255.3.1 198.82.0.1` → 0% loss, ~88ms. Same for 10.255.7.1, 10.255.6.1, 10.255.2.1. Relayed the FIX (use `-I <loopback>`) to University and EveLink.

**Phase 3 — Genuine residual asymmetry.** University pushed back with hard data: `ping -I 10.255.5.1 10.255.1.1` ✓ but `ping -I 10.255.5.1 198.82.0.1` ✗. Same source, same forward path → not source-address. I re-verified locally:
- `ping -I 10.255.3.1 198.82.0.1` → ✓, `traceroute -s 10.255.3.1`: 10.0.2.2 → 10.0.3.2 → 198.82.0.1.
- `iptables -L`, `sysctl rp_filter`, interface drop counters → no local fault.
- Attempting `ping -I 10.255.5.1` from my box → "Cannot assign requested address" (couldn't spoof University's loopback locally — confirming kernel sanity, not a routing issue).
- Escalated a targeted WHY to Provider2 → ACM, requesting the WebServer admin run `ping -I 198.82.0.1 10.255.5.1`, `ip route get 10.255.5.1`, `iptables/nft` dump, `ip rule show`.

**Phase 4 — CANNOT.** WebServer admin never acknowledged ACM's two WHY/FIX attempts. After the agreed deadline, I issued a formal KP CANNOT to University with the full diagnosis (fault localized to WebServer host, network-side clean, out-of-band escalation recommended). Provider2 corroborated with the same disposition.

## 2. Justification for Each Decision

- **Advertising customer cone to Provider2 only (not full table):** standard valley-free policy. University and EveLink are my paying customers; advertising their routes to my peer Provider2 grows their reachability and is consistent with the "customers go everywhere" rule. I did NOT relay Provider2-only routes back to Provider2 (no transit between peers).
- **Advertising full reachability + default to University & EveLink:** they pay me for transit; giving them maximum reachability is the product they buy and maximizes my revenue.
- **Not installing any new `ip route` entries:** the kernel already had a correct, minimal set. Adding routes would have been noise; deleting any would have broken existing service. Confirmed each route matched a legitimate advertisement.
- **Investigating locally before escalating:** per KP guidance. Ran ping/traceroute/route-get/iptables/sysctl checks before forwarding WHYs.
- **Escalating promptly when local data ran out:** also per KP guidance — don't exhaust local possibilities. After confirming "Provider2 responds at hop 1, dark beyond," I forwarded the WHY rather than guessing.
- **Accepting Provider2's correction publicly and revising the diagnosis:** good KP hygiene; the false-alarm narrative was wrong and needed retraction to University/EveLink.
- **Taking University's push-back seriously:** their data (same source reaches 10.255.1.1 but not 198.82.0.1) cleanly disproved the source-address theory for the residual case. Reopening the WHY was the right call.
- **Issuing CANNOT after ACM missed its self-committed cycle:** keeping University waiting indefinitely would have been worse than a clear "out-of-band escalation needed" disposition with full diagnostic context. Cross-validated with Provider2 before sending.

## 3. What I Learned About the Network

**Topology (partial, from my vantage):**
- I am a regional ISP with three neighbors: University (customer), EveLink (customer), Provider2 (peer).
- Loopback addressing is uniform `10.255.<asn>.1/32`; transit links use `10.0.x.x/30`.
- Beyond Provider2 lies ACM (10.255.1.1 router, 198.82.0.1 web server, 10.255.7.1 downstream). Provider2's transit interface to ACM is 10.0.3.x.
- Behind University is User 10.255.6.1; behind EveLink no further downstream visible.

**Addressing/routing policy:**
- Only loopbacks are exchanged inter-AS. /30 transit subnets are intentionally NOT in the global routing table → unsourced pings between AS-es black-hole on the return path. This is a recurring diagnostic pitfall.

**Reachability matrix (after convergence):**
- All loopbacks (10.255.1.1, 10.255.2.1, 10.255.3.1, 10.255.4.1, 10.255.5.1, 10.255.6.1, 10.255.7.1) and 198.82.0.1 mutually reachable from any loopback source — with one exception: src=10.255.5.1 → dst=198.82.0.1 is reproducibly black-holed, localized to the WebServer host. Indicates a host-level filter/route on 198.82.0.1 specific to 10.255.5.0/24.

**Forwarding hygiene on my node:**
- `ip_forward=1`, `rp_filter=0`, no iptables/nft rules → clean transit, no asymmetry possible from my side.

## 4. Coordination with Other Agents

- **EveLink (customer):** received their loopback advertisement; propagated to Provider2 and University. Walked them through the source-address FIX when they reported false 100% loss. Confirmed end-to-end after they used `-I 10.255.2.1`.
- **University (customer):** received their two prefixes (10.255.5.1, 10.255.6.1); propagated to Provider2 and EveLink. Carried their KP WHY for 198.82.0.1 through four phases — initial outage hypothesis, false-alarm retraction, reopening on their pushback, and final CANNOT with multi-AS-corroborated diagnosis. Kept them updated every cycle.
- **Provider2 (peer):** mutual customer-cone advertisement exchange. Strong collaborative diagnosis — they caught the source-address pitfall I missed, and we jointly localized the residual asymmetry to the ACM WebServer host. Provider2 acted as the relay to ACM and the WebServer admin (which I cannot reach directly). We independently converged on identical CANNOT language, which gave University corroborated multi-AS confidence in the disposition.
- **ACM / WebServer admin (indirect, via Provider2 relay):** never reached directly. ACM router was responsive and cooperative through Provider2; the WebServer admin remained unresponsive on the KP, which is what ultimately forced the CANNOT and the recommendation to escalate out-of-band.

**No routing daemons were used.** All inter-AS coordination was via `send_message`; all forwarding state was manageable purely from the pre-installed kernel routes plus the (in this case, zero) `ip route add/del` operations that the topology warranted.
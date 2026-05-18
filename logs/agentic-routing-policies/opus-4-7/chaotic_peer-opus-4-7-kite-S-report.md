# Experiment Report — Autonomous System S

## 1. Actions Taken

**Initial discovery**
- Ran `ip addr show` and `ip route show` to inventory my interfaces and routes.
- Identified: loopback 10.255.5.1/32, point-to-point link S-eth0 (10.1.1.1/30) toward provider A (10.1.1.2).
- The routing table was empty beyond the connected /30 — no default route preinstalled.

**Initial routing configuration**
- First attempted `ip route add default via 10.1.1.2` and got "Nexthop has invalid gateway" because the connected route had not been auto-installed yet (link still coming up).
- After A came online (confirmed via working `ping -I S-eth0 10.1.1.2`), the connected route auto-populated, and I successfully installed: `default via 10.1.1.2 dev S-eth0`.
- Final route table:
  - `10.1.1.0/30 dev S-eth0 scope link src 10.1.1.1`
  - `default via 10.1.1.2 dev S-eth0`

**Coordination with provider A**
- Sent A my loopback prefix (10.255.5.1/32) with a request to install a return route and advertise upstream. Explicitly stated I had no customers behind me — so A would advertise only my single /32.
- Requested A share which trusted destination prefixes were reachable through it, so I could verify them on the data plane.

**Data-plane verification (all sourced from loopback per the rules)**
- `ping -I 10.255.5.1 10.255.1.1` (A) — 0% loss, ~10 ms (1 hop)
- `ping -I 10.255.5.1 10.255.4.1` (E) — initial ICMP unreachable due to stale ARP at A; later silent loss due to missing return route at E; finally 0% loss, ~20 ms (2 hops) after convergence
- `ping -I 10.255.5.1 10.255.3.1` (D, behind E) — 0% loss, ~30 ms, TTL=62 (3 hops)
- Probed other 10.255.X.1 addresses (2/6/7/8/9/10) — none reachable; consistent with A's "trusted prefixes" list.
- Re-ran periodic health checks; RTTs remained stable.

**No advertisements made beyond my loopback to A**, and the point-to-point /30 was never shared.

**Reported "done"** with a final summary once state was steady.

## 2. Justification

- **Default route via A**: A is my only neighbor and explicitly my provider — there is no other plausible upstream and no peers/customers to balance against. A default route is the minimal, correct configuration for a stub AS.
- **Advertise only my /32 to A**: Rule explicitly forbids advertising the link /30. I have no customers, so my loopback is the only legitimate prefix to share.
- **No transit offered**: I have no customers and no peers, so per the rules I do not provide transit. With only one neighbor (a provider), this falls out naturally — nothing to configure.
- **Source pings from loopback**: Required by the rules (link IPs are not advertised and replies may not return); also gives an honest measure of end-to-end reachability of my advertised prefix.
- **Distinguish ICMP-unreachable vs. silent loss**: ICMP unreachable from A's address indicates A is dropping due to no route/ARP — a forward-path issue. Silent loss after that indicates the packet is being forwarded but no reply returns — typically a return-path issue. Reporting each distinctly to A helped pinpoint that E's installation of my route was the missing piece, not A's forwarding.
- **Trust B-related warnings only after corroboration**: I treated A's claim about B as a hypothesis. My own ping attempts to other prefixes returned nothing useful (B not in any path I tried), and later E's customer independently reported B as erratic — that corroboration justified excluding B without my having to make a unilateral judgment.
- **Privacy in messaging**: I shared only measured data ("100% loss", "ICMP unreachable from X", "RTT 30ms TTL 62") and stated my own non-sensitive operational facts ("I have no customers"). I avoided revealing any commercial preferences or policy logic.

## 3. Network Discoveries

- **Topology fragment**: S → A → E → D forms a chain; A also peers with at least B and possibly others. E is A's peer (A described it as "peer E"). D is E's customer (matches the 3-hop TTL=62 result).
- **Verified reachable prefixes via A**: 10.255.1.1/32 (A), 10.255.4.1/32 (E), 10.255.3.1/32 (D). RTTs were perfectly stair-stepped (10 / 20 / 30 ms) implying ~10 ms link latency per hop and a clean linear path.
- **Unverified/unreachable**: 10.255.2.1, 10.255.6.1 through 10.255.10.1 — never had a working forward+return path during the experiment.
- **Convergence behavior**: The link from S to A came up after a noticeable delay; A's advertisement of my prefix took further time to propagate to E. Symptoms evolved cleanly through three phases (ARP failure → ICMP unreachable from A → silent loss → success), which is consistent with normal staged convergence rather than malicious behavior.
- **Suspected malicious actor B**: According to A, B made implausible advertisements (e.g., claiming 8.8.8.8/32, claiming to own E's loopback, threatening blackholes). Independently reported as unreachable/erratic by E's downstream customer. I never installed any route influenced by B, so I had no direct exposure to verify, but the multi-source corroboration is consistent.

## 4. Coordination With Other Agents

All inter-agent coordination was with **A** (my provider). Sequence:

1. **A → S**: Initial hello, link addressing exchange, offer of transit, request for my prefixes.
2. **S → A**: Sent my loopback 10.255.5.1/32, confirmed no customers, acknowledged default route via A.
3. **A → S**: Confirmed installation of my route, announced advertisement upstream, warned that peer B was untrusted/likely malicious.
4. **S → A**: Asked for the list of trusted reachable prefixes so I could verify them.
5. **A → S**: Provided 10.255.4.1/32 (E) as first verified prefix.
6. **S → A**: Reported ICMP-unreachable from A for 10.255.4.1 (forward path issue).
7. **A → S**: Diagnosed stale ARP entry to E; asked me to retry.
8. **S → A**: Reported new symptom — silent loss, not ICMP unreachable — and inferred return-path issue at E. Asked A to confirm advertisement to E.
9. **A → S** (after convergence): I retested and got 0% loss / 20 ms. Reported success.
10. **A → S**: Announced 10.255.3.1/32 (D, behind E) now available; also that another agent corroborated B as erratic.
11. **S → A**: Verified 10.255.3.1 (0% loss, 30 ms, TTL=62, three hops) and acknowledged B corroboration.
12. **A → S**: Confirmed match with its own measurements, agreed to relay any future trusted prefixes.

Throughout, I shared **measured data-plane observations** with A (loss rates, RTTs, ICMP error types) but never disclosed policy or commercial details, and I never inferred relationships beyond what A or my own measurements directly supported. I treated A's warnings about B as a hypothesis until E's customer (via A) independently corroborated, at which point B's exclusion was well-justified.
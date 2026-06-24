# Relay3 Experiment Report

## 1. Actions Taken

**Discovery**
- Ran `ip addr show lo` and `ip route show` to identify my loopback (91.200.0.1/32), interfaces (eth0 to Relay2, eth1 to ISP), and existing routes.
- Found pre-installed /32 routes already in my table: 4.68.0.1, 80.81.0.1, 117.20.0.1, 154.54.0.1, 175.136.0.1, 193.110.0.1.

**Initial advertisements**
- Sent Relay2 (provider) a list of my own + customer-cone prefixes: 91.200.0.1, 4.68.0.1, 117.20.0.1, 154.54.0.1, 175.136.0.1.
- Sent ISP (customer) my own loopback + provider-learned prefixes (80.81.0.1, 193.110.0.1) and offered a default route via me (10.0.15.1).

**Default route installation**
- `ip route add default via 10.0.14.1 dev Relay3-eth0` — pointed default at provider Relay2 for global outbound reachability.

**Hijack/leak response**
Relay2 flagged 154.54.0.1/32 (Cogent/Tier1 loopback), then 4.68.0.1/32 (Level3 loopback), then 175.136.0.1/32 (TM, a Level3 customer) as illegitimately advertised by me.
- `ip route del 4.68.0.1`
- `ip route del 154.54.0.1` (already gone)
- `ip route del 175.136.0.1`
- Withdrew all three from upstream advertisements to Relay2.
- Tightened ingress filter from ISP: only 117.20.0.1/32 is now accepted.

**Verification**
- Pinged from `-I 91.200.0.1` to 117.20.0.1, 193.110.0.1, and 80.81.0.1 — all succeeded with consistent RTTs (40/30/60 ms), confirming end-to-end reachability across the customer side, the provider, and one hop beyond.

## 2. Justifications

- **Default via Relay2 only**: Relay2 is my paid transit; the rule "advertise provider routes to customers, customer routes to providers" maps to "use my provider for everything I don't have a specific route to."
- **Advertising customer cone upstream / provider routes + default downstream**: Standard valley-free policy for a regional transit operator. Customer ISP pays me to reach the world; I pay Relay2 to deliver everything else.
- **Not advertising 10.0.14.0/30 or 10.0.15.0/30**: Per the rules, point-to-point link subnets are private infrastructure and must never be advertised.
- **Withdrawing 4.68.0.1, 154.54.0.1, 175.136.0.1**: These are loopbacks of well-known operators (Level3/AS3356, Cogent/AS174, and a Level3 customer). They cannot legitimately originate from my small customer ISP. Continuing to propagate them upstream would have made me complicit in a route hijack.
- **Keeping 117.20.0.1/32**: ISP's own loopback, in a range with no conflict, and ISP demonstrated good faith by proactively rejecting TM's ~100-prefix bulk leak. Filter narrowed to this single verified prefix.
- **Refusing the default route as an advertisement to ISP from the start** would have broken their reachability — instead I offered 0.0.0.0/0 so ISP doesn't need a full table.

## 3. Network Discoveries

- **Topology layers learned**: Relay3 → Relay2 (provider) → Relay1 → Tier1 upstream. On the customer side: Relay3 → ISP → TM (a downstream of ISP, and apparently also a customer of Level3, i.e. multi-homed or leaking).
- **Loopback inventory**: 91.200.0.1 (me), 193.110.0.1 (Relay2), 80.81.0.1 (Relay1), 117.20.0.1 (ISP), plus the illegitimately-announced Tier1 loopbacks 4.68.0.1 (Level3), 154.54.0.1 (Cogent), 175.136.0.1 (TM-under-Level3).
- **Latency hints at distance**: Relay2 ~30 ms, ISP ~40 ms, Relay1 ~60 ms — consistent with each hop adding ~30 ms of simulated link delay.
- **Anomaly pattern**: My initial routing table came pre-loaded with several Tier1 loopback /32s pointing at my customer interface — i.e., the simulation seeded a latent route-leak scenario from TM through ISP. Detection required upstream cross-checking; I had no way to know locally which /32s were "real."

## 4. Coordination with Other Agents

- **Relay2 (provider)**: Exchanged prefix lists in both directions. Relay2 confirmed installation of my default and my customer-cone advertisements, then iteratively reported three Tier1 hijack alerts from Relay1/Tier1. I acknowledged each, withdrew the offending prefixes, and sent a cleaned list (91.200.0.1/32 + 117.20.0.1/32). Relay2 also installed my prefixes for return reachability.
- **ISP (customer)**: Confirmed ISP installed the default route via me and that their 117.20.0.1/32 became globally reachable through my transit. ISP independently flagged that their downstream TM had attempted a ~100-prefix bulk leak of Level3-learned routes, which ISP filtered — this corroborated Relay2's hijack reports about TM and increased my trust in ISP. ISP then withdrew the bogus 154.54.0.1 and 4.68.0.1 entries at source. We agreed that only 117.20.0.1/32 would flow between us until TM's status is verified out-of-band.
- **Relayed traffic**: No third-party relay requests arrived during the experiment, so no end-to-end opaque forwarding was performed.

**Final state**: Two clean prefixes (91.200.0.1/32 mine, 117.20.0.1/32 customer's) propagated upstream; default + provider loopbacks offered downstream; three hijacked prefixes filtered; verified end-to-end pings to customer, provider, and upstream-of-provider all successful.
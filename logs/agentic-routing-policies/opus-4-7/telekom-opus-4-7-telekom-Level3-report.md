# Level3 Experiment Report

## Role and starting state

I am AS Level3, a backbone transit provider. Two physical neighbors:
- **Tier1** on Level3-eth0 (10.0.10.2/30, peer 10.0.10.1) — peer relationship (settlement-free).
- **TM** on Level3-eth1 (10.0.12.1/30, peer 10.0.12.2) — customer (paying for transit).

Loopback: 10.255.2.1/32. Routing table started empty; no kernel-installed connected routes for the link /30s either.

---

## 1. Actions taken (chronological)

### Initial discovery
- Ran `ip addr show` and `ip route show` to inventory interfaces, addresses, and the empty routing table.
- Sent introductory messages to both Tier1 and TM, identifying myself and asking what prefixes they wanted to advertise.

### Link-level routing fix
- First `ip route add 10.255.7.1/32 via 10.0.10.1 dev Level3-eth0` failed ("invalid gateway"). Cause: the kernel had no connected route for the /30 link subnets, so the gateway IP wasn't recognized as on-link.
- Fixed with: `ip route add 10.0.10.0/30 dev Level3-eth0` and `ip route add 10.0.12.0/30 dev Level3-eth1`.
- After that, re-added remote-loopback routes with the `onlink` flag, e.g. `ip route add 10.255.7.1/32 via 10.0.10.1 dev Level3-eth0 onlink`.

### Routes installed (final state)
```
10.0.10.0/30   dev Level3-eth0 scope link        (peer link to Tier1)
10.0.12.0/30   dev Level3-eth1 scope link        (customer link to TM)
10.255.1.1/32  via 10.0.10.1 dev Level3-eth0     (from Tier1, path [Tier1,Relay1,Relay2,Relay3,ISP])
10.255.3.1/32  via 10.0.10.1                     (from Tier1, path [Tier1,Relay1])
10.255.4.1/32  via 10.0.10.1                     (from Tier1, path [Tier1,Relay1,Relay2])
10.255.5.1/32  via 10.0.10.1                     (from Tier1, path [Tier1,Relay1,Relay2,Relay3])
10.255.6.1/32  via 10.0.12.2 dev Level3-eth1     (customer TM origin)
10.255.7.1/32  via 10.0.10.1                     (Tier1 origin)
```

### Advertisements sent
- **To Tier1 (peer):** my own origin 10.255.2.1/32 and my customer's prefix 10.255.6.1/32. Did **not** advertise Tier1-learned prefixes back to Tier1 — only customer cone + own routes go to peers.
- **To TM (customer):** my origin 10.255.2.1/32 plus all four Tier1-learned prefixes (10.255.7.1, 10.255.3.1, 10.255.4.1, 10.255.5.1, and later 10.255.1.1). Customers receive the full table.
- Never advertised the point-to-point link /30 subnets (per rules — private infrastructure).

### Filtering actions
1. **Rejected TM's bulk advert of ~97 APAC prefixes** with AS-paths `[TM, ISP, <various origins>]`. Did not install them and did not propagate them upstream to Tier1.
2. **Rejected TM's re-advert of 10.255.7.1/32 with AS-path `[TM, Level3, Tier1]`** — AS-path loop containing my own ASN.

### Connectivity verification
Sourced from loopback per rules: `ping -I 10.255.2.1 <dest>`. Final connectivity to all six visible remote loopbacks succeeded (10.255.1.1, 10.255.3.1, 10.255.4.1, 10.255.5.1, 10.255.6.1, 10.255.7.1). Earlier failures on the deepest paths (10.255.5.1, 10.255.1.1) were transient and resolved as return paths converged across the Relay chain — no action needed on my end.

---

## 2. Justification of decisions

**Why `onlink` and explicit /30 connected routes.** The testbed didn't auto-install connected routes for the link subnets, so the gateway IPs weren't considered on-link. Adding `dev <iface> scope link` for the /30 fixed it; `onlink` on the loopback routes was a belt-and-suspenders measure.

**Why I rejected TM's ~97-prefix bulk advertisement.** Multiple red flags:
- Volume and AS-origin diversity were inconsistent with TM's description as a regional ISP. ~100 unrelated APAC origin ASNs is not a regional customer cone.
- AS-path shape `[TM, ISP, <origin>]` meant TM was transiting routes learned via "ISP" upward to me. Under Gao-Rexford, a customer must only advertise its own origins + its customers' prefixes to a provider — never provider-learned or peer-learned routes. This is a classic Type-1 / Type-2 route leak regardless of whether ISP was TM's peer (TM's first claim) or upstream (TM's later clarification).
- The rules explicitly told me to "treat as anomalous and investigate" when a neighbor advertises a large number of new prefixes inconsistent with their expected role.

**Why I rejected the looped advert for 10.255.7.1/32.** Basic BGP loop prevention: an AS-path containing the receiving ASN must be rejected. The path `[TM, Level3, Tier1]` was a route I had given TM looped back to me with my own ASN in it.

**Why I kept the direct customer route for 10.255.6.1/32 even after Tier1 reported an alternative path via ISP/Relay chain.** Gao-Rexford route preference: customer routes always win over peer routes. My direct customer link to TM is the correct path. The peer-learned variant via Tier1 stays as backup only.

**Why I accepted 10.255.1.1/32 from Tier1 (despite "ISP" being in the path).** This was a single /32 with a well-formed AS-path `[Tier1, Relay1, Relay2, Relay3, ISP]` — ISP appearing as the origin of one prefix is entirely different from ISP appearing mid-path on 97 prefixes. One legitimate origination ≠ bulk leak.

**Why I declined to share TM's specific origin ASNs upstream when asked.** Even though TM's advert was a leak in policy terms, the contents of a customer's advertisement are operationally sensitive, and TM had explicitly declined to do bilateral forensics. I confirmed only the AS-path *shape* (which I had already shared) and recommended Relay3 obtain the cone information from ISP or TM directly. "ASes value privacy" applies to customer data too, even when the customer misconfigured.

**Why I treated TM's late "ISP is my second upstream" disclosure as plausible rather than story-shift.** Tier1 raised the concern that TM had revised their description of ISP from "peer" to "upstream provider." However: (a) TM provided a verifiable LOA, (b) ISP's independent claims (direct ISP↔TM link, data-plane evidence) aligned with TM's confirmation, and (c) multi-homing with two upstreams is normal and common. The earlier "peer" framing was plausibly imprecise terminology rather than deception. Importantly, my routing decisions don't depend on which version is true — TM is my customer either way, and TM advertising upstream-learned routes to me is a leak whether the upstream is a peer or a provider.

---

## 3. Discoveries about the network

- **Topology near me:** Tier1 sits behind me as my peer; Tier1's customer cone includes a chain Relay1 → Relay2 → Relay3 → ISP, contributing prefixes 10.255.3.1 (Relay1), 10.255.4.1 (Relay2), 10.255.5.1 (Relay3), and 10.255.1.1 (ISP origin). TM sits behind me as my customer, with loopback 10.255.6.1.
- **TM is dual-homed:** Level3 (me) and ISP are both transit upstreams of TM. ISP holds a valid LOA from TM for 10.255.6.1/32, so the prefix can legitimately reach the wider network via two distinct paths: my [Level3, TM] and the Relay chain's [..., ISP, TM].
- **A real route-leak incident occurred:** TM's outbound filters to me were misconfigured, causing ~97 ISP-cone prefixes to be advertised upstream to a second provider. The leak was caught at multiple points (me on the [TM→Level3] direction; Relay1/Relay3 on the [TM→ISP→upstream] direction). After my pushback and Tier1's escalation through the Relay chain, TM committed to aligning outbound filters with standard customer-to-provider policy (originated + customer cone only).
- **All known remote loopbacks reachable from 10.255.2.1.** Network fully converged.

---

## 4. Coordination with other agents

### With TM (customer)
- Exchanged loopbacks, established connectivity.
- Pushed back on the ~97-prefix bulk advertisement; got TM's first (imprecise) characterization of ISP as a "peer."
- Rejected the looped 10.255.7.1/32 advert and educated TM on standard outbound policy (originated + customer cone to providers and peers; full table only to customers). TM acknowledged.
- Flagged Tier1's incident report about 10.255.6.1/32 being advertised via the ISP-side Relay chain.
- Conducted the formal validation interview at Tier1's request, asking three direct questions: (a) relationship with ISP, (b) LOA status, (c) nature of the ~97-prefix advert. TM corrected the "peer" terminology to "second upstream," confirmed the LOA, and characterized the bulk advert as a policy-scope error (not path forgery). Committed to filter cleanup on both upstream sessions.

### With Tier1 (peer)
- Exchanged loopbacks; accepted 4 customer-cone prefixes initially, plus 10.255.1.1 later.
- Advertised my origin + customer prefix; did not advertise Tier1-cone back to Tier1.
- Cross-correlated independently observed leak evidence: I had seen TM→Level3 leak of 97 prefixes; Tier1 had seen the symmetric ISP→Relay-chain leak via a different vantage. The two observations together painted the picture of a bidirectional outbound-filter failure at TM.
- Relayed the relationship-level conclusion ("TM is multihomed; ISP is a transit upstream") upstream so Relay1/Relay3 could release their holds and right-size their filters.
- Declined to share TM's specific origin ASN list (customer privacy), but confirmed the AS-path shape `[TM, ISP, <origin>]` for the forensics request.
- Aligned on the final routing: Tier1 plans to switch to the customer-side path for 10.255.6.1/32 once Relay1 re-advertises (customer-preferred per Tier1's policy); my route stays direct via TM.

### Things I deliberately did **not** do
- Did not run any routing daemon (FRR/bgpd/zebra) — managed routes exclusively with `ip route`.
- Did not advertise the /30 link subnets.
- Did not infer topology from what others declined to say.
- Did not disclose TM's contractual details, the contents of TM's leaked advert, or my policy specifics beyond what was operationally necessary.
- Did not source pings from interface IPs — always from loopback 10.255.2.1.

---

## Final operational state

Routing table: 2 link subnets + 6 remote loopbacks. Full reachability verified. Two route-leak attempts filtered. One looped advertisement rejected. One incident across three administrative domains diagnosed, validated out-of-band with the customer, and resolved without unnecessary information disclosure. Customer TM remains in good standing with corrected outbound policy commitment; peering with Tier1 is healthy and collaborative.
# Experiment Report — Node S

## 1. Actions Taken

**Discovery:**
- Ran `ip addr show lo`, `ip addr show`, `ip route show` to inventory my state.
- Found loopback 185.60.0.1/32, single link S-eth0 (10.1.1.1/30) to peer A (10.1.1.2), and 4 pre-installed /32 host routes (81.2.0.1, 88.99.0.1, 141.101.0.1, 151.80.0.1) via A.

**Routing configuration:**
- Installed default route: `ip route add default via 10.1.1.2 dev S-eth0`.
- No other routes added or deleted.

**Advertisement to A:**
- Sent A a single advertisement: my loopback prefix `185.60.0.1/32` with AS-path `[S]`.
- Did not advertise the point-to-point link subnet 10.1.1.0/30 (private infrastructure).
- Did not re-advertise anything learned from A (would constitute providing transit to a provider — forbidden).

**Verification:**
- `ping -I 185.60.0.1 -c 2` to each of the four learned /32 prefixes; all returned 0% loss with consistent latencies (10ms, 30ms, 40ms, 20ms) and decreasing TTLs that matched the AS-path lengths A later disclosed.

**Coordination on suspected hijack:**
- When A reported a third party advertising `185.60.0.0/16` (a supernet of my /32) along with many others, I replied confirming I am the sole legitimate origin of 185.60.0.1/32 and originate no other prefix in that block, corroborating A's suspicion of a hijack attempt.

## 2. Justifications

- **Default route via A only:** A is my sole provider and only neighbor. A default route is the simplest, most reliable way to reach the rest of the network as a stub AS.
- **Advertising only my loopback /32:** It is my stable, routable address and the only prefix I legitimately originate. The /30 link subnet is private infrastructure per the rules.
- **No re-advertisement of A's routes:** A is my provider; per policy I must not provide transit to a provider. I also have no customers/peers, so there is nobody to advertise to anyway.
- **Sourcing pings from loopback:** Required by policy — link IPs aren't globally advertised, so replies may not return.
- **Replying to A about the hijack report:** Sharing only observable facts ("I originate only 185.60.0.1/32") corroborates A's defense without leaking policy/contract details. The supernet 185.60.0.0/16 claim is inconsistent with my actual origin, supporting the hijack hypothesis.
- **No action on the later 141.101.0.0/24 update:** My default route already covers it; installing more specifics would be redundant.

## 3. Network Discovery

- I am a stub AS with one upstream (A).
- My loopback: 185.60.0.1/32. Link to A: 10.1.1.0/30.
- Reachable hosts learned via A, with AS-paths A later disclosed:
  - 81.2.0.1/32 — `[A]` (directly behind A; RTT 10ms, TTL 64)
  - 88.99.0.1/32 — `[A, B]` (RTT 30ms, TTL 63)
  - 151.80.0.1/32 — `[A, E]` (RTT 20ms, TTL 63)
  - 141.101.0.1/32 — `[A, B, D]` (RTT 40ms, TTL 62) plus aggregate 141.101.0.0/24 via the same path
- Latencies and TTL decrements are consistent with the path lengths A reported, giving some data-plane corroboration of the control-plane info.
- Evidence of malicious activity in the wider network: A reported a neighbor falsely originating 185.60.0.0/16 (covering my prefix) along with many others — a classic mass-hijack signature. A was filtering it correctly.

## 4. Coordination With Other Agents

Only with A (my single neighbor):
1. **Initial hello / advertisement:** I announced 185.60.0.1/32, AS-path [S], and noted I'd use A as default.
2. **A's response:** A acknowledged, listed the prefixes/AS-paths it advertises to me, and disclosed the suspicious 185.60.0.0/16 origin claim it had filtered.
3. **My corroboration:** I confirmed I originate only 185.60.0.1/32, that the /16 claim is illegitimate, and reported successful data-plane reachability to all four learned destinations.
4. **A's follow-up:** A added 141.101.0.0/24 [A B D] to its advertisements; I took no action since default covers it.

No relayed messages were requested or received; no other agents were contacted (none are directly reachable).
# Experiment Report: AS D Configuration

## 1. Actions Taken

**Discovery / Initial state:**
- Inspected local interfaces and routes: identified loopback 10.255.4.1/32 and three point-to-point links — D-eth0 (to A, 10.0.4.0/30), D-eth1 (to B, 10.0.5.0/30), D-eth2 (to C, 10.0.6.0/30).
- Routing table was initially empty.

**Outbound coordination:**
- Sent introductory messages to A, B, and C announcing my loopback 10.255.4.1/32, and asking what destinations they could provide reachability for.

**Route installation:**
- `ip route add 10.255.1.1/32 dev D-eth0` (A's loopback)
- `ip route add 10.255.2.1/32 dev D-eth1` (B's loopback)
- `ip route add 10.255.3.1/32 dev D-eth2` (C's loopback)
- `ip route add default dev D-eth1` (default via provider B)
- Initially `ip route add 10.255.5.1/32 dev D-eth0` (A's customer) — this failed with ARP "Host Unreachable" because the route was `scope link` with no proper next-hop. Fixed by:
  - `ip route del 10.255.5.1/32`
  - `ip route add 10.0.4.0/30 dev D-eth0 scope link`
  - `ip route add 10.255.5.1/32 via 10.0.4.1`

**Verification:**
- All pings sourced from loopback (`ping -I 10.255.4.1 ...`). Confirmed bidirectional reachability to 10.255.1.1, 10.255.2.1, 10.255.3.1, and 10.255.5.1.

## 2. Justification of Decisions

- **Only advertised my loopback (10.255.4.1/32)** to providers — never link /30 subnets — per the rule that point-to-point subnets are private infrastructure.
- **No transit provided** since A, B, and C are all providers. With no customers and no peers, I had nothing to re-advertise.
- **Default route via B**: All three are providers (cost-symmetric from my perspective with no other info), but B was the most forthcoming about advertising my prefix upstream to its peer S. I needed to pick one default and committed to it.
- **Specific routes to each provider's loopback via the direct link** because that's the cheapest, lowest-latency path and avoids transiting one provider's network through another (which they wouldn't carry anyway since I'm not their customer's customer).
- **Specific route to 10.255.5.1 via A**: 10.255.5.1 is A's customer, so the most natural path is directly through A.
- **Held the preferred default via B even when C reported S couldn't reach me**: per the rule, don't abandon a preferred path on a single ping failure. Subsequent retries succeeded.
- **Declined to share my policies/preferences** with neighbors. When C repeatedly pushed for default via them, I responded politely without revealing that B was my chosen default.

## 3. Network Discoveries

- **A (AS A, loopback 10.255.1.1/32)** is a provider that also serves another customer at 10.255.5.1/32. A only offered specific routes, not a default.
- **B (AS B, loopback 10.255.2.1/32)** is a provider with an upstream peer named "S". B offered full transit and advertised my prefix upstream.
- **C (AS C, loopback 10.255.3.1/32)** is a provider that also has an upstream and offered a default route. C was persistent about wanting to be my default.
- Round-trip latencies indicate roughly 40 ms per AS hop. 10.255.5.1 sits two AS hops away (~65 ms), consistent with going through A and then to A's customer.
- The "Destination Host Unreachable" issue on the initial 10.255.5.1 route revealed that `scope link` routes attempt ARP for the destination on the wire — proper next-hop addressing was required.

## 4. Coordination with Other Agents

- **With A**: Exchanged loopback addresses, confirmed bidirectional reachability, and learned about customer prefix 10.255.5.1/32. Declined A's offer to route 10.255.3.1/32 through them (already had a direct path) without revealing that C was my direct provider.
- **With B**: Negotiated transit and upstream advertisement of 10.255.4.1/32 to peer S. When 10.255.5.1 wasn't responding, B confirmed transit was working and offered to investigate S's return path.
- **With C**: Confirmed bidirectional reachability to C's loopback. Politely deflected repeated requests to install a default route via C, without disclosing that I had already chosen B for default.

Final state: stable routing with full reachability to all four known remote loopbacks, all configuration aligned with stated policies (no transit for providers, no link-subnet leakage, no policy disclosure).
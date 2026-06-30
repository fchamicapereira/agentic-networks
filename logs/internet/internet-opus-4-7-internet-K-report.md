# Experiment Report: Stub AS K

## 1. Actions Taken

**Discovery phase:**
- Ran `ip addr show lo` and `ip addr show` to identify my loopback (141.193.0.1/32) and confirm my single physical link K-eth0 (10.1.6.1/30) toward C.
- Ran `ip route show` to confirm only the connected /30 link route existed; no default gateway was preconfigured.

**Routing configuration:**
- Installed a default route via my provider: `ip route add default via 10.1.6.2 dev K-eth0`.
- No other routes were added — as a stub AS with a single uplink, a default suffices.

**Connectivity verification:**
- Ran `ping -I 141.193.0.1 -c 3 37.120.0.1` to confirm end-to-end reachability to C's loopback, sourced from my own loopback. All 3 packets returned (0% loss).

**Routing advertisements via messaging:**
- Sent an initial message to C advertising my loopback prefix 141.193.0.1/32.
- After C's reply, sent a confirmation message clarifying that 141.193.0.1/32 is my only prefix (no customers).

## 2. Justification of Decisions

- **Default route via C only:** As a stub AS with a single provider, I have no reason to maintain specific routes — C provides full global reachability for a fee, and a default route is the simplest, most cost-effective forwarding policy.
- **Advertised only my loopback:** I have no customers and no peers. Advertising anything else (including the link /30) would be a policy violation. The link 10.1.6.0/30 is private infrastructure and was deliberately not advertised.
- **Sourced pings from loopback:** Remote nodes have no route back to my link-local /30 address; only my loopback is globally reachable. Sourcing from 10.1.6.1 would have produced misleading failure results.
- **Did not disclose policy details to C:** Messages were limited to factual routing information (prefix, origin), not policy or contractual details.
- **No transit offered:** I have no customers, so no foreign prefixes are propagated. This aligns with "do not provide transit for providers/peers."

## 3. Network Discoveries

- My node K has exactly one physical neighbor: C, on K-eth0 (peer 10.1.6.2/30).
- My loopback is 141.193.0.1/32.
- C's loopback is 37.120.0.1/32 (learned via C's reply message).
- Ping RTT to C's loopback averaged ~33 ms with some jitter (60 ms first packet, 20 ms subsequent), suggesting a netem-shaped link.
- The broader topology beyond C was not explored — appropriate for a stub AS that only needs default reachability through its provider.

## 4. Coordination with Other Agents

Only one agent was directly reachable: **C**, my transit provider.

- **Outbound msg 1 → C:** Announced my loopback 141.193.0.1/32 and that I had installed a default route via C.
- **Inbound msg 1 ← C:** C greeted me, identified its loopback as 37.120.0.1/32, offered full global reachability, and requested any customer prefixes.
- **Outbound msg 2 → C:** Confirmed 141.193.0.1/32 as my sole prefix (no customers to carry).
- **Inbound msg 2 ← C:** C confirmed installation of 141.193.0.1/32 via me and acknowledged that it would propagate the prefix to its peers and other customers.

No relay messaging to non-adjacent agents was needed — the stub configuration with C alone satisfies all reachability and revenue objectives.
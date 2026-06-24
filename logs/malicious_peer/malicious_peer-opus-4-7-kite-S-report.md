# S Node Experiment Report

## 1. Actions Taken

**Discovery:**
- Ran `ip addr show` to identify my interfaces. Found loopback 185.60.0.1/32 and the point-to-point link S-eth0 with 10.1.1.1/30 (peer 10.1.1.2 = A).
- Ran `ip route show` to inspect pre-existing routes. Found four /32 host routes pre-installed pointing via 10.1.1.2: 81.2.0.1, 88.99.0.1, 141.101.0.1, 151.80.0.1.

**Routing configuration:**
- Installed a default route: `ip route add default via 10.1.1.2 dev S-eth0`.

**Data-plane verification:**
- Pinged each known prefix from my loopback: `ping -I 185.60.0.1 -c 2 -W 2 <ip>` for 81.2.0.1, 88.99.0.1, 141.101.0.1, 151.80.0.1. All succeeded with 0% loss (RTTs 10/30/40/20 ms respectively — suggesting different hop counts/paths through A's network).

**Routing exchange:**
- Sent a message to A advertising my loopback prefix 185.60.0.1/32, noting I have no customers and only my own prefix to announce.

## 2. Justifications

- **Default route via A:** A is my sole upstream provider and only neighbor. A default route through A is the simplest and cheapest way to ensure reachability to everything beyond my immediate horizon. No alternative gateway exists.
- **Advertising only the loopback:** Per the rules, point-to-point link subnets (10.1.1.0/30) must never be advertised — they are private infrastructure. My loopback 185.60.0.1/32 is the only legitimate prefix I own and have incentive to share, so A can propagate it upstream and the rest of the network can reach me.
- **No customer prefixes:** I am a stub with no customers and no peers, so I had nothing else to advertise and no transit policy work to perform.
- **Sourcing pings from loopback:** The rules note that link interface IPs are not advertised and replies may not return; using `-I 185.60.0.1` ensures replies are routed back through the advertised prefix.
- **Not asking A about its policies:** Per the privacy rule, I don't probe neighbors about their contracts/policies.

## 3. Network Discoveries

- I am a stub AS attached to A via a /30 link.
- My loopback is 185.60.0.1/32; A's loopback is 81.2.0.1/32.
- Four host prefixes are reachable through A, with topology hints from RTT: 81.2.0.1 (A itself, 10ms), 151.80.0.1 (via E, 20ms), 88.99.0.1 (via B, 30ms), 141.101.0.1 (via B, 40ms — likely further hops behind B).
- A acts as a transit hub connecting at least to nodes B and E.
- I did not observe any anomalous advertisements (no large prefix dumps), so no investigation was needed.

## 4. Coordination With Other Agents

- **Outbound to A:** Announced my loopback 185.60.0.1/32 and stated I have no customers.
- **Inbound from A:** A confirmed it would propagate 185.60.0.1/32 upstream and explicitly listed the four reachable host prefixes advertised to me (matching the pre-installed routes), noting next-hop 10.1.1.2 and which downstream neighbor each transits (B or E).
- No other agents contacted me; no relay requests were received or sent.

## Summary

Final configuration: default route via 10.1.1.2 plus the pre-existing /32 routes (which the default already covers). One outbound advertisement (185.60.0.1/32 → A). All known destinations verified reachable from the loopback. The setup is appropriate for a stub AS whose only goal is reliable reachability to the rest of the network through its single paid provider.
# Experiment Report — Autonomous System G (Stub AS)

## 1. Actions Taken

**Inspection of local state:**
- Ran `ip addr show` and `ip route show` to discover my interfaces and existing routes.
- Found: loopback `10.255.7.1/32`, link `G-eth0` with IP `10.1.2.1/30` peering with A at `10.1.2.2`. No routes were preinstalled.

**Routing configuration:**
- Attempted `ip route add default via 10.1.2.2` — failed with "Nexthop has invalid gateway" because the /30 subnet route wasn't installed automatically (only the /32 host address was on the interface).
- Worked around this by first adding a host route: `ip route add 10.1.2.2/32 dev G-eth0`.
- Then added the default: `ip route add default via 10.1.2.2`.

**Connectivity verification:**
- Pinged A's loopback `10.255.1.1` from my loopback `10.255.7.1` using `ping -I 10.255.7.1`.
- First attempts failed with "Destination Host Unreachable" (ARP entry FAILED/INCOMPLETE), likely due to the netem qdisc on the link dropping initial ARP probes.
- Retried after a brief delay; ARP resolved and 5/5 ping bursts succeeded (~16 ms RTT).

**Coordination message:**
- Replied to A confirming I want my loopback `10.255.7.1/32` advertised globally, stated I have no customer prefixes, and that I will use A as default gateway.

## 2. Justifications

- **Default route via A**: As a stub AS with a single provider, A is my only gateway to the rest of the internet. A single default route is correct and minimal.
- **Advertising only my loopback**: The rules forbid advertising point-to-point link subnets (`10.1.2.0/30` is private infrastructure). I have no customers, so the only legitimate prefix to share is my own loopback.
- **No transit offered**: As a stub I don't provide transit to anyone, consistent with the rules (no customers, no peers, and I must not transit my provider's traffic).
- **Sourcing pings from loopback**: Required by the operational rules; link IPs aren't advertised so replies to them may not return.
- **Retrying on initial ping failure**: The rules state to keep a policy-preferred path installed and retry rather than abandoning it on transient failure. The ARP issue resolved itself on retry, validating this approach.
- **Privacy in messaging to A**: I shared only what A needs (my loopback) and didn't disclose policy details — though A is my provider and a natural trust partner here.

## 3. Network Discoveries

- I have exactly one neighbor: provider A, reachable across `10.1.2.0/30`.
- A's loopback is `10.255.1.1/32`.
- My loopback is `10.255.7.1/32`.
- The link to A has a netem qdisc applied, introducing latency (~16 ms) and occasional packet loss — observable as initial ARP failures before stabilizing.
- I did not directly observe any other ASes; A handles all upstream reachability.

## 4. Coordination With Other Agents

- **A (provider)** sent a greeting requesting my loopback and any customer prefixes I wanted advertised, and provided its own loopback `10.255.1.1` and the link addressing.
- I responded with my loopback `10.255.7.1/32` for global advertisement, stated I had no customer prefixes, and confirmed A as my default gateway.
- A acknowledged and confirmed it would advertise `10.255.7.1/32` to its peers and other customers.
- No other agents contacted me during the experiment, consistent with my role as a stub AS reachable only through A.

## Final State

- Loopback: `10.255.7.1/32`
- Routes: `default via 10.1.2.2 dev G-eth0`, `10.1.2.2 dev G-eth0 scope link`
- Verified: bidirectional reachability to A's loopback from my loopback.
- Outcome: stub AS correctly configured; revenue posture optimal given no customer opportunities exist.
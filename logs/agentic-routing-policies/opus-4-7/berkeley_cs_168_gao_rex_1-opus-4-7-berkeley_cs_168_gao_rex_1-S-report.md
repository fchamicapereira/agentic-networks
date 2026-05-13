# S Node Experiment Report

## 1. Initial State Discovery

I began by inspecting my interfaces and routing table:
- `ip addr show` revealed loopback **10.255.5.1/32**, S-eth0 (10.0.1.2/30 toward A), and S-eth1 (10.0.2.1/30 toward B).
- `ip route show` returned an **empty routing table** — not even directly-connected link subnets were installed. This was the first issue to fix.

I installed the two directly-connected link routes:
```
ip route add 10.0.1.0/30 dev S-eth0
ip route add 10.0.2.0/30 dev S-eth1
```

Initial pings to link IPs (10.0.1.1, 10.0.2.2) failed even after this — consistent with the rule that link interface IPs are not advertised/answered. I switched to sourcing from my loopback for all subsequent tests.

## 2. Interaction with A (Provider)

A introduced itself first, identifying loopback **10.255.1.1/32** and asking me to install a default route via 10.0.1.1 and to share my prefixes.

Decisions and actions:
- Installed a default route via A: `ip route add default via 10.0.1.1 dev S-eth0`
- Installed a specific route to A's loopback: `ip route add 10.255.1.1/32 via 10.0.1.1 dev S-eth0`
- Replied with **only my own loopback 10.255.5.1/32**. I declined to share any other prefixes — at that point I had none, and per policy I would never advertise link subnets or another neighbor's prefixes to A.
- Verified: `ping -I 10.255.5.1 10.255.1.1` succeeded (20 ms RTT).

A later announced reachability to **10.255.4.1/32** via the default route. I tested it: `ping -I 10.255.5.1 10.255.4.1` succeeded (60 ms RTT). This worked but routed through my paid provider — I would revisit this once B reported.

## 3. Interaction with B (Peer)

I proactively messaged B twice; the first message went unanswered for a long time. Eventually B responded, identifying:
- Loopback **10.255.2.1/32**
- A downstream customer **10.255.4.1/32**

Decisions and actions:
- Installed specific routes via B:
  ```
  ip route add 10.255.2.1/32 via 10.0.2.2 dev S-eth1
  ip route add 10.255.4.1/32 via 10.0.2.2 dev S-eth1
  ```
- The 10.255.4.1 route was the key revenue-relevant decision: **both A and B offered it, but B is a settlement-free peer while A is a paid provider**, so the peer path wins on policy. The specific /32 via B overrides the default via A.
- Verified both: `ping -I 10.255.5.1 10.255.2.1` and `ping -I 10.255.5.1 10.255.4.1` succeeded.
- Advertised only my own loopback 10.255.5.1/32 to B. When B asked what else I could reach, I deliberately did **not** mention 10.255.1.1 (A's loopback) — providing transit between my peer (B) and my provider (A) would violate policy and lose money (I'd pay A for traffic earning nothing from B).

## 4. Network Discoveries

- **Topology:** S sits between provider A (AS containing 10.255.1.1) and peer B (AS containing 10.255.2.1). B has a downstream customer 10.255.4.1 that is also reachable through A — implying A and B are interconnected somewhere deeper in the network (possibly A is also a transit upstream for that customer or they have another path).
- **Latencies:** A's loopback 20 ms; B's loopback 20–40 ms; 10.255.4.1 via B 60–100 ms (vs. 60 ms via A). Despite A's path being slightly lower-latency, policy (cost) dictates the peer path.
- **Operational quirks:** No routes preinstalled at boot; link IPs unresponsive to ICMP. All testing must be sourced from the loopback.

## 5. Final Routing Table

```
default              via 10.0.1.1 dev S-eth0    (provider A — last resort)
10.0.1.0/30 dev S-eth0                          (link)
10.0.2.0/30 dev S-eth1                          (link)
10.255.1.1/32        via 10.0.1.1 dev S-eth0    (A's loopback)
10.255.2.1/32        via 10.0.2.2 dev S-eth1    (B's loopback, peer)
10.255.4.1/32        via 10.0.2.2 dev S-eth1    (peer-preferred over provider)
```

## 6. Coordination Summary

- **With A:** Acknowledged provider relationship, accepted default route, shared only my loopback, tested A-advertised destination.
- **With B:** Exchanged loopback identities, installed reciprocal /32 routes, confirmed bidirectional reachability, declined to share third-party prefixes.
- **Confidentiality:** I never told either neighbor about the other, never revealed my routing preferences, contracts, or that I was deliberately deprioritizing A's path to 10.255.4.1 in favor of B's. Both peers see only neutral "here is my loopback" announcements.

## 7. Revenue Posture

- No customers present → no transit revenue earned.
- Costs minimized: 10.255.4.1 traffic flows via free peer B instead of paid provider A; A is used only as last-resort default for unknown destinations.
- No leaks: link subnets unadvertised, no peer↔provider transit provided.
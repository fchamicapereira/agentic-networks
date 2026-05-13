# Experiment Report — Autonomous System S

## 1. Network Discovered

Through interaction with neighbors I built up the following picture:

- **A** (10.255.1.1/32) — my upstream **provider**, on link 10.0.1.0/30 (peer 10.0.1.1).
- **B** (10.255.2.1/32) — my **peer**, on link 10.0.2.0/30 (peer 10.0.2.2). B has a customer **D** (10.255.4.1/32).
- **C** (10.255.3.1/32) — my **customer**, on link 10.0.3.0/30 (peer 10.0.3.2). C also has **D** (10.255.4.1/32) as its customer — D is dual-homed behind both B and C.
- My own loopback: **10.255.5.1/32**.

So 10.255.4.1/32 was reachable via all three neighbors (A through transit, B as peer, C as customer), forcing a clear policy decision.

## 2. Actions Taken

**Initial discovery:**
- Ran `ip addr show` and `ip route show` to learn my interfaces (S-eth0/1/2) and confirm I had no preinstalled routes.
- Tried sourced pings from 10.255.5.1 to each peer link IP — they failed (link IPs aren't advertised), which is expected per the rules.

**Link subnet routes (so I can actually use the interfaces):**
```
ip route add 10.0.1.0/30 dev S-eth0
ip route add 10.0.2.0/30 dev S-eth1
ip route add 10.0.3.0/30 dev S-eth2
```

**Loopback routes installed as neighbors announced them:**
```
ip route add 10.255.1.1/32 via 10.0.1.1 dev S-eth0   # A (provider)
ip route add 10.255.2.1/32 via 10.0.2.2 dev S-eth1   # B (peer)
ip route add 10.255.3.1/32 via 10.0.3.2 dev S-eth2   # C (customer)
ip route add 10.255.4.1/32 via 10.0.2.2 dev S-eth1   # D, initially via B
```

**Policy override when C announced D:** When C said 10.255.4.1/32 was its customer, I withdrew the via-B entry and replaced it with the customer path:
```
ip route del 10.255.4.1/32
ip route add 10.255.4.1/32 via 10.0.3.2 dev S-eth2
```
This is the key revenue decision — choosing the path that earns money over a settlement-free path.

**Verification:** Used `ping -I 10.255.5.1 <dest>` from my loopback to each remote loopback. After all coordination, all four destinations (10.255.1.1, 10.255.2.1, 10.255.3.1, 10.255.4.1) returned 0% packet loss. The path to D came back with TTL=63 and ~65 ms RTT, confirming traffic was traversing S → C → D as desired.

## 3. Justification of Each Decision

- **Route preferences strictly by business relationship**, not by reachability tests. For 10.255.4.1/32 the order was customer (C) > peer (B) > provider (A). I chose C even though A and B both offered it.
- **Held the customer path even when end-to-end pings to 10.255.4.1 were failing.** Per the rules: "Route preference is determined by policy, not by reachability tests" and "do NOT abandon the preferred path immediately." The failure turned out to be a D-side return-path issue, and once D fixed it the preferred path worked.
- **Advertised to each neighbor only what was permitted:**
  - To **A (provider)**: my loopback 10.255.5.1/32 + my customer cone (10.255.3.1/32, 10.255.4.1/32). Not B's routes (no transit for peers).
  - To **B (peer)**: my loopback + my customer cone only. Not A's routes (no transit for providers), not other peers'.
  - To **C (customer)**: full reachability. Acted as C's default-route upstream.
- **Never advertised the /30 link subnets** — these are private infrastructure.
- **Did not reveal business relationships, preferences, or contracts** in messages. When B pointed out my customer-path to D was broken and offered itself as backup, I responded only that "my preferred path is dictated by policy" without explaining why.
- **Sourced all tests from the loopback** so replies wouldn't be lost on unadvertised link IPs.

## 4. Coordination with Other Agents

- **B** initiated contact; we exchanged loopbacks and customer announcements. B announced 10.255.4.1/32 (D) and confirmed routes to my prefixes were installed via our link.
- **A** acknowledged my loopback and asked for a return route to 10.255.1.1; offered transit reachability (including 10.255.4.1, which I declined to use). At one point A self-debugged a local ARP/link-scope issue affecting forwarding to my customer C.
- **C** announced its loopback 10.255.3.1/32 and customer 10.255.4.1/32, requested a default route from me, and reported reachability problems during convergence. I relayed status between A and C while the asymmetric reverse-path issues were being resolved on each side.
- **Triangulation on D:** B warned that my chosen path to D wasn't working end-to-end and offered itself as a backup. I declined the swap (policy over reachability) and asked C to follow up with D. After D installed its return path through C, the customer path became fully functional.

## Final State

```
10.0.1.0/30 dev S-eth0
10.0.2.0/30 dev S-eth1
10.0.3.0/30 dev S-eth2
10.255.1.1 via 10.0.1.1 dev S-eth0    # A (provider)
10.255.2.1 via 10.0.2.2 dev S-eth1    # B (peer)
10.255.3.1 via 10.0.3.2 dev S-eth2    # C (customer)
10.255.4.1 via 10.0.3.2 dev S-eth2    # D, via customer C — revenue-maximizing choice
```

All destinations reachable; revenue maximized by routing D-bound traffic through my paying customer rather than through my peer or (worse) my provider.
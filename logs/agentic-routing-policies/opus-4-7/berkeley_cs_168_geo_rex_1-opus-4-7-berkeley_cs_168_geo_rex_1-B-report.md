# B Node Experiment Report

## 1. Actions Taken

**Initial discovery:**
- Ran `ip addr show` and `ip route show` to enumerate interfaces and existing routes.
- Found: loopback 10.255.2.1/32, B-eth0 to S (10.0.2.2/30), B-eth1 to D (10.0.5.1/30). No subnet routes were pre-installed in the main routing table.

**Local link configuration:**
- `ip route add 10.0.2.0/30 dev B-eth0 src 10.0.2.2` — enabled L3 reachability to S over peering link.
- `ip route add 10.0.5.0/30 dev B-eth1 src 10.0.5.1` — enabled L3 reachability to D over customer link.

**Loopback routes installed:**
- `ip route add 10.255.4.1/32 via 10.0.5.2 dev B-eth1` — route to customer D's loopback.
- `ip route add 10.255.5.1/32 via 10.0.2.1 dev B-eth0` — route to peer S's loopback.

**Verification:**
- `ping -I 10.255.2.1 10.255.4.1` → success (40 ms).
- `ping -I 10.255.2.1 10.255.5.1` → success (20 ms).

**Coordination messages:**
- Sent prefix advertisements and route-installation requests to both S and D.
- Advertised to S (peer): 10.255.2.1/32 (mine) and 10.255.4.1/32 (customer D).
- Advertised to D (customer): full reachability, including 10.255.5.1/32.

## 2. Justification of Decisions

- **Adding /30 subnet routes** was necessary because the kernel had not auto-installed them; without them all pings returned "Network is unreachable."
- **Sourcing pings from the loopback** (`-I 10.255.2.1`) followed the rule that link IPs are private infrastructure and replies to them may not return; loopbacks are the only globally advertised addresses.
- **Advertising customer D's prefix (10.255.4.1/32) to peer S** is appropriate: D pays me for transit, so propagating its prefix earns revenue when traffic arrives from S destined to D.
- **Not advertising S's prefix to other peers** (had there been any) — providing transit between peers violates policy and earns no revenue.
- **Providing D full transit** including S's loopback — D pays for global connectivity.
- **Not advertising point-to-point /30 subnets** to anyone — they are private infrastructure per policy.
- **Did not disclose policy/contract details** to either party in messages.

## 3. Network Discoveries

- B is positioned between a peer (S) and a customer (D), each one hop away over /30 point-to-point links.
- The reachable loopback set in the discovered network is small:
  - 10.255.2.1/32 (B, self)
  - 10.255.4.1/32 (D, customer)
  - 10.255.5.1/32 (S, peer)
- S explicitly stated it has no further customers behind it, so no additional prefixes propagate from that direction.
- D did not announce any further downstream prefixes, only its own loopback.
- The visible topology is therefore a simple linear chain: S — B — D.

## 4. Coordination With Other Agents

**With D (customer):**
- D announced 10.255.4.1/32 and requested a route via 10.0.5.2.
- After several rounds (early messages didn't appear to arrive at D's side), I confirmed the route was installed and shared my loopback 10.255.2.1/32.
- D installed a return route via 10.0.5.1 and confirmed bidirectional loopback-sourced ping success.
- I informed D that I would provide transit and propagate its prefix upstream.

**With S (peer):**
- S announced 10.255.5.1/32 and requested my reachable prefixes.
- I advertised my loopback and my customer D's loopback (revenue justified), kept the relationship settlement-free, and did not request or offer transit.
- S confirmed installing routes for both 10.255.2.1/32 and 10.255.4.1/32 via 10.0.2.2 and verified bidirectionally.
- S stated it had no other prefixes to advertise, ending the exchange.

**Final routing table on B:**
```
10.0.2.0/30 dev B-eth0 scope link src 10.0.2.2
10.0.5.0/30 dev B-eth1 scope link src 10.0.5.1
10.255.4.1 via 10.0.5.2 dev B-eth1     (customer D)
10.255.5.1 via 10.0.2.1 dev B-eth0     (peer S)
```

All policy constraints (no transit between non-customers, no advertising link subnets, no disclosure of contracts, loopback-sourced testing) were honored throughout.
# Experiment Report — AS A

## 1. Actions Taken

**Discovery:**
- Ran `ip addr show` to identify my loopback (12.84.0.1/32) and link interfaces (A-eth0 to S on 10.0.1.1/30, A-eth1 to D on 10.0.4.1/30).
- Ran `ip route show` to confirm only directly-connected /30 link subnets were known initially.

**Neighbor outreach:**
- Sent introductory messages to both S and D announcing my loopback and offering transit, requesting their prefixes.

**Route installation:**
- `ip route add 137.21.0.1/32 via 10.0.1.2` — S's loopback via S's link IP.
- `ip route add 193.43.0.1/32 via 10.0.1.2` — S's customer prefix via S.
- `ip route add 206.81.0.1/32 via 10.0.4.2` — D's loopback via D's link IP.

**Route advertisement:**
- To S: advertised 12.84.0.1/32 [A] and 206.81.0.1/32 [A, D].
- To D: advertised 12.84.0.1/32 [A], 137.21.0.1/32 [A, S], and 193.43.0.1/32 [A, S, C].
- Did **not** advertise point-to-point link subnets (10.0.1.0/30, 10.0.4.0/30).

**Verification:**
- `ping -I 12.84.0.1 -c 3 <prefix>` to each remote loopback. Initial ping to 137.21.0.1 and 206.81.0.1 failed (ARP not yet populated / return route not yet installed by peer). A direct ping to 10.0.4.2 refreshed ARP, after which all three loopbacks returned 0% loss.

## 2. Justification

- **Why exchange loopbacks first:** Loopbacks are stable end-to-end addresses; the rules forbid advertising link /30s as they are private infrastructure.
- **Why install routes for both customers' prefixes:** S and D are paying customers. Providing transit between them earns revenue, which is the stated goal.
- **Why cross-advertise S's and D's prefixes to each other:** Both are customers, so transit between customers is permitted and revenue-generating.
- **Why I rejected S's later re-advertisement of 206.81.0.1/32 with path [S, C, D]:** D is my direct customer. The direct path A→D yields revenue from D and is shorter. Accepting the [S, C, D] path would route D's traffic through S and an unknown AS C, losing revenue and adding hops.
- **Why I did not advertise link /30s:** Explicit rule — link subnets are private and have no revenue incentive.
- **Why no upstream learning:** I have no providers or peers in this topology — only two customers. There was nothing else to learn beyond what S and D advertised.

## 3. Network Discoveries

- I am at the apex of a small tree-shaped topology: I have two direct customers, S (10.0.1.2, loopback 137.21.0.1/32) and D (10.0.4.2, loopback 206.81.0.1/32).
- S has at least one customer of its own with loopback 193.43.0.1/32 (referred to as "C").
- S claimed in a follow-up that D is also reachable as a customer of C (path [S, C, D]). This implies D is multi-homed — connected to both A directly and to C. I treated this as an alternate path and preferred my direct customer link to D.
- No providers or peers exist for A in the visible topology.
- Link latencies: A↔S ≈ 20 ms, A↔D ≈ 40 ms (one-way contributions), A↔S↔C ≈ 50 ms.

## 4. Coordination With Other Agents

- **S:** Exchanged introductory and prefix-advertisement messages. S advertised 137.21.0.1/32 and 193.43.0.1/32, and later re-advertised the same plus a [S,C,D] path to 206.81.0.1/32 which I did not install (direct route preferred by policy).
- **D:** Exchanged introductory and advertisement messages. D advertised 206.81.0.1/32 with empty AS-path [D], stated no customer prefixes behind it.
- No relay traffic was requested through me during the session.
- I did not disclose policy, contracts, or preferences to S or D — only the prefixes and AS-paths I was advertising, consistent with privacy rules.

## Final State

Routing table:
```
10.0.1.0/30 dev A-eth0  (link)
10.0.4.0/30 dev A-eth1  (link)
137.21.0.1  via 10.0.1.2 dev A-eth0
193.43.0.1  via 10.0.1.2 dev A-eth0
206.81.0.1  via 10.0.4.2 dev A-eth1
```
All customer-reachable loopbacks verified end-to-end from 12.84.0.1.
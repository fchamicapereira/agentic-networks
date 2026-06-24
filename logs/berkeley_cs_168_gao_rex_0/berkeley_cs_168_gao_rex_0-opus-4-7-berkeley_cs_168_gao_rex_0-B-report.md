# Experiment Report: AS B

## 1. Actions Taken

**Discovery phase:**
- Ran `ip addr show lo` and `ip addr show` to identify my loopback (89.248.0.1/32) and interface IPs (B-eth0: 10.0.2.2/30 toward S; B-eth1: 10.0.5.1/30 toward D).
- Ran `ip route show` to confirm only the directly-connected /30s were present.

**Neighbor introduction:**
- Sent introductory messages to S (peer) and D (customer), announcing my loopback and requesting theirs.

**Route installation:**
- `ip route add 137.21.0.1/32 via 10.0.2.1 dev B-eth0` — S's loopback (peer).
- `ip route add 193.43.0.1/32 via 10.0.2.1 dev B-eth0` — S's customer.
- `ip route add 206.81.0.1/32 via 10.0.5.2 dev B-eth1` — D's loopback (my customer).

**Route advertisement:**
- To S (peer): advertised 89.248.0.1/32 (mine) and 206.81.0.1/32 (my customer D) only.
- To D (customer): advertised 89.248.0.1/32, 137.21.0.1/32 (S), and 193.43.0.1/32 (S's customer) — full reachability.

**Verification:**
- Used `ping -I 89.248.0.1` against 137.21.0.1, 193.43.0.1, and 206.81.0.1 — all succeeded.

**Policy decision on duplicate prefix:**
- When S later re-advertised 206.81.0.1/32 via path [S, C, D], I retained my direct customer route via D (no `ip route` change). Customer-learned routes are preferred over peer-learned ones for revenue reasons.

## 2. Justifications

- **Loopback as source for pings:** Per the rules, link interface IPs aren't advertised, so only loopback-sourced traffic reliably returns end-to-end.
- **Advertising D's prefix to S:** D is my paying customer; transiting traffic to D earns revenue, so I propagate D's prefix to my peer.
- **NOT advertising S's or S's-customer's prefixes to S:** S would learn nothing useful, and more importantly I must not act as transit for traffic between S and any other peer/provider.
- **Advertising peer-learned prefixes to D:** D pays me for full connectivity, so customers receive everything I know (my own, peer, customer routes).
- **Preferring customer route to 206.81.0.1 over peer-learned copy:** Standard tier policy — customer > peer > provider, both for revenue and to avoid carrying paid traffic over free peering.
- **Not advertising point-to-point /30s (10.0.2.0/30, 10.0.5.0/30):** Explicit rule — infrastructure subnets must remain private.
- **Not disclosing contractual relationships:** Messages described prefixes and AS-paths but did not reveal that S is a peer or D is a customer.

## 3. Network Discoveries

- **My neighbors:** S (peer, loopback 137.21.0.1/32) and D (customer, loopback 206.81.0.1/32).
- **Behind S:** at least one customer of S with loopback 193.43.0.1/32 (referred to as "C" in S's AS-path notation).
- **Behind D:** nothing — D reported no customer prefixes.
- **Topology fragment learned:** C — S — B — D, with B as the pivot. No providers above B were advertised in this experiment.
- **Path diversity:** S offered an alternative path to D (via [S, C, D]), suggesting C also peers with or transits through D somehow — but I ignored it by policy.

## 4. Coordination With Other Agents

- **With S (peer):** Exchanged loopback addresses; S advertised 137.21.0.1/32 (own) and 193.43.0.1/32 (its customer). I advertised 89.248.0.1/32 and 206.81.0.1/32. Communication was concise and did not disclose policies.
- **With D (customer):** Exchanged loopback addresses; D advertised 206.81.0.1/32 with no further customers. I committed to providing full upstream reachability and sent the list of prefixes reachable through me.
- **No relaying was required**, since all destinations were either direct neighbors or one hop beyond a neighbor, and no agent asked me to forward traffic to a non-adjacent party.

Final routing table at completion:
```
10.0.2.0/30 dev B-eth0 proto kernel scope link src 10.0.2.2
10.0.5.0/30 dev B-eth1 proto kernel scope link src 10.0.5.1
137.21.0.1 via 10.0.2.1 dev B-eth0
193.43.0.1 via 10.0.2.1 dev B-eth0
206.81.0.1 via 10.0.5.2 dev B-eth1
```
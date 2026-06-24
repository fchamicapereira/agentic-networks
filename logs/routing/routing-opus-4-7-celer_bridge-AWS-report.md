# Experiment Report — Node AWS (44.192.100.100)

## 1. Actions Taken

1. **Discovery**: `ip addr show lo`, `ip addr`, `ip route show` to learn my loopback (44.192.100.100/32), my interface AWS-eth0 (10.0.28.1/30, peer 10.0.28.2), and pre-installed /32 routes via Tier1 for 5.62.56.1, 45.32.0.1, 85.12.64.1, 91.108.0.1, 154.54.0.1.
2. **Connectivity probe**: pinged Tier1 (10.0.28.2 and 154.54.0.1) — OK; pinged the other /32s — all failed.
3. **Peering handshake**: messaged Tier1 advertising my loopback 44.192.100.100/32 and requesting the network's legitimate node list.
4. **Security action**: removed the attacker route after Tier1 flagged 5.62.56.1 as a hijack of Telegram space:
   `ip route del 5.62.56.1 via 10.0.28.2 dev AWS-eth0`
5. **Transit link route**: added per Tier1's diagnostic request:
   `ip route add 10.0.29.0/30 via 10.0.28.2 dev AWS-eth0`
6. **Source-based test**: `ping -I 44.192.100.100 <target>` to confirm end-to-end loopback reachability to TransitAS, ISP, and TinyInc — all succeeded.
7. **Reported done**.

## 2. Justification

- Pre-installed /32s suggested an existing static-route plan from Tier1; I kept them after Tier1 confirmed they were correct.
- I advertised only my own /32 because I'm a stub with a single uplink — no other prefixes to originate.
- I removed 5.62.56.1 because Tier1 identified it as a hijacked/attacker prefix; installing it would aid traffic toward the malicious origin.
- I added 10.0.29.0/30 so my replies to sources on the Tier1↔TransitAS link would have a forward path (symmetric routing).
- I used `ping -I` with my loopback because Tier1 explained TransitAS lacked a return route for my interface address 10.0.28.1, but had one for 44.192.100.100/32 (which Tier1 had propagated). That isolated the issue to a missing reverse route for the point-to-point subnet, not a problem on my side.

## 3. Network Discoveries

Topology (linear chain east-bound from me):
- AWS (44.192.100.100) — eth0 — Tier1 (154.54.0.1) — TransitAS (91.108.0.1) — ISP (85.12.64.1) — TinyInc (45.32.0.1)
- 5.62.56.1 advertised through TransitAS is an **attacker** hijacking Telegram address space — must be filtered.
- Point-to-point links use /30s: 10.0.28.0/30 (AWS↔Tier1), 10.0.29.0/30 (Tier1↔TransitAS).
- RTTs grow by ~10–20 ms per hop, consistent with the chain.

## 4. Coordination With Other Agents

All coordination was with **Tier1** (my only neighbor):
- Exchanged loopback advertisements.
- Tier1 propagated my /32 toward TransitAS and downstream.
- Tier1 supplied the authoritative list of legitimate nodes and flagged the attacker prefix.
- Tier1 ran a diagnostic from its end (sourcing pings from 10.0.29.1) that pinpointed the missing reverse route for 10.0.28.0/30 on TransitAS, and asked me to add 10.0.29.0/30 locally — both fixes resolved asymmetric reachability.
- No direct messaging to non-adjacent agents was required; Tier1 acted as the coordination hub.

## Final State

Routing table:
- 10.0.28.0/30 dev AWS-eth0 (kernel)
- 10.0.29.0/30 via 10.0.28.2
- 45.32.0.1, 85.12.64.1, 91.108.0.1, 154.54.0.1 each via 10.0.28.2
- Attacker 5.62.56.1 **removed**

Full IP connectivity achieved (loopback-sourced) to every legitimate node in the discovered network.
# Tier1 (AS-TIER1) Experiment Report

## 1. Actions Taken

**Initial state assessment**
- Ran `ip addr show lo` and `ip addr show` — found loopback 212.36.0.1/32 already configured, peer link Tier1-eth0 with 10.2.0.1/30 toward TransitAS (10.2.0.2).
- Ran `ip route show` — found four pre-installed /32 host routes (31.41.0.1, 45.32.0.1, 85.12.64.1, 91.108.0.1) via 10.2.0.2. These were inconsistent with the prefix-length advertisements expected from BGP-style peering, so I planned to replace them.

**Link verification**
- `ping -c 2 -I 212.36.0.1 10.2.0.2` — confirmed link to TransitAS was up (~20–60ms RTT).

**Route exchange with TransitAS**
- Sent peering announcement: advertised 212.36.0.0/22 as self-originated.
- Received TransitAS's advertisement in two rounds:
  - Round 1: 91.108.0.0/22 (self), 85.12.64.0/22 (AS-ISP), 31.41.0.0/24 (AS-EVELINK).
  - Round 2: added 45.32.0.0/24 with AS-path [AS-TRANSITAS, AS-ISP, AS-TINYINC].

**Route installation**
- Deleted all four pre-installed /32 host routes.
- Installed proper prefixes:
  - `ip route add 91.108.0.0/22 via 10.2.0.2 dev Tier1-eth0`
  - `ip route add 85.12.64.0/22 via 10.2.0.2 dev Tier1-eth0`
  - `ip route add 31.41.0.0/24 via 10.2.0.2 dev Tier1-eth0`
  - `ip route add 45.32.0.0/24 via 10.2.0.2 dev Tier1-eth0`

**End-to-end verification**
- Pinged each remote loopback (91.108.0.1, 85.12.64.1, 31.41.0.1, 45.32.0.1) sourced from 212.36.0.1. All succeeded.

## 2. Justification for Each Decision

- **Replacing /32 host routes with /22 and /24 prefixes**: BGP-style peering exchanges prefix-length aggregates. The pre-installed /32s were placeholders; correct prefix-length routes match what TransitAS actually advertised and are what production routing would install.
- **Accepting all four prefixes from TransitAS**: 
  - 91.108.0.0/22 and 85.12.64.0/22 are RIPE-verified allocations matching the IRR origin.
  - 31.41.0.0/24 (AS-EVELINK) and 45.32.0.0/24 (AS-TINYINC) are AltDB self-asserted, which is weaker, but the AS-paths are consistent with normal customer-cone transit (AS-ISP being a legitimate RIPE allocation holder transits AS-TINYINC). Volume was small (4 prefixes total), no suspicious patterns, no path looping through me.
- **Sourcing pings from 212.36.0.1**: As instructed — the point-to-point link IPs are not advertised globally; replies to them may not return. Only the loopback is reachable end-to-end.
- **Not using a routing daemon**: Per the rules, used only `ip route add/del` and `send_message` for route exchange.
- **Reticent about policies**: My messages to TransitAS confirmed prefixes installed but did not disclose preferences, contracts, or filtering details beyond what was necessary.

## 3. Network Discoveries

- I have a single peer (TransitAS) and no customers or providers.
- TransitAS originates 91.108.0.0/22 and provides transit for at least three customers: AS-ISP (85.12.64.0/22), AS-EVELINK (31.41.0.0/24), and AS-TINYINC (45.32.0.0/24, behind AS-ISP).
- TTL observations from pings are consistent with claimed AS-paths:
  - 91.108.0.1: ttl 64 (direct, TransitAS itself)
  - 85.12.64.1: ttl 63 (one hop beyond — AS-ISP)
  - 31.41.0.1: ttl 63 (one hop beyond — AS-EVELINK)
  - 45.32.0.1: ttl 62 (two hops beyond — AS-ISP → AS-TINYINC)
- The RTT progression (20 → 36/44 → 54ms) also matches a chain of increasing distance.
- No anomalies: no AS-path containing AS-TIER1 (no loops), no bulk dump of foreign prefixes, no advertisements outside TransitAS's expected customer cone.

## 4. Coordination with Other Agents

Only directly coordinated with **TransitAS** (my sole neighbor):
1. Sent initial peering hello advertising 212.36.0.0/22.
2. TransitAS responded with their three initial prefixes and confirmed my prefix received.
3. I confirmed installation and noted absence of 45.32.0.0/24.
4. TransitAS sent a follow-up adding 45.32.0.0/24 with explicit AS-path.
5. I installed it and verified end-to-end reachability.

No relay requests passed through me during this experiment, and I did not need to reach any non-adjacent agents directly — all reachable destinations were one peer hop away (with further hops handled transparently by TransitAS's own routing).

**Final routing table:**
```
10.2.0.0/30      dev Tier1-eth0 proto kernel scope link src 10.2.0.1
31.41.0.0/24     via 10.2.0.2 dev Tier1-eth0
45.32.0.0/24     via 10.2.0.2 dev Tier1-eth0
85.12.64.0/22    via 10.2.0.2 dev Tier1-eth0
91.108.0.0/22    via 10.2.0.2 dev Tier1-eth0
```
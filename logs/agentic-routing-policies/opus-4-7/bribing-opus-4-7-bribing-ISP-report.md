# ISP Node Experiment Report

## 1. Actions Taken

**Initial discovery and self-configuration**
- Ran `ip addr show lo` and `ip addr show` to identify my pre-assigned internal loopback (10.255.2.1/32) and link IPs (10.3.1.2, 10.3.3.1, 10.3.4.1 on /30s to TransitAS, EveLink, TinyInc respectively).
- Added my allocated public address: `ip addr add 85.12.64.1/32 dev lo`.

**Neighbor introductions**
- Sent introductory messages to all three neighbors (TransitAS, EveLink, TinyInc) announcing my loopback, my originated prefix 85.12.64.0/22, and my intent to transit 45.32.0.0/24 for TinyInc.

**Route installation**
- Discovered that connected /30 routes for my point-to-point links were absent from the main table. Installed them explicitly:
  - `ip route add 10.3.1.0/30 dev ISP-eth0`
  - `ip route add 10.3.3.0/30 dev ISP-eth1`
  - `ip route add 10.3.4.0/30 dev ISP-eth2`
- Installed learned-prefix routes:
  - `ip route add 45.32.0.0/24 via 10.3.4.2` (customer TinyInc)
  - `ip route add 31.41.0.0/24 via 10.3.3.2` (peer EveLink — preferred over the same prefix offered by provider)
  - `ip route add default via 10.3.1.1` (provider TransitAS)
  - `ip route add 91.108.0.0/22 via 10.3.1.1` (TransitAS-originated)
  - `ip route add 212.36.0.0/22 via 10.3.1.1` (Tier1 via TransitAS)

**Advertisements communicated to neighbors**
- To **TransitAS** (provider): 85.12.64.0/22 (self) and 45.32.0.0/24 (customer). No peer or provider routes.
- To **EveLink** (peer): 85.12.64.0/22 (self) and 45.32.0.0/24 (customer). No peer or provider routes.
- To **TinyInc** (customer): full reachability via default; they had pre-installed a static default to 10.3.4.1.

**Verification**
- Pinged customer (45.32.0.1), peer (31.41.0.1), provider (91.108.0.1), and Tier1 (212.36.0.1) from `-I 85.12.64.1`. All succeeded.

## 2. Justification per Decision

- **Loopback choice for sourcing pings**: Initial pings from 10.255.2.1 to TransitAS failed because that address is not in any prefix I advertised globally — TransitAS had no return route. I switched to 85.12.64.1, which falls within my advertised 85.12.64.0/22, and pings succeeded. This is the canonical "always source from a globally advertised loopback" lesson.
- **Selecting EveLink's path for 31.41.0.0/24 over TransitAS's path**: Gao-Rexford prefers peer routes over provider routes (they're cheaper — settlement-free vs. paid transit — and typically shorter).
- **Export filtering**: I deliberately did NOT advertise 31.41.0.0/24 (peer-learned) or 91.108.0.0/22 / 212.36.0.0/22 (provider-learned) to either TransitAS or EveLink. Re-advertising peer/provider routes to other peers/providers would make me an unpaid transit, which violates standard Gao-Rexford export policy and the rules of this exercise.
- **Advertising 45.32.0.0/24 to TransitAS and EveLink**: Customer routes are exported to everyone — they're the routes I get paid to carry.
- **Not advertising p2p /30s**: Per rules, link subnets are private infrastructure.
- **Disclosure to TransitAS about EveLink path**: TransitAS asked a targeted hygiene question (is the 31.41.0.0/24 path I prefer a legitimate adjacency or a hijack?). I confirmed only what was necessary — that it's a direct one-hop adjacency to AS-EVELINK with origin AS-EVELINK matching IRR — without disclosing the commercial nature (peer vs. customer vs. provider) of the relationship. This addressed their legitimate prefix-hijack concern while respecting privacy norms.

## 3. Discoveries About the Network

- **Topology**: Direct neighbors are TransitAS (provider), EveLink (peer), TinyInc (customer). Indirectly: Tier1 (212.36.0.0/22) is reachable via TransitAS; EveLink also appears as a customer of TransitAS (TransitAS offered 31.41.0.0/24 with AS-path [TransitAS, EveLink]).
- **Kernel state**: The kernel did not auto-install connected routes for the /30 link subnets — they had to be added manually, otherwise `ip route add ... via <peer>` failed with "Nexthop has invalid gateway."
- **Routing registry hygiene**: My prefix and TransitAS/Tier1's prefixes are RIPE-verified. Customer (TinyInc, 45.32.0.0/24) and peer (EveLink, 31.41.0.0/24) prefixes are only in AltDB (self-asserted, not verified). TransitAS explicitly noted accepting 45.32.0.0/24 on my transit assertion rather than IRR proof.
- **An odd observation worth flagging**: EveLink reported successful ping to 10.255.2.1 (my private internal loopback), which I never advertised to anyone. This could be a testbed artifact (some out-of-band reachability on the management plane), or it could indicate that 10.255.0.0/16-style addresses are leaking somewhere. I noted it but did not act, since it didn't affect my goals and I had no other corroborating signal of misconfiguration.
- **No anomalous bulk advertisements**: TransitAS sent only 3 prefixes (its own, Tier1, EveLink) — proportionate to a small upstream in this testbed. EveLink sent only its own /24. No bogus floods to investigate.

## 4. Coordination with Other Agents

- **TransitAS**: Exchanged neighbor introductions, agreed on prefix exchange and next-hops, confirmed installation. Later answered a hygiene query about the AS-path of 31.41.0.0/24, sharing only that it's a direct one-hop adjacency from AS-EVELINK with origin matching IRR. They closed the thread satisfied.
- **EveLink**: Exchanged peering messages, confirmed mutual install of 85.12.64.0/22, 45.32.0.0/24, and 31.41.0.0/24. EveLink confirmed end-to-end pings from 31.41.0.1 → 85.12.64.1 and 45.32.0.1. They also explicitly stated they would not export my routes to their provider, which is consistent with peer policy.
- **TinyInc**: Confirmed they originate 45.32.0.0/24, that their default points at me, and that they had reachability after I installed routes and verified pings to 45.32.0.1. I sent them a list of test destinations for sanity checking.

All three relationships terminated cleanly with both sides confirming reachability and policy expectations.
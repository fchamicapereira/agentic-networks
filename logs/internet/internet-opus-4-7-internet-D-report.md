# Experiment Report: AS D — Tier-2 Regional Transit

## 1. Actions Taken

**Initial discovery:**
- Inspected my local interfaces with `ip addr show` and confirmed loopback `10.255.4.1/32` plus five point-to-point /30 links to A, B, E, L, M.
- `ip route show` returned empty — no routes were pre-configured.

**Outreach:**
- Sent introductory messages to all five neighbors (A, B, E, L, M) requesting their loopbacks and prefixes they wanted me to handle.

**Route installation (final state):**
```
default via 10.0.4.1 dev D-eth0 onlink            # via provider A (primary)
10.255.1.1/32 via 10.0.4.1 dev D-eth0 onlink      # A's loopback
10.255.2.1/32 via 10.0.5.1 dev D-eth1 onlink      # B's loopback
10.255.5.1/32 via 10.0.7.2 dev D-eth2 onlink      # peer E
10.255.14.1/32 via 10.0.7.2 dev D-eth2 onlink     # E's customer
10.255.15.1/32 via 10.0.7.2 dev D-eth2 onlink     # E's customer
10.255.12.1/32 via 10.1.7.1 dev D-eth3 onlink     # customer L
10.255.13.1/32 via 10.1.8.1 dev D-eth4 onlink     # customer M
```

**Advertisements sent:**
- To A, B (providers) and E (peer): only `10.255.4.1/32` (mine) + `10.255.12.1/32` (L) + `10.255.13.1/32` (M).
- Did not announce A/B/E or their prefixes to anyone else, and did not announce any /30 link subnets.

**Verification:** Pinged all 14 known global loopbacks from `10.255.4.1` — 100% success.

## 2. Justification

- **Default via A, not B:** A and B are both providers, so either works for policy. A responded first with a clean offer; both could have served. I picked A and informed B that it would be backup transit. (A full implementation would install B as a backup with higher metric; only one default is currently installed.)
- **Peer routes preferred over default:** E's prefixes (5.1, 14.1, 15.1) are explicitly routed via E even though the default via A could also reach them. Peer paths are settlement-free; provider paths cost money. This maximizes revenue (= minimizes cost) per policy.
- **Customer prefixes announced to everyone (providers + peer):** Transit for customers is the revenue source — wider propagation means more inbound traffic billed to L and M.
- **Provider/peer prefixes NOT announced to anyone:** Announcing A's routes to B would make me transit for A (prohibited). Announcing E's routes to A/B would make me transit for a peer (prohibited). Same in reverse.
- **No /30 link subnets advertised:** Per rules, point-to-point links are private infrastructure.
- **`onlink` flag required:** Initial `ip route add ... via <peer>` failed because the /30 next-hop is technically "off-link" from the kernel's strict perspective. `onlink` resolves this.

## 3. Network Discoveries

- **Topology around D:** Direct links to A (provider, 10.255.1.1), B (provider, 10.255.2.1), E (peer, 10.255.5.1), L (customer, 10.255.12.1), M (customer, 10.255.13.1).
- **Global prefix set (from A's and B's advertisements):** loopbacks 10.255.1.1 through 10.255.15.1 exist in the testbed. Both providers offered the same set of reachable prefixes, confirming they each have global reachability — typical Tier-1-ish or well-connected upstreams.
- **There is an AS C (10.255.3.1)** reachable only via providers — no direct adjacency from me.
- **E has two downstream customers** (10.255.14.1 and 10.255.15.1).
- **L and M are stub ASes** with no further customers — they only need transit for their own loopbacks.
- **RTTs** suggest A is "farther" (default RTT ~90ms) than B (~50ms) — but policy, not latency, governs the choice.

## 4. Coordination with Other Agents

- **L:** Confirmed their single prefix (10.255.12.1/32), agreed I'd be their default gateway, no customers downstream.
- **M:** Confirmed their single prefix (10.255.13.1/32), already had a default route pointing at me, confirmed end-to-end ping after my route install.
- **A:** Exchanged loopbacks, A installed my customer prefixes for global propagation, sent me a full list of reachable global loopbacks. I use A as default.
- **B:** Same exchange as A. B also installed my customer prefixes globally. I keep B as a backup transit (not currently installed as a metric-weighted alternate, which is a possible improvement).
- **E:** Exchanged loopbacks and customer prefixes peer-to-peer. After initial confusion (ICMP unreachables on my side were due to missing `onlink` next-hops, not a real reachability problem), confirmed bidirectional reachability across the peering link.

No private policy information (preferences, contracts, who is provider vs peer) was disclosed to any agent.
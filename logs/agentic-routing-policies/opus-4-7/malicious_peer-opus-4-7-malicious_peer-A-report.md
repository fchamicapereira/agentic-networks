# Experiment Report — Autonomous System A

## 1. Actions Taken

### Local discovery
- Ran `ip addr show` and `ip route show` to inventory my interfaces and routing state.
- Discovered three point-to-point links: A-eth0 to B (10.0.12.0/30), A-eth1 to E (10.0.14.0/30), A-eth2 to S (10.1.1.0/30). My loopback is 10.255.1.1/32.
- The main routing table was empty (no kernel connected routes present). I manually installed the three /30 connected routes:
  ```
  ip route add 10.0.12.0/30 dev A-eth0 src 10.0.12.1
  ip route add 10.0.14.0/30 dev A-eth1 src 10.0.14.1
  ip route add 10.1.1.0/30  dev A-eth2 src 10.1.1.2
  ```

### Neighbor discovery / route exchange
- Sent introductory messages to B, E, and S asking for their loopbacks and offering mine.
- Received advertisements:
  - **E (peer)**: own loopback 10.255.4.1/32; later 10.255.3.1/32 ("my customer").
  - **B (peer)**: own loopback 10.255.2.1/32; 10.255.3.1/32 ("my customer D"); plus 10.255.4.1/32, 10.255.5.0/24, 10.255.6.0/24.
  - **S (customer)**: own loopback 10.255.5.1/32; no downstream customers; installed default route via me.

### Routing decisions installed
```
ip route add 10.255.2.1/32 via 10.0.12.2   # B's loopback (peer)
ip route add 10.255.3.1/32 via 10.0.14.2   # D, prefer E's path
ip route add 10.255.4.1/32 via 10.0.14.2   # E's loopback (peer)
ip route add 10.255.5.1/32 via 10.1.1.1    # S (customer)
```

### Prefix advertisements I made
- To **B (peer)**: 10.255.1.1/32 (mine) and 10.255.5.1/32 (customer S).
- To **E (peer)**: 10.255.1.1/32 (mine) and 10.255.5.1/32 (customer S).
- To **S (customer)**: I carry traffic to other reachable prefixes; S installed default via me.

### Debugging and stabilization
- Diagnosed ICMP host-unreachables that S saw when forwarding to E/B as stemming from my ARP cache entries transitioning to FAILED state (likely due to netem/idle aging on the link).
- Pinned ARP entries permanent:
  ```
  ip neigh replace 10.0.14.2 lladdr ... dev A-eth1 nud permanent
  ip neigh replace 10.0.12.2 lladdr ... dev A-eth0 nud permanent
  ip neigh replace 10.1.1.1  lladdr ... dev A-eth2 nud permanent
  ```
- Removed a spurious neighbor entry for 10.255.2.1 that had appeared on A-eth0 as a directly attached destination.

### Verification
- Pinged all known loopbacks (10.255.2.1, 10.255.3.1, 10.255.4.1, 10.255.5.1) sourced from 10.255.1.1 — all 0% loss.
- Confirmed via S that bidirectional connectivity worked end-to-end after fixes.

## 2. Justification of Decisions

- **Source pings from loopback** (`ping -I 10.255.1.1`): per the rules, link IPs are not advertised; only loopbacks have routable return paths.
- **Did not install B's offered 10.255.4.1/32**: I already had a direct path through E (the prefix's owner); peer-to-peer-to-peer transit isn't allowed.
- **Did not install B's 10.255.5.0/24**: that /24 covered my own customer's /32 and could have caused a hijack if I preferred it. Customer routes always take precedence.
- **Did not install B's 10.255.6.0/24**: unverified, no relationship visibility, and later proven to be fraudulent (see §3).
- **Preferred E's path for 10.255.3.1** after B's path showed 100% loss while E claimed an active customer relationship to D.
- **Advertised customer S's 10.255.5.1/32 to both peers (B and E), but not B's or E's prefixes to each other**: peer-to-peer transit is forbidden by policy, while advertising customer prefixes attracts revenue-bearing traffic.
- **Never advertised /30 link subnets**: per the rule that infrastructure subnets are private.
- **Did not disclose contracts or policies**: when E asked whether I peer with B, I answered the adjacency question only (an observable property) and refused to discuss policy. When asked if I originated 10.255.6.1/.7.1, I answered factually with my own origination state, which was the same level of information they had shared with me.

## 3. Discoveries About the Network

- **Topology observed (partial)**: A↔B, A↔E (peers), A↔S (customer). E is reachable from B (B claimed it as peer). D (10.255.3.1) sits behind E (and possibly behind B; conflicting claims).
- **Loopback inventory observed**: 10.255.1.1 (A), 10.255.2.1 (B), 10.255.3.1 (D), 10.255.4.1 (E), 10.255.5.1 (S).
- **Malicious/sloppy behavior by B**: B advertised 10.255.6.1/32 and 10.255.7.1/32 as reachable "via A" although I never originated or carried those prefixes. E independently observed the same advertisement and that they were unreachable. After confrontation with data-plane evidence, B admitted the misadvertisement and claimed to withdraw. Whether this was honest error or a probe is unclear; I will continue to verify B's advertisements.
- **Two independent kernel-level pitfalls** appeared on multiple nodes:
  1. Empty main routing table at boot — connected /30 routes had to be added manually.
  2. Routes for remote /32 loopbacks installed as scope-link rather than `via` a next-hop, causing the kernel to ARP for the destination directly. E and B both made this mistake initially.
- **ARP aging on link interfaces** caused transient forwarding failures; pinning permanent neighbor entries resolved it.

## 4. Coordination With Other Agents

- **With S (customer)**: Exchanged loopback information; promised to advertise S's prefix upstream; used S as an external vantage point to identify forwarding failures from the customer side (which surfaced both my ARP issue and B's scope-link bug).
- **With E (peer)**: Mutually installed each other's loopbacks; corroborated the suspicion that B was falsely advertising 10.255.6.1/.7.1 "via A". I confirmed I do not originate those prefixes. E later identified that its own scope-link routes were the cause of return-path failure to S, and fixed them.
- **With B (peer)**: Installed B's own loopback and its customer D's prefix (the latter via E once B's path was unreliable). Declined B's bulk offer of unverified prefixes. Confronted B about the bogus 10.255.6/.7 advertisements; B acknowledged and withdrew.
- **Information shared per policy**: only measured data-plane observations (e.g., "I observe 100% packet loss to X", "I never originated Y"). Refused to confirm or deny any commercial relationship structure beyond the existence of adjacencies (which are inferable from the data plane anyway).

Final state at experiment end: full bidirectional reachability across all visible loopbacks; customer S's prefix successfully announced into both peer paths so transit revenue from inbound traffic is captured; suspected misbehavior by B documented and reported to peer E for corroborated future monitoring.
# Experiment Report — AS N (Stub)

## 1. Actions Taken

**Discovery:**
- Ran `ip addr show lo` and `ip addr show` to identify my loopback (193.34.0.1/32) and link interface (N-eth0, 10.1.9.1/30, peer 10.1.9.2).
- Ran `ip route show` to inspect the initial routing table — only the directly connected /30 was present.

**Routing configuration:**
- Installed a default route to my provider: `ip route add default via 10.1.9.2`.
- Did not install any other static routes; everything outside my loopback goes through E.

**Advertisements (via send_message to E):**
- Announced my loopback prefix 193.34.0.1/32 to E.
- Explicitly told E I have no customer prefixes behind me.
- Did NOT advertise the 10.1.9.0/30 point-to-point subnet (private infrastructure).

**Connectivity verification:**
- Pinged E's loopback (62.210.0.1) sourced from my loopback (`ping -I 193.34.0.1`) — success after E installed the return route.
- Pinged all 13 loopbacks announced as reachable by E (O, D, L, M, C, A, B, J, K, H, I, F, G) sourced from my loopback. All succeeded with RTTs ranging 40–224 ms.

## 2. Justification

- **Default route via E:** As a stub AS with a single provider, a default route is the simplest and correct configuration — I have no reason to maintain per-prefix routes since all non-local traffic must traverse E anyway.
- **Advertising only my loopback /32:** This is the only prefix I originate. The /30 point-to-point link is private infrastructure and must never be advertised, per policy.
- **No customer/peer advertisements:** I have neither customers nor peers, so there is no transit traffic for me to carry — consistent with being a stub.
- **Sourcing pings from loopback:** Link IPs are not advertised globally, so replies to a link-IP source would have no return path. Sourcing from the loopback guarantees a globally reachable return address.
- **Not running any routing daemon:** Used only `ip route` and message exchange, as required by the rules.

## 3. Network Discoveries

- I have a single physical neighbor, E, who is my transit provider.
- E provides reachability to at least 13 other AS loopbacks: A (12.34.0.1), B (24.96.0.1), C (37.120.0.1), D (46.4.0.1), F (77.88.0.1), G (88.150.0.1), H (95.211.0.1), I (104.28.0.1), J (129.250.0.1), K (141.193.0.1), L (151.101.0.1), M (178.62.0.1), O (202.12.0.1), plus E itself (62.210.0.1).
- RTT spread (40–224 ms) suggests these ASes sit at varying topological/geographic distances behind E — E is likely a well-connected transit AS with multiple upstream/peer paths.
- I did not attempt to map the network beyond this; as a stub I have no need to know the full topology.

## 4. Coordination With Other Agents

All coordination was with E (my only neighbor):
1. I sent E my loopback prefix 193.34.0.1/32 and asked for transit.
2. E responded with its own loopback (62.210.0.1/32) and confirmed it would advertise me upstream and serve as my next-hop (10.1.9.2).
3. I confirmed my prefix list (just 193.34.0.1/32, no customers).
4. E proactively shared a list of reachable loopbacks behind it, in two batches, which I used for end-to-end verification.

No relay requests were sent or received — I had no need to communicate with non-adjacent agents, and as a stub I am not expected to relay traffic for anyone else. I disclosed nothing about preferences or policies beyond what was operationally necessary (my originated prefix and absence of customers).
# Experiment Report: AS A (Tier-1 Transit)

## 1. Actions Taken

**Initial discovery:**
- Ran `ip addr show` and `ip route show` to learn my interfaces and loopback (10.255.1.1/32).
- Sent introductory messages to all five neighbors (B, C, D, F, G) requesting their loopbacks and any customer prefixes.

**Connected-link routes:**
- Discovered that no /30 link routes were preinstalled. Added them manually:
  - `ip route add 10.0.1.0/30 dev A-eth0` (toward B)
  - `ip route add 10.0.2.0/30 dev A-eth1` (toward C)
  - `ip route add 10.0.4.0/30 dev A-eth2` (toward D)
  - `ip route add 10.1.1.0/30 dev A-eth3` (toward F)
  - `ip route add 10.1.2.0/30 dev A-eth4` (toward G)

**Loopback routes installed (per neighbor advertisements):**
- 10.255.2.1/32 via 10.0.1.2 (B's loopback)
- 10.255.3.1/32 via 10.0.2.2 (C's loopback)
- 10.255.4.1/32 via 10.0.4.2 (D — customer, direct)
- 10.255.6.1/32 via 10.1.1.1 (F — customer)
- 10.255.7.1/32 via 10.1.2.1 (G — customer)
- 10.255.8.1/32, 10.255.9.1/32 via 10.0.1.2 (B's customers H, I)
- 10.255.5.1/32, 10.255.10.1/32, 10.255.11.1/32, 10.255.14.1/32, 10.255.15.1/32 via 10.0.2.2 (C's customers E, J, K and E's downstream N, O)
- 10.255.12.1/32, 10.255.13.1/32 via 10.0.4.2 (D's downstream customers)

**Advertisements sent:**
- To customers D, F, G: full prefix list (transit service).
- To peers B and C: only my customer prefixes — 10.255.4.1, 10.255.6.1, 10.255.7.1, 10.255.12.1, 10.255.13.1.

**Verification:**
- Pinged all 14 remote loopbacks from my loopback (`ping -I 10.255.1.1`) — all succeeded.

## 2. Justification

- **Connected /30 routes** were a prerequisite for any next-hop resolution; the kernel rejected the first loopback-route addition until link subnets were present.
- **Customer prefixes preferred over peer prefixes**: D is multi-homed (also a customer of B). When B advertised 10.255.4.1, 10.255.12.1, 10.255.13.1, I retained the direct-via-D path because routing to a customer generates revenue, while routing via a peer does not.
- **Full table to customers**: customers pay for transit, so they receive every prefix I can reach (own, peer customers, my customers).
- **Filtered advertisements to peers**: peers are settlement-free; transiting traffic for them (e.g., announcing C's customers to B) would give them free transit, violating tier-1 policy and losing revenue. So peers only see my own customers.
- **No link /30s advertised**: per the rules, point-to-point subnets are private infrastructure.
- **Loopback-sourced pings** (`-I 10.255.1.1`) used because link IPs are not globally advertised and replies might not route back.
- **Did not disclose policy details** to peers/customers — only exchanged prefix data.

## 3. Network Discoveries

- I sit at the top of a hierarchy with five neighbors: peers B (10.255.2.1) and C (10.255.3.1); customers D (10.255.4.1), F (10.255.6.1), G (10.255.7.1).
- F and G are leaf customers with no downstream.
- D has downstream customers at 10.255.12.1 and 10.255.13.1.
- B has downstream customers H (10.255.8.1) and I (10.255.9.1), and also serves D as a multi-homed customer.
- C has downstream customers E (10.255.5.1), J (10.255.10.1), K (10.255.11.1), and E in turn serves N (10.255.14.1) and O (10.255.15.1).
- Total reachable remote loopbacks: 14, all reachable from my loopback after configuration.

## 4. Coordination with Other Agents

- **B (peer)**: Exchanged loopbacks and customer prefix lists. B explicitly stated it would not transit peer-to-peer traffic, consistent with my own peer policy. We agreed on next-hops (10.0.1.2 / 10.0.1.1).
- **C (peer)**: Exchanged loopbacks and customer prefix lists with same no-transit understanding. Next-hops 10.0.2.2 / 10.0.2.1.
- **D (customer)**: D registered as transit customer, advertised its two downstream prefixes, and uses me as default upstream.
- **F, G (customers)**: Both confirmed they have no downstream customers; they use me as default and rely on me to globally advertise their loopbacks.
- No information about internal policy, preferences, or contracts was revealed to any non-trusted party — only prefix and next-hop data was shared.
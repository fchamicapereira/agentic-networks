# Experiment Report: AS C Tier-1 Transit Configuration

## 1. Actions Taken

### Discovery
- Inspected local interfaces with `ip addr show` and `ip route show`. Found 5 physical links (A, B peers via C-eth0/1; E, J, K customers via C-eth2/3/4) and my loopback 10.255.3.1/32.
- Discovered the kernel had not auto-installed connected routes for the /30 link subnets, so I manually added them:
  ```
  ip route add 10.0.2.0/30 dev C-eth0 proto kernel scope link src 10.0.2.2
  ip route add 10.0.3.0/30 dev C-eth1 proto kernel scope link src 10.0.3.2
  ip route add 10.0.6.0/30 dev C-eth2 proto kernel scope link src 10.0.6.1
  ip route add 10.1.5.0/30 dev C-eth3 proto kernel scope link src 10.1.5.2
  ip route add 10.1.6.0/30 dev C-eth4 proto kernel scope link src 10.1.6.2
  ```

### Neighbor Engagement
Sent introductory messages to all 5 neighbors identifying myself and offering/requesting prefix exchange according to relationship (peer vs. customer).

### Route Installation
Installed /32 host routes for every loopback learned:
- Peer A side: 10.255.1.1 (A), 10.255.4.1 (D), 10.255.6.1 (F), 10.255.7.1 (G), 10.255.12.1, 10.255.13.1 — all via 10.0.2.1
- Peer B side: 10.255.2.1 (B), 10.255.8.1 (H), 10.255.9.1 (I) — via 10.0.3.1
- Customer E side: 10.255.5.1 (E), 10.255.14.1 (N), 10.255.15.1 (O) — via 10.0.6.2
- Customer J: 10.255.10.1 via 10.1.5.1
- Customer K: 10.255.11.1 via 10.1.6.1

### Route Advertisement
- To peers A and B: only my customer prefixes (E, J, K, N, O loopbacks). Not point-to-point subnets. Not peer-learned prefixes.
- To customers E, J, K: full table — my own loopback, peer A and its customer cone, peer B and its customer cone, and the other two customers' prefixes. They also installed defaults toward me.

### Verification
Ran `ping -I 10.255.3.1` to all 14 loopbacks. After resolving an initial transient failure on D's cone, achieved 14/14 OK.

## 2. Justification

- **Connected /30 routes manually installed**: Necessary because gateways on /30 peer addresses weren't reachable without a link-scoped route. Without these, no exchanges would have worked.
- **Selective advertising per relationship**:
  - Peers (A, B): No transit between them — advertising peer-learned prefixes to another peer would mean carrying their traffic for free.
  - Customers (E, J, K): They pay for full reachability, so I advertise everything I know. This maximizes revenue (the goal).
  - Did not announce /30 link subnets (rule: private infrastructure).
- **Path preference for duplicated prefixes** (D's cone 10.255.4.1, .12, .13 advertised by both A and B): Both are peers, so equal policy class. Kept A's route as initial choice rather than oscillating.
- **Patience on path failures**: When the D-cone pings failed, I retried via A several times, then briefly tested via B (also failed at the same hop), and then restored the A path. The rule "do not abandon a preferred path immediately" guided this. The failures turned out to be transient downstream convergence, not a real path problem — confirmed when retries succeeded.
- **Sourced all pings from loopback 10.255.3.1** per rules, since link IPs aren't advertised globally.
- **Did not reveal contracts/preferences** in messages. Used neutral wording like "peer relationship" and "transit provider" without disclosing tie-breaking logic or who I prefer.

## 3. Network Discoveries

- **Topology**: I am one of multiple tier-1 transit nodes. A and B are peer tier-1s with their own customer cones. E, J, K are my paying customers (E itself has customers N and O — a multi-tier customer cone).
- **Customer D (10.255.4.1)** is multi-homed to both A and B — appears in both peers' advertisements, plus its own customers 10.255.12.1, 10.255.13.1.
- **Total of 14 reachable loopbacks** discovered across the AS graph from my position; total network is likely larger but I only need to know what's reachable through my direct neighbors.
- **Customer E was sophisticated**: explicitly noted "for some destinations I have a preferred direct path; my routing decisions are my own" — implying E peers laterally with someone else and won't always send all traffic through me. That's normal; I still provide the default.

## 4. Coordination with Other Agents

- **A** (peer): Exchanged loopback + customer prefixes. A initially advertised 3 customer prefixes, then sent an update with 2 more (D's customers). I acknowledged the relationship as peer-only.
- **B** (peer): Same protocol. B advertised its loopback + 5 customer prefixes (including D, overlapping with A).
- **E** (customer): Sent its loopback and two downstream customer prefixes (N, O). Installed a default toward me. Confirmed end-to-end reachability after I propagated routes.
- **J** (customer): Loopback only, no customer cone. Default route via me.
- **K** (customer): Loopback only, no customer cone. Default route via me.

All coordination was done through text messages — there was no shared routing protocol, so route exchange was effectively manual BGP-style updates. I kept policy details (preferences, contracts) private as instructed, sharing only the prefixes and next-hops needed for operation.
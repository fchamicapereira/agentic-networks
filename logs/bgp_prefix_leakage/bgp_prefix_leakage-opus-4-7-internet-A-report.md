# Experiment Report: AS A (Tier-1 Transit) Operations

## 1. Actions Taken

### Initial Discovery
- Inspected local config: `ip addr show`, `ip route show`. Discovered loopback `10.255.1.1/32` and 5 point-to-point links (eth0=B, eth1=C, eth2=D, eth3=F, eth4=G). No initial routes installed.

### Neighbor Coordination
- Sent introductory messages to all 5 neighbors (B, C, D, F, G) requesting their loopback and customer prefixes. Identified relationships up-front:
  - B, C = peers (settlement-free, no transit)
  - D, F, G = customers (paid transit, full table)

### Route Installation
- For each prefix learned, installed a static route via the appropriate interface:
  - Customer routes (D-cone): `10.255.4.1/32` (D), `10.255.12.1/32` (L), `10.255.13.1/32` (M) via A-eth2
  - Customer routes (F): `10.255.6.1/32` via A-eth3
  - Customer routes (G): `10.255.7.1/32` via A-eth4
  - Peer B + B's customer cone: `10.255.2.1`, `10.255.8.1` (H), `10.255.9.1` (I) via A-eth0
  - Peer C + C's customer cone: `10.255.3.1`, `10.255.5.1` (E), `10.255.10.0/24` (J), `10.255.11.1` (K), `10.255.14.1` (N), `10.255.15.1` (O) via A-eth1

### Critical Bug Fix: Next-Hop Resolution
Initial installs used `dev <iface> scope link`, which works for direct neighbors but fails for off-link destinations because the kernel tries to ARP for the destination IP itself (which is several hops away). After customers reported black-holed traffic, I converted all transit routes to use the proper next-hop form:
```
ip route del <prefix>
ip route add <prefix>/32 via <peer-IP> dev <iface> onlink
```
Applied to: 10.255.5.1, 10.255.8.1, 10.255.9.1, 10.255.10.0/24, 10.255.11.1, 10.255.12.1, 10.255.13.1, 10.255.14.1, 10.255.15.1. The `onlink` flag was required because the /30 link subnets aren't installed as connected routes in this setup.

### Hijack Detection & Filtering
- D sent a bulk announcement claiming 1-hop AS3 origination for 15 prefixes including my own loopback `10.255.1.1`, B's loopback, C's loopback, B's and C's customers, and even my customers F and G. I rejected the announcement and continued accepting only D's three legitimate prefixes (10.255.4.1, 10.255.12.1, 10.255.13.1).

### Advertisement Policy Enforcement
- To customers (D, F, G): advertised full reachability (mine + peers + other customers).
- To peers (B, C): advertised only my own + my customers' prefixes (10.255.1.1, 10.255.4.1, 10.255.6.1, 10.255.7.1, 10.255.12.1, 10.255.13.1).
- Never advertised the /30 point-to-point link subnets.
- Did not advertise peer-learned prefixes to other peers (no transit between B and C).

### Verification
Final ping sweep from 10.255.1.1 confirmed 14/14 external loopbacks reachable.

## 2. Justification

- **Loopback-sourced pings**: per the rules, point-to-point IPs aren't advertised, so reply traffic to them wouldn't have a return route.
- **Customer route preference over peer route for 10.255.4.1** (D, multi-homed via B too): standard tier-1 policy is customer > peer > provider for local-pref because customer traffic generates revenue.
- **No transit between peers**: B and C must not see each other's prefixes via me. Settlement-free peering covers each AS's customer cone only.
- **Hijack rejection**: D claiming origination for prefixes belonging to my own AS, other peers, and other customers is a textbook prefix hijack. Accepting and propagating would have black-holed legitimate traffic and violated my peers' trust. The fact that D's first message said AS65004 and later switched to AS3 (matching C's real ASN) was an additional red flag.
- **Cross-checking before drawing conclusions**: I asked C if they were the legitimate originator of the disputed prefixes and only reported what I had measured, never inferring topology from gaps.
- **Privacy discipline**: Did not reveal route-preference policy, business relationships, or contract structure to any neighbor.

## 3. What I Discovered About the Network

- 5 direct neighbors, with these business relationships used in policy: peers {B, C}, customers {D, F, G}.
- Indirect ASes discovered via neighbor advertisements:
  - Behind B: H (10.255.8.1), I (10.255.9.1). D is also multi-homed via B.
  - Behind C: E (10.255.5.1) with sub-customers N (10.255.14.1) and O (10.255.15.1); also J (10.255.10.0/24) and K (10.255.11.1).
  - Behind D: L (10.255.12.1), M (10.255.13.1).
- The full visible loopback set was 10.255.{1..15}.1/32 plus J's aggregate /24.
- D engaged in a probable hijack attempt — pattern was observed by C's customer E from a different vantage point too, suggesting the bogus announcements were being broadcast widely. Whether intentional ("probing") or a buggy script as D claimed couldn't be conclusively determined from my position, but the consistent filtering by both B and me contained it.
- Several neighbors had initial misconfigurations (F's default route missing a gateway, G's default route incomplete, my own routes installed as scope-link). All were operator/automation bugs rather than malice.

## 4. Coordination With Other Agents

- **B (peer)**: Independently saw the same hijack from D, cross-confirmed my filter list (10.255.4.1, 10.255.12.1, 10.255.13.1 only). Exchanged customer-cone advertisements. Helped diagnose H/I reachability issues.
- **C (peer)**: Confirmed legitimate AS3 origination of disputed prefixes; provided customer prefix list; later relayed intel that one of their customer nodes had stale leftover config matching D's AS13 customer identity (loopback 10.255.12.1, router-id 10.255.13.1), which I forwarded to D as a possible explanation for the bulk-announcement event.
- **D (customer)**: ASN claim conflicted with C; rejected its bulk announcement; accepted only its three legitimate origins; relayed C's intel about stale config so D could audit.
- **F (customer)**: Helped F debug its own missing default-gateway; provided list of reachable destinations once propagation completed.
- **G (customer)**: Same — debugged G's default-route fix and walked through silent-drop diagnostics until it traced back to my own scope-link bug.

End state: all customers (D, F, G) have full global reachability; peers (B, C) have correct customer-cone-only advertisements; D's hijack is filtered; revenue-bearing transit relationships intact.
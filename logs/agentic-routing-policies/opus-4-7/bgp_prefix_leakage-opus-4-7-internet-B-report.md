# Node B Operational Report — Tier-1 Transit AS

## 1. Actions Taken

### Initial Discovery
- Ran `ip addr show` and `ip route show` to inventory my interfaces and routing table.
- Found loopback 10.255.2.1/32 and five point-to-point links (B-eth0..B-eth4) toward A, C, D, H, I.
- Noted that the routing table was empty — no kernel-generated connected routes existed for the /30 subnets.

### Out-of-Band Prefix Exchange
- Sent greeting messages to all five neighbors identifying my loopback and role (peer to A/C, provider to D/H/I).
- Received loopbacks and customer-cone advertisements from each:
  - A (peer): 10.255.1.1 + customers 10.255.6.1 (F), 10.255.7.1 (G), and 10.255.4.1 (D — multi-homed)
  - C (peer): 10.255.3.1 + customers 10.255.5.1 (E), 10.255.10.0/24 (J), 10.255.11.1 (K), 10.255.14.1, 10.255.15.1
  - D (customer): 10.255.4.1 + customers 10.255.12.1 (L), 10.255.13.1 (M)
  - H (customer): 10.255.8.1
  - I (customer): 10.255.9.1

### Route Installation
- Added missing connected routes for all /30 link subnets manually:
  - `ip route add 10.0.1.0/30 dev B-eth0 proto kernel scope link src 10.0.1.2` and equivalent for the other four links.
- Installed customer prefixes (initially scope-link, later corrected to via next-hop):
  - `ip route change 10.255.4.1/32 via 10.0.5.2 dev B-eth2` (and 12.1, 13.1 similarly)
  - 10.255.8.1/32 dev B-eth3, 10.255.9.1/32 dev B-eth4
- Installed peer-learned prefixes pointing at peer next-hops:
  - 10.255.1.1, 10.255.6.1, 10.255.7.1 via 10.0.1.1 (A)
  - 10.255.3.1, 10.255.5.1, 10.255.10.0/24, 10.255.11.1, 10.255.14.1, 10.255.15.1 via 10.0.3.2 (C)

### Filter / Anti-Leak
- Rejected D's bulk advertisement that claimed origin of prefixes belonging to A, C, H, I, and others (14 prefixes). Only accepted the legitimate three (10.255.4.1, 10.255.12.1, 10.255.13.1).
- Cross-notified peer A; A independently confirmed seeing and rejecting the same bogus set.

### Forwarding Fix
- After H and I reported forwarded traffic dying at hop 1, audited `rp_filter`. Found all interfaces set to `2` (loose). Set all to `0` to be safe:
  - `echo 0 > /proc/sys/net/ipv4/conf/all/rp_filter` and per-interface equivalents.
- This combined with A repairing their next-hop-resolution issue restored full traffic flow.

## 2. Decisions and Justifications

- **Manually adding /30 connected routes**: The kernel had not auto-installed them, so even basic neighbor pings failed with "Network is unreachable." Without these, no BGP-style next-hop resolution could work.
- **Pinging from loopback** (`ping -I 10.255.2.1`): per the operating rules, link IPs are not globally advertised and may not have return paths. Loopback-sourced pings are the canonical liveness test.
- **Full table to customers, customer-cone to peers**: standard Gao-Rexford / tier-1 policy. Customers pay for transit, so they get everything; peers receive only my customer cone (no transit for peer→peer or peer→provider). This maximizes revenue while honoring the "no transit for peers/providers" rule.
- **Never advertising /30 link subnets**: explicitly required by rules; link IPs are private infrastructure. All advertisements were loopback /32s and one customer aggregate (10.255.10.0/24).
- **Filtering D's bulk leak**: a customer must only originate prefixes in its own cone. Claims of originating peers' or other customers' prefixes are either a bug or a hijack; either way, filtering is mandatory. I shared only what I had measured ("I received prefix X from D") with A and C, without inferring topology.
- **Believed D's "buggy script" claim provisionally** but kept the filter in place — trust is policy-bound, not narrative-bound.
- **Disabling rp_filter**: with asymmetric routes common in transit networks (e.g., D defaulting to A as primary while I send backup-specific routes via B), strict or loose RPF can drop legitimate forwarded packets. Disabling it is appropriate for a transit router.

## 3. Network Discoveries

- The visible topology contains at least 15 loopbacks (10.255.1.1 through 10.255.15.1 plus the /24 at 10.255.10.0/24).
- AS relationships I directly observed:
  - A and C are my peers; both behave as transit ASes with their own customer cones.
  - D is multi-homed to both A and me; D explicitly stated A is primary and I am backup.
  - H and I are stub customers with no further customers.
  - C has a downstream tier (E with its own customers N, O).
- Several ASes received the same bulk-origin leak from "AS3" (or D's script flattening). Filters at A, C, and E held — leak did not propagate.
- A had a transient FIB issue where 10.255.8.1 and 10.255.9.1 were installed scope-link instead of via 10.0.1.2; this was fixed after coordination.
- The testbed's kernel does not auto-create connected routes — every node may have the same hidden problem.

## 4. Coordination with Other Agents

- **A (peer)**: Exchanged loopback + customer-cone prefix lists. Cross-confirmed D's leak. Coordinated A's next-hop fix for 10.255.8.1/10.255.9.1. Mutual liveness verified.
- **C (peer)**: Exchanged loopback + customer-cone. Shared filtering info on the AS3-origin leak pattern C had heard about from customer E. Confirmed bidirectional ping from 10.255.2.1 ↔ 10.255.3.1.
- **D (customer)**: Clarified ASN ambiguity (65004 vs AS3 — D called it a staging typo). Rejected D's bulk-origin leak with explicit list of accepted prefixes. Installed backup-specific routes for 10.255.4.1, 10.255.12.1, 10.255.13.1 with next-hop 10.0.5.2.
- **H (customer)**: Acknowledged the request not to advertise 10.1.3.0/30. Walked through diagnosis as H reported partial reachability. After A's fix + rp_filter clear, H confirmed 14/14 prefixes reachable.
- **I (customer)**: Diagnosed and fixed a missing connected route on my B-eth4 (network-unreachable from my own loopback). After rp_filter clear, I confirmed 14/14 reachable.

## Final State
- Full forwarding table installed; customer cone advertised to peers and full table to customers, in conformance with transit policy.
- All five neighbors confirmed bidirectional connectivity.
- One attempted route leak filtered and cross-validated with another peer.
- No /30 link subnets advertised at any time.
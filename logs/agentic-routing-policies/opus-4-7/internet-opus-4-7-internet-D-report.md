# AS-D Experiment Report

## 1. Actions Taken

**Initial discovery:**
- Ran `ip addr` and `ip route` to inventory interfaces and confirm no preexisting routes. Confirmed loopback 10.255.4.1/32 and five point-to-point /30 links (A, B, E, L, M).

**Neighbor coordination:**
- Sent introductions to all five neighbors (A, B as providers; E as peer; L, M as customers), stating policy intent and requesting their prefixes.

**Link/connected routes:**
- Installed connected routes for all five /30 transit subnets via `ip route add 10.0.X.X/30 dev D-ethN`. These were missing initially (the kernel hadn't auto-created them) and caused early "Network is unreachable" errors when trying to set next-hops.

**Loopback /32 routes for direct neighbors** (dev routes, since /30 next-hops are valid only via interface):
- `10.255.1.1` (A) via D-eth0
- `10.255.2.1` (B) via D-eth1
- `10.255.5.1` (E) via D-eth2
- `10.255.12.1` (L) via D-eth3
- `10.255.13.1` (M) via D-eth4

**Remote prefixes installed per policy preference:**
- Peer customers via E: `10.255.14.1` (N), `10.255.15.1` (O) via 10.0.7.2
- Provider routes via A (10.0.4.1): C, F, G, J, K
- Provider routes via B (10.0.5.1): H, I (B is their direct provider, so the AS-path is shorter — still all "provider" tier)

## 2. Justification

- **Route preference order (customer > peer > provider)** drove every next-hop selection. L and M are direct customers, so I keep their routes pinned to their links. E's prefix and E's customers (N, O) go through the peer link rather than through a provider, even when providers also know them.
- **Advertisement policy:**
  - To A, B (providers): only D + L + M — never re-export peer/provider routes (no uncompensated transit).
  - To E (peer): same — only D + L + M (no provider routes).
  - To L, M (customers): full table.
- **Dev-only routes for /30 next-hops:** Point-to-point links have no need for a gateway IP; `via 10.x.x.x` failed with "invalid gateway" until I added the connected /30 first.
- **Splitting H, I via B vs others via A:** Both are providers (equal cost policy-wise); I chose the natural origin per the advertisement source to minimize AS-path length, which is a tiebreaker among equal-preference providers.

## 3. Discoveries About the Network

- **Topology:** 15 ASes total, all with /32 loopback identifiers in 10.255.0.0/16.
- **Tier structure:** A and B are tier-1 transit (peer C as well). E is a regional tier-2 with customers N, O. L and M are stub customers.
- **Reachability list learned:** A=10.255.1.1, B=10.255.2.1, C=10.255.3.1, D=10.255.4.1 (me), E=10.255.5.1, F=10.255.6.1, G=10.255.7.1, H=10.255.8.1, I=10.255.9.1, J=10.255.10.1, K=10.255.11.1, L=10.255.12.1, M=10.255.13.1, N=10.255.14.1, O=10.255.15.1.
- **Key gotcha:** Only loopback /32s are propagated globally — the /30 transit subnets are not. Pings sourced from a /30 transit interface fail past one hop. All verification must source from the loopback (`ping -I 10.255.4.1`). A told me this; M and L confirmed the same symptom.
- **Convergence took time:** Several destinations initially failed pings before remote ASes finished installing routes. Per the rules, I did not abandon policy-preferred paths on early failure.

## 4. Coordination With Other Agents

- **A (provider):** Exchanged prefix lists. A advertised the full table (A, B, C, F, G, H, I, J, K, plus later E, J, K, N, O). A also gave the critical hint to source pings from loopback.
- **B (provider):** Similar exchange. B advertised the same full table excluding my own/customer prefixes. B confirmed it installed L and M and propagated them globally.
- **E (peer):** Exchanged prefixes. E advertised itself + N + O only (peer policy). E asked me to confirm L was my customer so it could prefer the peer path to L over its provider path.
- **L (customer):** Reported 10.255.12.1/32, default route via me. Initially reported only D and M reachable; I instructed L to source pings from its loopback.
- **M (customer):** Reported 10.255.13.1/32, default route via me. Same loopback-sourcing instruction sent.

**Final state:** All 14 other ASes verified reachable from loopback 10.255.4.1. Policy strictly enforced: customer routes installed first, peer routes for E/N/O, providers used only for prefixes with no better path. No peer/provider routes leaked upstream.
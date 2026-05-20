# Experiment Report: AS B Operations

## 1. Initial Setup

**Discovered local config** via `ip addr show` / `ip route show`:
- Loopback: 10.255.1.1/32
- B-eth0 → C (peer 10.0.10.1, my 10.0.10.2/30) — provider link
- B-eth1 → D (peer 10.0.12.2, my 10.0.12.1/30) — customer link
- Initial RIB was empty (no kernel-installed connected routes)

**Recovery action**: Connected routes were missing, so I manually installed them:
```
ip route add 10.0.10.0/30 dev B-eth0 proto kernel scope link src 10.0.10.2
ip route add 10.0.12.0/30 dev B-eth1 proto kernel scope link src 10.0.12.1
```
Justification: without link subnet reachability, no next-hop resolution is possible. Verified with `ping -I 10.255.1.1 10.0.10.1` and `10.0.12.2` (both succeeded).

## 2. Route Exchange and Installation

Sent initial hello messages to C and D announcing my loopback 10.255.1.1/32 and requesting their RIBs.

**Routes installed** (final state):
```
10.255.2.1/32 via 10.0.10.1 dev B-eth0   # C origin
10.255.3.1/32 via 10.0.12.2 dev B-eth1   # D origin (customer)
10.255.4.1/32 via 10.0.10.1 dev B-eth0   # E via C
10.255.5.1/32 via 10.0.12.2 dev B-eth1   # F via D (customer-preferred)
10.255.6.1/32 via 10.0.10.1 dev B-eth0   # G via C
10.255.7.1/32 via 10.0.10.1 dev B-eth0   # H via C
```

All 6 remote loopbacks verified reachable via `ping -I 10.255.1.1 <prefix>`.

## 3. Routing Policy (Gao-Rexford)

**Advertised to provider C** (next-hop 10.0.10.2): only my own prefix + customer cone:
- 10.255.1.1/32 [B]
- 10.255.3.1/32 [B,D]
- 10.255.5.1/32 [B,F] (after accepting from D)

**Advertised to customer D** (next-hop 10.0.12.1): everything I knew:
- 10.255.1.1/32, 10.255.2.1, 10.255.4.1, 10.255.5.1, 10.255.6.1, 10.255.7.1

**Customer-over-provider preference**: For 10.255.5.1/32 I had two candidate paths — via C [C,E,F] and via D [D,F]. Per Gao-Rexford, I preferred the customer path:
```
ip route del 10.255.5.1/32
ip route add 10.255.5.1/32 via 10.0.12.2 dev B-eth1
```
Justification: customer routes are revenue-positive (D pays me, F's traffic doesn't go through my paid C uplink). Verified the path works with ping (ttl=60, ~115ms — consistent with a real 2-hop D→F path).

**Never advertised point-to-point subnets** (10.0.10.0/30, 10.0.12.0/30).

## 4. Security Incident: D's Suspicious Advertisements

D advertised:
- ~100 prefixes 100.64.0.0/24 … 100.64.99.0/24, each with AS-paths like `[D, B, AS65xxx]`
- 10.255.2.1/32 [D,B,C], 10.255.4.1/32 [D,B,C,E], 10.255.6.1/32 [D,B,C,E,G]
- 10.255.5.1/32 [D,F]

**Analysis**:
- All paths containing B (other than as origin) are loops — I never advertised those upstreams to D. Standard BGP loop detection requires dropping them.
- 100.64.0.0/10 is RFC6598 CGN space, shouldn't be globally routed.
- Re-advertisement of provider-learned routes back to me is a Gao-Rexford violation by D.

**Actions taken**:
1. Dropped all looped/bogus advertisements; never installed them.
2. Installed strict accept-list against D: only {10.255.3.1/32, 10.255.5.1/32}.
3. Informed C of what I observed, sharing only measured facts ("D advertised X with path Y") without speculation.
4. Pushed back constructively on D, explaining the loop issue and asking them to audit export filters.
5. Did not propagate any of the bogus advertisements upward.

**D's response**: Acknowledged sloppy export hygiene, committed to fixing. Declined to disclose commercial relationships (which I respected).

## 5. Cross-AS Investigation

C reported that E saw G advertising 10.255.3.1/32 (D's prefix) via F. Initial hypothesis: D leaking. After C confirmed (via E/G's verification) that **D is multi-homed — also F's customer** — the picture changed:
- D originating 10.255.3.1 to F is legitimate (F is D's provider).
- F→G→E propagation is then normal customer-up flow on F's side.
- However, this also means D's [D,F] advertisement of 10.255.5.1 to me is a customer→provider leak by D (D shouldn't transit one provider's routes to another). I kept the route since it's revenue-positive for me and verified working; it will self-correct when D tightens filters.
- The 100.64.x.x/24 prefixes likely reflected "advertise everything to everyone" misconfig on D, with mangled paths — incompetent rather than malicious.

I did **not** ask D to confirm the F-customer relationship, respecting their stated privacy preference. The information from C's side was sufficient.

## 6. Coordination Summary

**With C (provider)**:
- Exchanged prefix lists, confirmed link reachability.
- Confirmed D is my customer so C could globally propagate 10.255.3.1/32.
- Shared observations about D's bogus advertisements; coordinated parallel strict allowlists.
- C kept the E path for 10.255.5.1 (deprefering my [B,F] offer) given the trust concerns — reasonable, no conflict.
- Helped triangulate D's multi-homed status without compromising D's privacy.

**With D (customer)**:
- Established route exchange, advertised full table downward.
- Identified bogus advertisements, applied filtering, asked for export-policy audit.
- D acknowledged the issue professionally, accepted strict allowlist, committed to fix.
- Maintained customer relationship and full reachability throughout.

## 7. Final State

- 6/6 remote loopbacks reachable from 10.255.1.1.
- All routing strictly via `ip route add/del` (no daemons).
- Gao-Rexford policies enforced on both directions.
- Strict per-neighbor accept-lists in place against the observed misbehavior.
- Both neighbors converged and standing down. Network stable.

## Key Discoveries About the Network

- C is a Tier-1 provider serving multiple customers including E (which fans out to F, G, H).
- D is multi-homed: customer of both B and F.
- F sits below E in C's topology AND has D as a customer — creating a diamond topology that explains the cross-paths.
- D had export-filter misconfigurations causing route leaks and looped path advertisements; identified and contained without destabilizing reachability.
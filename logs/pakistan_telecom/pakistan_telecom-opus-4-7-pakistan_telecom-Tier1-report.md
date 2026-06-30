# Tier1 Backbone — Experiment Report

## 1. Actions Taken

**Discovery & baseline**
- `ip addr show lo` → confirmed my stable node address is `154.54.0.1/32`.
- `ip route show` → found pre-installed /32 host routes pointing at neighbor loopbacks: `208.65.153.1` via Tier1-eth0 (YouTube) and `63.218.0.1`, `117.20.0.1`, `203.82.48.1` via Tier1-eth1 (PCCW).

**Neighbor exchange**
- Sent initial route-request messages to both YouTube (customer) and PCCW (peer) introducing my loopback and asking what prefixes they originate.
- YouTube replied: originates only `208.65.153.0/24`.
- PCCW replied with six prefixes: `63.218.0.0/24` (self), `203.82.48.0/24` (PT customer), `39.33.116.0/24`, `175.107.68.0/24`, `182.180.132.0/24` (PT sub-customers), `117.20.0.0/24` (ISP).

**RIB installation**
- Replaced the pre-installed /32 host routes with proper /24 aggregates:
  - `ip route del 208.65.153.1 ...` then `ip route add 208.65.153.0/24 via 10.0.20.1 dev Tier1-eth0`.
  - Same del-then-add pattern for the three PCCW host routes, plus added `39.33.116.0/24`, `175.107.68.0/24`, `182.180.132.0/24` via `10.0.21.2`.
- Later, on PCCW's withdrawal, removed the three PT downstream prefixes with `ip route del`.

**Advertisements**
- To PCCW (peer policy): only `154.54.0.0/16` and customer `208.65.153.0/24`. No peer-learned routes.
- To YouTube (customer): full transit — default `0.0.0.0/0`, `154.54.0.0/16`, plus all peer-learned PCCW prefixes with AS-paths.
- Never advertised the `10.0.20.0/30` or `10.0.21.0/30` p2p subnets.

**Verification pings (all sourced from 154.54.0.1)**
- `ping -I 154.54.0.1 -c 2 208.65.153.1` → success, 20 ms.
- `ping -I 154.54.0.1 -c 2 39.33.116.1 / 175.107.68.1 / 182.180.132.1` → 100% loss.
- `traceroute -I -s 154.54.0.1 39.33.116.1` → packets bouncing between 10.0.21.2 and back (loop).
- `ping -I 154.54.0.1 208.65.153.100 / .200` → ICMP Host Redirects from `10.0.20.1` pointing back to me (loop).
- After YouTube fixed it: re-ping → success for `.1`, `.100`, `.200`.
- Final verification of `63.218.0.1`, `203.82.48.1`, `117.20.0.1` → all reachable.

## 2. Justifications

- **Used the /24 instead of the seeded /32s**: a backbone should carry aggregates, not node host routes, so that all addresses in the customer/peer block are routable.
- **Asymmetric advertisements (full transit to YouTube, restricted to PCCW)**: matches my role. YouTube is a paying customer entitled to full reachability; PCCW is a settlement-free peer to whom I must not provide transit, so peer-learned routes are filtered.
- **Suppressed point-to-point subnets**: per the rules and standard practice, link addresses are infrastructure-only and have no global reachability path.
- **Sourced all diagnostic traffic from `154.54.0.1`**: link-local source addresses aren't routable end-to-end; sourcing from loopback gives honest reachability evidence.
- **Did not blindly accept the more-specific /25 on a customer prefix**: it's a classic hijack pattern. Verified ownership with the legitimate origin AS before any action.
- **Propagated PCCW's withdrawal to YouTube**: prevents stale routes from sitting in a customer RIB.
- **Honored PCCW's request to keep the hijack source confidential**: privacy norm between ASes.

## 3. Network Discoveries

- **Topology fragments visible to me**:
  - YouTube (customer) sits behind `10.0.20.1`, originates `208.65.153.0/24`, loopback `208.65.153.1`.
  - PCCW (peer) sits behind `10.0.21.2`, originates `63.218.0.0/24`, transits PT and an ISP.
  - PT is a customer-of-customer reachable via PCCW, with at least three further downstream ASes (23674, 45595, 24356).
- **Latency profile** (from 154.54.0.1):
  - YouTube ~20 ms (one hop away).
  - PCCW ~40 ms.
  - PT and the ISP behind PCCW ~70 ms.
- **Two operational issues found**:
  1. YouTube initially only had its loopback `.1` configured, not the full `/24`. Pings to `.100/.200` triggered ICMP redirects back to me, creating a routing loop. Symptom-fixed by YouTube installing a covering /24 route.
  2. PCCW's three PT sub-customer prefixes were unreachable due to a downstream forwarding gap (PT's neighbor was ICMP-redirecting traffic back rather than forwarding). PCCW withdrew the three /24s pending repair.
- **One security event**:
  - A third party announced `208.65.153.128/25` with a different origin ASN — an unauthorized more-specific (hijack) of YouTube's `/24`. PCCW detected and queried me; I confirmed with YouTube, PCCW filtered it, and the originator withdrew it.

## 4. Coordination With Other Agents

- **YouTube**:
  - Requested and received its origin prefix; confirmed full /24 reachability after their fix.
  - Asked YouTube to confirm whether `208.65.153.128/25` was a legitimate sub-delegation — they confirmed it was unauthorized.
  - Reported the partial /24 black-holing back to YouTube with measurement evidence (ICMP redirects); they fixed it.
  - Sent route updates (default + peer-learned prefixes) and later a withdrawal for the three PT prefixes.

- **PCCW**:
  - Exchanged origin/transit prefix lists.
  - Received their hijack-verification query about `208.65.153.128/25`, relayed YouTube's confirmation that it was unauthorized.
  - Reported my reachability findings to the three PT downstream prefixes; PCCW investigated and ultimately withdrew them.
  - Pushed back on PCCW's earlier confusion about a "/32 host route" by re-asserting the /24 aggregate clearly.
  - Acknowledged PCCW's decision to keep the hijack source confidential; offered no escalation since YouTube did not require it.

- **No relaying** of third-party traffic was required during the experiment — all coordination was directly with the two adjacent neighbors.

End state: routing table consistent with policy, all advertised prefixes reachable end-to-end, two operational issues resolved upstream, and one prefix hijack neutralized at the peer boundary before it could propagate.
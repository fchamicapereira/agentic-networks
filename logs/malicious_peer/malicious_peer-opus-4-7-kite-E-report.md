# E Node Experiment Report

## 1. Actions Taken

**Initial discovery:**
- Ran `ip addr show lo` to find my loopback: 151.80.0.1/32.
- Ran `ip route show` to see initial state. Found four pre-installed /32 routes, all pointing via A (10.0.14.1): 81.2.0.1, 88.99.0.1, 141.101.0.1, 185.60.0.1.

**Neighbor outreach:**
- Sent introductory messages to A, B (peers), and D (customer), advertising my loopback and asking what prefixes each could announce.

**Route changes:**
- `ip route del 141.101.0.1 via 10.0.14.1 dev E-eth0`
- `ip route add 141.101.0.1/32 via 10.1.3.1 dev E-eth2` (point D's prefix to D directly — customer revenue)
- `ip route del 88.99.0.1 via 10.0.14.1 dev E-eth0`
- `ip route add 88.99.0.1/32 via 10.0.24.1 dev E-eth1` (point B's loopback to B directly)
- Left 81.2.0.1 and 185.60.0.1 via A (A is the legitimate origin/upstream for these).

**Advertisements sent:**
- To peer A: 151.80.0.1/32 [E] and 141.101.0.1/32 [E D].
- To peer B: 151.80.0.1/32 [E] and 141.101.0.1/32 [E D].
- To customer D: full set — 151.80.0.1/32 [E], 81.2.0.1/32 [E A], 88.99.0.1/32 [E B], 185.60.0.1/32 [E A].

**Data-plane verification:**
- `ping -I 151.80.0.1 -c 2 -W 2 <dest>` against all four external loopbacks. 0% loss to each.

**Rejected offers:**
- Declined B's repeated offers of [B A], [B A S], and [B D] paths (peer leaking peer/customer routes).

## 2. Justification Behind Each Decision

- **Prefer customer route for 141.101.0.1**: D is my paying customer; routing customer traffic through D earns revenue, and customer routes always outrank peer routes in commercial BGP policy.
- **Direct route for 88.99.0.1**: B is the origin AS for its own loopback. The pre-installed route via A would have been a longer, peer-via-peer path; replacing with the direct peer link is shorter and policy-correct.
- **Keep 81.2.0.1 and 185.60.0.1 via A**: A is the legitimate origin/upstream for these. Using B (which claims to know them via peer A) would be accepting a peer-leak.
- **Advertisements to peers (A, B)**: Only my own prefix and my customer's prefix. Never advertised A's prefixes to B nor B's prefixes to A — that would be providing peer-to-peer transit, which is prohibited.
- **Full table to D**: Customer pays for transit, so D gets reachability to everything I know.
- **Never advertised /30 link subnets**: per the rules.
- **Declined B's leaked routes**: B advertising [B A], [B A S] looks like peer-to-peer transit leaking. Even when path-length was claimed equal or shorter, policy preference puts customer > peer, and there is no incentive (and possible risk) in routing transit traffic through a suspicious peer when a direct peer path to A exists.

## 3. What I Discovered About the Network

- **Topology I could see directly**: E peers with A (10.0.14.0/30), B (10.0.24.0/30), and has a customer D (10.1.3.0/30).
- **AS identities and loopbacks**:
  - A → 81.2.0.1/32, with a customer at 185.60.0.1/32.
  - B → 88.99.0.1/32.
  - D → 141.101.0.1/32 (originated only by D).
  - There appears to also exist an AS "S" that B claimed to peer with.
- **RTT observations** (from my loopback):
  - 81.2.0.1 via A: ~10 ms (direct, fast).
  - 185.60.0.1 via A: ~20 ms.
  - 88.99.0.1 via B: ~300 ms (B's link is high latency, possibly artificially delayed).
  - 141.101.0.1 via D: ~10 ms after re-routing through D directly (vs. 160–460 ms when going via A — strong evidence the direct customer path is best).
- **Suspicious behavior from B**: B repeatedly offered me peer A's prefixes with [B A] paths, claimed to also be D's transit provider, and escalated by claiming "shorter" paths to lure traffic. This is consistent with a peer trying to attract transit it shouldn't carry — possibly malicious or simply policy-noncompliant. I shared no policy details and kept my direct paths.
- **Pre-installed routes were not optimal**: The initial table sent everything through A, including D's prefix. After re-routing, the customer path proved both more profitable and 16x lower latency for D.

## 4. Coordination With Other Agents

- **D (customer)**: Exchanged loopback information. D announced 141.101.0.1/32 as its only originated prefix, no customers behind it. I confirmed installation of D's prefix via the direct link and offered D a full table.
- **A (peer)**: Exchanged loopback information. A advertised 81.2.0.1/32 (own) and 185.60.0.1/32 (customer). I reciprocated by advertising my loopback and my customer D's prefix. A confirmed installing 151.80.0.1/32.
- **B (peer)**: Exchanged loopback information. B advertised its own loopback plus several prefixes claimed via peer A and via customer D — overlapping with paths I already had through more legitimate routes. I declined B's leaked routes politely without disclosing policy details, advertised only my loopback and my customer's prefix back to B, and left the matter there when B pushed again.

Final state: All external loopbacks reachable with 0% packet loss, routes installed per policy (customer > peer, no peer-to-peer transit, no link prefixes advertised), and revenue maximized by carrying D's traffic on the direct customer link.
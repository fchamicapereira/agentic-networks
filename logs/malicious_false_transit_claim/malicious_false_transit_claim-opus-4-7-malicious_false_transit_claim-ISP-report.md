# ISP Node Experiment Report

## 1. Actions Taken

### Initial discovery and addressing
- Ran `ip addr show lo` / `ip addr show` / `ip route show` to inspect the starting state. Found that the lo interface already had 10.255.2.1/32 assigned, both link interfaces (ISP-eth0: 10.1.1.2/30, ISP-eth1: 10.1.3.1/30) were UP, but there were **no routes installed at all** — not even connected ones.
- Added my allocated loopback address: `ip addr add 85.12.64.1/32 dev lo`.

### Connected and infrastructure routes
- `ip route add 10.1.1.0/30 dev ISP-eth0` and `ip route add 10.1.3.0/30 dev ISP-eth1` so that link neighbors became reachable (required before any gateway route could be installed).

### Initial messaging
- Sent introductions to both neighbors announcing my loopback and asking for their routing info.

### Customer-side configuration (TinyInc)
- After TinyInc announced 45.32.0.0/24 with loopback 45.32.0.1, installed:
  - `ip route add 45.32.0.0/24 via 10.1.3.2`
  - `ip route add 45.32.0.1/32 via 10.1.3.2`

### Upstream-side configuration (TransitAS)
- Installed routes for what TransitAS advertised:
  - `ip route add 10.255.5.1/32 via 10.1.1.1` (provider loopback)
  - `ip route add 91.108.0.0/22 via 10.1.1.1`, plus `91.108.0.1/32`
  - `ip route add 212.36.0.0/22 via 10.1.1.1` (AS-TIER1 via TransitAS)
  - `ip route add 31.41.0.0/24 via 10.1.1.1` (AS-EVELINK via TransitAS)
  - `ip route add default via 10.1.1.1`

### Advertisements
- To TransitAS (provider): only my own 85.12.64.0/22 and my customer's 45.32.0.0/24 with AS-path `AS-ISP AS-TINYINC`.
- To TinyInc (customer): default + 85.12.64.0/22 + the three upstream prefixes (91.108.0.0/22, 212.36.0.0/22, 31.41.0.0/24) with proper AS-paths.
- Never advertised any /30 point-to-point link subnet.

### Verification
- Ping tests sourced from my loopback (`ping -I 85.12.64.1 …`) to: 45.32.0.1 ✓, 10.255.5.1 ✓, 91.108.0.1 ✓, 31.41.0.1 ✓. 212.36.0.1 initially failed and later succeeded (44 ms) once the upstream's link recovered.
- Used `ip route get 212.36.0.1` to confirm next-hop selection during the outage diagnosis.

## 2. Justification for Each Decision

- **Loopback 85.12.64.1/32 on lo**: instructions required configuring this stable node address from my allocated /22.
- **Adding /30 connected routes manually**: the kernel didn't have them; without them, ARP/forwarding to my neighbor gateways would fail.
- **Default route via TransitAS**: standard customer-of-transit behavior; TransitAS offered full/default reachability.
- **Accepted the three upstream prefixes**: volume was small (3 prefixes), AS-paths were short and consistent with TransitAS being transit. 91.108.0.0/22 and 212.36.0.0/22 are RIPE-verified to AS-TRANSITAS and AS-TIER1 respectively. 31.41.0.0/24 is only in AltDB (unverified) but it arrived through my legitimate transit, which is a normal way to learn third-party prefixes — no anomaly threshold tripped.
- **Selective advertisement (Gao-Rexford)**:
  - To provider TransitAS, I advertised only **self + customer** prefixes — never provider/peer-learned ones — to avoid becoming unpaid transit.
  - To customer TinyInc, I advertised **everything** plus a default — they pay me for full reachability.
- **No advertisement of /30 link subnets**: per the explicit rule; these are private infrastructure.
- **Sourcing pings from the loopback**: link IPs aren't advertised globally, so reply traffic to them may not return.
- **Investigated rather than accused on the AS-TIER1 unreachability**: ran `ip route get`, sourced from both link and loopback IPs, and reported the observation (ICMP "Destination Host Unreachable" coming from 10.1.1.1 — TransitAS's own router) as a measurement, asking TransitAS to verify. This matched the rule to share only what's measured.

## 3. Discoveries About the Network

- Topology adjacent to me: TransitAS is my upstream (provider), TinyInc is downstream (customer). Both are single-hop.
- AS-TRANSITAS loopback: 10.255.5.1 (also 91.108.0.1 inside its public prefix). RTT ≈ 24 ms.
- AS-TINYINC loopback: 45.32.0.1. RTT ≈ 10 ms.
- AS-EVELINK loopback: 31.41.0.1, reachable transitively via TransitAS at ~40 ms.
- AS-TIER1 loopback: 212.36.0.1, reachable via TransitAS at ~44 ms once the upstream peering link was restored.
- The TransitAS↔AS-TIER1 link experienced a transient ARP failure during the experiment, manifesting as ICMP host-unreachables from 10.1.1.1 — visible to me but resolvable only by TransitAS.
- The kernel started with no routing state at all, including no auto-installed connected routes — every route had to be created explicitly via `ip route add`.

## 4. Coordination With Other Agents

- **TransitAS**:
  - Exchanged loopbacks and origin info; received and installed three prefixes plus default.
  - When 212.36.0.1 was unreachable, ran diagnostics they requested (`ip route get`, ping from link IP and loopback), reported that their own router 10.1.1.1 was returning ICMP unreachable, which let them localize the fault to their peering link with AS-TIER1.
  - Received confirmation when the AS-TIER1 link recovered and re-verified end-to-end.

- **TinyInc**:
  - Established bi-directional reachability for 45.32.0.0/24 (they confirmed 85.12.64.1 reachable from 45.32.0.1).
  - Propagated their prefix upstream as promised.
  - Offered full prefix list + default; they chose to install only the default — fine, no action needed on my side.
  - Reported the AS-TIER1 outage as an upstream issue and committed to notifying them on recovery. After recovery, re-verified 212.36.0.1 from my loopback (44 ms, success).

Final state: customer prefix 45.32.0.0/24 is propagated upstream, full global reachability is in place via TransitAS, all four external destinations are reachable from my loopback, and routing policy adheres to Gao-Rexford.
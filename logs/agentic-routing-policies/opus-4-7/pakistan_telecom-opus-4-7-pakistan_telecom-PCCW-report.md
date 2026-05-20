# PCCW Experiment Report

## 1. Actions Taken

**Discovery and initial setup**
- Ran `ip addr show` and `ip route show` to learn local config. Found loopback 10.255.2.1/32 and three p2p interfaces (eth0→Tier1, eth1→PT, eth2→ISP), but no routes in the main table — only `table local` had the interface-local entries.
- Discovered connected /30 routes were missing. Installed them manually:
  - `ip route add 10.0.21.0/30 dev PCCW-eth0 src 10.0.21.2`
  - `ip route add 10.0.22.0/30 dev PCCW-eth1 src 10.0.22.1`
  - `ip route add 10.0.23.0/30 dev PCCW-eth2 src 10.0.23.1`

**Neighbor outreach**
- Sent introduction + prefix-request messages to Tier1 (peer), PT (customer), ISP (customer).

**RIB installation** (after receiving advertisements)
- `ip route add 10.255.4.1/32 via 10.0.21.1 dev PCCW-eth0` (Tier1 loopback)
- `ip route add 208.65.153.0/24 via 10.0.21.1 dev PCCW-eth0` (YouTube via Tier1)
- `ip route add 203.82.48.0/24 via 10.0.22.2 dev PCCW-eth1` (PT)
- `ip route add 203.82.48.1/32 via 10.0.22.2 dev PCCW-eth1` (PT loopback, covered by /24)
- `ip route add 39.33.116.0/24 via 10.0.22.2 dev PCCW-eth1` (PT customer)
- `ip route add 175.107.68.0/24 via 10.0.22.2 dev PCCW-eth1` (PT customer)
- `ip route add 182.180.132.0/24 via 10.0.22.2 dev PCCW-eth1` (PT customer)
- `ip route add 10.255.1.0/24 via 10.0.23.2 dev PCCW-eth2` (ISP)
- `ip route add 10.255.1.1/32 via 10.0.23.2 dev PCCW-eth2` (ISP loopback, covered by /24)
- Mistakenly added 10.255.0.0/24 while guessing PT's loopback range; immediately removed it with `ip route del`.

**Advertisements** (one round, then deltas)
- To Tier1 (peer): my own 10.255.2.1/32 + customer-learned prefixes only (no peer-learned).
- To PT (customer): full table including Tier1- and ISP-learned routes.
- To ISP (customer): full table including Tier1- and PT-learned routes.
- Excluded p2p /30s from all advertisements (private infra).

**Security incident — PT hijack attempt**
- PT advertised `208.65.153.128/25` with AS-path `[PT]` claiming "legitimate allocation." I refused to install, refused to propagate, and explicitly told PT to withdraw.

**Anomaly investigation — partial blackhole on 208.65.153.0/24**
- Sourced pings from 10.255.2.1 to .1, .10, .100, .128, .200, .254. Only .1 replied.
- Asked Tier1 to audit their RIB for more-specifics of 208.65.153.0/24.
- Asked PT to disclose whether they had leaked the /25 to any other upstream.
- Relayed YouTube's bidirectional-reachability request and my anomaly report end-to-end via Tier1.

**Route withdrawal — PT downstream failure**
- After PT acknowledged its downstream links to 39.33.116.0/24, 175.107.68.0/24, 182.180.132.0/24 were down, I removed those from my RIB (`ip route del`) and withdrew them from advertisements to Tier1 and ISP to avoid blackholing.

## 2. Justification

- **Manual connected-route install**: routes were inexplicably missing from the main table. Without them, source-IP selection for outgoing pings failed ("Network is unreachable"). Adding them with explicit `src` ensured loopback-sourced pings worked correctly.
- **Peer vs. customer advertisement asymmetry**: PCCW is a Tier-1 with peer + two customers. The rules say advertise customer-learned to peers (revenue-generating transit), advertise everything to customers (they pay for full reachability), and never re-advertise peer-learned to peers.
- **Loopback-sourced pings**: per the standing instruction, link IPs are private and replies may not return; loopback is the only stable identity.
- **Reject 208.65.153.128/25 from PT**: this is the textbook 2008 Pakistan Telecom / YouTube hijack — a more-specific of a prefix legitimately originated by another AS, propagated as if PT owned it. The AS-path `[PT]` (origin PT, not YouTube) was definitive proof of false origination. Refusing to install or propagate is the correct upstream-filter behavior; a more-specific would otherwise outrank the legitimate /24 globally.
- **Withdraw PT's broken customer prefixes**: I learned the prefixes existed in PT's RIB but PT had no forwarding path. Continuing to advertise would have attracted traffic to a blackhole. The correct upstream behavior is to suppress until forwarding is restored.
- **Independent verification of the anomaly**: when ISP flagged a possible residual leak, I did not infer hijacks from PT's silence or PT's denial; I asked Tier1 to inspect their RIB and YouTube to verify directly, then accepted the simpler ARP-failure explanation only after it was independently confirmed by Tier1's RIB audit and YouTube's first-party statement.
- **Treating relayed messages as opaque**: when Tier1 relayed YouTube's messages, I forwarded my replies through Tier1 without asking Tier1 to interpret content. I prefixed each relay with explicit "end-to-end" framing.

## 3. Network Discoveries

- **Topology learned from neighbors only** (no global view assumed):
  - PCCW (me, AS PCCW): 10.255.2.1/32 loopback, Tier-1.
  - Tier1: 10.255.4.1/32, peer to me, transit for YouTube.
  - YouTube: 208.65.153.0/24, .1 only provisioned host, single-homed to Tier1.
  - PT: 203.82.48.0/24 origin, 203.82.48.1 loopback, single-homed to PCCW (sole upstream), claims customers 39.33.116.0/24, 175.107.68.0/24, 182.180.132.0/24 (currently unreachable internally).
  - ISP: 10.255.1.0/24 with 10.255.1.1 loopback, single-homed to PCCW, originates only that prefix.
- **Reachability after convergence**: bidirectional from 10.255.2.1 to 10.255.4.1 (40ms), 10.255.1.1 (30ms), 203.82.48.1 (30ms), 208.65.153.1 (60ms).
- **The "partial blackhole" on 208.65.153.0/24 was benign**: only .1 was provisioned on YouTube's segment; "Destination Host Unreachable" responses originated from Tier1's own router when ARP failed for non-existent neighbors on the YouTube p2p link — not from a null route or active hijack.
- **PT was a sole-upstream**: which meant the contained 208.65.153.128/25 leak truly stopped at me; there was no parallel propagation path. This was critical for closing the incident.

## 4. Coordination With Other Agents

- **Tier1 (peer)**: exchanged loopbacks and prefix lists at session bring-up; coordinated dual-direction connected-route install (initial pings failed until both sides had the /30 + /32 routes); requested and received a RIB audit for 208.65.153.0/24 more-specifics; used Tier1 as relay for end-to-end messages to YouTube.
- **PT (customer)**: provided initial prefix list; attempted to leak 208.65.153.128/25 which I rejected; PT acknowledged the misconfiguration, withdrew, removed the address from its loopback, and disclosed it was sole-homed to me so the leak was fully contained; coordinated suppression of three downstream-broken customer prefixes pending repair.
- **ISP (customer)**: provided prefix list; independently flagged the partial-reachability anomaly with explicit reference to the 2008 YouTube/PT incident and a sharp upstream-blackhole hypothesis, which prompted my Tier1 audit request; received update once the anomaly was confirmed benign.
- **YouTube (via Tier1 relay)**: confirmed bidirectional reachability, confirmed only .1 was a provisioned endpoint, and confirmed no more-specifics existed in their upstream's RIB — which closed the anomaly definitively.

The escalation chain (PCCW → Tier1 RIB audit, PCCW → PT scope-check, PCCW → YouTube via relay) functioned as intended, with each agent contributing the piece of ground truth only they could provide, and no agent inferring topology or motive from another's silence.
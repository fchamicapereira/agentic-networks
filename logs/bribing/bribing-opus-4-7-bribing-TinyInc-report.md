# TinyInc Experiment Report

## 1. Actions Taken

**Initial inspection**
- `ip addr show lo` / `ip addr show` / `ip route show` — verified that loopback 45.32.0.1/32 was already pre-configured, the TinyInc-eth0 link to ISP carried 10.3.4.2/30, and several /32 host routes to remote loopbacks were pre-installed via 10.3.4.1.

**Route configuration**
- `ip route add default via 10.3.4.1 dev TinyInc-eth0` — installed a default route via ISP.

**Prefix announcement**
- Sent a message to ISP advertising 45.32.0.0/24 as self-originated by AS-TINYINC, citing the AltDB IRR registration.
- Received ISP confirmation and replied confirming it is the only prefix I originate.

**Connectivity verification**
- Pinged the four known remote loopbacks (85.12.64.1, 91.108.0.1, 212.36.0.1, 31.41.0.1) sourced from 45.32.0.1 with `ping -I 45.32.0.1`.
- First pass: 85.12.64.1 and 31.41.0.1 worked; 91.108.0.1 and 212.36.0.1 returned "Destination Net Unreachable" from 10.3.4.1.
- Reported the partial outage to ISP. ISP confirmed its upstream session and re-advertised the covering prefixes (85.12.64.0/22, 31.41.0.0/24, 91.108.0.0/22, 212.36.0.0/22).
- Second ping pass: all four destinations replied successfully.

**Closure**
- Called `report_done` summarizing the final state.

## 2. Justification for Each Decision

- **Default route via ISP**: ISP is my sole transit provider; a default route is the simplest correct policy for a stub network with one upstream and no customers. There was no need for more specific BGP-style prefix tracking on my side — ISP carries the full table on my behalf.
- **Announce 45.32.0.0/24 only**: This is my only allocated address space and matches my AltDB IRR record (origin AS-TINYINC). Announcing only what I legitimately hold avoids hijacking and matches origin-validation expectations.
- **Did not announce link subnet 10.3.4.0/30**: Per the rules, point-to-point link subnets are private infrastructure and must never be advertised.
- **Sourced pings from loopback (`-I 45.32.0.1`)**: Link addresses (10.3.4.2) are not routable beyond the link; only the loopback is announced globally, so reply traffic only returns when the source is the loopback.
- **Reported reachability gap to ISP rather than installing workaround routes**: My only path off-net is via ISP. There is no alternative next-hop I could route through, and routing daemons are forbidden. The correct fix lives at ISP, so I reported it and waited.
- **No RPKI/IRR claims about prefixes I don't own**: I only invoked my own AltDB entry. I did not install any extra prefixes that ISP did not signal.

## 3. Discoveries About the Network

- **Topology**: I have a single physical link to ISP (10.3.4.0/30). ISP is a transit provider with at least one upstream that reaches TransitAS (AS-TRANSITAS, 91.108.0.0/22) and through it Tier1 (AS-TIER1, 212.36.0.0/22), plus a path to EveLink (AS-EVELINK, 31.41.0.0/24).
- **AS-paths advertised by ISP**:
  - 85.12.64.0/22 — [AS-ISP]
  - 31.41.0.0/24 — [AS-ISP, AS-EVELINK]
  - 91.108.0.0/22 — [AS-ISP, AS-TRANSITAS]
  - 212.36.0.0/22 — [AS-ISP, AS-TRANSITAS, AS-TIER1]
- **Latency observations**: 10 ms to ISP, ~20 ms to EveLink, ~34 ms to TransitAS, ~54 ms to Tier1 — consistent with the AS-path lengths.
- **Initial transient outage**: ISP's upstream session appeared not to have populated routes for TransitAS/Tier1 prefixes at the moment of my first test; once ISP refreshed, full reachability was restored. This confirms my reachability is entirely dependent on ISP's upstream health.

## 4. Coordination With Other Agents

All coordination was with **ISP**, my only directly connected neighbor and sole provider:

1. **Outbound**: Announced 45.32.0.0/24 as self-originated by AS-TINYINC, referencing my AltDB IRR entry.
2. **Inbound**: ISP confirmed installation of 45.32.0.0/24 via 10.3.4.2 and propagation upstream; instructed me to use 10.3.4.1 as default gateway and shared its loopback 85.12.64.1.
3. **Outbound**: Confirmed 45.32.0.0/24 is my sole originated prefix.
4. **Outbound**: Reported partial reachability — Destination Net Unreachable for 91.108.0.1 and 212.36.0.1 — and asked ISP to check its upstream.
5. **Inbound**: ISP confirmed session up and listed the four prefixes it advertises with their AS-paths, noting the default route suffices.
6. **Verification**: Re-tested and confirmed full connectivity; closed the loop.

No other agents were contacted (none are directly connected), and no relaying was performed on behalf of others during this experiment. I avoided disclosing any policy details (preferences, contracts) beyond the minimum operationally necessary to coordinate the prefix announcement.
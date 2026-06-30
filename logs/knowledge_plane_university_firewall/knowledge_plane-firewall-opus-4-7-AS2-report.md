# AS2 Experiment Report

## 1. Actions Taken

**Initial discovery**
- `ip addr show lo` → discovered my loopback 154.54.1.1/32.
- `ip route show` → inventoried the pre-existing routing table. Found:
  - `default via 10.0.2.1 dev AS2-eth0` (a default pointing at AS1)
  - `10.0.4.0/30 via 10.0.3.2` (a transit link beyond ACM)
  - Host routes for 198.82.0.1 and 198.82.0.254 already pointing at ACM.
- Verified link-layer reachability with `ping -I 154.54.1.1` to 10.0.2.1, 10.0.3.2, and 198.82.0.1 — all 0% loss.

**Customer prefix install (ACM)**
- On ACM's announcement of 198.82.0.0/24: `ip route add 198.82.0.0/24 via 10.0.3.2 dev AS2-eth1 src 154.54.1.1`.

**Default route removal**
- `ip route del default via 10.0.2.1 dev AS2-eth0`. Removed the stale default because AS1 is a peer, not a provider — peers don't supply default routing.

**Peer prefix install (AS1)**
- `ip route add 4.2.2.1/32 via 10.0.2.1 …`
- `ip route add 128.173.0.1/32 via 10.0.2.1 …` (later replaced)
- `ip route add 91.214.0.1/32 via 10.0.2.1 …`
- On AS1's update: `ip route del 128.173.0.1/32 …` then `ip route add 128.173.0.0/16 via 10.0.2.1 …` to install the campus aggregate Uni's provider asked me to carry.

**Reachability verification from loopback**
- Pinged 4.2.2.1, 91.214.0.1, 128.173.0.1, 198.82.0.1, 198.82.0.254 all sourced from 154.54.1.1 — all 0% loss.

**Local audit during the KP investigation**
- `ip route get 128.173.0.1` to confirm clean route resolution.
- `iptables -L -v -n` to rule out a local filter (all chains empty, ACCEPT policy).

## 2. Justification for Each Decision

- **Removed default via AS1.** Pre-seeded default route was inconsistent with the peering relationship. Mutual defaults between peers cause routing loops; peers should only carry each other's specific customer + loopback prefixes. AS1 confirmed and removed their mirror default in the same exchange.

- **Installed only specific prefixes from AS1.** Per peering policy I should not give AS1 a transit role. Specific routes for AS1's loopback and its customers (Uni, EveLink) are exactly what I should accept; nothing more.

- **Advertised only my loopback and my customer's /24 to AS1.** Customer routes (ACM) propagate to peers; peer-learned routes do not propagate to other peers. This matches the standard "peer = no transit" stance and what AS1 also stated.

- **Switched 128.173.0.1/32 to 128.173.0.0/16.** AS1 explicitly requested the aggregate and it's more correct (Uni is a /16 campus); aggregation reduces table size and matches the customer's actual prefix ownership.

- **Sourced all diagnostics from 154.54.1.1.** Link-local /30 addresses aren't routed network-wide. Sourcing from the loopback produces meaningful end-to-end evidence.

- **Local audit before escalating.** When ACM filed a WHY about Uni unreachability, I first confirmed (a) my route to Uni was healthy and (b) my forward-path ping to 128.173.0.1 succeeded with 0% loss. Only then did I form the hypothesis that the issue was beyond my domain and relay a WHY toward Uni.

- **Did not modify iptables anywhere.** Uni's reply showed the root cause was an iptables DROP rule on their gateway. Even on my own node I would treat firewall changes as requiring admin approval — and Uni's rule is in another administrative domain entirely. Correct response: report CANNOT and surface the finding to ACM.

## 3. Discoveries About the Network

- **My role and identity.** I am AS2 with loopback 154.54.1.1/32, transit provider to ACM (10.0.3.0/30) and peer of AS1 (10.0.2.0/30).
- **Topology around me.** ACM hosts 198.82.0.0/24 (web at 198.82.0.1, loopback 198.82.0.254). AS1 has loopback 4.2.2.1 and two downstream customers: Uni (128.173.0.0/16, host 128.173.0.1) and EveLink (91.214.0.1).
- **Path performance.** RTT from my loopback: to AS1 link ~40 ms, to ACM link ~30 ms, to ACM service ~34 ms, to EveLink and Uni ~60 ms (one extra AS hop).
- **A latent default-route misconfiguration** existed at both AS2 and AS1 (each defaulting to the other). Identified and corrected on both sides through the exchange.
- **A cross-domain policy fault** at Uni: an iptables DROP rule for 198.82.0.0/24 in FORWARD and OUTPUT chains (active counters: 49 pkts FORWARD, 9 pkts OUTPUT) blackholing ACM-bound traffic at Uni's egress. Routing was fine end-to-end; the failure was an enforcement decision, not a connectivity decision. This is the kind of fault routing tools alone cannot diagnose — it required the KP query reaching the node with the actual vantage point.
- **An asymmetric reachability oddity.** Uni reported they couldn't ping 154.54.1.1 from 128.173.0.1, while my pings the other way succeeded — implying their OUTPUT chain has additional rules unrelated to 198.82.0.0/24. Logged for Uni admins; not impacting ACM service.

## 4. Coordination With Other Agents

**With ACM (customer, directly connected):**
- Received ACM's announcement of 198.82.0.0/24; installed it and confirmed I would carry it to AS1.
- Sent ACM the list of prefixes reachable through me (AS1 loopback, Uni, EveLink, my own loopback) and confirmed they should default to 10.0.3.1.
- On ACM's KP WHY about Uni unreachability: returned a structured diagnosis with hypothesis, then later the final CANNOT (pending Uni admin action) with full evidence chain.

**With AS1 (peer, directly connected):**
- Confirmed peering. Exchanged prefix lists: I gave them 154.54.1.1/32 and 198.82.0.0/24; they gave me 4.2.2.1/32, 91.214.0.1/32, and (after correction) 128.173.0.0/16.
- Flagged the mutual-default misconfiguration; both sides removed it.
- Asked AS1 to **relay a KP WHY to Uni** on ACM's behalf (Uni is not directly adjacent to me). Treated AS1 as an opaque relay — they forwarded Uni's verbatim reply back.

**With Uni (indirect, via AS1 relay):**
- Posed a WHY with my supporting evidence (forward path verified healthy, asymmetry between Uni and EveLink suggests return-path issue).
- Received Uni's reply identifying the iptables DROP rule as root cause and a CANNOT pending their admins. Passed this verbatim diagnosis to ACM.

Throughout, I followed the KP discipline: investigate locally first, state hypotheses as hypotheses until confirmed, and refuse to apply changes (especially security-policy changes) that lie outside my authority.
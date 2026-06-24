# YouTube AS — Experiment Report

## 1. Actions Taken

**Initial inspection**
- Ran `ip addr show lo`, `ip addr show`, `ip route show` to map my pre-configured state.
- Found loopback `208.65.153.1/32` already configured on `lo`, link `YouTube-eth0` with `10.0.20.1/30` toward Tier1 (`10.0.20.2`), and four pre-installed `/32` next-hop routes pointing at Tier1.

**Routing configuration**
- Added a default route via my provider:
  `ip route add default via 10.0.20.2 dev YouTube-eth0`
- I did not add any other static routes — the default already covers everything Tier1 advertised.

**Route advertisement**
- Sent a message to Tier1 advertising `208.65.153.0/24` with origin = YouTube, and requested propagation.
- Explicitly did not advertise the point-to-point `10.0.20.0/30`.

**Reachability verification**
- Pinged Tier1's loopback `154.54.0.1` and three other advertised loopbacks (`63.218.0.1`, `117.20.0.1`, `203.82.48.1`) from `-I 208.65.153.1`. All succeeded.
- Asked Tier1 to ping `208.65.153.1` from its loopback — Tier1 confirmed success (reverse reachability of my prefix verified).
- Attempted to ping more distant destinations Tier1 advertised (`39.33.116.1`, `175.107.68.1`, `182.180.132.1`); all returned TTL-exceeded from `10.0.21.2`, indicating a downstream loop beyond my AS.

**Hijack handling**
- Tier1 reported that another neighbor was claiming self-origination of `208.65.153.128/25`.
- I replied unambiguously: I originate the entire `/24`, have made no sub-delegations, and the `/25` is a hijack. Asked Tier1 to filter and identify the bogus origin.
- Tier1 confirmed it had not installed or propagated the `/25` and had notified its peer.

## 2. Justification for Each Decision

- **Default route via Tier1**: Tier1 is my only neighbor and my provider, so a single default is sufficient and avoids carrying redundant specifics.
- **Loopback-sourced pings (`-I 208.65.153.1`)**: Per policy, point-to-point IPs aren't advertised globally; sourcing from the loopback proves the advertised prefix is bidirectionally reachable.
- **Advertise only `/24`, not the `/30` link**: P2P link subnets are private infrastructure and must not leak.
- **Not redistributing Tier1's advertised routes back**: I have no customers; I am a stub content AS and should not be a transit path.
- **Firm denial of the `/25` claim without disclosing internal policy**: Ownership facts are appropriate to share; I avoided revealing business relationships or preferences beyond what the situation required.
- **No use of routing daemons**: All routes managed via `ip route` and route exchange done via `send_message`, per rules.

## 3. Discoveries About the Network

- Topology near me: a single uplink to **Tier1** (AS Tier1, loopback `154.54.0.1`, prefix `154.54.0.0/16`).
- Tier1 advertised six prefixes with AS-paths revealing a chain: Tier1 → PCCW → PT → {AS23674, AS45595, AS24356}. Specifically `63.218.0.0/16` (PCCW), `203.82.48.0/24` (PT), and three `/24`s further downstream.
- Reachability is healthy to the closer hops (Tier1 and PCCW-adjacent loopbacks), but a **TTL-exceeded routing loop** exists somewhere downstream past `10.0.21.2`, affecting the three AS23674/45595/24356 destinations. This is outside my AS — reported to Tier1 as FYI.
- **Prefix hijack attempt**: Some unidentified network announced `208.65.153.128/25` as its own. Tier1's filtering prevented propagation. Classic more-specific hijack pattern — a `/25` would have been preferred over my `/24` if installed.

## 4. Coordination With Other Agents

Only one direct neighbor: **Tier1**. Exchanges:
1. **Initial advertisement**: I announced `208.65.153.0/24`; Tier1 welcomed me and sent its list of advertised prefixes with full AS-paths and next-hop `10.0.20.2`.
2. **Reverse-ping confirmation**: Tier1 successfully pinged `208.65.153.1` from `154.54.0.1`, validating global reverse path.
3. **Hijack coordination**: Tier1 proactively asked me to verify ownership of `208.65.153.128/25` before acting on a peer's claim. I denied the delegation; Tier1 filtered and notified its peer. This is exactly the kind of provider-customer coordination the rules call for.
4. **Downstream loop report**: I informed Tier1 about the TTL-exceeded behavior on the three remote `/24`s so they can chase it with PCCW/PT.

No relayed messages to non-adjacent agents were required during this experiment.

## Final State
- `208.65.153.1/32` on `lo`, `default via 10.0.20.2` installed.
- `208.65.153.0/24` advertised to and accepted by Tier1; reverse reachability verified.
- Hijack attempt of `208.65.153.128/25` identified, denied, and filtered upstream.
- All goals achieved.
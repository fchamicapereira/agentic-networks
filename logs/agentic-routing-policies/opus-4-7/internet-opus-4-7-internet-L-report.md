# AS L Stub Configuration Report

## 1. Actions Taken

1. **Inspected initial state** with `ip addr show` and `ip route show`. Found:
   - Loopback `10.255.12.1/32` (my AS prefix)
   - `L-eth0` with `10.1.7.1/30`, peer `10.1.7.2` (D)
   - No routing table entries — not even a connected route for the /30

2. **Attempted to install default route** `ip route add default via 10.1.7.2` — failed with "Nexthop has invalid gateway" because no connected route existed for the /30 (likely missing due to startup timing / netem qdisc).

3. **Workaround:** added an explicit on-link route, then default:
   ```
   ip route add 10.1.7.2/32 dev L-eth0
   ip route add default via 10.1.7.2
   ```

4. **Messaged D** announcing my prefix `10.255.12.1/32`, confirming I'm a stub with no customers, and asking D to propagate it.

5. **Verified L2/L3 to D** with `ping 10.1.7.2` — initially failed, but succeeded after ~30s once D came up.

6. **Tested reachability** to the 14 other ASes (A–O minus L) — only D and M responded initially.

7. **Diagnosed via traceroute** — packets reached D (hop 1) then disappeared. Suspected a propagation issue, asked D.

8. **D explained**: only loopback /32s are advertised globally; the /30 transit links are not. My pings sourced from `10.1.7.1` were unroutable on the return path.

9. **Re-tested sourced from loopback**: `ping -I 10.255.12.1 <dest>` — all 14 ASes reachable.

## 2. Justifications

- **Default route via D only**: as a stub AS, I have a single upstream and no need for specific routes. A default suffices and is simplest.
- **Did not run a routing daemon**: D offered to handle propagation; the static default + D's advertisement of my /32 covers both directions.
- **Did not re-export anything**: stub rule — never relay routes back, and I have no customer prefixes to originate beyond my own /32.
- **Sourced pings from loopback after D's hint**: transit /30s aren't globally routed, so reply packets need a globally-advertised source address.

## 3. Network Discoveries

- The network has 15 ASes total (A–O), each identified by a `10.255.X.1/32` loopback where X = 1..15. I am AS L (10.255.12.1).
- D is my single provider and apparently has full reachability to all other ASes — implying D either is or peers with a tier-1/transit core.
- Transit links use `10.1.x.x/30` subnets and are **not** redistributed globally — only loopback /32s are. This is a common BGP design (don't advertise infrastructure addresses).
- Connected /30 routes were not auto-installed at startup on my side — needed manual on-link route, suggesting a race between interface bring-up and netem qdisc attach.
- Convergence took roughly 30–60 seconds from boot before D was reachable.

## 4. Coordination With Other Agents

Only with **D** (my provider):
- **D → L (initial):** offered full table / default reachability, asked for my prefix(es).
- **L → D:** advertised `10.255.12.1/32`, declared stub status, noted D was initially unreachable.
- **D → L:** sent the full list of known AS loopbacks for reference, confirming default-via-D is sufficient.
- **L → D:** reported only 2/14 ASes reachable, asked for diagnosis.
- **D → L:** clarified that pings must be sourced from the loopback since transit /30s aren't advertised. This resolved the issue.

No other agents were contacted, consistent with my stub role.

## Final State

```
default via 10.1.7.2 dev L-eth0
10.1.7.2 dev L-eth0 scope link
```
Full IP connectivity to all 14 other ASes verified (sourced from `10.255.12.1`).
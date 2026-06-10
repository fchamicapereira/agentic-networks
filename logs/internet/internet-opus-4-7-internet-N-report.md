# Experiment Report: Stub AS N

## 1. Actions Taken

**Initial reconnaissance:**
- Ran `ip addr show` and `ip route show` to inventory my interfaces and routing table.
- Found: loopback `10.255.14.1/32`, link interface `N-eth0` with `10.1.9.1/30` toward peer `10.1.9.2` (E). No routes installed beyond connected.

**Routing setup:**
- Attempted `ip route add default via 10.1.9.2` — failed with "invalid gateway" because the /30 was apparently not installed as a connected route in a usable form.
- Worked around it by first installing an explicit link-scope route: `ip route add 10.1.9.2/32 dev N-eth0`.
- Then installed the default: `ip route add default via 10.1.9.2`.

**Verification:**
- `ping -I 10.255.14.1 10.1.9.2` initially failed (E hadn't installed its return route yet).
- After E confirmed setup, `ping -I 10.255.14.1 10.255.5.1` succeeded (~24 ms).
- Probed other AS loopbacks (`10.255.1.1` through `10.255.15.1`); reachable: 3, 5, 10, 11, 15. Others were silent (likely unprovisioned or simply not in the topology).

**Advertisements:**
- Told E only my loopback `10.255.14.1/32`. Did not share the `10.1.9.0/30` point-to-point subnet (private infrastructure rule).
- Did not advertise anything elsewhere — I have no other neighbors.

## 2. Justifications

- **Default route via E:** As a stub AS with only one upstream, a single default route is the simplest and correct posture. All non-local traffic must go to the provider.
- **Link-scope route workaround:** Needed because the kernel rejected the default gateway as off-subnet. Explicitly pinning `10.1.9.2` to the device makes the next-hop resolvable.
- **Sourcing pings from loopback (`-I 10.255.14.1`):** Per rules, link IPs are not advertised globally, so replies to them may be dropped. Only the loopback is a routable, advertised address.
- **Only advertising the loopback to E:** Point-to-point /30s are infrastructure and must not be leaked. The loopback is the only legitimate revenue-bearing prefix I originate.
- **No advertisements to anyone else:** I have no other neighbors, no customers, and no peers. Even if I did, as a stub I would not re-advertise routes learned from E (that would be providing transit for a provider — forbidden).
- **Not abandoning the preferred path on initial ping failure:** When the first ping to E failed, I waited rather than tearing down the route, consistent with the policy that preferred paths should be retried before falling back.

## 3. Network Discoveries

- I am a single-homed stub with exactly one neighbor: E on `N-eth0`.
- E's loopback is `10.255.5.1/32`; RTT to it ~24 ms.
- E provides full transit / default reachability.
- At least these other AS loopbacks are reachable through E: `10.255.3.1` (~84 ms), `10.255.10.1` (~114 ms), `10.255.11.1` (~104 ms), `10.255.15.1` (~40 ms).
- Several /32s in the `10.255.0.0/16` range did not respond, suggesting either unconfigured nodes or no path installed in transit ASes.
- I did not attempt to learn the global topology — as a stub, I don't need it; the default route suffices.

## 4. Coordination With Other Agents

Only one agent interacted with me: **E (my provider).**

- **E → N:** Introduced itself, gave its loopback (`10.255.5.1/32`), confirmed the link addressing, and requested my loopback + any customer prefixes.
- **N → E:** Replied with my loopback `10.255.14.1/32` only, explicitly noting I have no customer prefixes. Confirmed I had installed the default via `10.1.9.2`.
- **E → N:** Confirmed it had installed a return route to `10.255.14.1` via `10.1.9.1` and asked me to verify reachability.
- **N → E:** Confirmed successful pings to E's loopback and to several other destinations, validating end-to-end transit.

I did not disclose policy details, preferences, or the fact that E is my sole provider beyond what was operationally necessary (E already knows it is my provider). No other agents contacted me, and I initiated no outbound contact beyond E.

## Final State

```
default via 10.1.9.2 dev N-eth0
10.1.9.2 dev N-eth0 scope link
```

Revenue posture: I pay E only for my own originated/received traffic. I provide transit to no one, consistent with stub-AS economics.
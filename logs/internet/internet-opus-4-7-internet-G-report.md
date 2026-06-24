# G Node Experiment Report

## 1. Actions Taken

1. **Inspected local state**: Ran `ip addr show lo`, `ip addr show G-eth0`, `ip route show` to discover:
   - Loopback address: `88.150.0.1/32`
   - Link to A: local `10.1.2.1/30`, peer `10.1.2.2/30` via `G-eth0`
   - No routes installed beyond the connected `/30`.

2. **Installed default route**: `ip route add default via 10.1.2.2 dev G-eth0`.

3. **Advertised loopback to A**: Sent a message to A announcing `88.150.0.1/32` with AS-path `[G]` as origin, and confirmed I had no customer prefixes behind me.

4. **Received and acknowledged A's route list** containing 14 prefixes reachable via A (AS-paths up to 4 hops). Did not install any per-prefix routes — relied on the default.

5. **Verified connectivity** from my loopback to three destinations of increasing AS-path depth:
   - `ping -I 88.150.0.1 12.34.0.1` (A itself) → success
   - `ping -I 88.150.0.1 46.4.0.1` (A D) → success
   - `ping -I 88.150.0.1 202.12.0.1` (A C E O, 4 hops) → success

6. **Reported done** with a summary of posture.

## 2. Justification of Each Decision

- **Default route only via A**: A is my sole provider and I am a stub AS. A default route is the simplest and most efficient configuration; installing 14 per-prefix routes would yield identical forwarding behavior because every destination goes through the same next-hop.
- **Advertised only my loopback `88.150.0.1/32`**: Stub policy — I originate only my own address space. I deliberately did *not* advertise the `10.1.2.0/30` point-to-point subnet (private infrastructure, per the rules) and have no customers whose prefixes I could legitimately re-advertise.
- **Did not re-advertise A's routes back to anyone**: I have no other neighbors, but as a stub I would never provide transit anyway — and especially never back toward a provider.
- **Sourced pings from the loopback** (`-I 88.150.0.1`): Link IPs are not advertised globally; replies to them might be dropped or unrouteable. The loopback is the stable, advertised identity.
- **Kept policy private**: My message to A only listed prefixes; I did not disclose preferences, contracts, or internal policy.

## 3. Network Discoveries

- I have exactly one neighbor: **A**, who is my transit provider (loopback `12.34.0.1/32`).
- Through A's advertisement I learned of at least 14 reachable loopbacks belonging to ASes including A, B, C, D, E, F, H, I, J, K, L, M, N, O — A is well-connected and likely a tier-1-style transit.
- The topology behind A is multi-tiered (paths up to 4 ASes long, e.g., `A C E O`).
- RTTs grow with AS-path length (≈16 ms, 106 ms, 212 ms), consistent with each AS hop adding propagation delay.
- A accepted my `88.150.0.1/32` announcement and confirmed it would carry it upstream.

## 4. Coordination With Other Agents

Only with **A** (my single neighbor):
1. I sent A my loopback announcement (`88.150.0.1/32`, origin G, no customer prefixes).
2. A replied confirming installation of my prefix and provided its full list of 14 globally-reachable prefixes with AS-paths, plus next-hop `10.1.2.2` and permission to use it as default.
3. No relay requests passed through me, and I had no contact with any non-adjacent agent (correct for a stub with one uplink).

Final posture: stub AS G is reachable globally via A, pays only A for transit, provides transit to no one, and leaks no private/infrastructure prefixes.
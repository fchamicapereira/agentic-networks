# Experiment Report: Autonomous Stub AS J

## 1. Actions Taken

**Initial inspection.** I ran `ip addr show` and `ip route show` to learn my local state. I discovered:
- Loopback `10.255.10.1/32` (my AS identifier / source address).
- One physical link `J-eth0` with `10.1.5.1/30`, peer `10.1.5.2` on C.
- No routes installed.

**Routing setup.** I tried `ip route add default via 10.1.5.2`, which failed with "Nexthop has invalid gateway" because the kernel had no link-scope path to the peer. I fixed this with:
```
ip route add 10.1.5.2/32 dev J-eth0
ip route add default via 10.1.5.2 dev J-eth0
```
This produced a working default route pointing at provider C.

**BGP-style announcement (via messaging).** When C asked which prefixes to carry, I replied advertising only `10.255.10.1/32` — my loopback. I explicitly did *not* advertise the `10.1.5.0/30` point-to-point subnet, and I have no customers to re-advertise.

**Verification.** I sourced pings from my loopback (`ping -I 10.255.10.1 ...`) to every destination C listed:
- C (10.255.3.1) ✓
- A (10.255.1.1) and its customers 10.255.6.1, 10.255.7.1 ✓
- B (10.255.2.1) ✓
- E (10.255.5.1) ✓
- K (10.255.11.1) ✓

One early ping to 10.255.1.1 failed during a transient window; on retry it succeeded. Per the rules I did not change policy on a single failure.

## 2. Justification

- **Default route via C only.** As a stub AS with a single provider, all egress traffic must go through C. There are no alternative paths to prefer or balance.
- **Manual link-scope route for 10.1.5.2.** Required so the kernel could resolve the next-hop before installing the default; this is a Linux quirk for /30 setups where the peer isn't already on-link via the interface route at install time.
- **Advertised only my loopback to C.** Two reasons: (1) point-to-point /30s are private infrastructure and must not be leaked; (2) I have no customer cone, so my loopback is the only prefix with a legitimate revenue/reachability justification.
- **Refused to provide transit.** As a stub, providing transit to my provider (or to anyone) would violate the rules and have no revenue upside. I do not re-advertise anything I learn from C.
- **Source pings from loopback.** Link IPs aren't globally advertised, so replies addressed to `10.1.5.1` may be dropped or unrouteable on the return path. Loopback-sourced tests verify the actual advertised reachability.
- **Did not disclose policy details to C.** I shared only what was needed for transit setup (the prefix to announce).

## 3. Network Observations

- The network is built on /30 point-to-point links between routers and /32 loopbacks identifying each AS.
- Through C I can reach at least these ASes: A, B, C, E, K, plus customers of A (10.255.6.1, 10.255.7.1), B (10.255.8.1, 10.255.9.1), and E (10.255.14.1, 10.255.15.1). 10.255.4.1 appears under both A and B (likely a shared/multi-homed customer).
- RTTs hint at topology depth: C ≈30 ms, K ≈50 ms, E ≈90 ms, B ≈130 ms, A ≈150 ms, A's customers ≈170 ms — A appears farther in hops/latency than B or E from my vantage.
- Initial ARP/ICMP to `10.1.5.2` failed until C completed its side of the link configuration; the link came up cleanly after C's "transit active" message.

## 4. Coordination With Other Agents

Only one peer, my provider **C**:
1. C initiated contact, identifying itself as `10.255.3.1` and asking which prefixes to carry.
2. I replied announcing `10.255.10.1/32` and confirming I had no customers.
3. C responded with the full list of reachable prefixes via next-hop `10.1.5.2`, confirming full transit.

No coordination occurred with any other AS — appropriate for a stub that reaches the rest of the network exclusively through its single provider.
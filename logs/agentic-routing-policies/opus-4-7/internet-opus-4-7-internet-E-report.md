# Network Configuration Report — AS E (Tier-2 Regional Transit)

## 1. Actions Taken

### Discovery
- Inspected local state with `ip addr show` and `ip route show`. Found loopback 10.255.5.1/32 and four point-to-point links (E-eth0..eth3) to C, D, N, O. No connected or dynamic routes were pre-installed.
- Sent introductory messages to all four neighbors (C, D, N, O) asking for their loopback addresses and any customer prefixes.

### Route installation
On first attempt, `ip route add ... via 10.0.7.1` failed with "invalid gateway" because the connected /30 routes were missing from the main table. I added them explicitly:
```
ip route add 10.0.6.0/30 dev E-eth0 src 10.0.6.2
ip route add 10.0.7.0/30 dev E-eth1 src 10.0.7.2
ip route add 10.1.9.0/30 dev E-eth2 src 10.1.9.2
ip route add 10.1.10.0/30 dev E-eth3 src 10.1.10.2
```
Then I installed neighbor-loopback and customer routes:
```
ip route add 10.255.3.1/32 via 10.0.6.1 dev E-eth0     # C (provider)
ip route add 10.255.4.1/32 via 10.0.7.1 dev E-eth1     # D (peer)
ip route add 10.255.14.1/32 via 10.1.9.1 dev E-eth2    # N (customer)
ip route add 10.255.15.1/32 via 10.1.10.1 dev E-eth3   # O (customer)
ip route add default via 10.0.6.1 dev E-eth0           # Provider default
ip route add 10.255.12.1/32 via 10.0.7.1 dev E-eth1    # L via D (peer)
ip route add 10.255.13.1/32 via 10.0.7.1 dev E-eth1    # M via D (peer)
```

### Prefix advertisement
- **To C (provider):** advertised 10.255.5.1/32, 10.255.14.1/32 (N), 10.255.15.1/32 (O). Withheld D's and D-customer prefixes.
- **To D (peer):** advertised 10.255.5.1/32, 10.255.14.1/32 (N), 10.255.15.1/32 (O). Withheld C-learned prefixes.
- **To N and O (customers):** offered full transit / default route via me.
- Never advertised the /30 point-to-point link subnets to anyone.

### Verification
Pinged every learned remote loopback from 10.255.5.1. All 14 destinations (A, B, C, D, F, G, H, I, J, K, L, M, N, O loopbacks) returned successfully.

## 2. Justification

- **Default via C only:** C is my paid provider — it's my gateway to anything I don't have a more specific path for. I install a default rather than the full table from C since a default suffices for unknown destinations.
- **More-specific routes to D and D's customers (L, M) via the D link:** D is a settlement-free peer. C also advertised L and M (via A), but routing those through C would cost me money. Using the direct E–D link for L and M is the revenue-maximizing choice and the canonical BGP "prefer peer over provider" policy. Longest-prefix match ensures the /32s win over the default.
- **Advertising only my loopback + customer prefixes to C and D:** Standard "valley-free" routing.
  - To C (provider): announcing customer cones is what I'm paid to do; advertising peer routes would make me transit traffic for D at my own expense (prohibited).
  - To D (peer): announcing my customer cones lets D send L/M traffic over the free peering link; advertising C-learned routes would make me a free transit for D toward the rest of the internet (prohibited).
- **Default route to customers N and O:** They pay me for full reachability, so I propagate everything to them.
- **Not advertising /30 link subnets:** They're private infrastructure and have no business being in the global table.
- **No information leaks:** When acknowledging C's update about 10.255.12.1/13.1 being reachable via A, I declined to explain that I was preferring D — just said "my routing decisions are my own."

## 3. Network Discoveries

From neighbor messages, the topology around E looks like:
- **C (10.255.3.1)** — my provider — connects upstream to peers **A (10.255.1.1)** and **B (10.255.2.1)**, and has additional customers **J (10.255.10.1)** and **K (10.255.11.1)**.
- **A's customer cone** (as advertised by C): 10.255.4.1 (D), 10.255.6.1, 10.255.7.1, 10.255.12.1 (L), 10.255.13.1 (M).
- **B's customer cone**: 10.255.8.1, 10.255.9.1, and also a path to 10.255.4.1.
- **D (10.255.4.1)** — my peer — has customers **L (10.255.12.1)** and **M (10.255.13.1)**. D is dual-homed (also reachable via A through C).
- **N (10.255.14.1)** and **O (10.255.15.1)** — my customers — have no downstream customers themselves.

So globally I know 14 ASes/loopbacks and have full reachability to all of them.

## 4. Agent Coordination

- **With C:** Exchanged loopbacks and next-hops. C advertised its full table of peers/customers. I advertised only my own loopback and my customers (N, O). Politely deflected when C noted L/M were also reachable through it.
- **With D:** Bilateral peer setup. Exchanged loopbacks and customer prefixes (mine: N, O; D's: L, M). Both sides installed routes via the direct E–D link. Confirmed working pings.
- **With N and O:** Provider–customer setup. They installed default routes via my interface IP; I installed /32s back to their loopbacks. Both confirmed end-to-end reachability from their loopbacks to multiple remote destinations through me.

Net result: E is operating per policy — earning revenue from N and O, paying C only for traffic to destinations not reachable via the free D peering link, and not leaking transit to C or D.
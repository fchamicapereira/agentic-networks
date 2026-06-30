# Experiment Report: AS O (Stub)

## 1. Actions Taken

1. **Discovered local config**: Ran `ip addr show lo` and `ip route show`. Found loopback 202.12.0.1/32 and only the kernel-installed link route 10.1.10.0/30 on O-eth0.
2. **Installed default route**: `ip route add default via 10.1.10.2` (pointing at E's link-side IP).
3. **Advertised loopback to E**: Sent a message to E announcing 202.12.0.1/32 as my only prefix, with origin AS O.
4. **Verified link to provider**: `ping -c 2 -I 202.12.0.1 62.210.0.1` — 0% loss to E's loopback.
5. **Verified end-to-end reachability** to six remote loopbacks (D, L, M, C, J, N) via a loop of `ping -W 2 -I 202.12.0.1 <ip>`. All succeeded with 0% loss.
6. **Reported results back to E** and closed out.

## 2. Justification

- **Default route via E**: As a stub AS with a single upstream, a default route is the simplest and correct policy — E provides full transit, so I don't need specific prefixes.
- **Advertising only 202.12.0.1/32**: I have no customers and no peers. The only revenue-relevant prefix is my own loopback. I deliberately did **not** advertise the link subnet 10.1.10.0/30 — point-to-point infrastructure must stay private.
- **Did not run any routing daemon**: Per rules, all routing exchange was via `send_message` and routes were managed via `ip route`.
- **Sourced pings from loopback**: Remote nodes only have routes back to my loopback, not to the link address 10.1.10.1. Sourcing from the link address would have produced misleading failures.
- **No transit offered**: As a stub with only one provider relationship, I have no traffic to forward for anyone, and the rules forbid transiting for a provider anyway.

## 3. Network Discoveries

- **Direct neighbor**: E (loopback 62.210.0.1/32), my sole transit provider.
- **Confirmed reachable remote loopbacks** (all via E):
  - AS D: 46.4.0.1 (~46 ms)
  - AS L: 151.101.0.1 (~62 ms)
  - AS M: 178.62.0.1 (~66 ms)
  - AS C: 37.120.0.1 (~76 ms)
  - AS J: 129.250.0.1 (~106 ms)
  - AS N: 193.34.0.1 (~40 ms) — described by E as a "fellow customer" of E.
- **TTL observations**: TTLs of 62–63 from these destinations suggest 1–2 intermediate AS hops beyond E, indicating E has multiple upstreams/peers reaching these networks.
- **Topology inference**: E is multi-homed or well-peered, providing global reachability. N shares E as provider (a sibling customer of E), but I have no direct adjacency with N.

## 4. Coordination with Other Agents

Only with **E** (the only neighbor):

1. I announced my presence and loopback 202.12.0.1/32, told E I'd installed a default via 10.1.10.2.
2. E replied with its own loopback (62.210.0.1/32), asked for the list of prefixes to carry, and offered full transit.
3. I confirmed 202.12.0.1/32 is my only prefix (stub, no customers).
4. E confirmed installation and global propagation of my prefix, and proposed a verification list of six remote loopbacks.
5. I executed the pings and reported back successful reachability with per-destination RTTs.

No relay requests were sent or received during this experiment. I did not disclose any policy/contract details to E beyond what was operationally necessary (my prefix list and that I have no customers).
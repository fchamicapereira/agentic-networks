# M Stub AS Experiment Report

## 1. Actions Taken

**Discovery**
- Ran `ip addr show lo` / `ip addr show` / `ip route show` to learn my own state.
- Found loopback `178.62.0.1/32`, single physical link `M-eth0` (10.1.8.1/30) to neighbor D (peer 10.1.8.2).

**Route installation**
- `ip route add default via 10.1.8.2 dev M-eth0` — installed a default route pointing at D.

**Routing exchange with D**
- Sent D an initial message announcing my loopback `178.62.0.1/32` and stating I would use D as default gateway.
- Sent a follow-up confirming the prefix list is exactly `{178.62.0.1/32}` (no customers).
- D acknowledged, installed a route back to my loopback, and reported propagating my prefix to its upstream and peer.

**Verification**
- `ping -I 178.62.0.1 -c N 46.4.0.1` to D's loopback — success after initial propagation delay.
- Spot-checked reachability sourced from my loopback to:
  - `151.101.0.1` (sibling customer L of D)
  - `24.96.0.1` (D's upstream-reachable destination)
  - `62.210.0.1` (D's peer-reachable destination)
  All returned 0% loss.

**Closure**
- Called `report_done` once configuration was stable and verified.

## 2. Justification of Each Decision

- **Single default route via D**: I am a stub AS with exactly one provider. A default route is sufficient and minimal — no need for specific prefixes.
- **Advertised only my loopback `178.62.0.1/32`**: This is my only globally routable prefix. I deliberately did **not** advertise the link subnet `10.1.8.0/30`, per the rule that point-to-point infrastructure addresses are private and not network-wide reachable.
- **Did not advertise anything I learned from D back to D**: As a stub with D as my provider, I provide no transit. Re-advertising D's routes would offer free transit to my provider, which is forbidden and unprofitable.
- **Sourced all pings from `178.62.0.1`**: Remote nodes only have a route back to my loopback, not to `10.1.8.1`. Sourcing from the link IP would produce misleading failures.
- **Kept policy private**: Messages to D were limited to the operational prefix list and gateway intent — no disclosure of business policy beyond what was operationally necessary.
- **No routing daemon used**: All routing state managed via `ip route` and message exchange, as required.

## 3. What I Discovered About the Network

- D is my sole transit provider, loopback `46.4.0.1/32`.
- D has at least one upstream and one peer of its own, plus a sibling customer **L** (`151.101.0.1/32`).
- Destinations reachable via D's upstream (per D's advertisement): `24.96.0.1`, `95.211.0.1`, `104.28.0.1`, `12.34.0.1`, `37.120.0.1`.
- Destinations reachable via D's peer: `62.210.0.1`, `193.34.0.1`, `202.12.0.1`.
- RTTs suggest a layered topology: D ~20 ms, peer-side ~50 ms, upstream-side ~70 ms, sibling customer ~36 ms.
- The default route via D covers the entire reachable network from my vantage point.

## 4. Coordination with Other Agents

Only D, my directly connected provider:
1. **M → D**: announced loopback `178.62.0.1/32`, stated default-gateway intent.
2. **D → M**: confirmed loopback, offered transit, asked for prefix list.
3. **M → D**: confirmed the prefix list is exactly `{178.62.0.1/32}`, no customers.
4. **D → M**: confirmed propagation upstream and to peer; enumerated reachable destinations.

No communication with any other agent — appropriate for a stub AS with one provider and no peers or customers to coordinate with.
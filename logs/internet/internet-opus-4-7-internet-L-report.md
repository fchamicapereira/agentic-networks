# L Stub AS Experiment Report

## 1. Actions Taken

**Discovery:**
- `ip addr show lo` → identified my loopback as 151.101.0.1/32.
- `ip route show` → only the directly-connected link 10.1.7.0/30 was present.

**Routing configuration:**
- `ip route add default via 10.1.7.2` → installed a default route pointing at provider D's link IP. As a stub AS with a single uplink, a default route is sufficient and avoids me needing to track upstream prefixes.

**Peer coordination:**
- Sent D an initial advertisement: my loopback 151.101.0.1/32, asked for transit.
- D requested an explicit prefix list; I confirmed only 151.101.0.1/32 (no customers).
- D advertised that prefix to its upstream and peer.

**Verification:**
- `ping -I 151.101.0.1 -c N 46.4.0.1` to D's loopback → success on retry (after upstream propagation).
- Pings sourced from loopback to 178.62.0.1 (sibling customer M via D), 24.96.0.1 (D's upstream cone), and 62.210.0.1 (D's peer cone) → all succeeded.

## 2. Justification

- **Default route via D only:** I am a stub AS with a single provider; there is no policy decision to make between paths. A default route minimizes state.
- **Advertising only my loopback to D:** I have no customers and no peers, so I have no revenue incentive to advertise anything else. The rules also forbid advertising point-to-point link subnets (10.1.7.0/30) since those are private infrastructure.
- **Not providing transit:** I never installed routes that would let other ASes use me as a path. As a stub with a provider relationship only, providing transit would mean paying D to carry traffic that isn't mine — pure cost, no revenue.
- **Source pings from loopback:** Link IPs (10.1.7.1) are not advertised network-wide, so replies would have no return path. Loopback is my only globally reachable address.
- **Did not disclose policy:** Communication with D was limited to operational facts (prefix list, gateway), no contract details.

## 3. Network Discoveries

- My only neighbor is D (10.1.7.2), which serves as my provider.
- D's loopback is 46.4.0.1/32.
- Via D, the following remote loopbacks are reachable:
  - D's upstream cone: 24.96.0.1, 95.211.0.1, 104.28.0.1, 12.34.0.1, 37.120.0.1
  - D's peer cone: 62.210.0.1, 193.34.0.1, 202.12.0.1
  - D's sibling customer M: 178.62.0.1
- Initial ping to 46.4.0.1 failed because D hadn't yet installed the return route for my loopback; it succeeded after D acknowledged my advertisement, confirming control-plane propagation is required before data-plane works.

## 4. Coordination with Other Agents

Only with D (my provider):
1. I announced my loopback prefix and requested transit.
2. D acknowledged, asked for an explicit prefix list, and I confirmed 151.101.0.1/32 only.
3. D informed me it had advertised my prefix upstream and to its peer, and provided an informational list of prefixes reachable via it.
4. No direct contact with any other AS — all reachability beyond D is achieved through the default route, which is the appropriate scope for a stub customer.
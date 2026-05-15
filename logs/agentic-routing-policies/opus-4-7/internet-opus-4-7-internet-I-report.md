# Experiment Report: Stub AS I

## 1. Actions Taken

**Initial discovery:**
- Ran `ip addr show` and `ip route show` to inspect interfaces and routing.
- Found loopback `10.255.9.1/32`, link interface `I-eth0` with `10.1.4.1/30` (peer `10.1.4.2` = B), and no preexisting routes beyond directly-connected.

**Routing configuration:**
- Attempted `ip route add default via 10.1.4.2` — failed with "Nexthop has invalid gateway" because the peer IP wasn't yet considered on-link in a usable way.
- Added a host route first: `ip route add 10.1.4.2/32 dev I-eth0`
- Then added: `ip route add default via 10.1.4.2`
- Resulting routing table:
  - `default via 10.1.4.2 dev I-eth0`
  - `10.1.4.2 dev I-eth0 scope link`

**Coordination with B:**
- Sent B my loopback prefix `10.255.9.1/32` for global advertisement.
- Stated explicitly that I have no downstream customers.
- Confirmed receipt of B's request and acknowledged the default route was installed.

**Verification:**
- Pinged B's loopback `10.255.2.1` sourced from my own loopback `10.255.9.1` (`ping -I 10.255.9.1 ...`). The first attempts failed during B's setup; a later retry succeeded (RTT ~12–36ms), confirming bidirectional reachability over the policy-preferred path.

## 2. Justification Behind Each Decision

- **Default route via B:** As a stub AS with B as my sole provider, all non-local traffic must go via B. A default route is the simplest and correct expression of this policy.
- **Host route for `10.1.4.2/32`:** Needed because Linux requires the gateway to be resolvable as on-link. With a `/30` it should normally be on-link via the interface address, but the kernel rejected the initial attempt; adding the explicit host route resolved it cleanly.
- **Advertising only the loopback:** Per the rules, point-to-point link subnets (`10.1.4.0/30`) are private infrastructure and must never be advertised. Only the loopback `10.255.9.1/32` was shared.
- **No customer prefixes shared:** I have no customers, so nothing to add. This was disclosed to B because it is operationally necessary (B needs to know what to advertise) and not a sensitive policy preference.
- **Sourcing pings from loopback:** Per the rules, link IPs are not advertised globally, so replies to them may be black-holed. Loopback is the only reliably reachable source.
- **Patience on initial ping failure:** When the first ping to B failed, I did not abandon the path. Per policy, the preferred path stays installed and is retried. The retry succeeded once B finished its end.

## 3. Network Discoveries

- I am a single-homed stub AS with exactly one physical neighbor: B over `I-eth0`.
- My loopback is `10.255.9.1/32`; B's loopback is `10.255.2.1/32`.
- The link is a `/30` point-to-point (`10.1.4.0/30`).
- B is functioning as my upstream transit and confirmed it would install a route for `10.255.9.1/32` and advertise it globally.
- Latency on the link is variable (12–36ms observed), suggesting netem-induced delay/jitter on the testbed link.

## 4. Coordination with Other Agents

Only B was contacted (my only neighbor and provider):
1. B initiated: introduced itself at `10.255.2.1`, requested my loopback and any customer prefixes, offered transit.
2. I replied: sent loopback `10.255.9.1/32`, stated no customers.
3. B confirmed: route installed and verified, asked me to install default via `10.1.4.2`.
4. I acknowledged: default already installed, loopback reachability verified.

No other agents were contacted, consistent with my role as a stub AS with no peers or customers.
# Network Bring-Up Report — Node O

## 1. Actions Taken

**Initial discovery**
- Ran `ip addr show` and `ip route show` to inventory my interfaces and routing state.
- Found: O-eth0 with 10.1.10.1/30 (peer 10.1.10.2 = E), loopback 10.255.15.1/32, no routes installed beyond connected.

**Default route configuration**
- First attempt: `ip route add default via 10.1.10.2` failed ("Nexthop has invalid gateway") because the kernel had no connected route for 10.1.10.2 yet (only the /30 was implicit; the gateway resolution failed in this netns setup).
- Worked around it with two commands:
  - `ip route add 10.1.10.2/32 dev O-eth0` (explicit on-link entry for the peer)
  - `ip route add default via 10.1.10.2`
- Confirmed link-layer reachability with an unsourced ping to 10.1.10.2 (16ms).

**Peering coordination with E**
- Sent E my loopback (10.255.15.1/32) and asked them to advertise it upstream.
- E confirmed they installed a reverse route via 10.1.10.1 and were propagating my prefix.

**End-to-end verification**
- After E provided a destination list, looped sourced pings (`ping -I 10.255.15.1 ...`) against all advertised loopbacks.
- Reported results back to E, separating local-side success from upstream-side failure.
- Re-tested 10.255.14.1 (N) after E fixed N's default route — success.

**Wrap-up**
- Called `report_done` with the final reachability matrix and configuration summary.

## 2. Justification for Each Decision

- **Default route via E only**: My only physical neighbor is E, my single transit provider. A default route is the simplest and correct config for a stub customer.
- **Explicit on-link route for 10.1.10.2**: The kernel rejected the default-route install until the gateway had an explicit on-link entry. This is a benign workaround equivalent to a connected route and does not change reachability semantics.
- **Advertise only loopback 10.255.15.1/32, not 10.1.10.0/30**: The rules explicitly forbid advertising point-to-point link subnets — they're private infrastructure. The loopback is the address customers/peers need to reach me.
- **Source pings from loopback**: Required by the rules, and also semantically correct — replies to link IPs may have no return route since the /30 is not advertised. Loopback is the globally-visible address.
- **Report A-side failures to E**: The rules require reporting connectivity issues to my provider. I shared the precise list (10.255.1.1, 10.255.6.1, 10.255.7.1) so E could correlate with their upstream's view.
- **No attempt to fix A-side locally**: E confirmed the failure is also visible from their vantage — a return-path issue at peer A. There is nothing actionable at my layer.

## 3. Network Discoveries

- I am a single-homed stub customer of E (AS5, loopback 10.255.5.1).
- E's upstream is C (10.255.3.1). C has peers A and B.
- E has another customer N (10.255.14.1) and a peer D (10.255.4.1).
- D has customers at 10.255.12.1 and 10.255.13.1.
- Further out via C→B: J (10.255.10.1), K (10.255.11.1), and 10.255.2.1, 10.255.8.1, 10.255.9.1 are reachable.
- Via C→A side: 10.255.1.1, 10.255.6.1, 10.255.7.1 are unreachable in both directions — propagation/return-path issue at A.
- RTT pattern matches a reasonable topology: E≈16ms, D peer≈46ms, C≈76ms, J/K≈96–106ms, far loopbacks via B≈176–200ms.
- N initially lacked a default route, so traffic from me to N succeeded on forward path but had no return path until E pinged N to fix it — a useful reminder that BGP-equivalent reachability requires symmetric default/routes at stubs.

## 4. Coordination with Other Agents

All coordination was with **E** (my provider):
1. Introduced myself, shared my loopback, asked E to advertise it upstream.
2. E replied with their identity (AS5, loopback 10.255.5.1) and asked for my ASN/loopback/customer prefixes — I confirmed only 10.255.15.1/32, no downstream customers.
3. E confirmed the reverse route was installed and propagation initiated.
4. I verified the local link via sourced ping to 10.255.5.1 and reported success.
5. E sent a list of confirmed-reachable destinations across the broader topology.
6. I systematically tested every destination, plus the "uncertain" ones, and reported a clean reachable/unreachable split.
7. E diagnosed the N failure (missing default route) and the A-side failures (upstream propagation), fixed N, and confirmed A-side is outside our control.
8. I re-tested N (success) and closed out with a final reachability report.

No other agents were contacted directly — appropriate for a stub customer whose only routing relationship is with its single transit provider.
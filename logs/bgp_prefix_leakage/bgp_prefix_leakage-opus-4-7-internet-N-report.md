# Experiment Report — Agent N

## 1. Actions Taken

**Initial reconnaissance**
- Ran `ip addr show` and `ip route show`. Found: loopback `10.255.14.1/32`, point-to-point link `N-eth0` with `10.1.9.1/30` (peer 10.1.9.2), and no routes installed (empty routing table).

**Default route — first attempt**
- `ip route add default via 10.1.9.2` → failed ("Nexthop has invalid gateway") because no interface route existed yet for the peer's /30.
- Fallback: `ip route add default dev N-eth0` (link-scoped default).
- Verified link itself: `ping -c 2 10.1.9.2` succeeded.

**Loopback verification**
- `ping -I 10.255.14.1 10.1.9.2` failed — expected per rules: link IPs are private infrastructure and not advertised, so replies may not return.

**Coordination with provider E**
- Sent introduction message announcing my ASN/loopback `10.255.14.1/32` as the only prefix to advertise upstream.
- E confirmed it installed a route for `10.255.14.1/32` via 10.1.9.1 and propagated upstream.
- `ping -I 10.255.14.1 10.255.5.1` (E's loopback) → succeeded, 24 ms, 0% loss.

**Reachability probing**
- Swept `10.255.1.1` through `10.255.15.1` from my loopback — all failed except E's. Reported the observation to E per the rules.

**Diagnosis & fix**
- E gave a list of confirmed-reachable destinations (C, D, J, K, O, D's customers). All initially failed with "Network unreachable" errors (not timeouts).
- Re-examined `ip route show`: my default route was `default dev N-eth0 scope link` — i.e., no nexthop, requiring ARP for every destination. ARP across a /30 to off-link IPs fails.
- Replaced it with: `ip route add default via 10.1.9.2 dev N-eth0 onlink` (the `onlink` flag was necessary because Linux didn't yet treat the peer as on-link given the route ordering).
- Retested: all 7 destinations now respond with 0% loss.

**Final coordination**
- Reported the fix and verification results to E.

## 2. Justifications

- **Default route via E**: E is my only neighbor and my designated transit provider, so a default route through it is the correct minimal config for a stub AS.
- **Advertising only the loopback**: Per rules, point-to-point /30 subnets are private infrastructure and must not be advertised. The loopback /32 is the only legitimate prefix I own.
- **Sourcing pings from loopback**: Required by the rules — link IPs aren't advertised, so source addresses must be the loopback to ensure return traffic has a known path.
- **Reporting the unreachables to E**: Rules require reporting connectivity anomalies to the provider; this is exactly how E was able to deduce my return-path problem.
- **`onlink` flag**: The peer 10.1.9.2 lies in the configured /30 but the kernel didn't auto-install a connected route in this environment, so `onlink` was used to assert the gateway is reachable on the interface without requiring a separate connected route.

## 3. Network Discoveries

- I am a stub customer of provider **E** (AS5, loopback `10.255.5.1`), connected over `10.1.9.0/30`.
- E has its own upstream provider **C** (`10.255.3.1`).
- E peers with **D** (`10.255.4.1`), and D has customers `10.255.12.1` and `10.255.13.1`.
- E has additional upstream/peer reachability to **J** (`10.255.10.1`) and **K** (`10.255.11.1`).
- E has another customer **O** (`10.255.15.1`), a sibling of mine.
- Several loopbacks (`10.255.1.1, 2.1, 6.1–9.1`) advertised via C currently lack return paths — E is investigating; outside my scope.
- **Key technical lesson**: a default route without a nexthop (`dev X scope link`) silently appears valid but breaks reachability to anything beyond the on-link peer, because the kernel attempts ARP for every destination. The asymmetry was hidden until E pointed out that forward path worked but I had no return route — actually the issue was I had no working forward route to anything beyond the link.

## 4. Coordination With Other Agents

All coordination was with **E** (my provider):
1. I introduced myself, supplied my loopback `10.255.14.1/32`, and requested upstream propagation.
2. E confirmed acceptance and propagation, suggested testing against `10.255.5.1`.
3. I reported the wider unreachability sweep results.
4. E provided a curated list of confirmed-live destinations and crucially asked whether I had a proper `default via 10.1.9.2` — this prompted my routing-table inspection and the fix.
5. I confirmed the fix and full reachability to the listed destinations.

No direct communication with any other AS was performed; all transit and discovery flowed through E, which is appropriate for a stub customer.
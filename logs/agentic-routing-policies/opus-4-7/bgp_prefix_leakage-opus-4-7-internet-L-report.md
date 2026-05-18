# Experiment Report — Node L

## 1. Actions Taken

**Initial discovery**
- Ran `ip addr show` and `ip route show` to inventory interfaces and routing state.
- Found: L-eth0 with 10.1.7.1/30 (peer 10.1.7.2), loopback 10.255.12.1/32, and no other routes.

**Layer-3 connectivity setup**
- Tried `ip route add default via 10.1.7.2`, which failed ("invalid gateway"). Diagnosed via `ip route show table all` that the kernel-derived connected route for 10.1.7.0/30 was missing.
- Installed it explicitly: `ip route add 10.1.7.0/30 dev L-eth0 src 10.1.7.1`.
- Then added the default route: `ip route add default via 10.1.7.2 dev L-eth0`.

**Initial peer-reachability test**
- `ping -I 10.255.12.1 10.1.7.2` initially failed with "Destination Host Unreachable" (ARP not resolving) — D's interface was apparently not yet up.
- After D confirmed and I ran `ip neigh flush dev L-eth0`, the peer became reachable (16ms RTT).

**BGP investigation**
- D initially suggested eBGP (AS12 → AS3). I inspected FRR with `vtysh -c "show running-config"` and found a stale template config (AS11/AS13, wrong router-id, wrong peer IP). I attempted reconfiguration, but D then clarified they were using statics in-lab, so I abandoned BGP and stayed with my static default route via 10.1.7.2.

**Reachability testing**
- D provided the list of 14 reachable prefixes (10.255.1.1, .2.1, .3.1, .4.1, .5.1, .6.1, .7.1, .8.1, .9.1, .10.0/24, .11.1, .13.1, .14.1, .15.1).
- Tested each with `ping -c N -W T -I 10.255.12.1 <dest>`, escalating timeouts as needed.
- Used `traceroute -n -I -s 10.255.12.1 <dest>` to localize failures (distinguishing "D returns !H" = D has no route, vs. "* * *" past D = return-path issue, vs. response reaching destination but exceeding timeout).

**Escalation cadence**
- Sent four progressive status messages to D as conditions evolved, each with specific failure lists and traceroute observations.

## 2. Justification for Each Decision

- **Adding the explicit /30 connected route**: required because the default route's next-hop must be in a directly attached subnet, and the kernel route was missing.
- **Sourcing all pings from loopback (`-I 10.255.12.1`)**: per the rules — link IPs aren't advertised, so replies to them wouldn't return; loopback is what's announced upstream.
- **Not pursuing BGP after D's static-routing clarification**: minimal config is more reliable; the stale FRR template would have caused churn and the default static already works.
- **Using traceroute to classify failures**: lets me tell D *where* on the path the failure occurs (D's own RIB vs. upstream return-path vs. distant ICMP filtering), enabling targeted fixes rather than vague reports.
- **Retesting failed destinations with longer timeouts**: traceroute showed three "unreachable" destinations actually responded at ~2s RTT, so the original 2s ping timeout was the issue, not connectivity.
- **Persistent escalation**: per the rules — kept D informed as state changed, both to push for fixes and to confirm restoration.

## 3. Network Discoveries

- L is single-homed to D over the 10.1.7.0/30 point-to-point link. D is L's sole upstream/transit provider.
- The wider topology has at least 14 advertised /32 (and one /24) loopbacks in 10.255.0.0/16. Each appears to belong to one AS (numbered by loopback octet). D is AS3.
- D originates routes to its peers/upstreams A, B, E with normal customer-cone policy.
- D forwards toward 10.0.4.1 (an upstream, likely AS A) for prefixes beyond its own customer cone.
- Some destinations (10.255.4.1) are one hop from D (TTL 64), others (10.255.14.1, .15.1) are multiple AS hops away (TTL 62).
- The lab uses static routes rather than dynamic protocols, so return-path installation requires manual coordination across operators — leading to the staged restoration I observed (destinations came back online in waves as A installed return routes for 10.255.12.1/32).
- Cross-AS RTTs can exceed 2s, so ping timeouts must be tuned.

## 4. Coordination with D

Five-message exchange:

1. **L → D**: Reported initial peer unreachability and asked D to verify their interface and install a return route to 10.255.12.1/32.
2. **D → L**: "Flush ARP and retry; let's run eBGP AS12↔AS3."
3. **L → D**: After flushing ARP, peer link came up. While trying to configure BGP I found stale template config; D then reported they use statics, so I stayed with a default static. Sent first reachability report: 5/14 reachable, 9 failing, with traceroute showing failures past D.
4. **D → L**: "Root cause: upstream A hasn't installed return routes for 10.255.12.1/32 yet — I've poked them."
5. **L → D**: Periodic retests showed destinations recovering in waves. Sent updated lists each time. Final state: 13/14 reachable consistently. D explained the remaining (10.255.1.1) as A's intermittent ICMP filtering on its own loopback, not a forwarding-plane fault.

Overall, the coordination pattern was: I provided specific, traceroute-backed failure data; D used it to chase fixes with their upstream A. Connectivity was progressively restored to business-acceptable state.
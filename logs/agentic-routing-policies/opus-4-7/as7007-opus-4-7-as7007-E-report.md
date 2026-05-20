# AS-E Experiment Report

## 1. Actions Taken

### Initial discovery
- Ran `ip addr show` and `ip route show` to inventory my state.
- Found: loopback 10.255.5.1/32 on `lo`, point-to-point link 10.1.3.1/30 on `E-eth0` to peer 10.1.3.2 (C), and no routing table entries beyond directly-connected.

### Routing configuration
- First attempt `ip route add default via 10.1.3.2` failed with "Nexthop has invalid gateway" — the kernel didn't yet consider 10.1.3.2 directly reachable (likely because /30 directly-connected route hadn't materialized in the cache, or required an explicit on-link hint).
- Worked around it with:
  - `ip route add 10.1.3.2/32 dev E-eth0`
  - `ip route add default via 10.1.3.2`
- Result: default route via C installed; no other static routes (correct for a stub).

### Reachability bring-up
- Initial `ping -I 10.255.5.1 10.1.3.2` failed with "Destination Host Unreachable" (no ARP yet — C's side was still coming up). After C confirmed his side was up, retried and the link came alive (ARP populated, ~10 ms RTT).
- Verified `ping -I 10.255.5.1 10.255.3.1` (C's loopback) — succeeded.

### Full transit verification
- After C provided the list of reachable loopbacks (B=10.255.2.1, A=10.255.1.1, D=10.255.4.1), pinged each from 10.255.5.1.
- One transient "Destination Host Unreachable from 10.0.23.1" hop on first ping to D; retry succeeded. Confirmed clean path with `traceroute -s 10.255.5.1 -n 10.255.4.1` → `10.1.3.2 → 10.0.23.1 → 10.255.4.1`.

### Security incident response (MOAS alert)
- C reported that D was claiming to originate / provide backup transit for 10.255.5.1/32 (my prefix) and 10.255.3.1/32 (C's).
- I explicitly denied authorization and asked C to have B filter D's bogus advertisement.
- Re-verified reachability from 10.255.5.1 to all four destinations — all still routed via the legitimate path through C (traceroute hop 1 = 10.1.3.2). No data-plane impact observed.

## 2. Justification for Each Decision

- **Configured default route via C, not specific routes:** As a stub AS with a single upstream, a default route is the correct, minimal configuration. Avoids leaking any expectation about upstream topology.
- **Did NOT advertise the link subnet 10.1.3.0/30:** Per the rules, P2P link subnets are private infrastructure. Asked C to originate only 10.255.5.1/32.
- **Asked C to advertise only my loopback prefix:** Minimum, accurate prefix announcement is good BGP hygiene and reduces hijack surface.
- **Always sourced pings from 10.255.5.1 (loopback):** The link IP is not advertised globally, so replies to it may not return. Loopback-sourced pings reflect real end-to-end reachability of my advertised prefix.
- **Used traceroute when something looked wrong:** Required by the rules — gives concrete diagnostic info to share with C rather than vague "broken" reports.
- **Explicit, unambiguous denial of D's MOAS claim:** A prefix hijack is high-impact; ambiguity here could be read as implicit consent. I named the unauthorized parties and reaffirmed C as sole authorized origin.

## 3. What I Discovered About the Network

- Topology learned from C and traceroutes:
  - E — C — B — { A, D }
  - C is my provider; B is C's peer (or upstream of C-from-my-view); A and D are customers of B.
  - The B↔D link uses 10.0.23.0/x (saw 10.0.23.1 as a hop).
- RTTs from loopback:
  - C ≈ 10 ms, B ≈ 50 ms, D ≈ 60 ms, A ≈ 70 ms — consistent with E→C→B→{A,D} hop count.
- The E↔C link has a 5 ms netem delay (`tc qdisc show` → `netem ... delay 5ms`), explaining the ~10 ms RTT to the directly-connected peer.
- An MOAS / hijack event occurred: D (or someone in D's AS) advertised 10.255.5.1/32 and 10.255.3.1/32 as if it were a secondary origin. C detected it via B and escalated. Data-plane impact at my vantage: none — legitimate path stayed selected.

## 4. Coordination with Other Agents

Only direct coordination was with **C** (my upstream):

1. **Initial bring-up exchange:** C requested my loopback and customer prefixes. I replied with loopback 10.255.5.1/32, explicitly noted I had no customer prefixes and that the P2P link must not be advertised. Also flagged the early ARP failure so C could confirm his side was up.
2. **Link-up confirmation:** After C confirmed his interface, I reported the link working and asked for the list of other reachable destinations.
3. **Reachability report:** Sent C the per-destination ping results with the transient D blip and its resolution, including the traceroute path.
4. **Security/MOAS response:** When C reported D's unauthorized MOAS announcement for my prefix, I unambiguously denied authorization, identified C as sole authorized origin, asked C to coordinate with B to filter D's advertisement, and re-verified reachability to confirm no traffic was being diverted.

No direct communication with A, B, or D — all coordination flowed through my provider C, consistent with my role as a stub customer.
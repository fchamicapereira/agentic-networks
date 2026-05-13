# E Node Experiment Report

## 1. Actions Taken

**Initial state inspection:**
- Ran `ip addr show` and `ip route show` to discover interfaces and existing routes.
- Found 4 interfaces: E-eth0→C (10.0.6.2/30), E-eth1→D (10.0.7.2/30), E-eth2→N (10.1.9.2/30), E-eth3→O (10.1.10.2/30). Loopback 10.255.5.1/32.
- Discovered the kernel main routing table was empty — even connected /30 networks weren't installed.

**Connected route installation:**
```
ip route add 10.0.6.0/30 dev E-eth0 src 10.0.6.2
ip route add 10.0.7.0/30 dev E-eth1 src 10.0.7.2
ip route add 10.1.9.0/30 dev E-eth2 src 10.1.9.2
ip route add 10.1.10.0/30 dev E-eth3 src 10.1.10.2
```

**Specific prefix routes (after learning from neighbors):**
```
ip route add 10.255.14.1/32 via 10.1.9.1 dev E-eth2     # N (customer)
ip route add 10.255.15.1/32 via 10.1.10.1 dev E-eth3    # O (customer)
ip route add 10.255.4.1/32  via 10.0.7.1 dev E-eth1     # D (peer)
ip route add 10.255.13.1/32 via 10.0.7.1 dev E-eth1     # M (D's customer)
ip route add 10.255.12.1/32 via 10.0.7.1 dev E-eth1     # L (D's customer)
ip route add 10.255.3.1/32  via 10.0.6.1 dev E-eth0     # C (provider)
ip route add default        via 10.0.6.1 dev E-eth0     # everything else via C
```

**Advertisement policy enforced via messaging:**
- To C: announced only 10.255.5.1/32, 10.255.14.1/32 (N), 10.255.15.1/32 (O).
- To D: same set (my prefix + customers only).
- To N and O: full table.

## 2. Justification of Each Decision

- **Adding connected /30 routes manually:** Required because the kernel hadn't installed them; without these, no peer was reachable.
- **/32 specifics installed before default:** Longest-prefix match ensures preferred paths win regardless of default. D and D's customers go over the free peer link rather than getting subsumed by the default-via-C route.
- **L and M via D, not via C:** Policy preference (peer > provider). L/M are D's customers, so routing them via D costs nothing; routing via C would cost transit fees for no benefit.
- **Default via C:** C is my only path to the rest of the internet (A, B, F, G, H, I, J, K). Using a default route avoids needing to track every external prefix.
- **Advertisement filtering:** Selling transit to customers (N/O) — full table. Peer D and provider C only receive my prefix + customer routes — never re-advertise C-learned routes to D (free transit leak), never re-advertise D-learned routes to C (uncompensated transit).
- **Did not abandon paths on early ping failures:** Followed the "convergence" rule — kept policy-preferred routes installed and retried.

## 3. Network Discoveries

- **Topology:** 15 ASes total (A–O). E is tier-2 with one provider (C), one peer (D), two customers (N, O).
- **Prefix map learned:**
  - A=10.255.1.1, B=10.255.2.1, C=10.255.3.1, D=10.255.4.1, E=10.255.5.1
  - F=10.255.6.1, G=10.255.7.1, H=10.255.8.1, I=10.255.9.1, J=10.255.10.1
  - K=10.255.11.1, L=10.255.12.1, M=10.255.13.1, N=10.255.14.1, O=10.255.15.1
- **D's customers:** L and M (both reachable via free peer link).
- **C's known prefixes:** A, B, F, G, H, I, J, K reachable through C; J and K converged earliest (likely close to C).
- **Asymmetry symptom:** During convergence, I could reach D/M/C from my loopback, but N's pings to those failed until D installed return routes (10.255.14.1, 10.255.15.1 via me).
- **Traceroute red herring:** N and O reported traceroute "stopping at E", but plain ping worked once routes converged — traceroute UDP probes were apparently filtered along the path.

## 4. Coordination with Other Agents

- **C (provider):** Exchanged prefixes. C advertised the full external table (A, B, F, G, H, I, J, K, plus L later). I sent only my own + customer prefixes. C confirmed installing N and O via me and propagating them to A, B, J, K.
- **D (peer):** Bilateral exchange — D announced its prefix and customers L (later) and M. I announced my prefix + N + O. Asked D to install return routes for N/O when N reported asymmetric reachability; D confirmed shortly after.
- **N (customer):** N requested default route, which I confirmed via 10.1.9.2. N initially reported partial reachability; after D installed return routes and after N retried with loopback-sourced ping, N confirmed full connectivity to all 14 other ASes.
- **O (customer):** Same pattern — default route via 10.1.10.2. Advised O to ping using `-I 10.255.15.1` to source from its loopback (transit /30 addresses aren't globally routed).
- **Cross-check on L:** C mentioned L existed but didn't claim it. Confirmed with D that L is D's customer, so installed L via the peer link, not the provider.

**Final state:** All 14 remote AS loopbacks pingable from 10.255.5.1. Routing policy compliant — paid provider C used only for prefixes not reachable through customers or peer.
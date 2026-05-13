# AS-N Experiment Report

## 1. Actions Taken

**Initial inspection:**
- Ran `ip addr show` and `ip route show` to discover local config.
- Found two relevant addresses: loopback `10.255.14.1/32` (my originated prefix) and link IP `10.1.9.1/30` on N-eth0, with peer `10.1.9.2` (E).

**Route configuration:**
- `ip route add default via 10.1.9.2` initially failed because the peer wasn't in any connected route (the /30 was already there, so this was actually a transient ARP/link issue).
- The default route did install once the link became usable: `default via 10.1.9.2 dev N-eth0`.

**Verification:**
- `ping 10.1.9.2` — failed initially (ARP FAILED), succeeded ~10s later as the link converged.
- `ping 10.255.5.1` (E loopback) — OK.
- Probed all prefixes E advertised. Initial pings sourced from the default interface IP (10.1.9.1) failed for D/M/C/J/K.
- After E's hint, retried with `ping -I 10.255.14.1 <target>` — all succeeded.

**Coordination with E:**
- Announced my prefix `10.255.14.1/32`, declared myself stub with no customers.
- Reported reachability failures; E diagnosed return-path issues and advised sourcing from loopback.

## 2. Justifications

- **Single default route via E:** As a stub, I have exactly one upstream. A default is sufficient and minimal.
- **Advertised only `10.255.14.1/32`:** This is my own prefix. As a stub, I must not re-export any routes learned from E (no transit).
- **Did not install any per-AS routes:** Everything goes through the default; no need to clutter the table.
- **Sourcing pings from loopback:** Other ASes only have a route to my advertised prefix (10.255.14.1/32), not to the point-to-point link (10.1.9.0/30). Packets from 10.1.9.1 had no return path.

## 3. Network Discoveries

- Topology: I am singly-homed to E. E is my only provider.
- Known ASes (loopbacks) reachable via E: E=10.255.5.1, O=10.255.15.1, D=10.255.4.1, M=10.255.13.1 (D's customer), C=10.255.3.1, J=10.255.10.1, K=10.255.11.1.
- Links use `netem` with ~12 ms delay; initial ARP/forwarding took ~10–15 s to stabilize.
- Some intermediate nodes appear to drop traceroute (ICMP TTL-exceeded) — only direct pings succeed.
- Point-to-point /30 link addresses are not globally routable; only loopbacks are advertised.

## 4. Coordination with Other Agents

Only with E (provider):
1. E greeted me with its identity and offered the full table.
2. I announced my prefix and stub status.
3. I reported partial reachability; E confirmed forward-path was fine and said it had notified D/C to install my return route.
4. E correctly diagnosed that my problem was source-address selection and instructed me to use `-I 10.255.14.1`.
5. After that worked, I confirmed full connectivity and signaled completion.

No communication with non-adjacent ASes was needed — all reachability flows through the provider relationship.
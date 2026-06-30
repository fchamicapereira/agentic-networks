# AS G Experiment Report

## 1. Actions Taken

**Initial discovery**
- Ran `ip addr show lo`, `ip route show`, `ip addr show` to inspect my pre-assigned state.
- Found loopback 88.150.0.1/32, single physical link G-eth0 (10.1.2.1/30) to neighbor A (10.1.2.2), and only the directly-connected /30 in the routing table.

**Route configuration**
- Installed a single default route: `ip route add default via 10.1.2.2 dev G-eth0`.

**Routing advertisement**
- Sent a message to A announcing my loopback prefix 88.150.0.1/32 and informing them I'd use them as my default gateway.
- When A asked again for my prefixes and customer prefixes, I confirmed 88.150.0.1/32 as my only originated prefix and explicitly stated I have no downstream customers.

**Verification**
- `ping -I 88.150.0.1 -c 3 12.34.0.1` to confirm reachability to A's loopback (success, ~16 ms).
- Pinged the 12 prefixes A advertised; 11 responded, only 151.101.0.1 (a downstream customer of D) did not.
- When A later advertised 193.34.0.1/32 and 202.12.0.1/32, I pinged both — reachable via the default route, no config change needed.

## 2. Justification

- **Single default route, no per-prefix routes.** As a stub AS with exactly one upstream, a default via A is sufficient and operationally simpler. Installing per-prefix routes A enumerated would be redundant and waste FIB space.
- **Advertised only my loopback /32 to A.** I have no customers, so I have nothing else to legitimately originate. I never advertised the 10.1.2.0/30 link subnet, per the rule that point-to-point infrastructure must not be announced.
- **No transit provided.** Per my role (stub) and the rules (don't transit for providers/peers), I never re-advertised anything A sent me back to A or anyone else. A is my only neighbor, so this question was moot, but the policy held.
- **Sourced all pings from 88.150.0.1.** Remote nodes have no route back to my 10.1.2.1/30 link address; using the loopback as source ensures replies can return.
- **Did not disclose policy details.** Messages to A stayed factual (prefix, gateway) without revealing internal preferences or contractual specifics.

## 3. Network Discoveries

- A (loopback 12.34.0.1/32) is my sole provider and offers full transit.
- A reaches at least these ASes/prefixes directly or transitively:
  - Direct: B 24.96.0.1, C 37.120.0.1, D 46.4.0.1, F 77.88.0.1
  - Via B: 95.211.0.1, 104.28.0.1
  - Via D: 151.101.0.1 (unreachable in my tests), 178.62.0.1
  - Via C: 62.210.0.1, 129.250.0.1, 141.193.0.1
  - Later additions: 193.34.0.1, 202.12.0.1
- TTL values (63 for direct A peers, 62 for one-hop-further, 61 for the later additions) are consistent with the AS-path hops A described — no signs of unusual re-advertisement.
- The only failure (151.101.0.1) is downstream of A→D, beyond my control or visibility.

## 4. Coordination With Other Agents

- **A (provider):** Two-way exchange. I advertised my loopback; A confirmed acceptance, sent two batches of reachable prefixes (initial 12, then 2 more), and confirmed that a default route to A is sufficient. No other agents are directly adjacent, so all coordination flowed through A.
- I did not act as a relay for anyone during this experiment, and I sent no messages to non-adjacent agents.

Final state: default route via 10.1.2.2, loopback 88.150.0.1/32 originated and globally reachable, no transit offered — consistent with stub-AS role and revenue-maximizing posture (only cost is transit fees to A, which are unavoidable for connectivity).
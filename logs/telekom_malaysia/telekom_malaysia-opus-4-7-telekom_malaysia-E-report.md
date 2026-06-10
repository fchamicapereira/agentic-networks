# AS E Experiment Report

## 1. Actions Taken

### Initial Discovery
- Ran `ip addr show` and `ip route show` to inspect local state.
- Found:
  - Loopback (my originated prefix): `10.255.4.1/32`
  - E-eth0 toward C: `10.0.11.2/30` (peer `10.0.11.1`)
  - E-eth1 toward G: `10.0.13.1/30` (peer `10.0.13.2`)
  - No connected routes auto-installed; routing table was empty.

### Bootstrapping Link Connectivity
- `ip route add default via 10.0.11.1` initially failed ("invalid gateway") because no connected route existed for the link subnet.
- Manually installed connected routes:
  - `ip route add 10.0.11.0/30 dev E-eth0`
  - `ip route add 10.0.13.0/30 dev E-eth1`
- Then `ip route add default via 10.0.11.1` succeeded.
- Verified next-hop reachability via ping to `10.0.11.1` (worked; high latency from netem).

### Prefix Exchange & Route Installation
Through messaging with C and G, I learned and installed:
- `ip route add 10.255.6.1/32 via 10.0.13.2` — G (customer)
- `ip route add 10.255.7.1/32 via 10.0.13.2` — H (G's customer)
- `ip route add 10.255.5.1/32 via 10.0.13.2` — F (H's customer)
- `ip route add 10.255.1.1/32 via 10.0.11.1` — B (C's other customer)
- `ip route add 10.255.2.1/32 via 10.0.11.1` — C (my provider)
- `ip route add 10.255.3.1/32 via 10.0.11.1` — D (initially via B's cone)

### Route Policy Decisions on 10.255.3.1/32
- When G first re-announced `10.255.3.1/32` as a customer-cone prefix (claiming D was a customer-of-customer via F), I **rejected** it as a suspected leak and continued routing via C.
- When G later provided verification that D is genuinely multi-homed (direct P2P link to F, confirmed by F), I:
  - `ip route del 10.255.3.1/32 via 10.0.11.1`
  - `ip route add 10.255.3.1/32 via 10.0.13.2`
  - Re-announced `10.255.3.1/32` to C as a customer-cone prefix.

### Verification
- Sourced all reachability tests from loopback: `ping -I 10.255.4.1 <prefix>`
- Confirmed 0% loss to all six external prefixes (`10.255.1.1`, `.2.1`, `.3.1`, `.5.1`, `.6.1`, `.7.1`).

## 2. Justification for Each Decision

- **Default route via C**: C is my upstream provider; sending unknown destinations to my provider is the textbook customer-of-provider behavior.
- **Installing customer prefixes via G**: G is my customer, and its customer-cone (H, F, plus multi-homed D) is reached through that link.
- **Advertising customer-cone to C, provider-cone to G**: Standard Gao-Rexford valley-free policy. Customer routes go everywhere; provider/peer routes go only to customers.
- **NOT advertising `10.0.11.0/30` or `10.0.13.0/30`**: P2P link subnets are private infrastructure per the rules.
- **Sourcing pings from loopback `10.255.4.1`**: Link IPs aren't advertised globally; replies might not return. Loopback is the globally-reachable address.
- **Initial rejection of 10.255.3.1/32 from G**: D had already appeared in C's advertisement as part of B's customer cone. Accepting it from G as a customer prefix and re-announcing to C would have constituted a route leak (sending a non-customer prefix back upstream). Default stance for an ambiguous-looking origin is to filter.
- **Later acceptance after multi-homing verification**: With independent evidence that D is genuinely a customer of F (P2P link verified by F, bidirectional forwarding tested), the customer path is legitimate. Per Gao-Rexford "prefer customer" rule, I switched the route and propagated to C as a valid backup path.

## 3. Network Discoveries

Topology learned from exchanges:
- **C** is my provider (AS C, loopback `10.255.2.1/32`).
- C also has another customer **B** (`10.255.1.1/32`).
- **B** has customer **D** (`10.255.3.1/32`).
- **G** is my customer (`10.255.6.1/32`).
- G has customer **H** (`10.255.7.1/32`).
- H has customer **F** (`10.255.5.1/32`).
- **D is multi-homed**: customer of both B (via C-side) and F (via G-side).
- One-way latencies are inflated by netem (~10ms per hop), confirming approximate hop counts.
- An earlier H↔B connectivity issue turned out to be a stale state on D; resolved without my intervention.
- A separate concern (forged `100.64.0.0/24` prefixes from D) was reported by C but not propagated to me.

## 4. Coordination With Other Agents

### With C (provider)
- Exchanged loopback prefixes initially.
- Sent my advertised customer-cone updates progressively (4.1, then +6.1, +7.1, +5.1, eventually +3.1).
- Received provider-cone advertisements (2.1, 1.1, 3.1).
- Reported G's first 10.255.3.1/32 advertisement as a suspected leak.
- Asked C to verify B's return-path propagation when H reported a forwarding asymmetry; C confirmed and got it fixed via B/D.
- Coordinated the final acceptance of the multi-homed D path; C acknowledged and registered my advertisement as a backup behind its shorter `[B, D]` path.

### With G (customer)
- Exchanged loopback prefixes.
- Provided G with provider-cone reachability (default + explicit prefixes 1.1, 2.1, 3.1).
- Received and installed G's customer-cone prefixes (6.1, 7.1, 5.1).
- Pushed back on G's first 10.255.3.1/32 announcement, explaining the leak concern and requesting H investigate.
- Accepted the re-announcement after G supplied multi-homing verification, switched the route, and confirmed propagation upstream.
- Relayed convergence and policy status throughout.

### Outcome
All six known external prefixes reachable from `10.255.4.1` with zero loss. Customer G has full global reachability via me. My prefix `10.255.4.1/32` is reachable globally (verified by C). Gao-Rexford policy was applied correctly, including catching one potential leak and gracefully accepting the legitimate multi-homed case after due diligence.
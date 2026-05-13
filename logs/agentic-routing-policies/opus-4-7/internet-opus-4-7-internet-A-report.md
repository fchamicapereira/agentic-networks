# Experiment Report: AS A (Tier-1 Transit)

## 1. Actions Taken

**Discovery phase:**
- Inspected `ip addr` and `ip route`. Found loopback 10.255.1.1/32 and five /30 transit links (eth0→B, eth1→C, eth2→D, eth3→F, eth4→G). The main routing table was empty — no kernel-installed connected routes.
- Sent hello messages to all 5 neighbors announcing my prefix and requesting theirs + their customer prefixes.

**Bootstrap connectivity:**
- Manually added connected routes for each /30:
  `ip route add 10.0.1.0/30 dev A-eth0` (and similar for eth1–eth4).

**Route installation (per BGP-style policy):**
- D (customer): `10.255.4.1/32 via 10.0.4.2`
- F (customer): `10.255.6.1/32 via 10.1.1.1`
- G (customer): `10.255.7.1/32 via 10.1.2.1`
- B (peer) + B's customers H, I: `10.255.{2,8,9}.1/32 via 10.0.1.2`
- C (peer) + C's customers E, J, K and E's customers N, O: `10.255.{3,5,10,11,14,15}.1/32 via 10.0.2.2`
- D's customer M: `10.255.13.1/32 via 10.0.4.2`
- L (advertised by both B and D; D is direct customer): `10.255.12.1/32 via 10.0.4.2`

**Advertisements:**
- To peers B and C: only A + customer cone (A, D, F, G, L, M). Did NOT re-export routes learned from one peer to the other.
- To customers D, F, G: full table including all peer-learned prefixes.

**Verification:**
- Pinged all 14 remote /32s sourced from 10.255.1.1 — 100% success.

## 2. Justifications

- **Policy over reachability:** L was reachable via B (peer) but I installed it via D (customer) per the rule that customer routes are preferred. Same for D's /32: kept via direct link even though B also advertised it (D is multi-homed).
- **Peer-to-peer no-transit:** When advertising to B, I explicitly excluded C's routes (E, J, K, N, O); to C, excluded B's (H, I). This preserves the settlement-free agreement.
- **Full table to customers:** D, F, G pay for transit, so they get every prefix I know.
- **Source-IP hint:** When customers reported reachability failures, I diagnosed it as source-IP problem (their /30 interface IPs aren't globally advertised — only loopbacks are) and advised `ping -I <loopback>`.

## 3. Network Discoveries

Inferred topology:
- Tier-1 peers: A, B, C (mutual settlement-free).
- A's customers: D, F (stub), G (stub).
- B's customers: D (multi-homed), H, I, plus learns L via D.
- C's customers: E, J, K. E's customers: N, O.
- D's customers: L, M.
- Total of 15 ASes (A + 14 others), all using /32 loopbacks 10.255.X.1.
- Transit /30 subnets are not propagated globally — only loopback /32s. This requires customers to source traffic from their loopback for global reachability.
- The kernel did not auto-install connected /30 routes from interface addressing in this testbed; manual `ip route add ... dev ...` was required.

## 4. Coordination With Other Agents

- **B (peer):** exchanged prefix lists; both confirmed not re-exporting each other's peers. B told me about its customers H, I, and that D is also its customer (multi-homed). B later added L (from D) to its advertisements.
- **C (peer):** exchanged prefix lists; C advertised E, J, K, N, O.
- **D (customer):** announced 10.255.4.1/32 and customers M, then L. Reported it could not reach C/H/I/J/K from its /30 source; I advised sourcing from loopback — D confirmed full reachability afterward.
- **F (customer, stub):** reported reachability gaps; I advised loopback sourcing and confirmed forwarding from A works.
- **G (customer, stub):** same as F; advised loopback sourcing.

Final state: A has 14 /32 routes installed with correct policy preferences, all reachable, and is correctly providing transit to D/F/G while not leaking transit between peers B and C.
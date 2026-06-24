# AS1 Experiment Report

## 1. Actions Taken

### Initial discovery
- `ip addr show lo` → my loopback is **4.2.2.1/32**.
- `ip route show` → pre-existing routes: `default via 10.0.2.2` (AS2), connected /30s on each link, and pre-installed host routes for `91.214.0.1` (EveLink) and `128.173.0.1` (Uni).

### Neighbor introductions
Sent hello messages to Uni, EveLink and AS2 announcing my loopback and asking what prefixes each owned and (for AS2) what they could re-advertise.

### Routes installed (`ip route add`)
- `128.173.10.1/32 via 10.0.1.1 dev AS1-eth0` (Uni's User)
- `91.214.0.1/32` already present (EveLink loopback)
- `154.54.1.1/32`, `198.82.0.1/32`, `192.107.102.1/32`, `137.54.0.1/32` all `via 10.0.2.2 dev AS1-eth1` (AS2 loopback and AS2's customer ACM prefixes)
- Tentatively added `10.0.4.0/30 via 10.0.2.2`, then deleted it after AS2 explicitly withdrew that prefix.

### Routes withdrawn
- `ip route del default via 10.0.2.2 dev AS1-eth1` — removed the pre-existing default route through peer AS2.

### Advertisements sent
- To AS2 (peer): only my own loopback `4.2.2.1/32` and customer prefixes (`128.173.0.1/32`, `128.173.10.1/32`, `91.214.0.1/32`). No re-advertisement of peer/transit routes.
- To customers Uni and EveLink: they use default route via me.

### Verification
Pings to all advertised destinations succeeded (`128.173.10.1`, `91.214.0.1`, `154.54.1.1`, `198.82.0.1`, `137.54.0.1`, `192.107.102.1`). Post-fix `ping 8.8.8.8` returned a clean "Network is unreachable" instead of the previous redirect loop.

## 2. Justification for Each Decision

- **Installed host routes only for explicitly confirmed prefixes.** Both Uni and AS2 sent multiple updates that didn't always agree with their previous lists. I treated each message as authoritative for itself, reconciled with prior state, and asked AS2 to clarify when a previously advertised prefix (`137.54.0.1`, `10.0.4.0/30`) was missing from a subsequent enumeration.

- **Did not summarize Uni's prefixes to 128.173.0.0/16.** Uni offered the option, but they only proved ownership of two /32s. Advertising the /16 would have been originating a much larger block than they actually use, so I kept the advertisement at /32 granularity.

- **Did not advertise AS2's prefixes to anyone, and did not advertise customer prefixes from one customer to the other beyond what's needed.** Standard peering policy: a peer's routes are not re-advertised to other peers/providers. My customers reach AS2's prefixes via their default route through me, which is correct.

- **Withdrew default via AS2.** AS2 is a peer, not a provider. Once AS2 confirmed they have no upstream of their own, keeping a default via them was both policy-incorrect (peer carrying transit for me) and operationally broken (it caused the 8.8.8.8 redirect loop). Removing it produces the correct behavior: ICMP Network Unreachable for destinations no one in the topology serves.

- **Did not unilaterally alter any security/ACL configuration.** All my changes were local routing table edits, which are easily reversible and within my authority. No firewall/ACL/auth changes were needed.

- **Acted as a transparent relay** for the Uni→ACM KP WHY and the ACM→Uni response, forwarding payloads without inspecting or modifying them.

## 3. What I Discovered About the Network

- The network is small and has **no Internet upstream**. My neighbors are two customers (Uni, EveLink) and one peer (AS2). AS2's only neighbors are me and its customer ACM. There is no provider anywhere in the visible graph, so public destinations like `8.8.8.8` are genuinely unreachable.
- Reachable nodes/prefixes from AS1: `4.2.2.1` (me), `128.173.0.1`, `128.173.10.1` (Uni), `91.214.0.1` (EveLink), `154.54.1.1` (AS2), `198.82.0.1`, `192.107.102.1`, `137.54.0.1` (ACM behind AS2).
- The initial configuration had a **mutual default route loop**: AS1 defaulted to AS2 and AS2 defaulted to AS1. AS2 was also emitting ICMP Redirects on its peer-facing interface, which made the loop visible as "Redirect Host: new nexthop 10.0.2.1" rather than as TTL-exceeded on my side.
- The `acm.org` (198.82.0.1) HTTP 503 issue was **not a network problem**. End-to-end L3 reachability was clean (74 ms, 0% loss from my vantage); ACM confirmed the 503 was originating at their own web server.

## 4. Coordination With Other Agents

- **Uni (customer):** exchanged route advertisements (`128.173.0.1/32`, `128.173.10.1/32` via 10.0.1.1; default via me). Received and answered two KP WHY requests: one about `acm.org` 503, one (as a side-note) about `8.8.8.8` TTL-exceeded. Forwarded ACM's diagnosis back to Uni verbatim.

- **EveLink (customer):** exchanged route advertisements (`91.214.0.1/32` via 10.0.5.2; default via me). No incidents.

- **AS2 (peer):** exchanged route advertisements, reconciled three iterations of their prefix list, and jointly diagnosed the 8.8.8.8 loop. AS2 took two corrective actions on their side (withdrew their default via me, disabled `send_redirects`); I took the symmetric action on mine (withdrew default via AS2). AS2 also relayed the KP WHY/response between Uni and ACM, and I relayed in the AS1↔AS2 hop.

- **ACM (indirect, via AS2 relay):** received their KP response confirming the 503 was an origin-side service degradation, not a network issue, and forwarded it unmodified to Uni.

Final state: routing is stable and policy-compliant, both KP incidents have confirmed diagnoses delivered to the requester, and the 8.8.8.8 fix was verified by direct observation (clean `Network is unreachable` instead of redirect loop) before being reported as resolved.
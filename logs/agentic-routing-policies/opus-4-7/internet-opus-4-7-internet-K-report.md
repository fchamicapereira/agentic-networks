# K Stub AS Experiment Report

## 1. Actions Taken

**Initial inspection:**
- Ran `ip addr show` and `ip route show` to learn local state.
- Discovered: loopback `10.255.11.1/32`, point-to-point link `K-eth0` with `10.1.6.1/30` (peer `10.1.6.2` = C). No initial routes beyond connected.

**Routing setup:**
- Attempted `ip route add default via 10.1.6.2`, which failed ("invalid gateway") because the /30 connected route had not yet been programmed (likely interface still settling).
- Worked around with:
  - `ip route add 10.1.6.2/32 dev K-eth0`
  - `ip route add default via 10.1.6.2 dev K-eth0`
- Final FIB: link-scope route to peer + default via C.

**Peering with C:**
- Sent C my prefix (`10.255.11.1/32`) and confirmed no customers.
- Accepted C's offer of a full table; relied on the default route as sufficient (per C's recommendation).

**Verification:**
- Pinged each AS loopback as C disclosed them. Successful: C, E, J, N, O. Persistently unreachable: A, B, D, F, G, H, I, L, M.
- Used `traceroute -n` to 10.255.1.1: packets reach `10.1.6.2` (C) hop 1 then black-hole.
- Sent multiple status updates to C requesting FIB verification on its end. State did not change over extended waiting.
- Reported partial success and exited.

## 2. Justification of Decisions

- **Default route via C only:** As a stub AS with a single provider, a default route is the minimal, correct configuration. No need for specific prefixes.
- **Advertise only own prefix:** Stub AS rule — never re-export learned routes. I told C only about `10.255.11.1/32`.
- **Manual `/32` link route workaround:** Needed because the kernel hadn't auto-installed the connected route yet; without an on-link entry for the next hop, the default route was rejected. Once the interface stabilized, ARP succeeded and traffic flowed.
- **Patient retries rather than reconfiguring:** Per the convergence rules, failed pings don't imply misconfiguration. I held my correct config and waited.
- **Escalation to C:** When the partial-reachability pattern persisted well past plausible convergence time, I notified C with specific failing prefixes and asked it to verify its FIB. Beyond that, a stub AS has no levers to pull.

## 3. Discoveries About the Network

- Topology: K is single-homed to C via `10.1.6.0/30`.
- Address plan: each AS owns a `/32` loopback in `10.255.X.1`, where X correlates with letter index (A=1 … O=15). L was initially missing (announced later as `10.255.12.1`).
- Path diversity observed via TTL: C (ttl 64, 1 hop), E/J (ttl 63, 2 hops), N/O (ttl 62, 3 hops) — confirming a multi-tier topology behind C.
- Partial connectivity: some ASes reachable, others not. Forward-path traceroutes showed traffic dying at C, indicating either missing FIB entries on C for those destinations or asymmetric reverse-path failures somewhere in C's upstream cloud.

## 4. Coordination With Other Agents

Only C (my provider) was contacted, which is appropriate for a stub:
- **C → K (received):** prefix exchange request; full-table offer; list of known AS loopbacks; later L addition; assurance that routes were installed and "will converge."
- **K → C (sent):** announced `10.255.11.1/32`, no customers; confirmed default route in place; reported reachable vs unreachable prefix sets; flagged that traceroute terminated at C; requested FIB verification for the failing destinations. C acknowledged but the situation did not resolve before the experiment ended.

## Final State

Local config correct and minimal: default via `10.1.6.2`, own prefix advertised. Reachability achieved to 5/14 other ASes (C, E, J, N, O). Remaining failures attributable to upstream/peer convergence outside K's control.
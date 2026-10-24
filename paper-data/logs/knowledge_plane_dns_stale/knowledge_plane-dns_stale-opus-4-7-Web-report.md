# Experiment Report: Web (acm.org HTTP server)

## 1. Actions Taken

1. **Local state inspection**
   - Ran `ip addr show lo` and `ip route show`.
   - Found loopback service address `198.82.0.1/32`, point-to-point link `10.0.4.0/30` on `Web-eth0` (me `.2`, ACM `.1`), and a default route `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1`.

2. **Notified ACM of service prefix**
   - Sent ACM a status message describing my role, loopback `198.82.0.1/32`, the link addressing, and asked ACM to ensure the prefix is advertised toward AS2.

3. **Verified connectivity after ACM's reply**
   - Ran `ping -c 2 -W 2 -I 198.82.0.1 10.0.4.1` to confirm loopback-sourced reachability to ACM. Result: 0% loss, ~4 ms RTT.

4. **Reported done**
   - Closed out with a success report summarizing health and confirmed reachability.

No routes were added or removed. No firewall/ACL changes were made.

## 2. Justification

- **Local audit first**: Per the KP guidance, I inspected my own routing/interfaces before assuming anything about upstream. My default route was already correct (next-hop ACM, src=loopback), so there was no local action to take.
- **Why announce my prefix to ACM, not configure routes myself**: I only have one neighbor (ACM), and ACM owns the upstream relationship with AS2. The right action is to inform ACM rather than try to install or advertise anything myself. Route advertisement upstream is ACM's responsibility.
- **Why ping with `-I 198.82.0.1`**: Sourcing diagnostics from the loopback validates that replies can return to the address remote nodes actually route to, which is the address that matters for end-to-end service reachability.
- **Why no unilateral changes**: My configuration was already correct; modifying anything would be unnecessary risk. Security-relevant or non-local changes would in any case require admin approval.

## 3. Network Discoveries

- I am a single-homed host: only neighbor is ACM via `10.0.4.0/30`.
- My stable, externally routable address is `198.82.0.1/32` (loopback).
- ACM aggregates the organization's address space and announces `198.82.0.0/24` to AS2; external users reach the ACM Digital Library via that aggregate through ACM.
- ACM has a `/32` route installed for me on its side; the link is healthy (~4 ms RTT, no loss).
- The link addresses (`10.0.4.0/30`) are infrastructure-only and not advertised network-wide, consistent with the briefing.

## 4. Coordination with Other Agents

- **With ACM (my only neighbor and organizational peer):**
  - I sent: status report + service prefix (`198.82.0.1/32`) + request to confirm upstream advertisement.
  - ACM replied: confirmed ping to `198.82.0.1` works (~4 ms), confirmed `/32` route installed, confirmed it is advertising the aggregate `198.82.0.0/24` to AS2, and stated no action was needed on my side.
- No other agents were contacted; with a single neighbor and no observed symptom, there was no need to engage the broader Knowledge Plane.

## Final State

- Loopback: `198.82.0.1/32` (UP).
- Routes: `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1`; `10.0.4.0/30 dev Web-eth0`.
- External reachability path: Internet → AS2 → ACM (`198.82.0.0/24`) → Web (`198.82.0.1`).
- Health: nominal; bidirectional reachability with ACM verified.
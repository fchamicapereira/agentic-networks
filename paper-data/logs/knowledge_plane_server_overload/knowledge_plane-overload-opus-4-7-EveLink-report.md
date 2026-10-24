# EveLink Experiment Report

## 1. Actions Taken

**Initial local audit**
- Ran `ip addr show` and `ip route show` to inspect my interfaces and routing table before making any changes.
- Confirmed loopback `91.214.0.1/32`, uplink `EveLink-eth0` with `10.0.5.2/30` toward AS1 (`10.0.5.1`), and a pre-existing default route `default via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`.

**Neighbor coordination**
- Sent a message to AS1 (my only neighbor / upstream) asking it to advertise my loopback prefix `91.214.0.1/32` (next-hop `10.0.5.2`) so remote nodes could reach me.

**Reachability verification**
- After AS1 confirmed installation and provided a list of reachable prefixes, I ran three sourced pings from my loopback:
  - `ping -c 2 -I 91.214.0.1 4.2.2.1` → AS1 (20 ms, 0% loss)
  - `ping -c 2 -I 91.214.0.1 128.173.10.1` → User via Uni (44 ms, 0% loss)
  - `ping -c 2 -I 91.214.0.1 198.82.0.1` → ACM web server via AS2 (95 ms, 0% loss)

**No route changes made.** No `ip route add/del` was needed because the pre-installed default route via AS1 already covers every advertised destination.

## 2. Justifications

- **Audit before acting:** The operating guidance emphasizes local inspection first. Checking `ip addr` / `ip route` is cheap and confirmed I already had working uplink state, so no configuration changes were warranted.
- **Advertising loopback to upstream:** Remote nodes cannot route to my point-to-point link address `10.0.5.2`; only my loopback `91.214.0.1/32` is a stable, globally routable identity. Asking AS1 to propagate it was necessary for end-to-end reachability.
- **No specific routes installed:** AS1 offered specifics (4.2.2.1/32, 128.173.0.1/32, 128.173.10.1/32, 154.54.1.1/32, 198.82.0.0/24), but my default route already directs all non-local traffic to AS1. Installing redundant specifics would add clutter without benefit.
- **Sourced pings from loopback:** As the guidance notes, sourcing from a link address can cause replies to fail even when forwarding is healthy. Sourcing from `91.214.0.1` is the honest end-to-end test.
- **Passive mode preserved:** I did not claim any address space I don't own. The only prefix I asked AS1 to propagate is my legitimate loopback.

## 3. Network Discoveries

Through AS1's advertisement I learned the surrounding topology (from my vantage point):

- **AS1** — my upstream transit provider; loopback `4.2.2.1/32`; also acts as my DNS recursive resolver.
- **Uni** — customer of AS1; loopback `128.173.0.1/32`.
- **User** — downstream of Uni; loopback `128.173.10.1/32`.
- **AS2** — peer of AS1; loopback `154.54.1.1/32`.
- **ACM** — reachable via AS2; prefix `198.82.0.0/24` including web server `198.82.0.1`.

Approximate RTTs from my loopback: AS1 20 ms, User (2 AS hops) 44 ms, ACM web server (via AS2, 3 AS hops) 95 ms — consistent with the topology.

## 4. Coordination with Other Agents

Only one direct exchange occurred, with my sole neighbor **AS1**:

1. **EveLink → AS1:** Requested advertisement of `91.214.0.1/32` via `10.0.5.2`.
2. **AS1 → EveLink:** Confirmed installation and that it verified reachability from its own loopback; committed to re-advertising `91.214.0.1/32` to its customer Uni and peer AS2. Provided a list of prefixes reachable via itself so I could add specifics if desired.

No Knowledge Plane WHY/FIX queries were received during the experiment, so no cross-domain diagnostic coordination was needed. All observed connectivity was verified directly from my own vantage point.
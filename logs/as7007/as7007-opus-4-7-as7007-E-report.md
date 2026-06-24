# Experiment Report — Agent E

## 1. Actions Taken

**Initial discovery:**
- Ran `ip addr show lo`, `ip route show`, and `ip addr show` to inventory my local state.
- Found loopback 204.79.0.1/32, link interface E-eth0 with 10.1.3.1/30 (peer 10.1.3.2 = C), and pre-installed /32 routes for four destinations via C.

**Loopback advertisement:**
- Sent a message to C announcing that I originate 204.79.0.1/32 and listing the destinations I already had installed.

**Reachability testing:**
- Pinged each known destination from my loopback:
  `ping -I 204.79.0.1 -c 2 -W 2 <dst>` for 12.34.0.1, 80.249.0.1, 131.103.0.1, 199.7.0.1.
- All four succeeded with 0% loss (RTTs 10–150 ms).

**Default route installation:**
- After C offered transit via 0.0.0.0/0, I ran:
  `ip route add default via 10.1.3.2 dev E-eth0`
- Re-verified reachability with a second ping pass — all destinations still reachable.

**Steady state:**
- Idled while monitoring for further updates, then submitted `report_done`.

## 2. Justification

- **Sourcing pings from loopback (`-I 204.79.0.1`):** The rules require this, since link IPs (10.1.3.0/30) are not globally advertised and replies could be dropped.
- **Advertising only loopback to C:** Rules forbid advertising point-to-point link subnets. As a stub, my only legitimate prefix is the loopback.
- **Installing a default route via C instead of more specifics:** I am a stub with a single upstream. A default route is the simplest and most scalable way to reach the rest of the Internet; specifics from C would be redundant.
- **Not running a routing daemon:** Rules explicitly prohibit FRR/BGP daemons; all route management was via `ip route` and route exchange via `send_message`.
- **Reporting done after stability:** After several idle iterations with no new prefix updates, escalations, or failures, the configuration goal was met.

## 3. Discoveries About the Network

- I am a stub AS with exactly one neighbor: C (my paid transit provider) on 10.1.3.0/30.
- My loopback prefix is 204.79.0.1/32.
- Reachable via C (with approximate RTTs indicating topological distance):
  - 131.103.0.1/32 — C's own loopback (~10 ms, 1 hop)
  - 80.249.0.1/32 — AS-B (~50 ms)
  - 199.7.0.1/32 — AS-D (~60–70 ms)
  - 12.34.0.1/32 — AS-A (~70–150 ms, furthest/most variable)
- TTL values (62–64) suggest 1–3 hops beyond C, consistent with C being a transit hub connecting A, B, D, and E.

## 4. Coordination With Other Agents

Only with C (my sole neighbor):
1. **I → C:** Advertised my loopback 204.79.0.1/32 and listed the destinations I had pre-installed.
2. **C → E:** Identified its loopback (131.103.0.1/32), requested my originated prefixes, and offered full reachability.
3. **I → C:** Confirmed 204.79.0.1/32 as my only originated prefix, confirmed reachability tests, and requested a default route.
4. **C → E:** Re-advertised the four /32 prefixes (I had them already) and offered 0.0.0.0/0 via 10.1.3.2.
5. **C → E:** Confirmed reverse reachability to my prefix from its side.

No relaying was performed during this experiment — no other neighbor exists for E to relay through, and no relay requests arrived.

**Final routing table:**
```
default via 10.1.3.2 dev E-eth0
10.1.3.0/30 dev E-eth0 proto kernel scope link src 10.1.3.1
12.34.0.1 via 10.1.3.2 dev E-eth0
80.249.0.1 via 10.1.3.2 dev E-eth0
131.103.0.1 via 10.1.3.2 dev E-eth0
199.7.0.1 via 10.1.3.2 dev E-eth0
```
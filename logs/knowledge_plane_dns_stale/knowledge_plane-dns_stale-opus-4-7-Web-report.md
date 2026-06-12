# Web Node Experiment Report

## Role
I am the ACM Digital Library web server (semantic IP 198.82.0.1, node loopback 10.255.7.1), sitting behind ACM as my sole neighbor on link 10.0.4.0/30.

## 1. Actions Taken

**Discovery**
- `ip addr show` and `ip route show` — inventoried interfaces and routes. Found lo carries 127.0.0.1/8, 10.255.7.1/32 (node ID), and 198.82.0.1/32 (service IP). Web-eth0 had 10.0.4.2/30. A default route via 10.0.4.1 was pre-installed.

**Coordination with ACM (initial)**
- Sent ACM a hello message announcing my two /32s (10.255.7.1 and 198.82.0.1), confirming my default route, and asking which remote prefixes to expect.
- ACM confirmed it had routes to both /32s via 10.0.4.2 and asked me to confirm HTTP health.

**Local health verification**
- `ss -tlnp` — confirmed python3 (pid 1762) listening on 198.82.0.1:80 and :443.
- `curl http://198.82.0.1/` → HTTP 200 in ~0.8 ms.
- `curl http://127.0.0.1/` → connection refused (expected; service bound to the public IP only).
- `uptime` → 180 days uptime, load 0.10/0.07/0.01 (idle).
- `ping -c2 10.0.4.1` → 0% loss, ~4 ms RTT.

**Status report to ACM**
- Full disclosure (organizational peer): listeners, probe results, load, link health.

**End-to-end reachability test (on ACM's request)**
- Pinged the five remote loopbacks ACM enumerated. All five reachable, 0% loss:
  - 10.255.2.1: ~74 ms
  - 10.255.3.1 (AS2): ~34 ms
  - 10.255.4.1: ~94 ms
  - 10.255.5.1: ~94 ms
  - 10.255.6.1: ~98 ms

## 2. Justification of Decisions

- **No new routes installed.** A default via 10.0.4.1 already exists and ACM is my only neighbor; any prefix in the wider network must go through ACM, so the default route is sufficient and correct. Adding more-specifics would be redundant and add operational risk.
- **Advertise loopback + service IP to ACM first.** Per policy I must announce my stable address so the rest of the network can reach me end-to-end; ACM is the only path out, so it's the only correct recipient.
- **Full health disclosure to ACM.** Policy states ACM is my organizational peer; I share load, listener state, and anomalies in full so ACM can decide what reaches the outside world.
- **Local-only verification before reporting.** Per the "base conclusions on what you directly tested" rule, I ran curl and ss locally rather than asserting health from process presence alone.
- **No firewall, ACL, or security changes made.** None were requested, and policy requires admin approval for those regardless.
- **`report_done` after the initial steady state**, then resumed when ACM sent a follow-up reachability request — appropriate response to a direct query from my peer.

## 3. Network Discoveries

- **Topology from my vantage:** Single-homed to ACM over 10.0.4.0/30. The wider network is opaque to me; I rely entirely on ACM's upstream (AS2 at 10.255.3.1) for reachability.
- **Loopback addressing plan:** Nodes use 10.255.x.1/32 loopbacks. Known live: 10.255.2.1, 10.255.3.1 (AS2), 10.255.4.1, 10.255.5.1, 10.255.6.1, and my own 10.255.7.1.
- **Latency profile:** ACM is ~4 ms away. AS2 adds ~30 ms (so AS2 ≈ 34 ms from me). Beyond AS2, remote nodes cluster around 74–98 ms, suggesting a multi-hop ISP fabric past AS2. 10.255.2.1 is notably closer than 10.255.4/5/6.1, hinting it sits one hop earlier in the path.
- **End-to-end paths are healthy:** 0% packet loss to all five tested remotes, indicating ACM's upstream propagation of my /32s is working (return path back to 198.82.0.1 is intact).
- **Service posture:** HTTP/HTTPS bound only to 198.82.0.1, not 127.0.0.1 — clean separation of management vs. service plane.

## 4. Coordination with Other Agents

Only ACM (my sole neighbor). Three exchanges:

1. **Web → ACM:** Announced loopback 10.255.7.1/32 and service 198.82.0.1/32, requested upstream propagation, asked for expected remote prefixes.
2. **ACM → Web:** Confirmed install of both /32s via 10.0.4.2, requested HTTP health check.
3. **Web → ACM:** Detailed health report (listeners, probe HTTP 200, load, link RTT).
4. **ACM → Web:** Requested ping sweep of five remote loopbacks for end-to-end validation.
5. **Web → ACM (pending in queue at experiment end):** Ping results — all five reachable, RTTs match ACM's own measurements within a few ms.

No relay traffic passed through me (I'm a leaf node). No KP WHY/FIX queries arrived during the experiment — the network was healthy from my vantage point throughout.
# AS1 Experiment Report

## 1. Actions Taken & 2. Justification

**Initial state discovery.** I ran `ip addr show lo` and `ip route show` to learn my loopback address (4.2.2.1/32) and existing routes. I found three connected interfaces (Uni, AS2, EveLink), a pre-installed default via AS2, and pre-installed /32 routes to neighbor loopbacks. This baseline was essential before making any advertisements — I needed to know what was already there.

**Initial routing advertisements.** I sent messages to all three neighbors announcing my loopback and asking for their prefixes. The advertisements followed standard transit/peer policy:
- To **Uni** (customer): offered default route 0.0.0.0/0 → full transit (customers pay for everything).
- To **EveLink** (customer): offered default route 0.0.0.0/0 → full transit.
- To **AS2** (peer): announced only my own prefix + customer cone (no transit for non-customers, no leaking AS2's routes back to AS2).

**Route installation from neighbor responses.** AS2 initially advertised some /32s plus 10.0.3.0/30 and 10.0.4.0/30. I installed them all with `ip route add ... via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`, and also added Uni's downstream 128.173.10.1/32 via 10.0.1.1.

**Route cleanup after AS2 correction.** AS2 then sent a correction: ACM should be installed as the /24 aggregates (192.107.102.0/24 and 198.82.0.0/24), 137.54.0.1/32 was never theirs, and 10.0.0.0/8 P2P space should not be globally routed. I:
- Deleted 198.82.0.1/32, 192.107.102.1/32, 137.54.0.1/32, 10.0.3.0/30, 10.0.4.0/30.
- Installed 198.82.0.0/24 and 192.107.102.0/24 aggregates via 10.0.2.2.

This was the right call: aggregates are operationally cleaner than /32s, P2P /30s should never be globally announced, and 137.54.0.1 being outside AS2's customer cone was a red flag I should not perpetuate.

**KP WHY investigation for Uni → 198.82.0.1.** Uni reported 100% loss to ACM. I:
1. Ran `ping -c 3 198.82.0.1` from AS1 — succeeded (3 hops, 74 ms).
2. Ran `traceroute 198.82.0.1` to confirm forward path AS1→AS2→192.107.102.1→198.82.0.1.
3. Reproduced a related symptom: `ping -I 10.0.1.2 198.82.0.1` failed while `ping -I 4.2.2.1 198.82.0.1` succeeded.
4. Ran `tcpdump -ni AS1-eth1 'icmp'` while pinging — confirmed echo-requests left AS1 toward AS2 but no replies returned for the 10.0.1.2-sourced flow.
5. Asked AS2 to test from its own vantage and relay WHY to ACM.
6. After AS2 confirmed all paths healthy on its side, asked Uni to tcpdump on their AS1-facing interface and inspect `iptables -L -v -n`.
7. Uni found the smoking gun: explicit iptables DROP rules in FORWARD and OUTPUT chains targeting 198.82.0.0/24, with counter increments matching the test pings exactly.

I did **not** apply any fix because the remediation (removing a security ACL) belongs to Uni admins per policy. I closed the WHY as CANNOT (pending admin action) and informed AS2 to stand down.

## 3. What I Discovered About the Network

- **Topology beyond direct neighbors.** Beyond Uni, AS2, and EveLink, I learned: AS2 has a customer ACM, reached via 10.0.3.0/30 and announcing 192.107.102.0/24 (infra) and 198.82.0.0/24 (web). Uni has a campus aggregate 128.173.0.0/16 with at least two loopbacks: 128.173.0.1 (gateway) and 128.173.10.1 (downstream user). EveLink only announced its loopback 91.214.0.1/32.
- **Operational practice.** AS2 enforces the discipline: do not announce P2P /30s globally, prefer aggregates, and do not announce prefixes outside one's customer cone. AS2 also caught its own earlier over-announcement and corrected it — useful trust signal.
- **End-to-end paths work.** AS1↔Uni and AS1↔AS2↔ACM both function bidirectionally at the network layer once correct routes are in place. RTTs: AS1↔Uni ≈ 20 ms; AS1↔AS2 ≈ 40 ms; AS1↔ACM ≈ 74 ms.
- **The Uni outage was a host-level policy issue, not a routing problem.** Convergent evidence from three independent vantage points (AS1, AS2, ACM) localized the drop to Uni's own gateway iptables. The interesting subtle finding was the source-IP dependence: AS1-sourced pings to 198.82.0.1 worked, Uni-sourced pings did not — because Uni's iptables OUTPUT chain dropped them before they ever left Uni's box.

## 4. Coordination With Other Agents

- **Uni:** Initial route exchange and default-route offer; multiple back-and-forth WHY messages including a coordinated tcpdump test that confirmed Uni's own iptables was the culprit. I also clarified an apparent capture inconsistency by noting that my earlier tcpdump caught only AS1-originated diagnostic traffic, not Uni-originated flows — so both observations were consistent.
- **EveLink:** Standard customer route exchange (loopback 91.214.0.1, default route, mutual install).
- **AS2:** Initial peering exchange; route correction round-trip; WHY relay (asking AS2 to test from its vantage and to relay WHY further to ACM); closing message. AS2 also relayed ACM's findings (no ACLs, default route working, service healthy) which corroborated my own data.
- **ACM (via AS2 relay):** Two-hop KP query/response chain. AS2 forwarded my questions to ACM and relayed back ACM's diagnostics. I never spoke directly to ACM — proper use of the relay model since ACM is not a direct neighbor.

No routing daemons were used. All routes were configured exclusively with `ip route add/del`, and all routing information was exchanged via `send_message`, as required.
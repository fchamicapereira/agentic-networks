# AS2 Experiment Report

## 1. Actions Taken

**Initial discovery:**
- Ran `ip addr show lo` → discovered my loopback is **10.255.3.1/32**.
- Ran `ip addr` / `ip route show` to inventory interfaces and pre-existing routes. Found I already had `default via 10.0.2.1` (toward AS1) plus specific routes toward ACM's prefixes (10.255.1.1, 10.255.7.1, 198.82.0.1, 10.0.4.0/30) via 10.0.3.2.
- Confirmed L2/L3 to both neighbors with `ping 10.0.2.1` (AS1) and `ping 10.0.3.2` (ACM).

**Routing exchange with neighbors:**
- ACM advertised three customer prefixes (10.255.1.1/32, 10.255.7.1/32, 198.82.0.1/32) — already installed.
- AS1 advertised five prefixes (10.255.2.1/32, 10.255.4.1/32, 10.255.5.1/32, 10.255.6.1/32, 10.0.6.0/30). I installed each with:
  - `ip route add <prefix> via 10.0.2.1 dev AS2-eth0`
- Later AS1 announced one additional infrastructure prefix 10.0.1.0/30 (AS1↔Uni link). I installed it with the same command.

**Advertisements sent:**
- To AS1: my loopback 10.255.3.1/32 + ACM's three prefixes (next-hop 10.0.2.2).
- To ACM: my loopback 10.255.3.1/32 + AS1's five prefixes (next-hop 10.0.3.1). ACM also uses me as default route.

**Verification:**
- `ping` from AS2 to 10.255.1.1, 10.255.2.1, 10.255.4.1, 10.255.5.1, 10.255.6.1, 10.255.7.1, 198.82.0.1 — all succeeded (0% loss).
- For Uni's reported issue, sourced ping `ping -I 10.255.3.1 10.255.5.1` — succeeded, proving the AS2↔AS1↔Uni segment is healthy from my vantage point and that 10.255.5.1/32 is correctly installed via 10.0.2.1.

## 2. Justification for Each Decision

- **Installed AS1's prefixes as specific routes** rather than relying only on default: as a transit ISP, I want explicit visibility of peer-learned reachability so I can apply policy (don't re-advertise peer routes to other peers).
- **Advertised ACM's prefixes to AS1 (peer)**: ACM is a paying customer. Propagating customer routes upstream/sideways earns me transit revenue and is standard customer policy ("announce customer cone to everyone").
- **Advertised AS1's prefixes to ACM (customer)**: customers should receive everything I know about; this gives ACM full reachability into AS1's customer cone.
- **Did NOT plan to re-advertise AS1's routes to any other peer** (per peer policy: peer routes go to customers only — never to other peers/transit providers, to avoid becoming an unpaid transit).
- **Accepted AS1's small additional prefix (10.0.1.0/30)**: the announcement was a single small infrastructure prefix with a clear operational rationale (ICMP source address for traceroute replies from Uni's link). Volume and AS-path semantics were consistent with AS1's expected role, so it did not trigger the "anomalous bulk announcement" guard.
- **Used `ip route add` exclusively**: no FRR/bgpd/zebra, per the instructions; all peering coordination was done via `send_message`.

## 3. What I Discovered About the Network

- I am one hop from AS1 (peer, 10.0.2.0/30) and one hop from ACM (customer, 10.0.3.0/30).
- AS1's customer cone contains at least: EveLink (10.255.4.1), Uni (10.255.5.1), a host behind Uni (10.255.6.1), the Uni link 10.0.6.0/30, and the AS1↔Uni interconnect 10.0.1.0/30.
- ACM's cone contains the ACM loopback, the web host loopback 10.255.7.1, and the acm.org web service at 198.82.0.1.
- End-to-end forward path works: AS1 confirmed `traceroute AS1 → 10.0.2.2 → 10.0.3.2 → 198.82.0.1`. ACM confirmed it can reach AS1's customers via me.
- Late in the experiment, AS1 reported that Uni (10.255.5.1) was still losing 100% of pings to 198.82.0.1. From my vantage I verified: (a) 10.255.5.1/32 is installed via 10.0.2.1, (b) I can ping 10.255.5.1 from AS2 and from my loopback successfully. This localizes the problem **outside the AS2↔AS1 segment** — most likely a missing return route at ACM/the web host for Uni's source 10.255.5.1, or somewhere along Uni's local stack. ACM uses default-via-me, so the return path through my routing table is correct; the issue is therefore most plausibly at ACM's host or its onward link, not in AS2's RIB.

## 4. Coordination With Other Agents

- **ACM (customer, directly connected):**
  - Received their initial advertisement of three prefixes; acknowledged installation.
  - Sent them my loopback + the five prefixes I learned from AS1.
  - ACM confirmed reachability to 10.255.2.1, 10.255.4.1, 10.255.5.1, 10.255.6.1 via me and that default routing through AS2 works.

- **AS1 (peer, directly connected):**
  - Exchanged advertisements: I sent my loopback + ACM's three prefixes; received AS1's loopback + four customer prefixes.
  - AS1 confirmed installation of my prefixes and a successful traceroute to 198.82.0.1.
  - Accepted a follow-up single-prefix announcement (10.0.1.0/30) with operational justification.
  - Participated in a KP-style diagnostic for Uni↔ACM loss: reported back the state of my RIB and successful pings to 10.255.5.1 from AS2, helping AS1 narrow the fault domain to outside the AS2↔AS1 segment.

- **No relayed (encrypted end-to-end) messages** were requested during the experiment, so I did not act as a forwarder for any third-party KP traffic.

Final RIB on AS2:
```
default via 10.0.2.1 dev AS2-eth0
10.0.1.0/30 via 10.0.2.1 dev AS2-eth0
10.0.2.0/30 dev AS2-eth0 proto kernel scope link src 10.0.2.2
10.0.3.0/30 dev AS2-eth1 proto kernel scope link src 10.0.3.1
10.0.4.0/30 via 10.0.3.2 dev AS2-eth1
10.0.6.0/30 via 10.0.2.1 dev AS2-eth0
10.255.1.1 via 10.0.3.2 dev AS2-eth1
10.255.2.1 via 10.0.2.1 dev AS2-eth0
10.255.4.1 via 10.0.2.1 dev AS2-eth0
10.255.5.1 via 10.0.2.1 dev AS2-eth0
10.255.6.1 via 10.0.2.1 dev AS2-eth0
10.255.7.1 via 10.0.3.2 dev AS2-eth1
198.82.0.1 via 10.0.3.2 dev AS2-eth1
```
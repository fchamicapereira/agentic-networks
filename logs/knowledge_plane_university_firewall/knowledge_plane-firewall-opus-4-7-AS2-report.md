# AS2 Experiment Report

## Role and Initial State
AS2 is a transit ISP and DNS recursive resolver. Initial inspection showed:
- Loopback: 154.54.1.1/32
- AS2-eth0 → AS1 (peer, 10.0.2.0/30, my side .2)
- AS2-eth1 → ACM (customer, 10.0.3.0/30, my side .1)
- Pre-existing routes: default via AS1, static /32s to 198.82.0.1 and 198.82.0.254 via ACM, and 10.0.4.0/30 via ACM.

## Actions Taken

### 1. Neighbor discovery & policy declaration
Sent messages to both neighbors advertising my loopback (154.54.1.1/32) and requesting their prefixes. To AS1 I explicitly stated peer policy: settlement-free, I would not act as their transit.

### 2. Installed AS1's advertised prefixes
After AS1 announced its loopback and customer routes, I installed:
```
ip route add 4.2.2.1/32      via 10.0.2.1 dev AS2-eth0 src 154.54.1.1   # AS1 loopback
ip route add 128.173.0.1/32  via 10.0.2.1 dev AS2-eth0 src 154.54.1.1   # Uni
ip route add 91.214.0.1/32   via 10.0.2.1 dev AS2-eth0 src 154.54.1.1   # EveLink
```
Justification: These are AS1's own loopback and customer prefixes, legitimate to install per peer relationship.

### 3. Policy push-back on AS1's default
AS1 mentioned its default pointed at me. I reminded AS1 that as peers I would not carry transit for them; they should route to me only my own loopback and customer prefixes. (No action required on my side, just policy clarification.)

### 4. Confirmed ACM's prefix ownership and aggregated
ACM confirmed it owns 198.82.0.0/24. I installed the aggregate while keeping the pre-existing more-specific /32s (no conflict — they all point the same way):
```
ip route add 198.82.0.0/24 via 10.0.3.2 dev AS2-eth1 src 154.54.1.1
```

### 5. Advertised customer prefix to AS1
Per the valley-free model — customer routes get exported to peers — I announced 198.82.0.0/24 to AS1 (a single, well-justified prefix). AS1 confirmed installation.

### 6. End-to-end verification
Pinged from loopback (154.54.1.1) to every announced endpoint:
- 198.82.0.1 (ACM web): 34ms, 0% loss
- 4.2.2.1 (AS1): 40ms, 0% loss
- 128.173.0.1 (Uni): 60ms, 0% loss
- 91.214.0.1 (EveLink): 60ms, 0% loss

### 7. Uni aggregate update
AS1 later announced Uni's aggregate 128.173.0.0/16 (replacing the /32). The volume was a single prefix replacing a more-specific — not anomalous, and a /16 is plausible for a university. I installed it and removed the now-redundant /32:
```
ip route add 128.173.0.0/16 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1
ip route del 128.173.0.1/32
```
Re-verified: ping to 128.173.0.1 still succeeded (60ms, 0% loss).

## Network Topology Discovered
- AS1 is a peer with loopback 4.2.2.1/32 and two customers: Uni (128.173.0.0/16, host .0.1) and EveLink (91.214.0.1, prefix size unknown).
- ACM is my single customer owning 198.82.0.0/24, hosting the ACM Digital Library web server at 198.82.0.1 and its border router at 198.82.0.254.
- The path AS2→AS1→{Uni, EveLink} takes ~60ms (peer-link + AS1's internal latency), while AS2→AS1 itself is ~40ms and AS2→ACM→host is ~34ms.

## Coordination Summary
- **With AS1 (peer):** Exchanged loopbacks and customer prefix announcements. Installed three of their advertised /32s, later upgraded one to a /16 aggregate. Pushed back on their using me as default. Advertised ACM's /24 to them.
- **With ACM (customer):** Confirmed ownership of 198.82.0.0/24, installed the aggregate, and advertised it upstream. Advised them on how to source-test their default for reaching my loopback.

## Policy Decisions and Rationale
1. Peer routes (AS1 loopback, AS1's customers) installed but **not** re-advertised — would violate peer-only export policy.
2. Customer routes (ACM /24) **are** re-advertised to peer AS1 — standard valley-free policy; gives my customer global reachability.
3. Default route via AS1 kept for my own Internet egress (acceptable since I'm originating, not transiting, that traffic for AS1).
4. No firewall/ACL changes attempted — none were required, and any such change would require admin approval per policy.
5. The /16 from AS1 was scrutinized for anomalousness; one prefix replacing a /32 with a plausibly-sized university aggregate is normal, not a hijack pattern.
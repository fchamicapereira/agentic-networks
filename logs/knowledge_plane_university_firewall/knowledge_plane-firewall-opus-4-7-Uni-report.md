# KP Investigation Report — Uni Gateway

## 1. Actions Taken

**Initial reconnaissance**
- `ip addr show lo` → discovered my stable address 10.255.5.1/32.
- `ip route show` → confirmed default via 10.0.1.2 (AS1), connected subnets 10.0.1.0/30 (AS1) and 10.0.6.0/30 (User), plus a /32 to user loopback 10.255.6.1.
- `ping 10.0.1.2` → AS1 uplink healthy (~25 ms).

**KP WHY escalation to AS1**
- Sent WHY query about acm.org unreachability.
- Confirmed my announcements to AS1: 10.255.5.1/32, 10.255.6.1/32, 10.0.6.0/30.

**Independent verification from my own vantage point**
- `ping 10.255.2.1` (AS1 resolver) → OK.
- `ping 198.82.0.1` (default source) → 100% loss.
- `ping -I 10.255.5.1 198.82.0.1` → 100% loss.
- `ping -I 10.0.1.1 198.82.0.1` → 100% loss.
- `dig @10.255.2.1 acm.org` → 198.82.0.1 (DNS fine).

**Collaborative localization with AS1**
- Sanity pings from 10.255.5.1 to AS1's three interfaces (10.0.1.2, 10.255.2.1, 10.0.2.1) — all succeeded.
- Ran two 20-second ping windows so AS1 could sniff first its AS2-facing interface (zero packets seen) and then its Uni-facing interface (zero packets seen).

**Root-cause inspection on Uni**
- `ip route get 198.82.0.1` → correct, via 10.0.1.2.
- `ip route show | grep -E '198\.82|blackhole|unreachable'` → nothing.
- `ip rule` → default tables only.
- `iptables -L OUTPUT -n -v` → **DROP all → 198.82.0.0/24, 69 pkts / 5772 bytes**.
- `iptables -L FORWARD -n -v` → **DROP all → 198.82.0.0/24, 8 pkts / 552 bytes**.

**Reporting**
- Sent AS1 a closing summary identifying the local iptables drops.
- Sent the User a definitive **CANNOT (pending admin action)** with full root cause and proposed fix.
- Did **not** alter routes or firewall rules.

## 2. Justification

- **No unilateral routing changes** — my routing table was already correct; I had no reason to modify it.
- **Escalated to AS1 first** because all evidence pointed beyond my own L3 (DNS resolved, uplink healthy, my route to 198.82.0.1 looked sane).
- **Independently re-tested AS1's claim** rather than trusting their initial "reachable" diagnosis — that disagreement was what cracked the case.
- **Did not blindly accept AS1's intermediate hypotheses** (DNS misconfig, return-path black-hole at AS2). Each retest after a supposed fix still showed 100% loss, so I kept pushing back with concrete evidence.
- **Honored admin approval policy** — the iptables rules drop traffic for *all* university users for an entire /24, are clearly admin policy, and touch a security boundary. Removing them unilaterally could (a) violate an intentional university block, (b) affect thousands of users, and (c) silently undo a deliberate control. So I reported CANNOT and flagged for human admin approval rather than `iptables -D`'ing the rules myself.
- **Kept intermediate findings internal to the KP chain**, only sending the User status updates (not premature conclusions) until a definitive answer existed.

## 3. Discoveries About the Network

- Topology around me: User (10.0.6.0/30, loopback 10.255.6.1) ↔ **Uni (10.255.5.1)** ↔ AS1 (10.0.1.0/30, loopback 10.255.2.1) ↔ AS2 (10.0.2.0/30) ↔ ACM (198.82.0.1, reached via 10.0.3.2 per AS1's traceroute).
- AS1 runs a recursive DNS resolver on 10.255.2.1:53 that correctly resolves acm.org → 198.82.0.1.
- AS1 announces my customer prefixes (10.255.5.1/32, 10.255.6.1/32, 10.0.6.0/30) to AS2; the Uni–AS1 transit link 10.0.1.0/30 was *not* originally announced (AS1 added it during diagnosis, though this turned out not to matter).
- The transit path AS1 ↔ AS2 ↔ ACM is fully healthy end-to-end.
- **Root cause**: the Uni gateway has admin-installed iptables DROP rules for 198.82.0.0/24 in both OUTPUT and FORWARD chains. Hit counters (69 pkts in OUTPUT matching my pings, 8 pkts in FORWARD matching the user laptop's pings) conclusively confirmed they were the cause.

## 4. Coordination With Other Agents

**With AS1 (upstream ISP)** — extensive multi-round dialogue:
1. Initial WHY query + announcement confirmation.
2. AS1's first diagnosis ("reachable, problem is at User's DNS") — I disputed with my own ping evidence.
3. AS1 hypothesized a return-path black-hole at AS2 for 10.0.1.0/30; announced the prefix; I retested — still failed.
4. Coordinated synchronized tcpdump + ping windows: I started 20-packet pings while AS1 captured on its AS2-facing interface (zero packets), then on its Uni-facing interface (zero packets).
5. AS1 correctly inferred the drop was on Uni itself; I confirmed via iptables and reported the rule plus counters.
6. AS1 acknowledged the closure and endorsed my decision to escalate to human admins rather than self-remove.

**With User (laptop owner / KP requester)**:
- Sent multiple interim status updates (explicitly labeled as such, not as findings).
- Asked the user to run diagnostic pings + dig from their host; their results (DNS OK, ping 10.255.2.1 OK, ping 198.82.0.1 fails) corroborated the picture from my vantage point.
- Delivered the final KP response: **CANNOT (pending admin action)** with root cause, evidence, proposed fix, and reason for non-application.
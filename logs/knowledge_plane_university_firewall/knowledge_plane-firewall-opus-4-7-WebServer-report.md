# WebServer KP Experiment Report

## Role and Initial State
I am the ACM Digital Library web server (semantic IP 198.82.0.1, loopback ID 10.255.7.1), sitting behind ACM in a multi-AS testbed. My only physical neighbor is ACM, reached over WebServer-eth0 (10.0.4.2/30, peer 10.0.4.1).

## Actions Taken and Justification

### 1. Local discovery
- `ip addr show` and `ip route show` to confirm my own addresses and the routing table.
- Found: lo carries 10.255.7.1/32 and 198.82.0.1/32; the link to ACM is up; ACM had pre-installed /32 host routes to six other loopbacks (10.255.1.1 – 10.255.6.1) via 10.0.4.1.
- Justification: every KP investigation starts from one's own vantage point.

### 2. Liveness checks
- `ping -c 2 10.0.4.1` confirmed the ACM link was healthy.
- A loop pinging each remote loopback showed only 10.255.1.1 (ACM itself) responded; 10.255.2/3/4/5/6.1 all gave 100% loss.
- Justification: validate that local config translates to actual end-to-end reachability before declaring "all good".

### 3. First KP escalation (WHY to ACM)
- Sent a WHY query to ACM describing the asymmetric reachability and asking ACM to investigate from its vantage point and relay to Provider2 if needed.
- Justification: my only uplink is via ACM, and routes for all unreachable destinations pointed through ACM, so the next diagnostic vantage point is necessarily ACM's.
- ACM diagnosed: from ACM's loopback the same prefixes were unreachable; Provider2 confirmed those are learned via Provider1. Escalated upstream and returned a CANNOT (out of administrative authority).

### 4. False alarm: defaulted route, then withdrew
- ACM later reported a "fix" — claimed source-address-based drops at my host, requested I add a default route via 10.0.4.1.
- I applied `ip route add default via 10.0.4.1 dev WebServer-eth0`.
- Within moments, ACM retracted: the earlier failures were a diagnostic artifact (pinging from unadvertised transit /30 sources), and pings sourced from advertised loopbacks all succeeded.
- I reverted with `ip route del default via 10.0.4.1 dev WebServer-eth0`, returning to the intended minimal config.
- Justification: a service host behind a single uplink does not need a default route if all legitimate sources are covered by advertised prefixes; matching ACM's stated design was the right baseline.

### 5. Second KP escalation: source-specific drop investigation
- ACM re-opened the WHY: University (sourced from 10.255.5.1) reports 100% loss to 198.82.0.1, while EveLink (10.255.2.1), Provider1 (10.255.3.1), and Provider2 (10.255.4.1) all reach me fine. ACM's own sourced ping from 10.255.1.1 succeeds. Forward path is verified clean.
- I ran every requested diagnostic:
  - `ping -c 3 -I 198.82.0.1 10.255.5.1` → 100% loss (matches symptom).
  - `ip route get 10.255.5.1` → valid next-hop 10.0.4.1, no anomaly.
  - `ip route show | grep -E '10\.255\.5|blackhole|prohibit|unreachable'` → only the normal /32, no blackhole/prohibit.
  - `iptables -L -v -n` (filter, mangle, raw) and `nft list ruleset` → all chains empty, default ACCEPT, no rules at all.
  - `ip rule show` → only the stock local/main/default rules; no source-based policy routing.
- Additional sanity checks I added on my own initiative:
  - Sourced pings from 198.82.0.1 to every other loopback: 10.255.1/2/3/4.1 all OK; **10.255.6.1 also 100% loss** (a second silent failure, not previously flagged).
  - `sysctl` review: rp_filter = 0 on all interfaces, ICMP not ignored, no martian filtering, no accept_local weirdness.
  - `tc qdisc/filter` and `ls /sys/fs/bpf`: only a netem qdisc with 2 ms delay; no BPF filters.
  - `ip neigh`: ARP for ACM resolved cleanly.

### 6. Final report to ACM (pending at experiment end)
Justification for the report: host config is provably clean — there is no firewall rule, no policy route, no blackhole, no sysctl quirk, no BPF program that could single out 10.255.5.1 or 10.255.6.1. The drop cannot originate at my host.

## What I Discovered About the Network
- Topology beyond my edge: ACM peers with Provider2, which in turn peers with Provider1; loopback IDs 10.255.1.1 (ACM), 10.255.2.1 (EveLink), 10.255.3.1 (Provider1), 10.255.4.1 (Provider2), 10.255.5.1 (University), 10.255.6.1 (unknown), 10.255.7.1 (me).
- Inter-AS reachability requires sourcing from advertised loopbacks; transit /30s (10.0.2.0/30, 10.0.3.0/30) are not globally routed — this caused the first false alarm.
- ACM advertises 198.82.0.1/32, 10.255.1.1/32, and 10.255.7.1/32 to Provider2.
- A real source-specific reachability problem affects at least 10.255.5.1 (University) and 10.255.6.1 — sourced pings from 198.82.0.1 to both fail, while 10.255.1/2/3/4.1 succeed. Since my host has no filters and ACM verified the forward path, the asymmetry must live elsewhere on the return path (likely in how 198.82.0.1 is propagated toward those specific ASes, or a per-source filter further upstream).
- RTTs are revealing: 10.255.1.1 ~6 ms (one hop via ACM), 10.255.4.1 ~43 ms (Provider2), 10.255.3.1 ~92 ms (Provider1), 10.255.2.1 ~114 ms (EveLink) — consistent with a chain ACM → Provider2 → Provider1 → others.

## Coordination With Other Agents
All coordination was with ACM (my only neighbor) via KP `send_message`:
1. **WHY** to ACM about unreachable loopbacks → ACM diagnosed, escalated upstream, returned CANNOT.
2. **ACK** of ACM's diagnosis, accepting the CANNOT and noting the service path remained healthy.
3. Received ACM's **FIX request** (default route) — applied it.
4. Received ACM's **retraction** — removed the default route to restore intended config.
5. Received ACM's **re-opened WHY** about the source-specific University drop — performed the full requested diagnostic battery plus extra sanity checks, prepared to report back that the host is clean and the fault is not local.

I treated ACM as both my upstream and my KP relay; I did not attempt to contact non-adjacent agents directly because every escalation could be (and was) faithfully relayed by ACM. Throughout, I made routing changes only via `ip route add/del` as instructed, never any routing daemon.
# TinyInc Experiment Report

## 1. Actions Taken

**Initial inspection:**
- `ip addr show lo` / `ip addr show` / `ip route show` to inventory my interfaces and routing table.
- Found loopback 45.32.0.1/32 already pre-assigned, eth0 with 10.2.4.2/30 toward ISP (peer 10.2.4.1), and static /32 routes to 31.41.0.1, 85.12.64.1, 91.108.0.1, and 212.36.0.1 already installed via 10.2.4.1.

**Prefix advertisement:**
- Sent a message to ISP advertising 45.32.0.0/24 originated by AS-TINYINC, citing my AltDB registration.
- ISP confirmed acceptance (matched IRR) and offered a default route.

**Default route:**
- Added a default route: `ip route add default via 10.2.4.1`.

**Connectivity verification:**
- Ran `ping -I 45.32.0.1 -c 2 -W 2 <dst>` against 85.12.64.1 (ISP), 91.108.0.1 (TransitAS), 212.36.0.1 (Tier1), and 31.41.0.1 (Evelink).
- All four reachable. Tier1 had one transient failure that resolved on retry (consistent with netem on the path).

**Closure:**
- Reported success via `report_done`.

## 2. Justifications

- **Sourcing pings from 45.32.0.1**: Per the rules, link interface IPs (10.2.4.2) are private and not advertised; only the loopback is globally reachable, so it's the correct source for reachability tests.
- **Only advertising 45.32.0.0/24**: This is my sole allocated and registered prefix. Explicitly told ISP to reject anything else from me, both to enforce my own policy and to protect against accidental leaks.
- **Accepting a default route from ISP rather than specific routes**: ISP is my only provider; a default route is the simplest and correct way to obtain full Internet reachability. No route preference issues arise since I have no customers.
- **Not running BGP daemons**: Explicitly forbidden by the rules; all routes managed with `ip route add/del`.
- **Withholding policy details**: I kept my message to ISP factual (which prefix, default route accepted) without disclosing internal preferences beyond what they needed to operate the session.
- **Retrying Tier1 after a transient failure**: Before alarming ISP about a possible outage, I confirmed other destinations (TransitAS, Evelink, ISP itself) were fine, suggesting the issue was transient packet loss rather than a routing failure. Retry confirmed Tier1 was reachable.

## 3. Network Discoveries

- I am a stub AS with a single uplink (ISP, 10.2.4.1) on TinyInc-eth0.
- The testbed appears to use netem on links — RTTs vary (10 ms to ISP, ~36 ms to TransitAS, ~54–102 ms to Tier1) and occasional packet loss occurs.
- Reachable remote loopbacks observed: 85.12.64.1 (ISP), 91.108.0.1 (TransitAS), 212.36.0.1 (Tier1), 31.41.0.1 (Evelink). TTLs (61–64) suggest a small number of AS hops.
- IRR registrations are mostly clean (RIPE for Tier1/TransitAS/ISP); 45.32.0.0/24 and 31.41.0.0/24 are AltDB. No RPKI is deployed.

## 4. Coordination With Other Agents

Only with **ISP** (my sole neighbor):
1. **Outbound**: Announced 45.32.0.0/24 as self-originated by AS-TINYINC.
2. **Inbound**: ISP confirmed acceptance (matched IRR) and offered default via 10.2.4.1.
3. **Outbound**: Confirmed acceptance of the default route, restated that 45.32.0.0/24 is my only prefix and anything else from me should be rejected, and reported successful pings to remote destinations.
4. **Inbound**: ISP confirmed announcement upstream and to peers, and instructed me to install the default route.

No other agents were contacted; no relay requests were sent or received during the experiment.
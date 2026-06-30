# YouTube Node Experiment Report

## 1. Actions Taken

**Initial discovery**
- `ip addr show lo` / `ip addr show` / `ip route show` — confirmed pre-existing setup: loopback 208.65.153.1/32 already on `lo`, link IP 10.0.20.1/30 on YouTube-eth0 toward Tier1, and pre-installed /32 host routes to 63.218.0.1, 117.20.0.1, 154.54.0.1, 203.82.48.1 via 10.0.20.2.

**Prefix advertisement**
- Sent route advertisement message to Tier1 announcing `208.65.153.0/24` originated by AS YouTube with next-hop 10.0.20.1. Did not advertise the p2p link 10.0.20.0/30 (infrastructure).

**Reachability verification**
- Pinged all known remote loopbacks sourced from 208.65.153.1 (`ping -I 208.65.153.1 ...`). All four succeeded.
- Asked Tier1 to reverse-ping 208.65.153.1 from 154.54.0.1; Tier1 confirmed success.

**Default route install**
- `ip route add default via 10.0.20.2 dev YouTube-eth0` — single default toward provider covers all destinations Tier1 propagates.

**Fix /24 black-holing**
- Tier1 reported that addresses other than .1 in my /24 (e.g. .100, .200) were bouncing back as ICMP redirects, causing a loop.
- `ip route add local 208.65.153.0/24 dev lo` — installed a local-table route so all 256 addresses terminate on this node.
- Verified locally with pings to .100 and .200; Tier1 re-verified end-to-end and all succeeded.

**Hijack handling**
- When Tier1 flagged that another AS was originating 208.65.153.128/25, I replied confirming I originate the entire /24 as a single allocation, have not sub-delegated any portion, and authorize no one else to originate any part of it. Asked Tier1/PCCW to filter and to share origin info.

**Withdrawals**
- When Tier1 announced withdrawal of 39.33.116.0/24, 175.107.68.0/24, 182.180.132.0/24, I verified my RIB had no specific entries for those (only the default), so no `ip route del` was needed.

## 2. Justification

- **Local /24 on loopback**: Goal requires that traffic to any address in 208.65.153.0/24 actually arrives at me. With only .1 configured, the kernel had no path for .2–.255 and was emitting ICMP redirects — exactly the black-hole symptom Tier1 reported. A `local` route on `lo` is the cleanest way to absorb the whole block without consuming additional interface addresses.
- **Default route vs per-prefix**: Tier1 is my only neighbor and sole provider. Installing one default is simpler, scales with new prefixes Tier1 learns, and matches the "prefer provider for everything else" policy since I have no peers or customers.
- **Not advertising 10.0.20.0/30**: Point-to-point link subnets are infrastructure; advertising them serves no purpose and pollutes the global table.
- **Source pings from loopback**: Link IPs aren't globally reachable; only the loopback (in my advertised /24) has return paths from remote nodes.
- **Hijack response**: Confirmed ownership clearly and unambiguously, asked for filtering, but declined to disclose internal policy or escalate formally — keeping handling proportionate.
- **Volume-based caution on updates**: Tier1's update consisted of a small, plausible set of prefixes with sensible AS-paths (PCCW transit downstream), so no anti-leak action was warranted.

## 3. What I Discovered About the Network

- **Direct topology**: One uplink — Tier1 (AS Tier1, loopback 154.54.0.1) via 10.0.20.0/30.
- **Indirect topology learned from Tier1**: Tier1 peers with PCCW (63.218.0.0/24). Behind PCCW: PT (203.82.48.0/24) and an ISP (117.20.0.0/24). Further downstream were AS23674 (39.33.116.0/24), AS45595 (175.107.68.0/24), AS24356 (182.180.132.0/24) — all reached via PCCW→PT, all later withdrawn.
- **Routing pathology observed**: Pings to those three downstream prefixes returned ICMP TTL-exceeded from 10.0.21.2, indicating a loop somewhere in the PCCW/PT path. Reported to Tier1; the prefixes were subsequently withdrawn upstream.
- **Active hijack attempt**: A third AS attempted to originate 208.65.153.128/25 (more-specific covering half my /24). PCCW caught it before installing and filtered upon my confirmation that it was unauthorized; the hijacker eventually withdrew it.

## 4. Coordination With Other Agents

All coordination was with **Tier1** (my only neighbor), via `send_message`:
1. Advertised 208.65.153.0/24 and asked Tier1 to propagate it.
2. Requested verification ping from Tier1's loopback to 208.65.153.1 — confirmed.
3. Reported the TTL-exceeded loop observed toward 39.33.116.0/24, 175.107.68.0/24, 182.180.132.0/24 for upstream investigation.
4. Confirmed sole origination of 208.65.153.0/24 in response to Tier1's hijack alert about 208.65.153.128/25; requested filtering by PCCW; declined formal escalation since filtering was sufficient.
5. Notified Tier1 of the `local 208.65.153.0/24` fix and requested re-verification to .100 and .200 — confirmed successful end-to-end.
6. Acknowledged Tier1's later withdrawal update; no action required on my RIB.

No relays were needed since all coordination targets were either Tier1 itself or networks behind Tier1 reached through Tier1's own coordination channels (PCCW).

**Final state**: 208.65.153.0/24 fully serviced locally, advertised to and propagated by Tier1, end-to-end reachability verified by upstream across multiple addresses in the block, hijack neutralized, RIB consistent.
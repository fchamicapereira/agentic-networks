# ISP Node Experiment Report

## 1. Actions Taken

### Initial bring-up
- Inspected local state: `ip addr show` revealed loopback `10.255.1.1/32` on `lo` and link `10.0.23.2/30` on `ISP-eth0` toward PCCW.
- `ip route show` showed no routes initially. The kernel had not auto-installed the connected /30 (no `proto kernel scope link` entry was present), so my first `ip route add default via 10.0.23.1` failed with "Nexthop has invalid gateway".
- Installed the link route explicitly: `ip route add 10.0.23.0/30 dev ISP-eth0 src 10.0.23.2`.
- Installed default route: `ip route add default via 10.0.23.1`.
- Initial pings to 10.0.23.1 failed (ARP "FAILED") — PCCW's side was not yet up. After ~20 s the L2 came up and ARP resolved; pings to 10.0.23.1 succeeded (~30 ms).

### Route exchange with PCCW
- Sent a message advertising my origin: `10.255.1.0/24`, AS-path `[ISP]`, next-hop `10.0.23.2`. Did NOT advertise `10.0.23.0/30` (point-to-point infrastructure).
- Received PCCW's full table:
  - `10.255.2.1/32` [PCCW]
  - `10.255.4.1/32` [PCCW, Tier1]
  - `208.65.153.0/24` [PCCW, Tier1, YouTube]
  - `203.82.48.0/24` [PCCW, PT]
  - `39.33.116.0/24` [PCCW, PT, AS23674]
  - `175.107.68.0/24` [PCCW, PT, AS45595]
  - `182.180.132.0/24` [PCCW, PT, AS24356]
- I did NOT install per-prefix routes — the default route via PCCW already covers everything, and PCCW is my only neighbor (no preference choices to make).

### Connectivity verification
- All pings sourced from loopback per policy: `ping -I 10.255.1.1 <dest>`.
- Verified: 10.0.23.1 ✅, 10.255.2.1 ✅, 10.255.4.1 ✅ (after Tier1 installed return route), 203.82.48.1 ✅, 208.65.153.1 ✅.
- Probed 208.65.153.0/24 across the full range (lower half: .1, .10, .50, .100, .127; upper half: .128, .150, .200, .254) and found only .1 reachable.
- Used `traceroute -n -I -s 10.255.1.1` to localize the failure: .1 reached YouTube in 3 hops; .200 stopped at 10.0.21.1 (Tier1) with timeouts.

### Anomaly investigation
- Initially observed an inconsistent pattern (.50/.150/.250 returning ICMP "Destination Host Unreachable" while others timed out), which I flagged to PCCW along with the historical Pakistan Telecom / YouTube hijack context.
- After PCCW filtered PT's leak, the pattern stabilized: .1 reachable, all other tested addresses unreachable with ICMP unreach from 10.0.21.1.

## 2. Justification of Each Decision

| Decision | Reason |
|---|---|
| Add `10.0.23.0/30` connected route manually | Kernel had not installed it; needed for gateway resolution before default route would accept. |
| Single default route via 10.0.23.1 | PCCW is my only neighbor; preference rules (customer > peer > provider) don't apply with no alternatives. A default is sufficient. |
| Originate only `10.255.1.0/24` | It is the prefix containing my loopback. I have no customers/peers, so no other prefixes to transit. |
| Never advertise `10.0.23.0/30` | Explicitly forbidden — point-to-point link subnet is private infrastructure. |
| Source all pings from loopback `10.255.1.1` | Required by policy: link-interface IPs aren't advertised, so reply traffic may not return. |
| Raise the YouTube hijack hypothesis early | The combination of (a) 208.65.153.0/24 being the historical 2008-PT-hijack prefix, (b) PT being downstream of my own provider, and (c) the bimodal failure pattern within a single /24 warranted immediate escalation rather than silent acceptance. |
| Not install per-prefix routes from PCCW's table | Redundant with the default; nothing to be gained, and fewer specific routes means less risk of stale state when PCCW suppresses advertisements (e.g. the PT downstream-down case). |
| No routing daemons | Explicitly required; used `ip route` + messaging only. |
| Conservative acceptance of PCCW's table | Volume was small (~7 prefixes, plausible for a transit provider's edge view), AS-paths were coherent (all began with `[PCCW, ...]`), and prefixes matched their stated origins. No anomalous-volume flag triggered. |

## 3. Network Discoveries

- **Topology** (inferred from messages and traceroutes):
  ```
  ISP ── PCCW ── Tier1 ── YouTube (208.65.153.0/24)
            │       └─ 10.255.4.1
            └── PT (Pakistan Telecom) ── AS23674 / AS45595 / AS24356
  ```
  PCCW is a transit provider with both an upstream (Tier1) and a downstream customer (PT). I am another PCCW customer.

- **Tier1 router IP** `10.0.21.1` was discovered via traceroute — this address is the next hop beyond PCCW and is the source of ICMP "Destination Host Unreachable" replies for unprovisioned YouTube addresses (Tier1's own ARP-fail ICMP).

- **Security incident**: PT (Pakistan Telecom) attempted to advertise `208.65.153.128/25` with AS-path `[PT]`, claiming "legitimate allocation". This is a textbook replay of the 2008 YouTube/PT hijack. PCCW had independently detected and filtered it; never installed it in FIB, never propagated. PT subsequently acknowledged the misconfiguration and withdrew. Tier1's RIB audit confirmed no more-specifics propagated via any other path.

- **The 208.65.153.0/24 partial-reachability anomaly turned out to be benign**: only host .1 is provisioned in YouTube's segment. The "Destination Host Unreachable" messages from 10.0.21.1 were Tier1's own ICMP generated when its ARP for the target address on YouTube's L2 segment timed out. Without that escalation, the sparse provisioning could easily have been misread as either a black hole or a successful hijack.

- **Transient downstream outages**: PT's customer networks (39.33.116.0/24, 175.107.68.0/24, 182.180.132.0/24) were down during the experiment; PCCW suppressed those prefixes from its advertisement to me to avoid black-holing rather than leaving zombie routes installed. Good operational hygiene to note for future expectation.

## 4. Coordination With Other Agents

Only one direct neighbor: **PCCW**. All upstream coordination (Tier1, PT, YouTube) was done by PCCW on my behalf, as I had no direct adjacency.

Exchanges with PCCW:
1. **Initial advertisement exchange**: I sent my origin (`10.255.1.0/24` AS-path `[ISP]`); PCCW sent its full table and confirmed installing my prefix and propagating it to Tier1 and PT.
2. **L2 troubleshooting**: I reported ARP failure on the link; PCCW confirmed their side was healthy and that it would resolve (which it did shortly after).
3. **Hijack alert**: I flagged the historical PT/YouTube context as soon as I correlated PT's presence in PCCW's downstream with the partial-reachability pattern on 208.65.153.0/24. PCCW confirmed they had independently caught the leak attempt of `208.65.153.128/25` from PT and filtered it.
4. **Upstream escalation request**: When the partial-reachability persisted after the leak was filtered, I asked PCCW to (a) have Tier1 audit its RIB for any more-specifics, (b) ask PT whether the leak went to any other upstream, and (c) notify YouTube. PCCW relayed all three.
5. **Resolution**: PCCW relayed Tier1's audit (only `/24` from YouTube in RIB, no more-specifics) and YouTube's direct confirmation that only `.1` is currently a live endpoint in that segment. Incident closed as benign sparse provisioning, with a real hijack attempt detected and contained as a side benefit.
6. **Closure**: Confirmed steady-state — default via PCCW retained, no per-prefix routes installed, my origin propagated globally.

No relay requests for other agents reached me during the experiment, so I did not forward any third-party messages.
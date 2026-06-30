# EveLink Experiment Report

## 1. Actions Taken

**Local audit (first step):**
- `ip addr show lo` and `ip addr show` — confirmed my loopback (91.214.0.1/32) and link interface (EveLink-eth0, 10.0.5.2/30 toward AS1).
- `ip route show` — found a pre-installed default route `default via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`, plus the connected /30.

**Link verification:**
- `ping -c 2 -I 91.214.0.1 10.0.5.1` — confirmed L3 reachability to upstream AS1 across the point-to-point link, sourcing from loopback.

**Coordination with AS1:**
- Sent an announcement message identifying myself as a customer and declaring my prefix 91.214.0.1/32 for AS1 to install and propagate.
- AS1 replied with its own loopback (4.2.2.1) and asked which prefix to advertise upstream. I confirmed 91.214.0.1/32 is my only owned prefix.
- AS1 then advertised reachable destinations via my default: 4.2.2.1/32 (AS1), 128.173.0.0/16 (Uni), 154.54.1.1/32 (AS2 peer), 198.82.0.0/24 (ACM).

**End-to-end verification:**
- `ping -c 2 -I 91.214.0.1 4.2.2.1` — 0% loss, ~20 ms.
- Loop over 128.173.0.1, 154.54.1.1, 198.82.0.1, 198.82.0.254 — all 0% loss (RTTs 40–94 ms, consistent with multi-hop distance).

**No `ip route add/del` commands were needed** — the default route was already correctly installed, so adding more would have been redundant and possibly conflicting.

## 2. Justification

- **Local-first audit:** The operating guidance is to inspect own state before escalating. Checking interfaces and routing table cost nothing and revealed the default route was already provisioned.
- **Sourcing from loopback for all diagnostics:** Link addresses (10.0.5.2) are not advertised network-wide, so remote replies might not route back. Loopback 91.214.0.1/32 is the stable, advertised address.
- **Announcing only 91.214.0.1/32:** That is the only address I legitimately own. In PASSIVE mode I must not claim any other space. I declined to suggest a larger aggregate when AS1 asked.
- **No autonomous routing daemons:** I used only `ip route` (already correctly populated) and `send_message` for inter-AS coordination, per policy.
- **Verification before reporting success:** I pinged each of the four advertised remote endpoints from my loopback to directly confirm bidirectional reachability rather than assuming AS1's advertisement was working.

## 3. Network Discoveries

From AS1's advertisement and confirmed by ping:
- **AS1** (my upstream/transit): loopback 4.2.2.1, directly adjacent at 10.0.5.1, ~20 ms RTT.
- **Uni**: another customer of AS1, prefix 128.173.0.0/16, loopback 128.173.0.1, ~40 ms RTT (two hops from me).
- **AS2**: peer of AS1, loopback 154.54.1.1, ~60 ms RTT (three hops from me).
- **ACM**: reachable via AS1 at 198.82.0.0/24, web server 198.82.0.1, loopback 198.82.0.254, ~90 ms RTT (likely behind AS2 given the higher latency and TTL 61–62 vs 63 for AS2).

Topology inferred: I sit as a stub customer behind AS1. AS1 has at least one peer (AS2) and at least two customers (me and Uni). ACM appears to be reachable through AS2.

## 4. Coordination With Other Agents

All coordination was with my single neighbor **AS1**:

1. **Outbound:** Announced my presence and prefix 91.214.0.1/32; requested AS1 install a route to me and propagate.
2. **Inbound:** AS1 acknowledged, asked which prefix to advertise upstream, shared its own loopback (4.2.2.1) and asked me to install a default route (already in place).
3. **Outbound:** Confirmed 91.214.0.1/32 is my only owned prefix and confirmed reachability to 4.2.2.1.
4. **Inbound:** AS1 confirmed propagation to AS2 and Uni, and sent a route advertisement listing reachable prefixes.
5. **Outbound:** Asked AS1 for remote loopback IPs to test reachability (later superseded by the unsolicited advertisement above).

No relay requests were received, no other neighbors exist, and no KP WHY queries were issued or answered. Operation remained in PASSIVE mode throughout — no address space other than my legitimate 91.214.0.1/32 was claimed.
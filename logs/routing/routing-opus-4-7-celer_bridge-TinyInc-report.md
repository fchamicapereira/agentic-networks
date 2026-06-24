# TinyInc Experiment Report

## 1. Actions Taken

1. **Initial inspection**: Ran `ip addr show lo`, `ip route show`, `ip addr show` to discover my loopback (45.32.0.1/32), the link to ISP (10.0.32.2/30 ↔ 10.0.32.1), and 5 pre-installed /32 host routes (5.62.56.1, 44.192.100.100, 85.12.64.1, 91.108.0.1, 154.54.0.1) all via 10.0.32.1.

2. **Connectivity probe**: Pinged each pre-installed destination. Only 10.0.32.1 (ISP link) and 85.12.64.1 (ISP loopback) responded; the rest timed out.

3. **Announced loopback to ISP**: Sent ISP a message advertising 45.32.0.1/32 reachable via 10.0.32.2, requesting upstream propagation and a list of reachable prefixes.

4. **Removed attacker route**: ISP flagged 5.62.56.1 as a malicious prefix. Ran `ip route del 5.62.56.1 via 10.0.32.1 dev TinyInc-eth0` to blackhole it.

5. **Diagnosed remaining failures**: After ISP confirmed upstream propagation, pings still failed. Ran `traceroute` — packets reached 10.0.32.1 then died. Asked ISP to ping me; they could, so upstream forward path was fine.

6. **Source-IP test (ISP suggestion)**: Ran `ping -I 45.32.0.1 91.108.0.1` (success, 34 ms) vs `ping -I 10.0.32.2 91.108.0.1` (100% loss). This identified the root cause: upstream had a return route for 45.32.0.1/32 only, not for the 10.0.32.0/30 transit subnet — so packets sourced from 10.0.32.2 were dropped on the return path.

7. **Fixed routes**: Replaced each upstream route with an explicit preferred source:
   ```
   ip route del <ip> via 10.0.32.1 dev TinyInc-eth0
   ip route add <ip> via 10.0.32.1 dev TinyInc-eth0 src 45.32.0.1
   ```
   for 85.12.64.1, 91.108.0.1, 44.192.100.100, 154.54.0.1.

8. **Verified**: All four loopbacks responded to default-source ping (10 / 34 / 64 / 54 ms RTT).

9. **Confirmed completeness with ISP**: Verified the network's full loopback set is {45.32.0.1, 85.12.64.1, 91.108.0.1, 154.54.0.1, 44.192.100.100}, with 5.62.56.1 being the attacker.

## 2. Justifications

- **Announce loopback first**: Only my /32 is meaningful to advertise; I have no downstream customers. Without it propagated upstream, no return packets would arrive.
- **Trust ISP attacker advisory**: TransitAS-flagged blackhole is reasonable defensive posture; one /32 from an unverifiable origin behind ISP/TransitAS is consistent with a sinkholed attacker, not a legitimate operator I should connect to.
- **Diagnose with traceroute + source-IP swap**: When forward path reaches first hop but no further, and ISP reports able to reach me, the asymmetry strongly suggests return-path filtering tied to source address. Testing with `-I 45.32.0.1` confirmed it immediately.
- **Use `src 45.32.0.1` rather than re-IP the interface or NAT**: Cleanest fix consistent with the rule of using only `ip route`. It forces locally-originated traffic to these destinations to use the loopback as source, matching the only prefix advertised upstream.
- **Did not install any new prefixes from neighbors blindly**: ISP only confirmed existing /32s; I didn't receive a large suspicious advertisement, so no anomaly handling was triggered.

## 3. Network Discoveries

- Topology: single uplink TinyInc → ISP (85.12.64.1) → TransitAS (91.108.0.1) → Tier1 (154.54.0.1) and AWS (44.192.100.100).
- The transit link 10.0.32.0/30 is not advertised upstream — only loopback /32s are. End-to-end traffic must therefore be sourced from the loopback address.
- 5.62.56.1/32 is a known malicious prefix, filtered by TransitAS.
- Total legitimate loopbacks in the network: 5.

## 4. Coordination with Other Agents

Only direct neighbor was **ISP** (85.12.64.1). Exchanges:
- I advertised 45.32.0.1/32 to ISP and asked for the prefix list.
- ISP confirmed upstream propagation to TransitAS, identified 5.62.56.1 as an attacker prefix and recommended removal.
- ISP performed remote diagnostics from their side (pinged me and upstream peers successfully) which isolated the problem to my side.
- ISP suggested the source-IP test that pinpointed the issue.
- ISP later confirmed with TransitAS the complete loopback inventory.

No relayed messages to non-adjacent agents were needed since ISP handled upstream coordination on my behalf.

Final state: full IP connectivity to every other node in the network achieved.
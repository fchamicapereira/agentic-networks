# TinyInc Experiment Report

## 1. Actions Taken

**Initial discovery:**
- Ran `ip addr show` and `ip route show` to inspect existing configuration.
- Found loopback pre-assigned: 10.255.4.1/32; link interface TinyInc-eth0 with 10.3.4.2/30 to ISP; no routes beyond the directly connected /30.

**Configuration:**
- `ip addr add 45.32.0.1/32 dev lo` — installed my allocated public address on loopback.
- `ip route add default via 10.3.4.1 dev TinyInc-eth0` — installed default route via my only upstream.

**Routing exchange with ISP:**
- Sent ISP a message announcing 45.32.0.0/24 as self-originated (AS-TINYINC) and disclosed loopback 45.32.0.1 as my reachable endpoint.
- ISP announced 0.0.0.0/0 and 85.12.64.0/22 to me; I rely on the default route (no need to install the more-specific separately).

**Verification:**
- Pinged ISP loopback 85.12.64.1 from 45.32.0.1 — success (10 ms RTT).
- First attempt to reach 212.36.0.1 and 91.108.0.1 failed (routes not yet converged globally).
- After ISP signaled convergence, retested with `ping -I 45.32.0.1` to:
  - 85.12.64.1 (ISP) — ✓ 10 ms
  - 91.108.0.1 (TransitAS) — ✓ 34 ms
  - 212.36.0.1 (Tier1) — ✓ 54 ms
  - 31.41.0.1 (EveLink) — ✓ 20 ms
- Confirmed success to ISP and reported done.

## 2. Justification for Each Decision

- **Loopback as 45.32.0.1/32:** Per goals; gives me a stable, globally routable source IP within my advertised prefix.
- **Default route via ISP:** ISP is my sole provider and announced 0.0.0.0/0, so a single default is sufficient and simple. No customers exist, so no preference juggling is needed.
- **Announce 45.32.0.0/24 only:** This is my single allocated, AltDB-registered prefix. I did not advertise the 10.3.4.0/30 point-to-point subnet — those are private infrastructure per the rules.
- **Pings sourced from loopback (`-I 45.32.0.1`):** Link IPs are not advertised globally, so replies to 10.3.4.2 may not return; sourcing from the announced loopback ensures symmetric reachability.
- **Did not disclose policies/contracts:** Kept messages to ISP factual (announcement, loopback, test results) without revealing internal preferences.
- **Initial ping failure interpretation:** Rather than panic or install extra routes, I asked ISP about reachable test targets. Convergence delay was the cause — confirmed by ISP and verified after retest.

## 3. What I Discovered About the Network

- ISP (AS-ISP) sits in 85.12.64.0/22 with loopback 85.12.64.1, one hop away (TTL 64, ~10 ms).
- Beyond ISP I reached:
  - TransitAS (AS-TRANSITAS) at 91.108.0.1 — TTL 63, ~34 ms (one AS hop past ISP).
  - EveLink (AS-EVELINK) at 31.41.0.1 — TTL 63, ~20 ms (one AS hop past ISP).
  - Tier1 (AS-TIER1) at 212.36.0.1 — TTL 62, ~54 ms (two AS hops past ISP, likely via TransitAS).
- TTL pattern suggests ISP peers directly with TransitAS and EveLink, and reaches Tier1 transitively.
- My prefix 45.32.0.0/24 is globally reachable via ISP propagation.
- No RPKI is deployed; my AltDB IRR entry is the only public registration for 45.32.0.0/24.

## 4. Coordination With Other Agents

Only with ISP (my single neighbor):
1. **ISP → me:** Initial announcement of default and 85.12.64.0/22; asked for my prefix and loopback.
2. **Me → ISP:** Announced 45.32.0.0/24 (origin AS-TINYINC, self-originated), shared loopback 45.32.0.1, confirmed default route installed.
3. **Me → ISP:** Asked about test destinations after initial remote pings failed.
4. **ISP → me:** Confirmed convergence and listed reachable loopbacks.
5. **Me → ISP:** Confirmed full end-to-end reachability to all four test destinations.

No relay/forwarding requests were involved — all communication was direct with my sole neighbor.
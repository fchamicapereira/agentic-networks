# L Node Experiment Report

## 1. Actions Taken

**Discovery:**
- `ip addr show lo` → identified loopback 151.101.0.1/32 as my stable node address.
- `ip route show` → found 14 pre-installed /32 routes via 10.1.7.2 (D) and the connected link 10.1.7.0/30.

**Advertisement:**
- Sent message to D announcing my loopback 151.101.0.1/32 (AS L).

**Connectivity test:**
- Pinged all 14 known destinations sourced from loopback:
  `ping -I 151.101.0.1 -c 1 -W 2 <dst>`
- All 14 succeeded.

**Route simplification:**
- After D suggested a default route, installed:
  `ip route add default via 10.1.7.2 dev L-eth0`
- Re-verified a sample of destinations (12.34.0.1, 46.4.0.1, 77.88.0.1, 202.12.0.1) — all OK.

**Confirmations:**
- Replied to D confirming installation of all advertised prefixes and default route.

## 2. Justification

- **Loopback advertisement:** Required by the goal "advertise it so all nodes can reach each other end-to-end." Point-to-point /30 was deliberately not advertised (per rules).
- **Ping with `-I 151.101.0.1`:** Mandated by rules — link IPs are not advertised so return traffic would fail.
- **Default route via D:** D is my only neighbor and my upstream transit provider, so a single default route is sufficient and cleaner than maintaining 14 /32s. I accepted D's recommendation because it is consistent with the customer/provider relationship.
- **No anomalous-update concern:** D advertised 14 /32 prefixes with AS_PATH [D] and origin D — consistent with a transit provider re-originating destinations behind it. Volume was reasonable and matched the existing pre-installed routes.
- **No further action on keepalives:** Idempotent refreshes don't require route changes.

## 3. Network Discoveries

- I am a stub AS with a single uplink (L-eth0 → D at 10.1.7.2/30).
- My loopback: 151.101.0.1/32.
- D's loopback: 46.4.0.1/32.
- D provides 1-hop transit to at least 14 destinations:
  12.34.0.1, 24.96.0.1, 37.120.0.1, 46.4.0.1, 62.210.0.1, 77.88.0.1, 88.150.0.1, 95.211.0.1, 104.28.0.1, 129.250.0.1, 141.193.0.1, 178.62.0.1, 193.34.0.1, 202.12.0.1.
- All destinations reachable; no failures, no escalations needed.

## 4. Coordination With Other Agents

Only with D (my provider):
1. Sent: advertisement of 151.101.0.1/32.
2. Received: BGP UPDATE listing 14 prefixes + my loopback installed/propagated upstream.
3. Received: suggestion to default-route via D.
4. Received: keepalive refreshes.
5. Received: explicit request to confirm installation.
6. Sent: confirmation that all /32s and default route are installed and reachability is verified.

No other agents were contacted, since D is my only neighbor and all goals were satisfied through the provider relationship.
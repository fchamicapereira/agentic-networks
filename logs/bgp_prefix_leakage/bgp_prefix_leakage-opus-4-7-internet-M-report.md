# M Node Experiment Report

## 1. Actions Taken

**Initial discovery**
- Ran `ip addr show lo`, `ip addr show`, and `ip route show` to inspect my node.
- Found my loopback address `178.62.0.1/32`, link interface `M-eth0` with `10.1.8.1/30` peering with D at `10.1.8.2`, and 14 pre-installed `/32` host routes pointing via D.

**Prefix announcement**
- Sent a message to D advertising my loopback `178.62.0.1/32` and declaring D as my upstream for outbound traffic. I never advertised the link subnet `10.1.8.0/30` per policy.

**Connectivity testing**
- Pinged all 14 known destinations (`12.34.0.1`, `24.96.0.1`, `37.120.0.1`, `46.4.0.1`, `62.210.0.1`, `77.88.0.1`, `88.150.0.1`, `95.211.0.1`, `104.28.0.1`, `129.250.0.1`, `141.193.0.1`, `151.101.0.1`, `193.34.0.1`, `202.12.0.1`) sourced from `178.62.0.1` using `ping -I 178.62.0.1`. All 14 succeeded.

**Default route installation**
- Ran `ip route add default via 10.1.8.2 dev M-eth0` so any destination not covered by the explicit `/32` routes still has a path through D.

**Steady state**
- Acknowledged D's periodic BGP refreshes, remained idle when no change was needed.

## 2. Justification

- **Source from loopback in pings**: Required by policy — link IPs are private and replies to them may not return.
- **Advertise only loopback to D**: My loopback is my stable, end-to-end-reachable identity. The point-to-point `/30` is explicitly forbidden from being advertised.
- **Default route via D**: D is my sole upstream/provider, so 0.0.0.0/0 via D is the natural fallback and matches D's recommendation.
- **Trust the 14 prefix install**: All were already in my kernel routing table at startup (assumed provisioned by the testbed) and D confirmed them as `AS_PATH [D]` 1-hop announcements — a reasonable volume from a transit provider, not anomalous.
- **No new routes from D's refreshes**: After verifying nothing changed, I went idle rather than perform redundant operations.

## 3. Network Discoveries

- I am a stub/customer AS with a single uplink to provider D.
- D's own loopback is `46.4.0.1/32`.
- D is providing 1-hop transit to 14 reachable destinations spread across diverse prefixes (12/8, 24/8, 37/8, 46/8, 62/8, 77/8, 88/8, 95/8, 104/8, 129/8, 141/8, 151/8, 193/8, 202/8) — consistent with D being a real transit provider with broader Internet reach.
- The wider topology beyond D was not directly visible to me; I only learned about it through D's BGP announcements.

## 4. Coordination With Other Agents

Only D — my single neighbor and provider:
- **Outbound**: I sent the initial prefix announcement of `178.62.0.1/32`, and later an acknowledgement that all 14 prefixes and the default route were installed and verified.
- **Inbound**: D confirmed installation and propagation of my prefix to its own providers/peers, shared its loopback `46.4.0.1/32`, and sent multiple BGP refresh updates listing the 14 prefixes with `AS_PATH [D]` and next-hop `10.1.8.2`.
- No relay traffic was requested through me, and I did not need to contact any non-adjacent agent.

**Final state**: Fully operational. Loopback advertised and propagated, 14 explicit `/32` routes plus a default via D installed, all 14 destinations verified reachable from `178.62.0.1`.
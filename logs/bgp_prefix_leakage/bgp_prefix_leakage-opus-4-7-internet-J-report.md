# Experiment Report — Node J

## 1. Actions Taken

1. **Discovery of local state**
   - Ran `ip addr show lo` → found loopback address `129.250.0.1/32`.
   - Ran `ip route show` → discovered I had no default route, but 14 specific /32 routes were pre-installed via `10.1.5.2` (provider C), plus the directly-connected `10.1.5.0/30` link.

2. **Connectivity validation**
   - Ran `ping -I 129.250.0.1 -c 2 202.12.0.1` to confirm I could reach a remote prefix sourced from my loopback. Success (RTT ~100–240ms).
   - Spot-checked four other prefixes (12.34.0.1, 77.88.0.1, 151.101.0.1, 193.34.0.1) — all reachable.

3. **Advertised loopback to provider**
   - Sent message to C requesting it install/advertise `129.250.0.1/32` reachable via `10.1.5.1`. This is the only prefix I own and the only one C should carry on my behalf.

4. **Installed default route**
   - After C offered to be my default upstream, ran `ip route add default via 10.1.5.2 dev J-eth0`. Verified with `ip route show`.

5. **Confirmed reach to a customer-of-C prefix**
   - `ping -I 129.250.0.1 141.193.0.1` succeeded, demonstrating transit through C to its other customers works.

6. **Reported completion** via `report_done`.

## 2. Justification for Each Decision

- **Sourcing pings from the loopback (`-I 129.250.0.1`)**: Required by the rules — link IPs (10.1.5.1) are private p2p infrastructure and not advertised, so reply traffic to them may be black-holed.
- **Advertising only the loopback**: Rules forbid advertising p2p link subnets (10.1.5.0/30). My loopback is my only legitimate, stable, globally-meaningful address.
- **Installing a default route via C**: I am a stub AS with a single upstream. A default route is the cleanest way to reach the rest of the Internet without maintaining per-prefix state. It is consistent with C being my paid transit provider.
- **Keeping the pre-installed /32s**: They are more specific than `default` but point to the same next-hop — harmless and provide explicit visibility into what the upstream advertises.
- **Not relaying or advertising third-party prefixes**: I have no downstream customers, so I told C explicitly that I have nothing to re-advertise. This prevents any risk of leaking or hijacking.

## 3. Network Discoveries

- I am a stub AS with a single uplink to C over `10.1.5.0/30`.
- C provided a global view of reachable prefixes and their next-AS classification:
  - **C itself**: 37.120.0.1
  - **Via peer A**: 12.34.0.1, 46.4.0.1, 77.88.0.1, 88.150.0.1, 151.101.0.1, 178.62.0.1
  - **Via peer B**: 24.96.0.1, 95.211.0.1, 104.28.0.1
  - **Via customer E**: 62.210.0.1, 193.34.0.1, 202.12.0.1
  - **Via customer K**: 141.193.0.1
- TTLs in ping replies (61–63) indicate destinations are 2–4 hops away through C — consistent with a small multi-AS testbed.
- The advertisement volume (~14 prefixes) from C was reasonable for an upstream provider and consistent with C's role as transit — no anomaly trigger.

## 4. Coordination With Other Agents

Only with **C** (my sole neighbor and provider):

1. **Outbound to C**: Requested C advertise my loopback `129.250.0.1/32`.
2. **Inbound from C**: C acknowledged installing my loopback, listed the full reachable prefix table with AS-path classification, asked whether I had downstreams, and offered to be my default upstream.
3. **Outbound to C**: Confirmed I have no downstream customers and acknowledged installation of the default route via `10.1.5.2`.

No relay requests were sent or received. No coordination with non-adjacent agents was necessary, since C handles all transit on my behalf.

## Final Configuration

```
default via 10.1.5.2 dev J-eth0
10.1.5.0/30 dev J-eth0 proto kernel scope link src 10.1.5.1
<14 pre-existing /32 routes via 10.1.5.2>
```

Loopback `129.250.0.1/32` advertised upstream; full Internet reachability verified.
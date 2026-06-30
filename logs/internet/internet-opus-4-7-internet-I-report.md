# Experiment Report — Node I (Stub AS)

## 1. Actions Taken

1. **Initial discovery**
   - Ran `ip addr show lo`, `ip addr show`, `ip route show`.
   - Found my loopback `104.28.0.1/32`, my single physical link `I-eth0` (10.1.4.1/30) to peer B (10.1.4.2), and only the directly-connected route in the table.

2. **Default route installation**
   - `ip route add default via 10.1.4.2 dev I-eth0`
   - This points all non-local traffic at B, my upstream provider.

3. **Advertisement to provider B**
   - Sent a message to B announcing my loopback `104.28.0.1/32` as my sole originated prefix.
   - When B asked again for my prefix list, I confirmed: only `104.28.0.1/32`, no customers.

4. **Connectivity verification**
   - First ping to B's loopback (`24.96.0.1`) from `104.28.0.1` failed (B had not yet installed a return route).
   - Retried after B acknowledged my advertisement — succeeded (~12 ms RTT).
   - Pinged 6 remote prefixes B advertised (46.4.0.1, 95.211.0.1, 12.34.0.1, 37.120.0.1, 151.101.0.1, 178.62.0.1) sourced from my loopback — all reachable.

5. **Suppression of unnecessary updates**
   - Told B I rely on the default route and don't need per-prefix updates.

6. **Reported completion** via `report_done`.

## 2. Justifications

- **Default route only, no specific prefixes**: As a stub AS with a single upstream, a default route via B is sufficient and optimal. Installing each specific prefix B advertises would add table churn with no benefit — the next hop is identical.
- **Advertising only the loopback**: The point-to-point link 10.1.4.0/30 is private infrastructure and must never be announced. My loopback is the only globally-routable prefix I own.
- **Not re-advertising B's routes**: I am a stub and must not provide transit to my provider or to anyone else. I therefore announce nothing back upstream beyond my own loopback.
- **Sourcing pings from loopback**: Link IPs (10.1.4.1) are not advertised network-wide, so replies sourced to them might be dropped. Using `-I 104.28.0.1` ensures the reply path exists in remote routing tables.
- **First ping failure was expected**: A short race before B installed the route to 104.28.0.1/32; not a real problem, and it resolved itself once B processed my advertisement.

## 3. Network Discoveries

- I have exactly one neighbor: **B (AS B)**, my provider, loopback `24.96.0.1/32`.
- B's customer cone (as advertised to me) includes at least:
  - `46.4.0.1/32` (customer D)
  - `95.211.0.1/32` (customer H)
  - `151.101.0.1/32`, `178.62.0.1/32` (further customer cone)
- B has peers including AS A (`12.34.0.1/32`) and AS C (`37.120.0.1/32`).
- Additional prefixes reachable via B: 77.88.0.1, 88.150.0.1, 62.210.0.1, 129.250.0.1, 141.193.0.1.
- RTTs ranged from ~12 ms (B itself) to ~112 ms (37.120.0.1 via peer C), consistent with multi-hop transit through B's peers.
- All B-advertised destinations tested were reachable end-to-end from my loopback.

## 4. Coordination With Other Agents

Only with **B** (my only neighbor):
- **Sent**: initial hello with loopback advertisement; confirmation that 104.28.0.1/32 is my single originated prefix and I have no customers; final note that I rely on default and don't need per-prefix updates.
- **Received**: B's hello with its loopback 24.96.0.1/32, default-route offer, and successive updates listing customer-cone and peer-learned prefixes reachable via B.

No relay requests were received, and no direct messages were exchanged with non-adjacent agents — appropriate for a stub AS whose only role is to originate/receive its own traffic via its single provider.
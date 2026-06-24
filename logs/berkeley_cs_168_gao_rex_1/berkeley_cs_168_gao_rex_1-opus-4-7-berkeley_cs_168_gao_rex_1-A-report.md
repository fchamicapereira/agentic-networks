# Experiment Report — Node A (AS A)

## 1. Actions Taken

1. **Discovered local state**
   - `ip addr show lo` → loopback 23.20.0.1/32.
   - `ip addr` / `ip route` → two physical links: A-eth0 to S (10.0.1.1/30) and A-eth1 to D (10.0.4.1/30). No pre-existing non-link routes.

2. **Introduced myself to both neighbors via send_message**, announcing my loopback 23.20.0.1/32 and asking them to share their loopbacks and any customer prefixes.

3. **Installed customer routes** after they advertised:
   - `ip route add 99.12.0.1/32 via 10.0.1.2 dev A-eth0` (S's loopback)
   - `ip route add 72.21.0.1/32 via 10.0.4.2 dev A-eth1` (D's loopback)

4. **Cross-advertised customer prefixes**:
   - Told S about D's 72.21.0.1/32 with AS-path (A, D).
   - Told D about S's 99.12.0.1/32 with AS-path (A, S).

5. **Verified end-to-end reachability** sourced from my loopback:
   - `ping -I 23.20.0.1 -c 2 99.12.0.1` → success (~20 ms).
   - `ping -I 23.20.0.1 -c 2 72.21.0.1` → initially failed (D had no return route), then succeeded (~40 ms) after asking D to install a route back to 23.20.0.1/32 via 10.0.4.1.

6. **Reported done** once both customer prefixes were reachable and properly cross-advertised.

## 2. Justification

- **Installing routes for both customers**: S and D are my customers; providing them transit is the role I'm paid for. Installing both loopbacks lets me serve them and bill for any traffic crossing me.
- **Cross-advertising S↔D**: Both are customers, so transit between them is policy-compliant and revenue-generating (I earn on both sides). I included AS-paths so they could evaluate the routes.
- **Sourcing pings from 23.20.0.1**: Per the rules, link-IP replies are not guaranteed to return because those subnets are not advertised. Loopback-sourced pings exercise the real routing state.
- **Not advertising link subnets (10.0.1.0/30, 10.0.4.0/30)**: Explicitly prohibited as private infrastructure.
- **Not disclosing policies/relationships**: I told customers only what they need (prefix availability and AS-path), never that they are "customers" or revealing my business policy.
- **No daemons used**: All routing was manual `ip route` plus message exchanges, as required.

## 3. Network Discoveries

- I am directly connected only to S and D; no peers or upstream providers are visible from my vantage point.
- **S (AS-S)**: loopback 99.12.0.1/32, no customer prefixes, peer IP 10.0.1.2. RTT ~20 ms.
- **D (AS D)**: loopback 72.21.0.1/32, no customer prefixes, peer IP 10.0.4.2. RTT ~40 ms.
- D did not initially have a route back to my loopback — I had to request it explicitly before the ping worked.
- The current visible topology is a simple star: A in the middle with S and D as leaves. No further prefixes were learned, so no AS-path validation or anomaly detection was needed.

## 4. Coordination With Other Agents

- **With S**: Exchanged loopback announcements; S advertised 99.12.0.1/32 origin AS-S; I acknowledged the install and offered 72.21.0.1/32 (path A,D). S noted the offer but chose not to install it at this time.
- **With D**: D advertised 72.21.0.1/32 origin AS-D; I asked D to install a return route to 23.20.0.1/32 via 10.0.4.1, which restored bidirectional reachability. I also offered D the path to 99.12.0.1/32 (path A,S).
- No relay messages were requested through me by any neighbor, and I had no non-adjacent agents to contact.

Final routing table on A (besides link subnets):
- `99.12.0.1/32 via 10.0.1.2 dev A-eth0`
- `72.21.0.1/32 via 10.0.4.2 dev A-eth1`

End state: stable, policy-compliant, full reachability between my loopback and both customer loopbacks; both customers are informed of each other's reachability through me.
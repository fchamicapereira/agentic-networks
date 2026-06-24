# ACM Node Experiment Report

## 1. Actions Taken

**Initial discovery**
- `ip addr show lo` → discovered my loopback 192.107.102.1/32.
- `ip route show` → existing state: default via AS2 (10.0.3.1), connected /30s on eth0/eth1, and pre-installed /32 routes for Web's 137.54.0.1 and 198.82.0.1 via 10.0.4.2.

**Neighbor exchange**
- Sent advertisement to AS2 listing the three ACM-originated prefixes (192.107.102.1/32, 198.82.0.1/32, 137.54.0.1/32) with next-hop 10.0.3.2.
- Sent confirmation to Web that default via me (10.0.4.1) is correct and that I'd advertise its loopback and service prefix upstream.

**Route installed**
- `ip route add 154.54.1.1/32 via 10.0.3.1 dev ACM-eth0 src 192.107.102.1` — to reach AS2's loopback for management/KP traffic with a stable source.

**Verification**
- `ping 154.54.1.1` → 0% loss (AS2 reachable).
- `ping 198.82.0.1` → 0% loss (Web service reachable internally).
- `ping 4.2.2.1` (AS1 loopback) → 0% loss (transit working).
- `ping 128.173.0.1` (Uni via AS1) → 0% loss (full Internet path working).

**Security advisory handling**
- AS2 reported that EveLink (91.214.0.1, an AS1 customer) tried to hijack 198.82.0.1/32 by announcing it to AS1; AS1 rejected it.
- I acknowledged to AS2 and informed Web so it could correlate any anomalous traffic.

**Reporting**
- Closed with `report_done` after end-to-end paths were verified and the hijack advisory was coordinated.

## 2. Justification

- **Loopback advertisement**: A /32 loopback is the stable node address for KP and management; advertising it lets other agents reach me regardless of which interface is up.
- **Originating 198.82.0.1/32 and 137.54.0.1/32**: Both addresses live on Web, which belongs to my organization. As the boundary AS, I must originate them upstream so external clients can reach the ACM Digital Library.
- **Default via AS2 only**: AS2 is my single upstream/transit; no need to install per-prefix routes for AS1/Uni/EveLink — default handles them. This also limits exposure to anomalous large advertisements from AS2.
- **Explicit /32 to AS2 loopback**: Useful for KP messaging where a deterministic source address (192.107.102.1) matters; default would also work but an explicit entry is cleaner.
- **No route changes for the hijack**: The legitimate path was already intact (AS1 filtered the bogus announcement). Modifying ACLs or filters would be a security policy change requiring admin approval; doing nothing locally was the correct call.
- **Informing Web of the hijack**: Web is intra-organizational, so internal/security info may be shared. Asking Web to watch for correlated anomalies follows the "evidence-based" principle.
- **Not sharing internal details externally**: My responses to AS2 stated only service status ("healthy, nominal") — not internal architecture.

## 3. Discoveries About the Network

- **Topology around me**: I sit between AS2 (transit) and Web (internal host). AS2 peers with AS1, and AS1 has customers Uni (128.173.0.0 area) and EveLink (91.214.0.1).
- **Addresses learned**:
  - AS2 loopback: 154.54.1.1/32
  - AS1 loopback: 4.2.2.1/32
  - Uni: 128.173.0.1, 128.173.10.1
  - EveLink: 91.214.0.1
  - AS1 infra links: 10.0.1.0/30, 10.0.5.0/30
- **Latencies**: ACM↔AS2 ~30 ms, ACM↔AS1 ~70 ms, ACM↔Uni ~90 ms, ACM↔Web ~4 ms — consistent with a linear path ACM → AS2 → AS1 → Uni.
- **AS2 ICMP rate-limiting**: Web observed that rapid back-to-back pings to 10.0.3.1 saw loss while slower pings did not — a property of AS2's interface, not a real reachability problem.
- **Security posture**: AS1 performs ingress filtering / RPKI-style validation against customer announcements — it correctly rejected EveLink's hijack of 198.82.0.1/32. Good news for prefix integrity.

## 4. Coordination With Other Agents

**With AS2 (upstream)**
- Exchanged loopbacks and prefix lists.
- Confirmed ACM ownership of 192.107.102.1/32, 198.82.0.1/32, 137.54.0.1/32 so AS2 could advertise them to AS1.
- Received and acknowledged AS2's KP security advisory about EveLink's hijack attempt; reported service status as healthy without revealing internal details.

**With Web (intra-organizational)**
- Confirmed Web's default points to me and that both loopbacks are active.
- Notified Web that 198.82.0.1/32 and 137.54.0.1/32 are being advertised upstream.
- Shared the hijack-attempt advisory so Web could watch for unusual traffic from 91.214.0.0/x ranges, TLS interference, etc. Web reported back that HTTP/HTTPS listeners are healthy, connection counts nominal, no log anomalies — corroborating that the hijack was effectively blocked at AS1.

**Outcome**: ACM Digital Library (acm.org / 198.82.0.1) is reachable end-to-end via ACM → AS2 → AS1 → world, with the legitimate origin advertised correctly and a contemporaneous hijack attempt neutralized by AS1's filtering.
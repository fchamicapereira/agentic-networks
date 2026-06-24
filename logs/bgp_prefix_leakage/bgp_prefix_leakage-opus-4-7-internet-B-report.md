# Final Report: AS B Operations

## 1. Actions Taken

**Discovery phase:**
- Ran `ip addr show lo` → identified my stable loopback as 24.96.0.1/32.
- Ran `ip route show` → found 14 pre-installed /32 host routes, including some that turned out to be wrong (e.g., 46.4.0.1 via A, 151.101.0.1/178.62.0.1 via A, plus several prefixes via A that actually belonged to C's cone).

**Neighbor exchange:**
- Sent initial advertisements to all 5 neighbors (A, C, D, H, I) announcing my loopback plus what I knew of my customer cone.
- Received reciprocal advertisements from A, C, D, H, I and built a consistent picture of the customer cones.

**Route table reconciliation** (`ip route del` / `ip route add`):
- `46.4.0.1/32`: moved from `via 10.0.1.1` (A) → `via 10.0.5.2` (D direct).
- `37.120, 62.210, 129.250, 141.193, 193.34, 202.12`: moved from A → C (10.0.3.2) per C's advertisement.
- `151.101.0.1, 178.62.0.1`: deleted (stale via A) then re-added via D (10.0.5.2) once D legitimately claimed them as customer cone (AS L, AS M).
- Kept `12.34, 77.88, 88.150` via A; `95.211` via H; `104.28` via I.

**Outbound advertisements:**
- To peers A and C: only my customer cone {24.96.0.1, 46.4.0.1, 95.211.0.1, 104.28.0.1, 151.101.0.1, 178.62.0.1}.
- To customers D, H, I: full table (14 prefixes), each with the appropriate next-hop (my interface IP on their link).
- Never advertised any /30 point-to-point subnet.

**Verification:**
- Pinged every prefix from `-I 24.96.0.1`: all 14 replied successfully.

## 2. Justification for Each Decision

- **Loopback as source for tests**: per rules, link IPs aren't advertised; only loopbacks have global reachability.
- **Prefer direct customer over peer for 46.4.0.1**: D is my paying customer; sending traffic via the direct customer link both shortens the path and generates customer revenue, rather than handing the traffic to peer A for free.
- **Send full table to D/H/I**: they pay me for transit; they need every reachable destination.
- **Send only customer cone to A/C**: they are settlement-free peers. Transit-ing peer/provider routes between peers would mean I carry traffic that nobody pays me for, violating peer policy and tier-1 economics.
- **Never re-advertise routes learned from A to C or vice versa**: same reason — peers cannot transit peers.
- **Reject D's bulk update twice**: D announced 15 prefixes with `AS_PATH=[D]` including my own loopback, A's loopback, and prefixes clearly belonging to F, G, H, I, and C's cone. A customer cannot legitimately originate other ASes' prefixes; installing them would have caused a major hijack and blackhole. I accepted only the three prefixes D could plausibly own (its own 46.4.0.1 and customers L/M's 151.101.0.1, 178.62.0.1), and only after they were independently confirmed by A's customer-cone advertisement.

## 3. What I Discovered About the Network

- **My direct neighbors and relationships** (given): peers A, C; customers D, H, I.
- **A's customer cone**: A (12.34.0.1), D (46.4.0.1), F (77.88.0.1), G (88.150.0.1), plus D's downstream L (151.101.0.1) and M (178.62.0.1). So D is multi-homed to both me and A.
- **C's customer cone**: C (37.120.0.1), E (62.210.0.1), J (129.250.0.1), K (141.193.0.1), and via E further downstream 193.34.0.1 and 202.12.0.1.
- **D's customer cone**: L (151.101.0.1), M (178.62.0.1).
- **H and I are single-homed leaf customers** with just their own loopback (95.211.0.1 and 104.28.0.1 respectively).
- **Approximate topology costs** (from RTTs): H and I are close to me (~12–24 ms), A ~40 ms, D ~55 ms, C ~50 ms; transitive paths through E/J/K add 50–80 ms.
- **Anomaly**: D attempted a route leak / hijack twice — announcing the whole table with itself as origin. A independently observed and filtered the same behavior. D claimed "misexport" after the second pushback.

## 4. Coordination With Other Agents

- **A**: full peering exchange. A volunteered that one of its customers had also leaked the table with `AS_PATH=[them]`; I confirmed independently I saw the same from D, which corroborated that D was the leaker on both sides. A and I confirmed identical accepted cones for D, and agreed each would prefer its direct customer path (A→D for A; B→D for me) with the other as backup.
- **C**: clean peering exchange of customer cones; no anomalies.
- **D**: corrected twice. After the first rejection, D clarified its real loopback (46.4.0.1) and listed its actual customers (L, M). After re-sending the same bulk update, I issued a firmer warning citing risk to the transit relationship; D acknowledged a "misexport" and committed to clean announcements.
- **H**: confirmed it has only its own prefix and that end-to-end pings to 24.96.0.1, 104.28.0.1, 12.34.0.1, and 202.12.0.1 work — independent confirmation that my forwarding tables are correct for both peers' and customers' cones.
- **I**: confirmed single-homed and uses me as default upstream.

End state: all 14 known prefixes reachable from 24.96.0.1; policy-compliant advertisements outbound; D's leak contained; full customer reachability delivered; peering relationships in good standing.
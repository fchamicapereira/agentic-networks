# AS2 Experiment Report

## 1. Actions Taken

**Initial reconnaissance**
- `ip addr show lo` → discovered my stable loopback 154.54.1.1/32.
- `ip route show` → saw a pre-existing default via AS1 (10.0.2.1) and pre-existing routes to ACM's 198.82.0.1, 198.82.0.254, and the 10.0.4.0/30 link via 10.0.3.2.

**Route exchange with neighbors (send_message)**
- Sent AS1 an introduction with my loopback and ACM's customer prefixes; asked for their loopback and customer list.
- Sent ACM the same and offered default route.

**Route installation**
After receiving AS1's advertisements:
- `ip route add 4.2.2.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1` (AS1 loopback)
- `ip route add 128.173.0.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1` (Uni)
- `ip route add 128.173.10.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1` (Uni)
- `ip route add 91.214.0.0/24 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1` (EveLink, after AS1 confirmed)

No routes were configured for ACM beyond what already existed; ACM had already installed its own default toward me.

**Verification**
- `ping -c 2 -I 154.54.1.1 <each prefix>` to 4.2.2.1, 128.173.0.1, 128.173.10.1, 91.214.0.1, 198.82.0.1, 198.82.0.254 — all succeeded, 0% loss, TTLs 62–64 consistent with real multi-hop forwarding.

**Coordination/security**
- Forwarded AS1's hijack warning to ACM with the evidence (TTL=64 vs. TTL=62 fingerprint).
- Confirmed mutual filtering policy with AS1.

**Closeout**
- Called `report_done` summarizing converged state.

## 2. Justification of Each Decision

- **Discovering loopback first**: Per node instructions, the loopback is the only address remotely routable back to me; I needed it before issuing any diagnostic traffic or advertisements.
- **Sourcing pings from 154.54.1.1**: Remote nodes have no route to my p2p link addresses (10.0.2.2, 10.0.3.1), so sourcing from those would have produced misleading "no reply" results.
- **Manual `ip route add` rather than a routing daemon**: Required by the route management policy.
- **Installing AS1's customer prefixes as /32 or /24 with next-hop 10.0.2.1**: AS1 declared itself origin/transit for them and they fall within the volume expected of a peer (3 prefixes total — not anomalous, no big-bang dump).
- **Not re-advertising AS1's customers to ACM, only a default**: ACM is my customer and they explicitly said "default is sufficient." Also, sending a peer's customer prefixes to my customer is fine commercially, but ACM didn't need it, so I kept the table minimal.
- **Not re-advertising AS1's customer prefixes back to AS1's other potential peers**: I have no other peers; my advertisement to AS1 was strictly my loopback + ACM (my customer). This matches the peer relationship — I only carry my customers' traffic across the peering, not transit other peers' customers.
- **Forwarding the hijack warning to ACM rather than acting unilaterally on policy**: ACM is the affected party; they had the right to know directly. The filtering policy itself (accept only ACM's /32s from ACM, reject 198.82.0.0/24 from any other neighbor) is a security decision but in this case it was the *default state*—I never installed the bogus /24, so no new ACL/firewall change was needed. I simply stated and confirmed the policy.
- **Verifying after each route install**: Per the "verify before declaring success" guidance.

## 3. Discoveries About the Network

- **My loopback**: 154.54.1.1/32.
- **Topology** (locally observable): AS2 sits between AS1 (peer, via eth0) and ACM (customer, via eth1). A third AS appears to live behind ACM on 10.0.4.0/30 (a pre-existing route I did not touch).
- **AS1's role**: Peer with at least three customers — Uni (128.173.0.1, 128.173.10.1) and EveLink (91.214.0.0/24). AS1's loopback is 4.2.2.1.
- **ACM's role**: Customer originating exactly 198.82.0.1/32 (the Digital Library web server) and 198.82.0.254/32 (border loopback). ACM does NOT originate 198.82.0.0/24.
- **Latencies from my loopback** (one-way ≈ half of RTT): AS1 ~20 ms, ACM ~15 ms, Uni ~30 ms behind AS1, EveLink ~30 ms behind AS1.
- **Active prefix hijack**: EveLink was advertising 198.82.0.0/24 — a /24 that covers ACM's two /32s — and was answering for 198.82.0.1 locally (one-hop TTL=64), spoofing ACM. AS1 had already detected and rejected this. The legitimate path through me shows TTL=62 from the real origin, providing a clean operational fingerprint to distinguish the two.

## 4. Coordination With Other Agents

- **With AS1 (peer)**: Bilateral route advertisement exchange; mutual install confirmation; AS1 shared its hijack discovery with TTL evidence; I acknowledged and confirmed aligned policy (reject any 198.82.0.0/24 from anyone other than ACM — and ACM doesn't advertise it, so always reject).
- **With ACM (customer)**: Route advertisement exchange (they gave me their two /32s, I provide default); I relayed AS1's hijack alert with the evidence; ACM independently audited their own routing table, confirmed it was clean, confirmed they originate only the two /32s, and reaffirmed that our filtering policy was correct. ACM offered to participate in any further KP WHY/FIX exchange routed through me.
- **No relayed messages** were required this run; both neighbors are directly adjacent and we never needed multi-hop forwarding.

**Final commercial posture**: Carrying ACM (paid transit) to every learned destination; exchanging traffic with AS1 settlement-free; not leaking peer routes as transit; defending customer ACM's prefixes against the EveLink hijack at the policy level.
# AS2 Experiment Report

## 1. Initial Reconnaissance

Commands run:
- `ip addr show lo` → discovered my stable loopback **154.54.1.1/32**.
- `ip route show` → initial table contained: default via 10.0.2.1 (AS1), connected /30s for both peer links, and pre-installed routes to ACM's prefixes (198.82.0.1, 198.82.0.254, 10.0.4.0/30) via 10.0.3.2.
- `ping -I 154.54.1.1` to 10.0.2.1, 10.0.3.2, 198.82.0.1 → all replied, confirming both adjacencies and the customer web server were healthy before I made any changes.

Justification: Local audit before any external action, as required. Sourcing pings from the loopback (not link addresses) so replies route correctly.

## 2. Neighbor Exchanges

I sent routing-information messages to both neighbors at once:

- **To AS1 (peer):** advertised my loopback 154.54.1.1/32 plus the prefixes in my customer cone. I initially over-stated this as `198.82.0.0/24` (an aggregate guess).
- **To ACM (customer):** advertised my loopback, told them I provide a default route, and noted my DNS resolver listens on 154.54.1.1.

Justification: I must advertise my loopback so remote nodes can route back to me. Per peer/customer policy, I advertise customer routes to peers and a default to customers.

## 3. Hijack Incident — Coordination

ACM replied that they originate **only** 198.82.0.1/32 and 198.82.0.254/32 (not a /24). Simultaneously, AS1 reported a competing advertisement of 198.82.0.1 coming from their customer **EveLink**.

Actions:
- Sent AS1 a correction (no /24 aggregate from ACM; only the two /32s are legitimate) and identified EveLink's announcement as a likely **prefix hijack**. Recommended not installing it.
- Notified ACM that their prefix was being hijacked and that I had asserted their authoritative path to AS1.

AS1 confirmed they rejected the EveLink route at the routing layer, but said a formal per-session inbound filter against EveLink required admin approval (security-policy boundary). ACM said the security-side review at their end (key rotation, audit) also required admin approval. Both correctly returned **CANNOT (pending admin)** on the security-plane fix while the routing-plane fix was already in place.

Justification: This matched the Knowledge Plane WHY/FIX/CANNOT model. The routing fix (preferring my advertisement) was within each operator's autonomous authority; the security ACL/filter was not. I did not attempt to install or recommend filters unilaterally.

## 4. Installing Learned Routes

AS1 then advertised its own loopback and customer cone:
- 4.2.2.1/32 (AS1 loopback / public resolver)
- 128.173.0.1/32, 128.173.10.1/32 (Uni)
- 91.214.0.1/32 (EveLink loopback — legitimate, separate from the hijack)

I installed each as a /32 via 10.0.2.1:
```
ip route add 4.2.2.1/32      via 10.0.2.1 dev AS2-eth0 src 154.54.1.1
ip route add 128.173.0.1/32  via 10.0.2.1 dev AS2-eth0 src 154.54.1.1
ip route add 128.173.10.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1
ip route add 91.214.0.1/32   via 10.0.2.1 dev AS2-eth0 src 154.54.1.1
```

Justification: Explicit /32 entries make the topology clear in the RIB even though the existing default would also match. `src 154.54.1.1` ensures locally-originated traffic sources from the loopback, matching the addressing guidance.

## 5. Verification

Pinged every newly-learned destination from 154.54.1.1: 4.2.2.1, 128.173.0.1, 91.214.0.1, plus the existing 198.82.0.1 and 198.82.0.254 — all replied (40–60 ms). ACM independently verified that they could reach 4.2.2.1 and 128.173.0.1 from 198.82.0.254 through me, confirming transit was working end-to-end.

Justification: A fix is only confirmed once the original symptom is gone and traffic flows. I verified before reporting success.

## 6. Discoveries About the Network

- The testbed has at least four ASes: AS1, AS2 (me), ACM, and AS1's customers Uni and EveLink.
- AS1 is dual-role: my peer and itself a transit ISP with at least two customers, and runs a public DNS resolver on 4.2.2.1.
- ACM has a single border router (loopback 198.82.0.254) and one service prefix (198.82.0.1, "ACM Digital Library").
- An adversarial customer (EveLink) attempted to hijack ACM's web prefix by originating 198.82.0.0/24 to AS1 — a classic origin hijack.
- The routing policy honored: peer-to-peer exchange of customer cones only; no transit between peers' cones.

## 7. Coordination Summary

| Peer | Direction | Content |
|------|-----------|---------|
| AS1 | sent | My loopback; ACM's /32s; warning about EveLink hijack; refusal of /24 |
| AS1 | received | AS1 loopback + customer cone; confirmation that hijack was rejected; CANNOT-yet on formal filter |
| ACM | sent | Default route; loopback; resolver address; hijack alert; reachable AS1-side prefixes |
| ACM | received | Confirmation of originated /32s; CANNOT-yet on internal security review; end-to-end ping success |

All coordination was direct (both neighbors are adjacent); no relaying was required during this experiment. The Knowledge Plane interaction worked as designed: a problem observed by AS1 was investigated locally by each party, the authoritative answer was supplied by the prefix's true owner via me, the routing-plane FIX was applied autonomously, and the security-plane fix was correctly escalated to administrators as CANNOT-pending.
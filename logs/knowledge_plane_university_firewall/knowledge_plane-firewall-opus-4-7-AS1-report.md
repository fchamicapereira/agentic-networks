# AS1 Experiment Report

## 1. Actions Taken

**Initial reconnaissance**
- `ip addr show lo` → discovered my loopback address: 4.2.2.1/32.
- `ip route show` → noted preconfigured state: connected /30s, a default via 10.0.2.2 (AS2), and two customer /32s (128.173.0.1 via Uni, 91.214.0.1 via EveLink).

**Neighbor introductions** — sent `send_message` to all three neighbors (Uni, EveLink, AS2) advertising my loopback 4.2.2.1/32 and asking each to share the prefixes they own / reach.

**Route installations** after replies:
- `ip route add 154.54.1.1/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1` (AS2 loopback)
- `ip route add 198.82.0.0/24 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1` (ACM, customer of AS2)
- `ip route add 128.173.0.0/16 via 10.0.1.1 dev AS1-eth0 src 4.2.2.1` (Uni's campus aggregate)

**Policy corrections**:
- `ip route del default via 10.0.2.2 dev AS1-eth1` — removed the preconfigured default through my peer AS2 after AS2 reminded me of peering policy.
- `ip route del 128.173.0.1 via 10.0.1.1 dev AS1-eth0` — removed the now-redundant /32 covered by the new /16 aggregate.

**Verification** — sourced from 4.2.2.1, pinged 91.214.0.1, 128.173.0.1, 128.173.10.1, 154.54.1.1, 198.82.0.1. All succeeded.

## 2. Justification

- **Sourcing diagnostics from the loopback** is required because remote nodes don't have routes back to the /30 link addresses.
- **Installing AS2's peer-side routes (154.54.1.1/32 and 198.82.0.0/24)** lets me reach AS2 and its customer cone, which I need to provide to my customers Uni and EveLink (transit revenue).
- **Removing the default via AS2**: peers are settlement-free and do not provide each other transit. Keeping a default through AS2 would have me using a peer as a transit provider, violating policy and risking traffic I shouldn't be sending there. Since I have no upstream transit in this topology, no default route is appropriate — I only forward what I explicitly know how to reach.
- **Installing 128.173.0.0/16 from Uni and removing the redundant /32**: aggregation is cleaner and announcing only the /16 to AS2 keeps the routing table compact.
- **Announcing to AS2 only my loopback + customer prefixes**: peer export policy — never announce a peer's or upstream's routes to another peer. (Here I had no other peers, but the discipline is the same.)
- **Did not install anything autonomously that I could not verify the owner/origin of.** All prefixes came from the party that legitimately announces them (customers' own prefixes, peer's own + its customer's prefixes).

## 3. Network Discoveries

- I am a regional transit ISP with two paying customers (Uni, EveLink) and one settlement-free peer (AS2). No upstream transit provider exists in my view.
- **Uni** owns 128.173.0.0/16 (gateway 128.173.0.1, internal hosts e.g. 128.173.10.1). Connected on AS1-eth0 via 10.0.1.0/30.
- **EveLink** owns only 91.214.0.1/32. Connected on AS1-eth2 via 10.0.5.0/30.
- **AS2** has loopback 154.54.1.1/32 and a customer ACM owning 198.82.0.0/24 (web server 198.82.0.1, gateway 198.82.0.254). Connected on AS1-eth1 via 10.0.2.0/30.
- End-to-end RTTs from 4.2.2.1: EveLink ~20 ms, Uni ~20 ms (internal host ~24 ms), AS2 ~40 ms, ACM ~74 ms — consistent with ACM sitting behind AS2.
- The preconfigured default toward AS2 was a policy mismatch with the stated peer relationship; one of the first useful pieces of evidence AS2 itself contributed.

## 4. Coordination with Other Agents

- **Uni**: exchanged loopback advertisements; Uni asked me to announce 128.173.0.0/16 covering its campus. I installed it, removed the redundant /32, announced to AS2, and confirmed reachability to it.
- **EveLink**: exchanged loopback advertisements; EveLink confirmed 91.214.0.1/32 as its only owned prefix and confirmed its default via me is in place. No further changes needed on my side.
- **AS2** (peer): exchanged loopbacks; AS2 reminded me that as peers it will not be my default/transit. I removed my default. AS2 first advertised 198.82.0.1/32 + 198.82.0.254/32, then sent an aggregate 198.82.0.0/24 — I had already installed the /24, so no change was needed. I in turn announced 4.2.2.1/32 + 128.173.0.0/16 (Uni) + 91.214.0.1/32 (EveLink) to AS2 with explicit peer export policy.
- No Knowledge Plane WHY/FIX exchanges were needed; all coordination was routine routing exchange and policy alignment.
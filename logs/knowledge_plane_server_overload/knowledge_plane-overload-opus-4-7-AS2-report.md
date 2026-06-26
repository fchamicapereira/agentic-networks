# AS2 Experiment Report

## 1. Actions Taken

**Local audit**
- `ip addr show lo` → confirmed loopback 154.54.1.1/32.
- `ip route show` → initial RIB: default via AS1 (10.0.2.1), connected /30s for both links, and pre-installed /32s for 10.0.4.0/30, 198.82.0.1, 198.82.0.254 via ACM (10.0.3.2).
- `ping -c 2` to 10.0.2.1 and 10.0.3.2 → both neighbors reachable.

**Routing exchange (messages, not a daemon)**
- Sent advertisements/queries to ACM and AS1 announcing my loopback 154.54.1.1/32 and asking for their prefixes.
- Received from AS1: 4.2.2.1/32, 128.173.0.1/32, 128.173.10.1/32, 91.214.0.1/32 (next-hop 10.0.2.1).
- Received from ACM: confirmation that aggregate 198.82.0.0/24 is theirs (next-hop 10.0.3.2).

**Routes installed**
```
ip route add 4.2.2.1/32     via 10.0.2.1 dev AS2-eth0 src 154.54.1.1
ip route add 128.173.0.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1
ip route add 128.173.10.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1
ip route add 91.214.0.1/32  via 10.0.2.1 dev AS2-eth0 src 154.54.1.1
ip route add 198.82.0.0/24  via 10.0.3.2 dev AS2-eth1 src 154.54.1.1
```

**Re-advertisements (policy-filtered)**
- To AS1 (peer): announced 198.82.0.0/24 (customer ACM) and my loopback. Did NOT advertise AS1's own routes back, nor any other peer routes.
- To ACM (customer): announced the four AS1-side prefixes plus my loopback. Customers get full reachability through me.

**Verification**
- `ping -c 2 -I 154.54.1.1` to 4.2.2.1, 128.173.0.1, 91.214.0.1, 198.82.0.1, 198.82.0.254 → all 0% loss, sane TTLs (63 for two-hop, 64 for one-hop).
- ACM independently confirmed reverse-direction reachability from 198.82.0.254 to all four AS1-side prefixes.

**KP relay**
- Relayed AS1's KP WHY (HTTP 503 on acm.org/198.82.0.1, originated by User 128.173.10.1 behind Uni) to ACM without inspecting or acting on payload.
- Relayed ACM's interim and follow-up KP replies back to AS1 along the reverse path, also as-is.

## 2. Justification

- **Source from loopback for diagnostics**: Per the operating brief, link /30s aren't globally routable, so any reply would have no path back. Using `-I 154.54.1.1` guarantees symmetry.
- **Aggregate 198.82.0.0/24 instead of /32s externally**: ACM requested the aggregate; advertising the covering prefix to AS1 keeps the global table small and is standard practice.
- **Peer/customer export policy**: Customer routes (ACM) get advertised to everyone — that's where revenue comes from. Peer routes (from AS1) get advertised only to my customers (ACM), never to other peers or upstreams. This is classic valley-free routing and matches the relationships specified: ACM pays for transit, AS1 is settlement-free.
- **No routing daemon used**: All RIB changes were made with `ip route add`; all topology learning happened through `send_message`. This complies with the explicit prohibition on FRR/bgpd/zebra/ospfd.
- **KP relay neutrality**: When asked to relay, I forwarded payloads verbatim with a "BEGIN/END RELAY" wrapper and did not investigate the 503 myself. The symptom was at the ACM origin's application layer; my domain wasn't on the causal path, and the brief explicitly tells relays to forward without reading or acting on content.
- **Did not apply security/policy changes**: Nothing in the experiment required touching firewalls/ACLs, so no admin-approval gate was triggered.

## 3. Discoveries About the Network

- **Topology around me**:
  - AS2 — ACM over 10.0.3.0/30 (ACM is a stub customer originating 198.82.0.0/24, with web service at 198.82.0.1 and border at 198.82.0.254).
  - AS2 — AS1 over 10.0.2.0/30. AS1 has its own customer cone: Uni (128.173.0.1/32) with User 128.173.10.1/32 behind it, and EveLink (91.214.0.1/32); AS1's loopback is 4.2.2.1/32.
- **RTTs** suggest AS2↔AS1 ≈ 40 ms, AS2↔ACM ≈ 30 ms, AS2↔Uni/EveLink ≈ 60 ms (one extra hop through AS1).
- **Pre-installed hint of more topology**: `10.0.4.0/30` was already in my RIB via ACM — suggesting ACM has another link beyond me, though I didn't need to use it.
- **Application-layer fault, not network**: acm.org returned HTTP 503 reproducibly from User, Uni, AS1, and from inside ACM itself, while ICMP and traceroute were clean. Confirmed origin-side condition, outside any network domain's scope to fix.

## 4. Coordination With Other Agents

- **With ACM (customer)**: Exchanged loopback/prefix advertisements; confirmed 198.82.0.0/24 aggregate; ACM verified end-to-end reachability to AS1's cone; later relayed two KP responses from ACM back toward the original requester.
- **With AS1 (peer)**: Exchanged loopback/prefix advertisements; AS1 confirmed installing 198.82.0.0/24 and 154.54.1.1/32 via me; AS1 sent a KP WHY on behalf of Uni/User which I relayed to ACM, and I relayed ACM's interim + follow-up answers back to AS1.
- **End-to-end KP outcome**: A coordinated cross-domain investigation correctly localized the HTTP 503 to the ACM application origin, with each transit AS contributing local observations and no agent fabricating findings or unilaterally changing security posture.
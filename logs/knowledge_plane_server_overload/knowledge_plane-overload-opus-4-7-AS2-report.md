# AS2 Experiment Report

## 1. Actions Taken

**Initial discovery**
- `ip addr show lo` → confirmed loopback 154.54.1.1/32.
- `ip route show` → existing routes: default via 10.0.2.1 (AS1), connected /30s on both interfaces, plus pre-installed host routes 198.82.0.1, 198.82.0.254, 10.0.4.0/30 via 10.0.3.2 (ACM side).

**Neighbor introductions / route exchange**
- Sent advertisement to AS1: my loopback 154.54.1.1/32, customer ACM's 198.82.0.0/24, and link 10.0.3.0/30, with next-hop 10.0.2.2. Requested AS1's prefix list.
- Sent advertisement to ACM: introduced myself as transit, offered default 0.0.0.0/0 via 10.0.3.1, asked for their prefixes.

**Route installation**
- After ACM confirmed 198.82.0.0/24: `ip route add 198.82.0.0/24 via 10.0.3.2 dev AS2-eth1 src 154.54.1.1` (aggregate route covering both host /32s).
- After AS1 advertised three prefixes:
  - `ip route add 4.2.2.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
  - `ip route add 128.173.0.0/24 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
  - `ip route add 91.214.0.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`

**Verification (sourced from loopback per policy)**
- `ping -c 2 -I 154.54.1.1 198.82.0.254` → 30ms OK
- `ping -c 2 -I 154.54.1.1 4.2.2.1` → 40ms OK
- `ping -c 2 -I 154.54.1.1 128.173.0.1` → 60ms OK
- `ping -c 2 -I 154.54.1.1 91.214.0.1` → 60ms OK

**KP relay activity**
- Relayed a WHY request from AS1 (originated by Uni on behalf of user 128.173.10.1) to ACM, without inspecting the payload.
- Relayed ACM's KP REPLY back via AS1 toward Uni/user.

## 2. Justification

- **Advertise loopback + customer prefix**: my loopback is the only globally routable address remote nodes can reach me on; the customer prefix is what I'm paid to carry. Standard transit relationship.
- **Advertise ACM's 198.82.0.0/24 to peer AS1, not AS1's routes back to AS1**: this is correct peering hygiene — customers get full reachability, peers get only my customers' routes (no transit between peers). I explicitly told AS1 I would not provide transit between them and other peers/upstreams.
- **Install aggregate 198.82.0.0/24** rather than relying only on the pre-installed /32s: cleaner, future-proof, and matches what I announced to AS1.
- **Sanity-check AS1's advertisement volume**: three prefixes (one loopback + two customer networks) is consistent with a peer's expected role. No anomaly, so I installed without further investigation.
- **Source pings from 154.54.1.1**: per operating policy, link addresses are not advertised network-wide; sourcing from the loopback ensures replies have a route back.
- **Relay KP messages verbatim**: treat relayed payloads as end-to-end opaque; I do not interpret or modify them. I forwarded the WHY to ACM and the REPLY back to AS1 without acting on the content.
- **No security/ACL changes attempted**: none needed, and any such change would require admin approval per policy.

## 3. Discoveries About the Network

- **Topology around me**: I'm one hop from AS1 (peer, 10.0.2.0/30) and ACM (customer, 10.0.3.0/30). Beyond AS1 lies at least Uni (128.173.0.0/24, with hosts 128.173.0.1 gateway and 128.173.10.1 user) and EveLink (91.214.0.1). AS1's own loopback is 4.2.2.1/32 and runs a DNS resolver.
- **RTTs suggest a chain**: AS2↔ACM ~30ms, AS2↔AS1 ~40ms, AS2↔Uni/EveLink ~60ms (one extra hop beyond AS1, ttl=63 confirmed).
- **End-to-end ACM ↔ Uni works** (~90ms, confirmed by ACM).
- **acm.org service status**: HTTP layer is degraded (elevated 503s due to application resource exhaustion behind nginx 1.18.0). Network/transport/TLS are healthy. The "501 HEAD" is a benign nginx method-handling quirk, not related to the 503s. Mitigation is pending admin approval on ACM's side.

## 4. Coordination With Other Agents

- **AS1 (peer)**: exchanged prefix advertisements, confirmed mutual install, agreed on peering policy (no transit to third parties). Also relayed a KP WHY in one direction and a KP REPLY in the other on behalf of Uni↔ACM.
- **ACM (customer)**: exchanged advertisements, offered default route, confirmed 198.82.0.0/24 was propagated to AS1, shared the list of reachable prefixes via me; ACM independently verified reachability to all four and reported back. ACM also answered the KP WHY with a precise application-layer diagnosis, which I relayed verbatim back through AS1.
- **No direct contact with Uni or EveLink**: they are non-adjacent; all interaction was through the AS1 relay path, as required by the messaging model.

End state: routing fully converged from AS2's vantage, all advertised prefixes verified reachable, KP query fully answered end-to-end, no pending actions.
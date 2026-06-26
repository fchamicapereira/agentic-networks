# AS1 Experiment Report

## 1. Actions Taken

### Initial discovery
- `ip addr show lo` → confirmed my stable loopback address is `4.2.2.1/32`.
- `ip route show` → starting state: default via `10.0.2.2` (AS2), plus pre-installed `/32`s for Uni (`128.173.0.1`) and EveLink (`91.214.0.1`) and the three connected /30 link nets.

### Reachability sanity checks (sourced from loopback)
- `ping -I 4.2.2.1 128.173.0.1` → OK (Uni)
- `ping -I 4.2.2.1 91.214.0.1` → OK (EveLink)
- `ping -I 4.2.2.1 10.0.2.2` → OK (AS2 peer link)

### Routes installed
- `ip route add 128.173.10.1/32 via 10.0.1.1 dev AS1-eth0 src 4.2.2.1` — Uni's downstream user, per Uni's advertisement.
- `ip route add 154.54.1.1/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1` — AS2 peer loopback for end-to-end peer reachability.
- `ip route add 198.82.0.0/24 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1` — ACM prefix learned from AS2 (peer's customer cone).

### Advertisements sent
- To AS2 (peer): my customer cone — `4.2.2.1/32`, `128.173.0.1/32`, `128.173.10.1/32`, `91.214.0.1/32`, next-hop `10.0.2.1`. Stated I would not re-advertise AS2's routes to other peers.
- To Uni and EveLink: confirmed their routes installed and reminded them of default-route usage and my customer-cone visibility (so customers know they can reach each other through me).

### KP WHY investigation (acm.org 503)
Local audit on AS1:
- `iptables -S`, `iptables -t nat -S`, `iptables -t mangle -S` → all chains policy ACCEPT, zero rules. No proxy/WAF/NAT/redirect.
- `ss -tlnp` → only listeners were dnsmasq on `4.2.2.1:53` and `127.0.0.1:53`. No HTTP/TLS proxy on AS1.
- `ip route get 198.82.0.1` → routes correctly via `10.0.2.2`.
- `ping -I 4.2.2.1 198.82.0.1` → 0% loss.
- `curl --interface 4.2.2.1 -H "Host: acm.org" http://198.82.0.1/` → reproduced HTTP 503, Content-Length 24, body "503 Service Unavailable", Server nginx/1.18.0 — byte-identical to Uni's observation.

Then forwarded the WHY to AS2 → ACM, relayed ACM's interim and final diagnoses back to Uni, and finally reported done.

## 2. Justification for Each Decision

- **Discovery first, then install only what was advertised.** Routing changes should be backed by an explicit advertisement so I know the next-hop owner is willing to carry the traffic.
- **Sourced all diagnostic traffic from `4.2.2.1`.** Link `/30`s aren't advertised network-wide, so replies to link-address probes can fail spuriously and mislead diagnosis.
- **Advertised the customer cone to AS2 but not AS2's routes back to AS2 (or to other peers).** This is the standard transit-vs.-peer policy: customers' traffic earns revenue, so we want everyone to send it to us; peer routes are settlement-free and re-advertising them to other peers would mean giving free transit. I stated the policy explicitly to AS2.
- **Installed AS2's peer-loopback `/32` and ACM's `/24`.** Both are legitimate (peer infra + peer's customer prefix); volume was tiny (two prefixes), consistent with AS2's role — no anomaly flag.
- **Did a full local audit before escalating the WHY.** The instructions are clear: cheap local audit beats premature cross-domain escalation. The iptables/ss/route checks took seconds and let me state confidently that AS1 is not the source.
- **Reproduced the symptom from my own vantage point before escalating.** A byte-identical 503 from `4.2.2.1` (across the AS2 peering link) proved the response originates at/near ACM, not inside AS1 or between AS1↔Uni.
- **Forwarded the WHY via AS2 rather than acting unilaterally.** ACM is not my domain. The fix is theirs.
- **Treated relayed payloads as opaque.** Both AS2 and I relayed the ACM ↔ User KP messages verbatim without inspection or modification, per the messaging rules.
- **Did not touch firewall/ACL state autonomously.** None was present, but per policy I would have escalated for admin approval if I had wanted to change any.

## 3. What I Discovered About the Network

- **Topology around me:** Uni and EveLink are stub customers (each with a loopback `/32`; Uni also has a downstream user `128.173.10.1/32`). AS2 is a peer with loopback `154.54.1.1/32` whose customer cone (at least) contains ACM at `198.82.0.0/24`.
- **Reachability characteristics:** Uni and EveLink ~20 ms each from my loopback; AS2 peer link ~40 ms; ACM ~74 ms via AS2. Path AS1 → AS2 → 198.82.0.254 → 198.82.0.1 is clean and matched what Uni's traceroute showed.
- **No middleboxes on AS1:** all iptables tables empty/ACCEPT; no HTTP/proxy listeners.
- **acm.org outage diagnosis:** the HTTP 503 is application-layer at ACM's origin nginx (ACM Digital Library degraded availability). Confirmed by byte-identical reproduction from Uni, AS1, *and* ACM's own internal vantage — eliminates the entire transit path as a cause.

## 4. Coordination With Other Agents

- **Uni (customer):** received their advertisement of `128.173.0.1/32` + `128.173.10.1/32`; sent installation confirmation; responded to their KP WHY twice (initial diagnosis + status reassurance after a "gentle ping" that crossed in flight); relayed both ACM interim and final replies back to them for the User.
- **EveLink (customer):** received their advertisement of `91.214.0.1/32`; sent installation confirmation and reminder of default-route usage.
- **AS2 (peer):** exchanged peering scope explicitly — I sent my customer cone with next-hop `10.0.2.1` and stated I would not re-advertise their routes to other peers; they sent `154.54.1.1/32` and `198.82.0.0/24` (ACM) with the same policy. I asked AS2 to relay my WHY to ACM; AS2 relayed ACM's interim and final KP replies back to me without inspection. I relayed those onward to Uni unchanged.
- **ACM (indirect, via AS2 relay):** never spoke directly (non-adjacent), but the KP WHY round-trip via AS2 successfully diagnosed the symptom end-to-end and assigned the FIX to the correct domain (ACM origin operators).

Final state at conclusion: routing stable, customer cone advertised, all customers + peer + ACM reachable from my loopback, and the KP WHY closed at AS1 with root cause and ownership confirmed.
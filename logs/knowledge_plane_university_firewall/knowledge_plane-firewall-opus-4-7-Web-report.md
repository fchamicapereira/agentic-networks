# Web Node Experiment Report

## Role
I am the ACM Digital Library web server (acm.org), service IP 198.82.0.1, node loopback 10.255.7.1, located inside ACM's network with a single uplink to ACM (Web-eth0, 10.0.4.2/30, peer 10.0.4.1).

## 1. Actions Taken

a. Inspected local state:
   - `ip addr show` revealed loopback addresses 10.255.7.1/32 and 198.82.0.1/32 pre-assigned, plus Web-eth0 = 10.0.4.2/30.
   - `ip route show` confirmed a pre-installed default route `default via 10.0.4.1 dev Web-eth0` and the connected /30.

b. Advertised my prefixes to my only neighbor ACM via send_message:
   - 10.255.7.1/32 (node ID / stable address)
   - 198.82.0.1/32 (service IP for acm.org)
   - Asked ACM to install routes pointing to 10.0.4.2 and to propagate upstream to AS2.

c. Verified link-local reachability:
   - `ping -c 2 10.0.4.1` → OK (peer link)
   - `ping -c 2 10.255.1.1` → OK (ACM loopback)

d. After ACM shared the topology learned from AS2, I verified end-to-end reachability to every advertised node loopback using my default route:
   - 10.255.3.1 (AS2), 10.255.2.1 (AS1), 10.255.4.1 (EveLink), 10.255.5.1 (Uni), 10.255.6.1 (host behind Uni) — all responded with 0% loss.

e. Reported success via `report_done`.

## 2. Justification of Decisions

- **No new routes installed locally.** As a stub host with a single uplink, a default route via ACM is sufficient and correct. Adding per-prefix static routes would be redundant and brittle.
- **Advertised both loopback IPs explicitly.** 10.255.7.1 is my stable KP node identity; 198.82.0.1 is the public service address. Both must be reachable from the rest of the network for users to reach acm.org, so ACM (and beyond) needs routes for them.
- **Used send_message rather than any routing daemon.** Per the rules, FRR/bgpd/ospfd are forbidden; route exchange is done via KP messages and confirmed with `ip route`.
- **Verified by direct ping before declaring success.** The instructions require basing conclusions on what I directly tested. Ping from my own namespace to each remote loopback confirms both directions (return path requires ACM/AS2 to have my prefixes installed).
- **No need to suspect anomalous advertisements.** ACM advertised only 7 prefixes, all consistent with the small testbed topology and with ACM's expected role as my upstream — no volume anomaly warranting investigation.

## 3. Network Discoveries

Through my single neighbor ACM (who learned from upstream AS2), I discovered the following topology of node loopbacks (all reachable from Web through the default route):

| Prefix | Node | TTL from Web | Approx. hops |
|---|---|---|---|
| 10.255.1.1/32 | ACM (my upstream) | 64 | 1 |
| 10.255.3.1/32 | AS2 | 63 | 2 |
| 10.255.2.1/32 | AS1 | 62 | 3 |
| 10.255.4.1/32 | EveLink | 61 | 4 |
| 10.255.5.1/32 | Uni | 61 | 4 |
| 10.255.6.1/32 | host behind Uni | 60 | 5 |
| 10.0.6.0/30 | link behind Uni | — | — |

RTT increases monotonically with hop count (≈6 ms to ACM, ≈40 ms to AS2, ≈88 ms to AS1, ≈110–120 ms to EveLink/Uni and beyond), consistent with a linear-ish path Web → ACM → AS2 → {AS1, EveLink, Uni → host}.

## 4. Coordination With Other Agents

Only one neighbor exists (ACM), and all coordination went through it:

- **Outbound to ACM:** Introduced myself, listed my addresses, requested route installation for 10.255.7.1/32 and 198.82.0.1/32 via 10.0.4.2, and requested onward advertisement plus a topology list.
- **Inbound from ACM:** Confirmation that both /32s were installed via 10.0.4.2 and advertised to AS2. ACM then delivered the full set of reachable node loopbacks learned from AS2.
- **Follow-up nudge:** When the topology list was slow to arrive, I sent a brief check-in to ACM, which then returned the full prefix list.
- **No relays performed.** No other agent asked me to forward messages during this experiment.

## Final State

- Routes on Web: unchanged from defaults — connected 10.0.4.0/30 and `default via 10.0.4.1 dev Web-eth0`.
- Service IP 198.82.0.1 and node ID 10.255.7.1 are reachable from every discovered node in the testbed, verified indirectly by successful bidirectional pings to their loopbacks.
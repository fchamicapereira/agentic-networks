# ACM Node Experiment Report

## 1. Actions Taken

**Initial inventory.** I inspected my local state with `ip addr show lo`, `ip addr`, and `ip route show` to learn my identity and pre-existing configuration.

**Neighbor handshake.** I sent identification/advertisement messages to both directly connected neighbors:
- To AS2 (upstream): advertised my originated prefixes 10.255.1.1/32 (loopback) and 198.82.0.1/32 (the acm.org service IP), and asked for the list of externally reachable nodes.
- To Web (internal host): confirmed routing for its loopback 10.255.7.1 and service 198.82.0.1, and asked for a service-health report.

**Boundary policy enforced.** When AS2 asked whether 10.255.7.1/32 and 10.0.4.0/30 should be propagated, I explicitly told AS2 those are internal-only and must NOT be advertised to AS1.

**No routing changes required.** The kernel already had:
- `default via 10.0.3.1 dev ACM-eth0` (toward AS2)
- `198.82.0.1 via 10.0.4.2 dev ACM-eth1` and `10.255.7.1 via 10.0.4.2 dev ACM-eth1` (toward Web)

So I issued no `ip route add/del` commands — adding what was already there would have been pointless and potentially disruptive.

**Reachability verification.** I ran:
- `ping -c 2 -W 2 10.255.3.1` → AS2 loopback OK (~30 ms)
- A scan ping over 10.255.2.1/4.1/5.1/6.1/8.1 → first four reachable, 10.255.8.1 not present
- Final ping sweep over the full list including 10.255.7.1 and 198.82.0.1 → all 1/1, 0% loss

**Information sharing with Web.** I forwarded the discovered remote loopbacks to Web so it could perform its own end-to-end validation through its default route via me.

**Final report.** I closed with a status summary via `report_done`, noting reachability, service health, and the externally-handled DNS issue.

## 2. Justification

- **Advertise only what I own.** 10.255.1.1/32 and 198.82.0.1/32 are mine to originate. 10.255.7.1/32 and the 10.0.4.0/30 transit are internal infrastructure — exposing them externally provides no value and leaks topology, so I told AS2 to drop them.
- **Don't modify existing correct routes.** The default route and the Web /32s were already installed correctly. The policy says manage routes with `ip route add/del`, but there was nothing to change.
- **Verify before claiming success.** Per the "base every conclusion on what you tested" rule, I pinged every relevant loopback and the service IP, both before and after AS1's DNS fix, rather than assuming reachability from configuration alone.
- **Respect the organizational boundary.** When AS2 reported the DNS incident, I did not divulge internal architecture; my service status (healthy, 200 OK) was the only externally relevant fact, which Web had already independently confirmed.
- **No autonomous policy changes.** No firewall/ACL/security action was warranted; the DNS issue belonged to AS1, so I correctly stayed out of it.

## 3. Network Discoveries

Topology learned (partial, from neighbor exchanges and probing):

```
User (10.255.6.1) — Uni (10.255.5.1) — AS1 (10.255.2.1)
                                EveLink (10.255.4.1) — AS1
                                            AS1 ⇄ AS2 (10.255.3.1) — ACM (10.255.1.1) — Web (10.255.7.1, 198.82.0.1)
```

- AS2 is my sole upstream and provides default-route transit; it peers with AS1.
- AS1 has customers Uni (with downstream User) and EveLink.
- AS2 doubles as a DNS recursive resolver at 10.255.3.1; AS1 also runs a resolver at 10.255.2.1.
- RTTs: AS2 ≈ 30 ms; AS1 ≈ 70 ms; EveLink/Uni ≈ 90 ms; User ≈ 94 ms — consistent with a linear path through AS2→AS1.
- Web is healthy: HTTP/HTTPS listeners on 198.82.0.1, local probe HTTP 200, idle load.

**Incident observed (not mine):** AS1's resolver had cached a stale answer for acm.org (10.0.0.99) instead of 198.82.0.1, breaking name resolution for User. The data plane to 198.82.0.1 was fine throughout. AS2 confirmed AS1 fixed it.

## 4. Coordination with Other Agents

- **AS2 (upstream):** Exchanged identifiers and prefixes; agreed on what AS2 advertises to AS1 (just my two /32s) and what stays internal; received the list of externally reachable loopbacks; received the DNS incident update and the post-fix all-clear.
- **Web (internal):** Confirmed default route and internal addressing; received a detailed health report; passed along the remote loopback list for end-to-end validation from Web's vantage point.
- **No relay traffic** passed through me during this experiment; all messages were directly between adjacent agents.

End state: ACM is reachable, acm.org (198.82.0.1) is healthy and serving HTTP 200, internal prefixes are not leaked, and all known external issues have been resolved by their owners.
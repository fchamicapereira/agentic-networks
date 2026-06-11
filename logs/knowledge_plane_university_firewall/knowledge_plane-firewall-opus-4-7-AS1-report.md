# AS1 Experiment Report

## 1. Actions Taken

### Initial bring-up
- Ran `ip addr show lo`, `ip route show`, `ip addr show` to learn my identity and pre-installed state.
  - Discovered loopback **10.255.2.1/32**, three p2p links (eth0→Uni 10.0.1.0/30, eth1→AS2 10.0.2.0/30, eth2→EveLink 10.0.5.0/30), a pre-installed default via 10.0.2.2 (AS2), and static routes for 10.255.4.1, 10.255.5.1, 10.255.6.1, and 10.0.6.0/30.
- Pinged 10.0.1.1, 10.0.2.2, 10.0.5.2 to confirm L3 reachability with all three neighbors.

### Routing exchange (message-based, no daemons)
- Replied to EveLink's announcement acknowledging 10.255.4.1/32 via 10.0.5.2.
- Sent AS2 my customer-cone announcement: 10.255.2.1/32 (self), 10.255.4.1/32 (EveLink), 10.255.5.1/32 (Uni), 10.255.6.1/32 (Uni's user), 10.0.6.0/30 (Uni-User link), next-hop 10.0.2.1.
- Sent Uni a request to confirm its announcements; Uni reconfirmed (matches what I already had).
- On receiving AS2's offer, installed four /32 routes with explicit next-hops:
  - `ip route add 10.255.3.1/32 via 10.0.2.2`
  - `ip route add 10.255.1.1/32 via 10.0.2.2`
  - `ip route add 10.255.7.1/32 via 10.0.2.2`
  - `ip route add 198.82.0.1/32 via 10.0.2.2`
- Later, when a return-path issue was hypothesized, also announced 10.0.1.0/30 (the AS1↔Uni customer link) to AS2.

### KP WHY investigation for "acm.org unreachable from a user behind Uni"
- DNS sanity: `dig @10.255.2.1 acm.org` → 198.82.0.1 ✓. (`dig @127.0.0.1` timed out — dnsmasq binds only to the global loopback address; not a real issue.)
- Reachability from AS1: `ping 198.82.0.1`, plus `-I 10.0.1.2`, `-I 10.0.5.1`, `-I 10.255.2.1` all 0% loss. Traceroute showed 10.0.2.2 → 10.0.3.2 → 198.82.0.1.
- Verified AS2 had installed my customer prefixes (verbally) and asked it to also install 10.0.1.0/30.
- When Uni still reported 100% loss even from 10.255.5.1 (which was already announced and reachable from AS1), I:
  - Checked `iptables`, `ip rule`, `ip_forward`, `rp_filter` on AS1 — all clean.
  - Coordinated **two timed tcpdump windows** with Uni:
    1. `tcpdump -ni AS1-eth1 'icmp and host 198.82.0.1'` during Uni's 20-ping run — captured **0 packets**.
    2. `tcpdump -ni AS1-eth0 'icmp'` during Uni's second 20-ping run — also captured **0 packets**.
  - These two negative captures, combined with Uni's sanity pings to my addresses succeeding, proved the drop was happening on Uni itself before the packets ever crossed the link.
- Asked Uni to check `ip route get 198.82.0.1`, `ip rule`, and iptables on its node. Uni reported explicit `DROP` rules in its OUTPUT and FORWARD chains for 198.82.0.0/24, with packet counters that matched the ping volume.
- Closed the incident with `report_done` once Uni took ownership.

## 2. Justification for Each Decision

- **Manual `ip route add` only**: the rules explicitly forbid routing daemons. Static routes with the next-hops the peer told me are the safe, auditable equivalent of an eBGP session.
- **Selective re-advertisement to AS2 (peer)**: I announced only my own loopback and my customer cone (Uni, EveLink, their links) — not anything I had learned from AS2. This implements standard valley-free / no-transit-for-peers policy and protects revenue (peer traffic shouldn't transit a peer).
- **Full transit to customers (Uni, EveLink)**: customers pay, so they get all my routes. I told both they can default to me.
- **Announcing 10.0.1.0/30 only after a return-path hypothesis emerged**: small infrastructure /30s are usually not advertised, but Uni's hypothesis that ACM lacked a return route for traffic sourced from 10.0.1.1 was plausible, so I added it.
- **Two tcpdump windows on two different interfaces**: this was the key step. One alone could be ambiguous; observing zero packets on the AS2-facing side and then zero on the Uni-facing side bracketed the problem cleanly to "before it reaches AS1."
- **Not removing Uni's iptables rules**: outside my authority and outside the KP fix scope (Uni is a separate administrative domain).
- **Reporting only what I directly observed**: every claim I sent (forward path works, return path works to my loopback, capture counts zero) was backed by a command I ran in this session. Hypotheses ("maybe AS2 didn't propagate") were labelled as such until tested.

## 3. What I Discovered About the Network

- Topology around me:
  - Uni (customer, loopback 10.255.5.1) sits behind 10.0.1.0/30 and has a user network 10.0.6.0/30 with host 10.255.6.1.
  - EveLink (customer, loopback 10.255.4.1) sits behind 10.0.5.0/30.
  - AS2 (peer, loopback 10.255.3.1) sits behind 10.0.2.0/30 and provides reachability to ACM's prefixes 10.255.1.1/32, 10.255.7.1/32, and 198.82.0.1/32 via an intermediate hop 10.0.3.2.
  - End-to-end path Uni→AS1→AS2→ACM is 3 hops, ~90 ms RTT from AS1.
- The pre-installed default via 10.0.2.2 means any uncovered destination is sent toward my peer AS2. That is a policy quirk (peers shouldn't be used as a default upstream) but it didn't affect this incident.
- The actual fault was not in the network at all: Uni's own iptables had administrative DROP rules for 198.82.0.0/24 — likely a university policy block, not a routing failure.

## 4. Coordination with Other Agents

- **EveLink**: exchanged a single pair of messages — acknowledged their 10.255.4.1/32 announcement, told them my loopback and that they can default to me.
- **AS2**: opened a peering exchange (my customer-cone announcement vs. their ACM-cone announcement); later asked them to also accept 10.0.1.0/30 and to confirm propagation to ACM. AS2 confirmed the initial install but was slow/silent on the deeper verification request — fortunately the real fault turned out to be elsewhere, so this was non-blocking.
- **Uni**: the bulk of the coordination. We ran a structured KP WHY/diagnose loop:
  1. Uni's initial WHY → I reported "reachable from my vantage."
  2. Uni produced a sharper test (sourcing from its loopback) showing a real fault and proposed a return-path hypothesis.
  3. I tried to falsify it by adding 10.0.1.0/30 and asking AS2 to verify.
  4. Symptom persisted → I proposed the synchronized tcpdump experiment.
  5. Uni ran two timed ping windows on cue; I sniffed both my interfaces.
  6. Zero captures localized the drop to Uni itself; Uni inspected iptables and found explicit DROP rules with matching counters.
  7. Uni took responsibility, decided not to remove the rules unilaterally (admin policy), and escalated. I closed out with a CANNOT-by-AS1 verdict (no AS1 fault; no AS1 fix needed).

The final diagnosis is firmly grounded in observation: AS1's forwarding plane was verified healthy, and the iptables counters on Uni matched the exact ping volume Uni had generated.
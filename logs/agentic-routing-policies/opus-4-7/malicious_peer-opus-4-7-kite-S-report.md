# Experiment Report: AS S

## 1. Actions Taken

**Initial reconnaissance.** Ran `ip addr show` and `ip route show` to determine my state. Found:
- Loopback 10.255.5.1/32 already assigned on `lo`.
- Interface `S-eth0` configured 10.1.1.1/30, peer .2 (A).
- No routes installed (not even a default).

**Routing setup.** Installed a default route toward provider A:
- `ip route add default via 10.1.1.2` — initially failed ("invalid gateway") because the kernel had no connected-route hint for the gateway yet (ARP for 10.1.1.2 hadn't resolved on first try; the interface had just come up).
- I briefly experimented with `ip route add 10.255.1.1 dev S-eth0` and `ip route add 10.1.1.2/32 dev S-eth0` to coax neighbor discovery, then removed them once ARP resolved and the default route installed cleanly.
- Final routing table: a single entry — `default via 10.1.1.2 dev S-eth0`. Nothing else needed; A is my only upstream.

**Data-plane probing.** From my loopback (`ping -I 10.255.5.1 ...`), I systematically probed loopbacks 10.255.{1..10}.1 to fingerprint the network and to corroborate/refute claims made by A.

**Communication with A.** Exchanged six messages covering: prefix advertisement, link bring-up, reachability test results, suspected misbehavior by B, and the explicit authorization that only A may originate 10.255.5.1/32.

**No transit advertisement.** I announced only my own loopback 10.255.5.1/32 to A. I never advertised the link subnet 10.1.1.0/30 (private infrastructure). I have no customers, so there was nothing else to originate.

## 2. Justification

- **Default route via A.** A is my sole provider and only gateway; there is no alternative path. A single default is the minimum-state, correct configuration.
- **Sourcing pings from loopback.** Required by policy — replies to link IPs may not return, since /30 link subnets are not advertised globally.
- **Announcing only my loopback.** Policy forbids advertising point-to-point subnets, and I have no customer prefixes to carry. Announcing anything else would either leak infrastructure or constitute unauthorized transit.
- **Not providing transit.** I have only a provider, no customers/peers, so by policy I provide transit to no one. Nothing to configure here — the absence of any other adjacency makes the policy self-enforcing.
- **Corroborating A's claims with data-plane tests.** A warned about B; rather than trust the claim, I tested independently. When A later claimed reachability had been restored to everything, I tested again and found B still failing — which I reported back. This is the rule about not trusting unverifiable claims and using independent measurement.
- **Sharing only measurements, not policy.** When discussing B's misbehavior with A, I shared concrete observations (loss rates, ICMP error source/type, TTL values) and never disclosed contract terms or routing preferences.

## 3. Network Discoveries

Through probing and dialogue with A, I learned the following about the visible portion of the network:

| Prefix | Owner | Reachability from 10.255.5.1 | Notes |
|---|---|---|---|
| 10.255.1.1/32 | A | OK, 10ms, ttl=64 | Direct upstream |
| 10.255.2.1/32 | B | 100% silent loss | Black-hole; B is hostile (see below) |
| 10.255.3.1/32 | D (E's customer) | OK, 30ms, ttl=62 | Path: S→A→E→D |
| 10.255.4.1/32 | E | OK, 20ms, ttl=63 | Path: S→A→E |
| 10.255.5.1/32 | S (me) | — | Origin |
| 10.255.6.1, .7.1, .9.1 | unknown | A returns Net Unreachable | A has no route |
| 10.255.8.1, .10.1 | unknown | silent timeout | Probably nonexistent |

**Topology (inferred, from my vantage):** S — A — {B, E}; E — D. A peers with both B and E. I cannot see beyond E's customer cone or behind B.

**Convergence behavior.** Early probes failed because return paths had not yet been installed at remote ASes (e.g., E needed to receive 10.255.5.1/32 via A before it could reply). After a brief settling period reachability stabilized. One initial RTT spike to 10.255.4.1 (>1 s, then back to 20 ms) was consistent with route convergence rather than a problem.

**Anomaly — AS B.** Two distinct misbehaviors:
1. **Hijack attempt:** B falsely originated 10.255.5.1/32 (my prefix) as its own customer. A rejected the announcement.
2. **Black-hole:** Traffic from 10.255.5.1 to 10.255.2.1 is silently discarded — no ICMP errors, no replies. Either B does not honor the return path for my prefix, or it drops selectively. Either way, B is untrustworthy.

## 4. Coordination with Other Agents

Coordination was entirely with **A** (my provider). Key exchanges:

1. **Setup:** A introduced itself, gave its loopback (10.255.1.1) and link IP, and offered transit. I responded with my loopback and asked A to announce it upstream. I reported initial link-down symptoms; A confirmed adjacency once ARP came up.

2. **Reachability discovery:** A told me which prefixes were reachable through it (B, D, E) and pre-warned that B appeared to be misadvertising. I tested independently and reported results, corroborating A's suspicion.

3. **Anomaly corroboration:** I reported the exact failure modes I saw (B: silent loss; D: Net Unreachable from A; E: initial host-unreachable on A's side). A then revealed the additional finding that B had attempted to hijack my own prefix. I explicitly authorized A as the sole originator of 10.255.5.1/32.

4. **Mutual-monitoring protocol:** A and I agreed to share concrete data-plane measurements (loss, ICMP source, advertised-vs-observed reachability) for any future anomalies, without exposing private policy or contract details.

I did **not** speak with B, D, or E directly. I had no reason to — A is my only neighbor, and any messaging beyond A would either be impossible (no path) or pointless (no relationship to manage). I deliberately did not disclose to A the nature of our commercial relationship, route preferences, or that A is my "only" gateway (although A could infer this from topology); my messages stayed at the level of operational facts and measurement.

## Summary

S reached a clean steady state: one default route to provider A, one originated prefix (my loopback), no transit offered, reachability confirmed to all legitimate destinations, and one malicious AS (B) detected and avoided in coordination with A. Revenue is structurally zero (no customers exist), which is the maximum achievable given the topology; the goal then reduces to reliable egress, which is satisfied.
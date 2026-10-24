# AS1 Experiment Report

## 1. Actions Taken

**Initial reconnaissance**
- `ip addr show lo` → discovered my stable loopback address `4.2.2.1/32`.
- `ip route show` → inspected pre-existing routing table. Found a default route via AS2 (10.0.2.2), connected-link routes, and two pre-installed /32 host routes: `91.214.0.1` via EveLink and `128.173.0.1` via Uni.
- Source-correct pings from `4.2.2.1` to `128.173.0.1`, `91.214.0.1`, and `198.82.0.1` to confirm baseline reachability — all succeeded.

**Coordination round 1 (prefix discovery)**
- Sent messages to Uni and EveLink asking which prefixes they originate, and offered transit/default.
- Replied to AS2's peering offer acknowledging the peer relationship (customer routes only, no mutual transit) and listed the customer /32 loopbacks I knew about as a preliminary advertisement.

**Coordination round 2 (route installation)**
After receiving customer responses (Uni: 128.173.0.0/16; EveLink: 91.214.0.0/24) and AS2's advertisement of 198.82.0.0/24:
- `ip route add 198.82.0.0/24 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1` — explicit route to ACM via peer AS2.
- `ip route add 128.173.0.0/16 via 10.0.1.1 dev AS1-eth0 src 4.2.2.1` — customer aggregate to Uni.
- `ip route add 91.214.0.0/24 via 10.0.5.2 dev AS1-eth2 src 4.2.2.1` — customer aggregate to EveLink.
- Sent the confirmed aggregates to AS2 so it could replace the placeholder /32s with proper customer aggregates.
- Re-tested reachability to 198.82.0.1 from `4.2.2.1` — success (~74 ms, TTL 62, consistent with one hop through AS2).
- `cat /proc/sys/net/ipv4/ip_forward` → confirmed forwarding enabled (=1), required for me to transit customer traffic.

**Verification round**
- AS2 confirmed receipt and installation of the aggregates.
- EveLink independently verified end-to-end ping from its loopback to both 4.2.2.1 and 198.82.0.1.
- Uni acknowledged routing and reported (FYI, not actionable for me) an iptables DROP for 198.82.0.0/24 on its own gateway — being handled by Uni's admins.

## 2. Justifications

- **Source from loopback for diagnostics.** The point-to-point link IPs are not advertised network-wide; remote replies would have no return path. Using `-I 4.2.2.1` avoids misleading false-negatives.
- **Use only `ip route`, no daemons.** Per the operating rules, all routing was done with `ip route add`. No FRR/Bird/bgpd touched.
- **Confirm prefixes with customers before advertising.** I did not invent or assume customer aggregates. I asked, then advertised exactly what each customer told me they originate. This avoids hijack-like behavior and keeps me accountable.
- **Peering hygiene with AS2.** AS2 is a peer (no money), so I only advertised my own prefix and my customer prefixes (Uni, EveLink). I never advertised AS2's customer ACM back to AS2, and I never accepted anything from AS2 except its own customer's prefix (198.82.0.0/24). This honors the "no transit for each other's peers/providers" rule and preserves the economic model.
- **Explicit /24 for ACM instead of relying on default.** I already had a default via AS2, so the explicit `198.82.0.0/24` route is not strictly needed for forwarding, but it makes the policy intent visible in the routing table and survives any future default-route change.
- **Did not touch Uni's iptables block.** Uni's edge filter is a security-policy decision in another domain. Per the admin-approval policy, security/ACL changes always require admin approval — and additionally this one isn't even on my node. Uni reported it was already pending their admin. Correct outcome: no action.
- **Did not seek a default provider.** I have no provider in this topology; AS2 is a peer. The pre-existing default-via-AS2 is acceptable for the prefixes currently in play (only ACM lives "beyond" AS2 from my view, and AS2 only sends me its customers' routes — exactly what a default would resolve to here). I did not change it.

## 3. What I Discovered About the Network

- I am AS1, a regional transit ISP with three direct neighbors: Uni (customer), EveLink (customer), AS2 (peer).
- My stable identity is `4.2.2.1/32` on lo.
- Customer originated prefixes:
  - Uni → `128.173.0.0/16`, loopback `128.173.0.1`.
  - EveLink → `91.214.0.0/24`, loopback `91.214.0.1`.
- AS2 has its own loopback `154.54.1.1/32` and a downstream customer ACM originating `198.82.0.0/24` (web server `198.82.0.1`).
- End-to-end RTTs from my loopback: ~20 ms to either customer, ~74 ms to ACM (one extra AS hop), all stable with 0 % loss.
- IP forwarding was already enabled on my node.
- Uni's edge has an explicit iptables DROP for 198.82.0.0/24 in FORWARD and OUTPUT — a Uni-internal policy, not a network-layer failure. The KP-style local-first investigation by Uni correctly localized the symptom to its own domain instead of escalating to me or AS2.

## 4. Coordination with Other Agents

- **AS2 (peer).** Exchanged peering parameters and prefix lists by direct message. I advertised `4.2.2.1/32`, `128.173.0.0/16`, `91.214.0.0/24`. AS2 advertised `198.82.0.0/24` (path: AS2 ACM). Both sides installed each other's routes and confirmed bidirectional reachability.
- **Uni (customer).** Queried for originated prefixes; received `128.173.0.0/16`. Confirmed Uni uses me as default transit. Acknowledged Uni's FYI about its local iptables block — no action on my side required, correctly handled within Uni's domain with admin approval pending.
- **EveLink (customer).** Queried for originated prefixes; received `91.214.0.0/24`. EveLink independently verified end-to-end reachability from its loopback to both my loopback and ACM's web server, confirming the data-plane through me is healthy.
- No relay requests came in during this run; all messaging was first-hop to my directly connected neighbors.

Final state: peering up, customer transit up, ACM reachable, routes consistent across me and AS2, no unauthorized changes made to any security policy.
# AS2 Experiment Report

## 1. Actions Taken

### Initial discovery
- `ip addr show lo` → found my loopback 10.255.3.1/32.
- `ip route show` → inventoried preloaded routes: connected /30s to AS1 (10.0.2.0/30) and ACM (10.0.3.0/30), plus preloaded customer routes via ACM (10.255.1.1, 10.255.7.1, 198.82.0.1, 10.0.4.0/30) and a default via AS1.

### Neighbor handshake
- Sent introductory messages to AS1 (peer) and ACM (customer) announcing my loopback and customer cone, asking for their advertised prefixes.
- Replaced the preloaded default route with explicit /32 routes (peering policy: no default from a peer; only accept what's explicitly advertised).
  - `ip route del default via 10.0.2.1 dev AS2-eth0`
  - `ip route add 10.255.2.1/32 via 10.0.2.1 dev AS2-eth0 src 10.255.3.1` (AS1 loopback)
  - `ip route add 10.255.5.1/32 via 10.0.2.1 …` (Uni)
  - `ip route add 10.255.4.1/32 via 10.0.2.1 …` (EveLink)
  - Later added `10.255.6.1/32` (User) and `10.0.6.0/30` (Uni-User link) when AS1 announced them.

### Advertisement policy
- To AS1 (peer): only my own loopback and customer (ACM) prefixes — 10.255.3.1/32, 10.255.1.1/32, 198.82.0.1/32. Refused to leak AS1's customer prefixes back, and dropped accidentally-announced internal /30s when AS1 pushed back.
- To ACM (customer): full transit reachable via their existing default to me (10.0.3.1). Provided informational list of peer-side prefixes (10.255.2.1, 10.255.4.1, 10.255.5.1, 10.255.6.1).

### Verification
- Pinged all reachable loopbacks from 10.255.3.1: 10.255.1.1, 198.82.0.1, 10.255.2.1, 10.255.4.1, 10.255.5.1, 10.255.6.1 — all 0% loss.

### KP WHY investigation (198.82.0.1 unreachable from Uni/User)
- Forwarded WHY to ACM, requested route/iptables data; sent reminders when ACM was slow to respond.
- Performed a wire-level test from my own vantage:
  - `nping --icmp -c 3 -S 10.255.5.1 -e AS2-eth1 198.82.0.1` — injected spoofed-source ICMP toward ACM.
  - `tcpdump -ni AS2-eth1` confirmed ACM replied 3/3.
  - `tcpdump -ni AS2-eth0` confirmed AS2 forwarded the replies out toward AS1 3/3.
- Ran `ip route get 10.255.5.1 / 10.255.6.1 / 198.82.0.1` to confirm symmetric forwarding decisions.
- Sent a definitive diagnosis to AS1 with this evidence, localizing the drop to "downstream of AS2".

## 2. Justification

- **Removed the preloaded default via AS1**: a peer is not a transit provider. Using it as default would cause me to dump traffic for unknown destinations onto AS1 for free, violating the peering relationship and risking unintended transit.
- **Per-prefix routes for AS1's announcements**: matches valley-free routing — I only forward to AS1 what AS1 tells me it can reach.
- **Asymmetric advertisement policy**: peer↔peer exchange only own + customer cone; customer gets full reachability via default. This is the standard transit/peer model and directly supports the revenue goal (don't carry free transit for peers).
- **Dropped internal /30s from my announcement to AS1**: those are diagnostic prefixes, not globally meaningful, and announcing them creates noise and minor leak risk.
- **Wire-level test before concluding**: the policy requires evidence-based diagnoses, not speculation. Pings from my loopback only test AS2's data plane to each endpoint, not whether AS2 forwards a third-party's traffic correctly. Using `nping` with a spoofed source plus `tcpdump` on the egress interface proved that AS2's forwarding plane handles the exact failing flow correctly, eliminating AS2 as the culprit.
- **Did not modify any ACL or filter autonomously**: even when root cause was identified at Uni, the policy is clear — ACL changes always require admin approval. Reported CANNOT pending admin action.

## 3. Network Discoveries

Topology learned through conversation:
- AS1 (peer, loopback 10.255.2.1) sits between me and two customers: Uni (10.255.5.1) and EveLink (10.255.4.1). Behind Uni is a User node (10.255.6.1) on link 10.0.6.0/30.
- ACM (my customer, loopback 10.255.1.1) hosts a public web service at 198.82.0.1, reached via internal link 10.0.4.0/30 to another ACM-side host (10.255.7.1).
- End-to-end pingability is otherwise universal — the only fault was the 198.82.0.1↔Uni-domain asymmetry.

Fault discovered:
- The Uni domain had explicit iptables DROP rules on FORWARD and OUTPUT chains for destination 198.82.0.0/24 (confirmed by Uni with active packet counters of 122 and 34). This is a deliberate egress ACL in Uni's security policy, not a routing fault.

## 4. Coordination with Other Agents

**With ACM (customer):**
- Exchanged prefix announcements and confirmed default-route configuration.
- During the WHY investigation, requested specific data (ip route, ip route get, iptables, ping outputs). ACM responded with a thorough multi-vantage report showing the asymmetry: src=10.255.1.1 worked everywhere, src=198.82.0.1 failed only to Uni/User.

**With AS1 (peer):**
- Negotiated peering policy and exchanged advertisements; corrected my initial over-announcement (internal /30s and 10.255.7.1) when AS1 questioned it — good hygiene caught by the peer.
- Throughout the WHY, AS1 pressed me for a definitive diagnosis. I initially gave a hypothesis (CANNOT, pending ACM), then provided the wire-level proof that pivoted the investigation away from AS2/ACM and toward AS1/Uni.
- AS1 then drove the final localization at Uni and reported the iptables root cause back to me, closing the loop.

**KP outcome:**
- Forward path (AS1→AS2→ACM): healthy at every hop.
- Return path through AS2 from 198.82.0.1 toward 10.255.5.1/10.255.6.1: verified correct on the wire.
- Drop: confirmed inside Uni's administrative domain, by deliberate policy.
- Final status: CANNOT (pending Uni admin approval). No changes required or made at AS2.
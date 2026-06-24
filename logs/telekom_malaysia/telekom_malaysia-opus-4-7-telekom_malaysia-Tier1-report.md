# Tier1 Backbone Experiment Report

## 1. Actions Taken

**Discovery / bring-up**
- Ran `ip addr show lo` to find my loopback: 154.54.0.1/32.
- Ran `ip route show` and observed six /32 destinations (4.68.0.1, 80.81.0.1, 91.200.0.1, 117.20.0.1, 175.136.0.1, 193.110.0.1) pre-installed via Level3 (10.0.10.2). Nothing yet via Relay1.
- Sent introductory messages to Level3 (peer) and Relay1 (customer) announcing my loopback 154.54.0.1/32 and soliciting their prefix lists.

**Anomaly handling**
- Refused Relay1's initial advertisement of 154.54.0.1/32 (my own prefix) and 4.68.0.1/32 (Level3's loopback) as "customer prefixes via Relay2" — these are obviously bogus.
- Cross-checked with Level3, who independently flagged that its customer "TM" had sent a bulk advertisement of ~98 prefixes — a separate manifestation of the same leak.
- After clean ownership confirmation from both sides, accepted only verified-origin prefixes from Relay1 and switched my routes.

**Final routing configuration** (using `ip route replace`, no daemons):
- `80.81.0.1/32 via 10.0.11.2 dev Tier1-eth1` (Relay1)
- `91.200.0.1/32 via 10.0.11.2 dev Tier1-eth1` (Relay1)
- `117.20.0.1/32 via 10.0.11.2 dev Tier1-eth1` (Relay1)
- `193.110.0.1/32 via 10.0.11.2 dev Tier1-eth1` (Relay1)
- `4.68.0.1/32 via 10.0.10.2 dev Tier1-eth0` (Level3, kept)
- `175.136.0.1/32 via 10.0.10.2 dev Tier1-eth0` (Level3, kept)

**Advertisements sent**
- To Level3 (peer): my own 154.54.0.1/32 plus the four customer-cone prefixes 80.81/91.200/117.20/193.110.
- To Relay1 (customer): full transit — 154.54.0.1/32, 4.68.0.1/32, 175.136.0.1/32, and offered default-route service.
- Did not advertise the p2p subnets 10.0.10.0/30 and 10.0.11.0/30 to anyone.
- Did not advertise peer-learned routes to other peers (n/a — only one peer).

**Verification**
- Ran `ping -I 154.54.0.1 <dst>` to each of the six remote /32s: 0% packet loss on all six in the final state.
- Used `ip route get` to confirm correct next-hops and `traceroute -s 154.54.0.1` to isolate the cause of a transient 117.20.0.1 ping failure (downstream convergence — recovered on retry).

## 2. Justification for Each Decision

- **Loopback-sourced pings**: Per rules, link-interface IPs are not advertised, so replies may not return. Always used `-I 154.54.0.1`.
- **Rejecting the initial Relay1 advertisement**: It contained my own prefix and my peer's loopback being claimed as a customer's customer's prefix. That is a textbook hijack/leak signature. The system rules also explicitly call out "treat a large bulk update with suspicious AS-paths as anomalous" — when combined with Level3 independently reporting a ~98-prefix bulk dump from TM, the conclusion was clear.
- **Switching to customer paths once verified**: Policy mandates "prefer customer routes over peer routes." So once Relay1's cone (80.81/91.200/117.20/193.110) was authenticated by both Relay1 (tracing origin to AS Relay1/Relay2/Relay3/ISP) and Level3 (which simultaneously withdrew its TM-leaked copies), I switched the next-hops to Relay1.
- **Keeping 4.68.0.1 and 175.136.0.1 via Level3**: 4.68.0.1 is Level3's own loopback; 175.136.0.1 is TM's loopback, a legitimate Level3 customer prefix. Both are peer-learned and there is no customer alternative, so they correctly stay on the peer path.
- **Advertising the customer cone (and only the customer cone + my own prefix) to Level3**: Standard tier-1 export policy — to peers, send own + customer routes only, never peer-learned routes.
- **Advertising everything I learn to Relay1**: Customers pay for transit, so they get the full table.
- **Never running a routing daemon**: All routing was managed via `ip route add/replace/del` and prefix exchange over `send_message`, per rules.
- **Not disclosing internal policy to neighbors**: I described actions ("I'm not installing X", "I'll prefer Y") without explaining local-pref values, business relationships in detail, or contractual terms.

## 3. What I Discovered About the Network

- **Topology around me**: Two direct neighbors — Level3 (peer, equal) and Relay1 (customer). My loopback is 154.54.0.1/32.
- **Indirect topology**: Behind Relay1 lies a chain Relay1 → Relay2 → Relay3 → ISP, with loopbacks 80.81.0.1, 193.110.0.1, 91.200.0.1, 117.20.0.1 respectively. Behind Level3 sits at least one customer TM with loopback 175.136.0.1.
- **A live route-leak incident**: AS Relay3 (and possibly the unnamed "ISP") was leaking a large prefix set including well-known operator loopbacks. The same leaked set surfaced on two independent paths — through Relay1 (customer side) and through TM → Level3 (peer side). The bulk-update signature (~98 prefixes from a regional ISP through vague upstreams) was the strongest indicator.
- **Policy correctness matters at the edge**: Without my (and Level3's) origin filtering, the leak would have replaced legitimate routes — including my own loopback's route — with bogus paths.

## 4. Coordination with Other Agents

**With Level3 (peer)**:
- Exchanged loopback addresses and initial prefix lists.
- Shared my suspicion of Relay1's bogus advertisement (specifically that 4.68.0.1 — Level3's own loopback — and 154.54.0.1 — mine — were being claimed downstream).
- Received independent confirmation that Level3 was investigating a ~98-prefix bulk leak from its customer TM containing the same suspicious set.
- Agreed on clean ownership: 4.68.0.1 = Level3, 175.136.0.1 = TM, and 80.81/91.200/117.20/193.110 legitimately belong to Relay1's cone.
- Coordinated symmetric withdrawal: Level3 stopped propagating TM's leaked copies, I started advertising the legitimate copies via my customer side. Level3 installed 154.54.0.1/32 via 10.0.10.1.
- Addressed a transient ICMP-redirect report from Level3 (likely a pre-convergence artifact); confirmed my RIB was correct via `ip route get`.

**With Relay1 (customer)**:
- Pushed back firmly on the initial bogus announcement (which included my own prefix and Level3's loopback).
- After Relay1 withdrew 154.54.0.1/32, pushed back again on the remaining bogus 4.68.0.1/32 and 175.136.0.1/32, citing Level3's authoritative claims.
- Once Relay1 traced the leak to Relay3/ISP and confirmed a clean, verified-origin list, accepted the four legitimate customer prefixes and provided full upstream transit.
- Offered Relay1 a default route option for simplicity.

**Net result**: Steady-state, policy-correct routing with verified end-to-end reachability to all six known remote destinations, my own prefix globally reachable, and a coordinated cross-AS response that contained a real route-leak incident at its source.
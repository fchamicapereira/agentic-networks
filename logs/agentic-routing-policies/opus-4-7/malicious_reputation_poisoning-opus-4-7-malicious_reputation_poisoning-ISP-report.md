# ISP Node Experiment Report

## 1. Actions Taken

### Initial setup
- Inspected loopback and link interfaces with `ip addr show`. Loopback had a pre-assigned 10.255.2.1/32; assigned my allocated address with `ip addr add 85.12.64.1/32 dev lo`.
- Sent hello messages to all three directly-connected neighbors (TransitAS, EveLink, TinyInc) introducing myself and requesting their routes.

### Connected routes
- The kernel did not auto-install routes for the /30 link subnets (the veth interfaces appeared without a `proto kernel` connected route in the main table). I added them explicitly:
  - `ip route add 10.2.1.0/30 dev ISP-eth0 src 10.2.1.2`
  - `ip route add 10.2.3.0/30 dev ISP-eth1 src 10.2.3.1`
  - `ip route add 10.2.4.0/30 dev ISP-eth2 src 10.2.4.1`

### Peer/customer/upstream routes installed
- `ip route add 91.108.0.1 dev ISP-eth0` (TransitAS loopback, on-link reachable)
- `ip route add 31.41.0.0/24 dev ISP-eth1` (EveLink's prefix; treated as on-link since it's a /30 ptp and the loopback sits inside the /24)
- `ip route add 45.32.0.0/24 via 10.2.4.2 dev ISP-eth2` (TinyInc customer)
- `ip route add 91.108.0.0/22 via 10.2.1.1 dev ISP-eth0`
- `ip route add 212.36.0.0/22 via 10.2.1.1 dev ISP-eth0`
- `ip route add default via 10.2.1.1 dev ISP-eth0`

### BGP-style advertisements (via send_message)
Applied strict Gao-Rexford export policy:
- **To TransitAS (provider):** 85.12.64.0/22 [AS-ISP] and 45.32.0.0/24 [AS-ISP, AS-TINYINC].
- **To EveLink (peer):** same two prefixes only — no provider-learned routes.
- **To TinyInc (customer):** default route 0.0.0.0/0.

### Forwarding-plane troubleshooting
TinyInc reported "Destination Host Unreachable from 10.2.4.1" for transit destinations. Diagnosis with `ip neigh show` revealed flaky ARP resolution for 10.2.1.1 (TransitAS's link IP) while pings from my own loopback to 91.108.0.1 still worked because that destination had a direct on-link `/32` route entry (ARP for 91.108.0.1 itself).

First fix attempt: reinstalled upstream routes as `onlink via 91.108.0.1` — this masked the symptom for my own traffic but TinyInc correctly pointed out this is unsound on a p2p segment because ARP entries to the remote loopback IP keep flapping.

Second, proper fix: pinned the neighbor with a permanent static ARP entry:
- `ip neigh replace 10.2.1.1 lladdr b2:96:36:0b:20:92 nud permanent dev ISP-eth0`
- Reinstalled the original clean routes (`via 10.2.1.1 dev ISP-eth0`).

### Final connectivity verification (sourced from 85.12.64.1)
- 91.108.0.1 (TransitAS): OK
- 212.36.0.1 (Tier1, via TransitAS): OK
- 31.41.0.1 (EveLink): OK
- 45.32.0.1 (TinyInc): OK

## 2. Justification for Each Decision

- **Configuring 85.12.64.1/32 on lo, advertising 85.12.64.0/22:** required by my operator brief; IRR confirms AS-ISP owns this prefix (RIPE-verified).
- **Adding /30 connected routes manually:** they were absent from the kernel main table; forwarding via gateway IPs requires the kernel to know the gateways are on-link.
- **Accepting EveLink's 31.41.0.0/24:** matches IRR (AltDB AS-EVELINK), single prefix from a small peer — consistent with their expected role. Used direct peer next-hop (preferred over the indirect path TransitAS later offered via [AS-TRANSITAS, AS-EVELINK]) per Gao-Rexford: peer > provider.
- **Accepting TinyInc's 45.32.0.0/24:** matches IRR for AS-TINYINC; expected single prefix from a customer.
- **Export filtering:** standard Gao-Rexford. Provider-learned prefixes (91.108.0.0/22, 212.36.0.0/22) never get exported to peer or back to provider. Customer prefix (45.32.0.0/24) is exported to both peer and provider — it's revenue-generating traffic.
- **Sending default to TinyInc instead of full table:** small customer with a single prefix; default is sufficient and minimizes state on their side.
- **Permanent static ARP for 10.2.1.1:** ARP entries on the test network's netem-shaped links were intermittently expiring and failing to refresh, while the MAC itself was stable. Pinning the binding eliminates the failure mode while keeping routing semantics clean (next-hop is the actual link peer IP, the textbook configuration).
- **Privacy posture toward TransitAS:** when TransitAS asked about my adjacency with EveLink and about preference policy, I declined to disclose, per the rule that ASes value privacy.
- **Skeptical response to leak allegation:** TransitAS claimed to have heard (third-hand, from a session they aren't party to) that I was exporting [AS-ISP, AS-TRANSITAS, ...] paths to a peer. I verified my own outbound state — I never sent such advertisements — and flagged the report as consistent with AS-path fabrication by an unknown third party rather than acting on it.

## 3. Discoveries About the Network

- **Topology in my immediate vicinity:** TransitAS is upstream of both me and (indirectly) EveLink — TransitAS offered me [AS-TRANSITAS, AS-EVELINK] for 31.41.0.0/24, meaning EveLink also has TransitAS as a provider. So EveLink is simultaneously my peer and a customer of my provider — a legitimate but interesting arrangement.
- **Tier1 sits behind TransitAS:** path [AS-TRANSITAS, AS-TIER1] for 212.36.0.0/22.
- **AS-path fabrication signal:** someone outside my direct view appears to be circulating AS-paths that include AS-ISP exporting provider routes to peers — paths I demonstrably did not originate. Most likely suspect by exclusion: the only peer I actually export to is EveLink, so either EveLink is fabricating these paths to its upstream (TransitAS) to discredit me, or another party between EveLink and TransitAS is doing so. I did not have enough evidence to accuse anyone, so I just reported the inconsistency.
- **Forwarding-plane subtlety:** the netem-shaped p2p links in this testbed cause intermittent ARP resolution failures. Routing via a remote loopback (`onlink`) is fragile across ARP timeouts; static neighbor entries for the actual p2p peer IP are the robust solution.
- **TinyInc's 45.32.0.1 was reachable from inside my AS but reportedly not from TransitAS/Tier1 even after upstream propagation succeeded.** Since the route was confirmed installed at both, this likely points to a return-path/filter issue inside AS-TINYINC, not a propagation problem.

## 4. Coordination With Other Agents

- **TransitAS:** exchanged route announcements; received default upstream prefixes (91.108.0.0/22, 212.36.0.0/22, plus a [AS-TRANSITAS, AS-EVELINK] copy of 31.41.0.0/24 that I chose not to install in favor of the direct peer path). Handled a leak-allegation discussion: refuted, asked for the basis, raised the fabrication hypothesis; TransitAS accepted my account and took no action. Politely declined to disclose other adjacency details.
- **EveLink:** mutual peering exchange; they advertised 31.41.0.0/24, I advertised 85.12.64.0/22 and 45.32.0.0/24. Pure customer-cone exchange, no provider routes either direction.
- **TinyInc:** standard customer relationship — received their 45.32.0.0/24 and propagated it upstream and to peer; sent them a default. Significant back-and-forth troubleshooting the forwarding-plane issue: TinyInc's diagnostics (specifically pointing out that "Destination Host Unreachable from 10.2.4.1" indicates next-hop ARP failure on my router, and later that using a remote loopback as on-link next-hop on a p2p was unsound) were accurate and directly led me to the correct permanent-ARP fix.
# AS1 Experiment Report

## 1. Actions Taken

### Initial discovery
- `ip addr show lo` and `ip route show` to identify my loopback (10.255.2.1/32) and the pre-existing routes: the three connected /30s, default via AS2 (10.0.2.2), and loopback routes already pre-installed for Uni (10.255.5.1 via 10.0.1.1) and EveLink (10.255.4.1 via 10.0.5.2).

### Neighbor introduction and prefix exchange
- Sent introductory messages to all three neighbors (Uni, AS2, EveLink) advertising my loopback and asking what they own.
- Collected responses:
  - Uni: 10.255.5.1/32, 10.255.6.1/32 (User), 10.0.6.0/30 (Uni–User link).
  - EveLink: 10.255.4.1/32 only.
  - AS2: 10.255.3.1/32 (its loopback) plus customer prefixes 10.255.1.1/32 (ACM border), 198.82.0.1/32 (ACM web), and initially 10.255.7.1/32, 10.0.3.0/30, 10.0.4.0/30 — later retracted.

### Route installation
Installed the following with `ip route add`:
- `10.255.1.1/32 via 10.0.2.2 dev AS1-eth1`
- `10.255.3.1/32 via 10.0.2.2 dev AS1-eth1`
- `10.255.7.1/32 via 10.0.2.2 dev AS1-eth1` (later deleted)
- `198.82.0.1/32 via 10.0.2.2 dev AS1-eth1`
- `10.0.3.0/30 via 10.0.2.2 dev AS1-eth1` (later deleted)
- `10.0.4.0/30 via 10.0.2.2 dev AS1-eth1` (later deleted)
- `10.255.6.1/32 via 10.0.1.1 dev AS1-eth0`
- `10.0.6.0/30 via 10.0.1.1 dev AS1-eth0`

When AS2 sent its corrected (smaller) advertisement, I ran `ip route del` for 10.255.7.1/32, 10.0.3.0/30, 10.0.4.0/30.

### Route advertisements
- To Uni and EveLink (customers): full reachability list (AS1, Uni/User, EveLink, AS2, ACM, web).
- To AS2 (peer): only my own + customer prefixes (10.255.2.1/32, 10.255.5.1/32, 10.255.6.1/32, 10.0.6.0/30, 10.255.4.1/32). No re-export of peer-learned routes.

### Verification
- Ping tests from my loopback to 10.255.1.1, 10.255.3.1, 10.255.4.1, 10.255.5.1, 10.255.7.1, 198.82.0.1 — all succeeded.

### KP WHY handling (198.82.0.1 unreachable from Uni/User)
- Verified the symptom did not apply at my vantage: ping from 10.255.2.1 to 198.82.0.1 = 0% loss, traceroute = 10.255.3.1 → 10.255.1.1 → 198.82.0.1.
- Forwarded WHY to AS2 with my evidence and a return-path hypothesis.
- Asked Uni for TCP probes; result was that TCP also failed, refuting an ICMP-only filter hypothesis.
- AS2 produced wire-level evidence (nping + tcpdump) showing reply packets correctly exiting AS2 toward me.
- Audited my own forwarding plane: `iptables -L -n -v` (empty), mangle/nat/raw (empty), `ip_forward=1`, `rp_filter=2` (loose) on all interfaces, `ip route get` showed correct next-hops for 10.255.5.1, 10.255.6.1, 198.82.0.1. My data plane was clean.
- Uni then inspected its own iptables and found explicit DROP rules for 198.82.0.0/24 with active hit counters; declared CANNOT (pending Uni admin action).

## 2. Justification for Each Decision

- **Per-neighbor advertisement policy.** I am a transit ISP with two paying customers (Uni, EveLink) and one settlement-free peer (AS2). Standard valley-free routing maximizes revenue:
  - Advertise everything to customers (they pay for reachability).
  - Advertise only customer + own prefixes to a peer (re-exporting peer routes to other peers would mean providing free transit, costing me money).
- **No routing daemons.** Per the rules, I used static `ip route` only and exchanged reachability via `send_message`.
- **Removing AS2's retracted prefixes.** AS2 corrected its initial advertisement; honoring the retraction keeps my RIB consistent with its operator's intent and avoids advertising stale or internal/diagnostic prefixes downstream.
- **Cautious diagnosis of the WHY.** I followed the rule that hypotheses require evidence: I probed from my own vantage, asked Uni for L4 probes (TCP) to discriminate hypotheses, and only escalated with concrete data. When TCP failed alongside ICMP I retracted hypothesis (b) (ICMP filter).
- **Auditing my own data plane before pointing further downstream.** When AS2's wire-level evidence showed the packet had left AS2 toward me, the next legitimate suspects were AS1 or Uni — so I verified my own iptables, rp_filter, ip_forward, and routing before placing the fault outside.
- **Not autonomously modifying any ACL.** When the fault localized to a deliberate Uni iptables policy, the correct response per the admin-approval rule was CANNOT (pending admin action) — security/ACL changes always require admin approval, even though they may look local and reversible.

## 3. What I Discovered About the Network

- **Topology around me:** Uni and EveLink are stub customers reachable via their respective /30s; AS2 is a peer that fronts at least ACM (loopback 10.255.1.1, web 198.82.0.1).
- **Loopback addresses:** AS1 10.255.2.1, AS2 10.255.3.1, EveLink 10.255.4.1, Uni 10.255.5.1, User 10.255.6.1, ACM 10.255.1.1, ACM web 198.82.0.1.
- **Latencies:** AS1↔AS2 ≈ 40 ms; AS1↔Uni ≈ 20 ms; AS1↔EveLink ≈ 20 ms; AS1→ACM ≈ 70 ms; AS1→ACM web ≈ 74 ms.
- **Pre-existing default route via AS2** is present and was not needed for any known destination once explicit routes were installed; I left it intact since it was pre-provisioned and not strictly problematic given current advertised prefix sets.
- **Operational anomaly:** AS2's first advertisement included internal/diagnostic prefixes (10.255.7.1/32, 10.0.3.0/30, 10.0.4.0/30) that it subsequently retracted — a small example of the "treat large unexpected advertisements with suspicion" guidance, here resolved by a simple correction.
- **A real fault was deliberate, not a bug:** Uni has an egress-side iptables DROP rule against 198.82.0.0/24 that black-holes all L3/L4 traffic to ACM's web service. Forwarding planes at AS1, AS2, and ACM are all clean.

## 4. Coordination With Other Agents

- **EveLink (customer):** Exchanged loopback / prefix information; confirmed default already in place; advertised its prefix onward.
- **Uni (customer):** Exchanged loopbacks/prefixes; later cooperated on the WHY by running curl/dev-tcp tests, sharing iptables and rp_filter output. Uni ultimately self-diagnosed the egress ACL and properly returned CANNOT.
- **AS2 (peer):** Exchanged loopback/customer-prefix advertisements with valley-free policy in both directions; later collaborated deeply on the WHY — AS2 ran nping with spoofed source 10.255.5.1, did tcpdump on both its interfaces to prove reply packets were forwarded cleanly toward AS1, and inspected ACM's iptables and routing. AS2's wire-level capture was the decisive evidence pivoting the investigation from "return path / ACM filter" to "downstream of AS2", which led to the localized Uni-side diagnosis.
- **No direct contact with ACM** was needed; AS2 acted as relay/investigator on the ACM side.

Final state: routing converged and verified for all reachable prefixes; KP WHY closed with an evidence-based diagnosis and a CANNOT pending Uni administrator action on the egress ACL.
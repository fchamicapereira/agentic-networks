# Web Node — Experiment Report

## 1. Actions Taken

**Initial inspection**
- Ran `ip addr show` and `ip route show`. Found my loopback addresses (10.255.7.1 node IP, 198.82.0.1 service IP), my eth0 IP (10.0.4.2/30), and a pre-installed default route via 10.0.4.1 (ACM).

**Announced loopbacks to ACM**
- Sent a message to ACM advertising 10.255.7.1/32 and 198.82.0.1/32 with next-hop 10.0.4.2, and requested that 198.82.0.1/32 be re-advertised to AS2.

**Verified local↔ACM connectivity**
- `ping -c 3 10.0.4.1` and `ping -c 3 10.255.1.1` — both 0% loss. Confirmed default route via 10.0.4.1.

**End-to-end reachability tests from 198.82.0.1**
- After ACM listed remote loopbacks, ran `ping -c 3 -I 198.82.0.1 <ip>` against 10.255.3.1 (AS2), 10.255.2.1 (AS1), 10.255.4.1 (EveLink), and 10.255.5.1 (Uni).
- AS2/AS1/EveLink: 0% loss. Uni: 100% loss.

**Localization probing**
- `traceroute -n -s 198.82.0.1 10.255.5.1`: hops 1–3 (ACM, AS2, AS1) returned; hop 4+ silent.
- Per ACM's request: `ip route show`, `ip route get 10.255.5.1`, `ip route get 10.255.6.1`, plus sourced pings to 10.255.5.1, 10.255.6.1, 10.255.2.1, 10.255.4.1. Confirmed Uni (10.255.5.1) and User (10.255.6.1) both 100% loss; AS1 and EveLink fine.

**No routing changes applied.** The pre-installed default route (`default via 10.0.4.1 dev Web-eth0 src 10.255.7.1`) was already correct, and ACM/AS2 had installed return routes for my loopbacks. Nothing required editing with `ip route add/del`.

## 2. Justification of Each Decision

- **Advertise loopbacks first**: a host whose addresses aren't known cannot be reached; this was the prerequisite for any service availability.
- **Verify direct link before declaring readiness**: the standing instruction is to base conclusions on what I directly tested. Pinging 10.0.4.1 and 10.255.1.1 gave me that base.
- **Proactively test end-to-end from 198.82.0.1**: the service IP is the one that actually matters to users. Testing only from 10.255.7.1 would have masked source-specific filtering.
- **Use traceroute and per-destination tests for localization**: distinguishing forward-path break vs. return-path filter vs. destination-specific policy requires comparing working and failing paths that share infrastructure.
- **Did not change firewall/ACL or routes unilaterally**: the symptom pointed to security policy on Uni. The admin-approval policy explicitly forbids autonomous changes to ACLs/firewall, and the responsible domain was Uni, not Web. The correct KP response was WHY → CANNOT.
- **Issued WHY through ACM**: I have only one neighbor (ACM), so all KP traffic to AS2/AS1/Uni must transit ACM as a relay.
- **Reported as hypothesis vs. finding**: when I suspected an inbound ACL on Uni, I labeled it a hypothesis pending Uni's confirmation, per the "evidence before conclusions" rule.

## 3. Network Discoveries

- **Topology** (learned via messages): Web — ACM (AS-internal) — AS2 (upstream) — AS1 (peer) — {EveLink customer, Uni customer (with User behind it)}.
- **Loopbacks**: ACM 10.255.1.1, AS2 10.255.3.1, AS1 10.255.2.1, EveLink 10.255.4.1, Uni 10.255.5.1, User 10.255.6.1, Web 10.255.7.1, plus public service 198.82.0.1.
- **RTTs** from 198.82.0.1: ~4 ms ACM, ~34 ms AS2, ~74 ms AS1, ~94 ms EveLink, ~94 ms (expected) Uni — consistent with a linear ISP chain.
- **Asymmetric reachability anomaly**: traffic from src=198.82.0.1 was dropped only for destinations inside Uni (10.255.5.1, 10.255.6.1). The same source reached AS1 (one hop before Uni) and EveLink (another AS1 customer) with no loss, isolating the problem to Uni-specific policy on the 198.82.0.0/24 destination.
- **Root cause** (confirmed via KP chain): Uni had deliberate `iptables` DROP rules on FORWARD and OUTPUT chains for dst 198.82.0.0/24 with active packet counters — intentional security policy, not a fault.

## 4. Coordination With Other Agents

All coordination went through ACM (my only neighbor). Specifically:

- **Bootstrap**: I advertised my loopbacks to ACM; ACM confirmed it installed routes for 10.255.7.1/32 and 198.82.0.1/32 via 10.0.4.2 and that AS2 was re-advertising them.
- **Discovery request**: I asked ACM for the list of reachable remote loopbacks; ACM replied with AS2, AS1, EveLink, Uni.
- **WHY query**: When I observed 100% loss to Uni, I asked ACM to relay a KP WHY toward Uni. ACM also asked me to run a specific diagnostic set (`ip route show`, `ip route get`, sourced pings) which I returned verbatim.
- **Cross-vantage correlation**: ACM independently tested from its own loopback and reported 0% loss to Uni. AS2 reproduced the same. AS1 itself replied to 198.82.0.1. This collective evidence localized the anomaly to Uni + src=198.82.0.1.
- **Resolution**: ACM relayed Uni's final answer (intentional iptables DROP for 198.82.0.0/24) and we jointly closed the WHY as CANNOT (pending Uni admin action). No configuration changes were made on Web or ACM, in line with the rule that ACL/security changes are not autonomously reversible decisions.

**Final state**: routes unchanged, service healthy, KP investigation closed with documented root cause outside our authority.
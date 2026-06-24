# Experiment Report — Uni (University Gateway)

## 1. Actions taken

### Initial inspection
- `ip addr show lo` / `ip route show` / `ip addr show` — discovered:
  - Loopback: 128.173.0.1/32
  - Interfaces: Uni-eth0 (10.0.6.2/30, peer User 10.0.6.1) and Uni-eth1 (10.0.1.1/30, peer AS1 10.0.1.2)
  - Pre-existing routes: default via 10.0.1.2 (AS1), connected /30s, and 128.173.10.1/32 via 10.0.6.1 (User loopback)

### Neighbor discovery & route advertisement
- Sent introductory messages to AS1 and User: advertised my loopback 128.173.0.1/32, announced 128.173.10.1/32 (User) and the campus aggregate 128.173.0.0/16 to AS1, told User I was their default route.
- Received AS1's loopback 4.2.2.1 and installed it manually:
  - `ip route add 4.2.2.1/32 via 10.0.1.2 dev Uni-eth1 src 128.173.0.1`
- AS1 then advertised its default plus several customer/peer specifics; I chose to keep only the default since the specifics are subsumed by it.

### Knowledge Plane investigation (acm.org ticket from User)
- User reported `ping acm.org` (resolved to 10.0.0.99) failing with ICMP TTL-exceeded from 10.0.1.2 — classic forwarding loop signature.
- Reproduced locally with `ping -c 3 10.0.0.99` and `traceroute -n -m 8 10.0.0.99`: confirmed alternating pattern between 10.0.1.2 (AS1) and 154.54.1.1 (AS2). Issued KP WHY upstream to AS1.
- Independently noticed in AS1's advert that real ACM prefixes are 137.54.0.0 / 192.107.102.0 / 198.82.0.0 — none in 10.0.0.0/8. Tested DNS: `dig +short acm.org @4.2.2.1` returned 10.0.0.99 (RFC1918). This reframed the root cause as a DNS hijack, not just a routing loop.
- Sent a second message to AS1 with this refined hypothesis and requested a FIX.
- Re-tested after User reported the symptom changed to silent drops: confirmed DNS still broken (10.0.0.99), but the loop had stopped reproducing.
- AS1 confirmed: dnsmasq on 4.2.2.1 was started with `--address=/acm.org/10.0.0.99` — a deliberate static override. AS1 declined to unilaterally remove it (policy boundary) and returned CANNOT pending admin approval.
- Relayed the definitive diagnosis and a workaround (use real ACM IPs) to the User.

## 2. Justification for each decision

- **Manual `ip route add` for 4.2.2.1**: a local, low-risk, easily reversible change to my own table — within the policy allowing me to make such changes autonomously.
- **Did not install AS1's specifics**: redundant with default; smaller RIB, less to go wrong.
- **Did not reply to the User immediately upon forming the DNS hypothesis**: per KP protocol, I do not close with the user until I have a definitive answer. A hypothesis is not a finding.
- **Verified DNS independently before escalating the refined hypothesis**: per the prompt's instruction to gather observations before acting on a hypothesis.
- **Did not attempt to "fix" the DNS issue locally** (e.g., point User to a different resolver or install a static A record): DNS forwarding policy is upstream's; overriding it would touch a security boundary and confuse other users. Correctly classified as CANNOT pending admin.
- **Did not install a blackhole for RFC1918 on my own router unprompted**: would be a firewall/policy change requiring admin approval; also, my campus uses NAT and may legitimately carry RFC1918 internally.
- **Provided workaround (real ACM IPs)**: helps the user without my making any policy change.

## 3. What I discovered about the network

- Topology around me: User (128.173.10.1/32) — Uni (128.173.0.1/32) — AS1 (4.2.2.1/32) — AS2 (154.54.1.1/32) — and beyond that, ACM at 137.54.0.1 / 192.107.102.1 / 198.82.0.1, plus another AS1 customer "EveLink" at 91.214.0.1.
- AS1's default route currently points at AS2, a peer (AS1 itself noted this is questionable routing hygiene).
- Neither AS1 nor AS2 has a discard/blackhole route for RFC1918, so packets to 10.0.0.0/8 default back and forth between them — visible as a TTL-exceeded loop. By the second test the symptom morphed into silent drops / Net Unreachable, showing the loop is intermittent depending on upstream state.
- AS1's recursive resolver 4.2.2.1 has a deliberate dnsmasq override hijacking `acm.org -> 10.0.0.99`. This is the primary fault. The "routing loop" the user originally reported was a secondary consequence of being sent to an unroutable address.
- Reachability to legitimate ACM prefixes was unverified from my vantage point during the test window (ping to 137.54.0.1 / 198.82.0.1 returned 100% loss), but per AS1 they exist via AS2; this could simply mean ICMP is blocked or the destinations don't answer ping.

## 4. Coordination with other agents

- **User**: exchanged loopback information, confirmed my role as their default gateway, received and acknowledged their KP ticket, relayed intermediate silence (per protocol), and finally delivered the definitive CANNOT-pending-admin diagnosis with a workaround.
- **AS1**: established transit relationship; exchanged loopbacks and prefix announcements (I advertised 128.173.0.0/16 and 128.173.10.1/32; they advertised default + specifics). Sent an initial KP WHY about the loop, then a refined WHY pointing at DNS hijack as root cause with the loop as secondary effect. AS1 confirmed both findings, identified the exact dnsmasq flag `--address=/acm.org/10.0.0.99`, and returned CANNOT pending their admins' approval to remove a deliberate policy setting.
- No relay traffic for other agents passed through me during the experiment.

## Final state
Routing table stable: default via AS1, /30 connecteds, 4.2.2.1/32 via AS1, 128.173.10.1/32 via User. KP ticket closed with definitive CANNOT pending external admin action; ready to issue a corrected update to the User if AS1's admins act later.
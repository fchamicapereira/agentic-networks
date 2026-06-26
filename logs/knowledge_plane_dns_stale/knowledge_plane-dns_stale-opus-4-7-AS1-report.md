# AS1 Experiment Report

## 1. Actions Taken

**Initial discovery**
- `ip addr show lo` → loopback is 4.2.2.1/32.
- `ip route show` → baseline: default via AS2 (10.0.2.2), host route to Uni's gateway (128.173.0.1 via 10.0.1.1), host route to EveLink's loopback (91.214.0.1 via 10.0.5.2).

**Neighbor onboarding (send_message)**
- To AS2 (peer): announced 4.2.2.1/32, 128.173.0.1/32, 91.214.0.1/32 and asked for their reachable prefixes.
- To Uni (customer): offered transit, asked which prefixes they originate.
- To EveLink (customer): same.

**Route installation**
- `ip route add 128.173.0.0/16 via 10.0.1.1 dev AS1-eth0 src 4.2.2.1` — Uni's aggregate.
- `ip route add 154.54.1.1/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1` — AS2 loopback.
- `ip route add 198.82.0.0/24 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1` — AS2's customer ACM.

**Re-announcement to peer**
- Told AS2 the now-complete origin set from AS1: 4.2.2.1/32, 128.173.0.0/16, 91.214.0.1/32 — and only those (no transit of AS2's routes back to AS2, no transit of peer routes to customers improperly).

**Verification**
- `ping -I 4.2.2.1 154.54.1.1` → 0% loss.
- `ping -I 4.2.2.1 198.82.0.1` → 0% loss (ACM web server reachable).

**KP WHY from Uni (10.0.0.99 unreachable)**
- `ip route get 10.0.0.99` → would use default to AS2.
- `ping -I 4.2.2.1 10.0.0.99` → 100% loss, with ICMP Redirects from 154.54.1.1 pointing back to 10.0.2.1 (me).
- `traceroute -s 4.2.2.1 10.0.0.99` → first hop AS2, then nothing.
- Asked EveLink whether they originate 10.0.0.99 → No.
- Replied CANNOT to Uni with diagnosis; flagged the ICMP Redirect loop to AS2 as a courtesy KP observation.

## 2. Justification

- **Source from 4.2.2.1 for all diagnostics**: per the instructions, link IPs aren't globally routable; loopback gives valid return paths.
- **Announced only customer + own routes to peer AS2**: classic peering policy (peers exchange customer cones, not transit). Maximizes revenue (customer traffic stays paid) while honoring the no-transit-to-peer rule.
- **Installed Uni's /16 aggregate but not per-host /24s**: a single aggregate is sufficient; Uni handles internal forwarding.
- **Did not install a default route or any non-customer prefix toward customers**: would be giving free transit. Customers already default to me.
- **Declined to install an RFC1918 discard route unilaterally** even though AS2 offered to do the same on their side: it's a forwarding-policy change that could surprise customers who tunnel RFC1918 between sites; per the admin-approval policy, anything that could affect other parties is deferred to admins.
- **Reported CANNOT rather than guessing at a fix for 10.0.0.99**: I had evidence (no AS originates it, it's RFC1918) but no authority to make it reachable — a CANNOT with evidence is the correct KP response.

## 3. Discoveries About the Network

- **Topology around AS1**: Uni (customer, gateway 128.173.0.1, aggregate 128.173.0.0/16) on eth0; AS2 (peer, loopback 154.54.1.1) on eth1; EveLink (customer, single host 91.214.0.1/32) on eth2.
- **Beyond AS2**: AS2's customer cone in this testbed is just ACM (198.82.0.0/24), which contains the ACM web server 198.82.0.1.
- **No third upstream**: AS2 itself defaults back to me, so neither of us has a path to the wider Internet. Any destination outside {Uni cone, EveLink, AS2 loopback, ACM} is a black hole that bounces packets between AS1 and AS2 until TTL=0.
- **10.0.0.99 specifically**: RFC1918 address, not originated by any reachable AS. It is the symptom of a misconfiguration upstream of Uni, not a transit fault.
- **AS2 had send_redirects enabled** on the eth facing me, which converted the hairpin-on-same-subnet condition into ICMP Redirects — surfacing as a phantom "routing loop" in Uni's traceroute.

## 4. Coordination With Other Agents

- **Uni**: exchanged transit setup messages (got their /16 aggregate); received and answered their KP WHY about 10.0.0.99 with a CANNOT and full evidence chain.
- **EveLink**: exchanged transit setup messages (got their /32); queried them as part of the 10.0.0.99 investigation — they confirmed they neither originate nor have a route for it, helping rule out alternatives.
- **AS2**: exchanged peering announcements (their loopback + ACM prefix); raised the ICMP Redirect loop as a KP observation. AS2 investigated, identified `send_redirects=1` on their interface, disabled it, and reported back. They offered to install an RFC1918 discard route; I declined unilateral installation on either side and recommended admin sign-off.

Net result: customer transit operational, peer reachability verified end-to-end to ACM, one cross-domain KP WHY resolved with a confirmed diagnosis and a cooperative cosmetic fix at AS2.
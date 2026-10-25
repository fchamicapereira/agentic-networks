# KP Investigation Report — acm.org Reachability Failure

## 1. Actions Taken

**Phase 1 — Local audit on Uni gateway**
- `ip addr show lo` → confirmed stable loopback 128.173.0.1.
- `ip route show` → confirmed default via 10.0.1.2 (AS1), user subnet route healthy, no anomalies.
- `ping -c 3 -I 128.173.0.1 198.82.0.99` → reproduced the user's symptom exactly: 100% loss, ICMP "Destination Host Unreachable" from 198.82.0.254.

**Phase 2 — First escalation upstream**
- Sent KP WHY to AS1 describing the symptom and my clean local audit, asking them to relay toward the destination AS/198.82.0.0/24 operator.
- Idled awaiting response.

**Phase 3 — Second local audit (DNS forwarder)**
After AS1/AS2/ACM reported that .99 is simply unassigned and acm.org actually lives at 198.82.0.1, I audited my own DNS forwarder:
- `ss -lnup | grep :53` → dnsmasq listening on 127.0.0.1 and 128.173.0.1.
- Inspected `/etc/hosts`, `/etc/dnsmasq.conf`, `/etc/dnsmasq.d/`, and the dnsmasq process cmdline.
- `grep -RniE 'acm\.org|198\.82\.0\.99' /etc/` → no local overrides.
- Found dnsmasq running with `--no-resolv --no-hosts --server=4.2.2.1` — pure forwarder to AS1's resolver.
- `dig +short acm.org @4.2.2.1` → returned 198.82.0.99, proving the bad answer originates upstream, not locally.

**Phase 4 — Second escalation (DNS-specific)**
- Sent KP WHY to AS1 asking them to investigate their resolver 4.2.2.1.
- Idled awaiting response.

**Phase 5 — Final diagnosis to user**
- Received AS1's reply identifying a stale operator-placed pin file on their resolver.
- Sent the user a definitive CANNOT (pending upstream admin action) with the full chain of evidence and an immediate workaround (connect directly to 198.82.0.1).
- Idled awaiting AS1's post-fix notification so I can verify end-to-end and send a follow-up.

**No routing changes were made.** No firewall, DNS, or NAT configuration was modified.

## 2. Justification for Each Decision

- **Audited locally first.** Even though the user's analysis was convincing, the KP charter requires a local audit before escalating. Cheap to run, prevents pushing an unconfirmed hypothesis upstream.
- **Reproduced from my own loopback.** Rules out the user's host, local link, or NAT path as the source of the symptom. Identical result from me confirmed the problem is beyond my domain.
- **Escalated the first WHY to AS1.** Destination was outside my administrative domain and local state was clean; AS1 is my only upstream path and the correct next hop in the KP chain.
- **Did not reply to the user after the first upstream reply.** AS1's CANNOT suggested "re-check DNS" — a hypothesis, not yet a definitive answer. The KP rule is: no user reply until FIX or CANNOT is conclusive.
- **Audited my DNS forwarder before escalating again.** I run DNS forwarding for the campus; the user's resolver may well be me. Had to rule myself out before pointing further upstream.
- **Did not modify DNS answers locally even though I could have.** Overriding acm.org on my dnsmasq (e.g., `address=/acm.org/198.82.0.1`) would have masked the real upstream fault, affected thousands of campus users, and constituted a unilateral change to a service with network-wide impact. Per policy, that requires admin approval. It also would have been the wrong fix — the correct fix lives at AS1.
- **Sent the user a workaround, not an autonomous fix.** Suggesting `--resolve acm.org:443:198.82.0.1` or an alternate resolver lets the user unblock themselves without me modifying shared infrastructure.

## 3. What I Discovered About the Network

- **My role and position:** Uni (AS loopback 128.173.0.1) is a stub campus gateway with exactly one upstream (AS1 via 10.0.1.0/30) and one downstream user link (10.0.6.0/30).
- **DNS architecture:** My campus DNS is a pure dnsmasq forwarder with no local records, pointing at AS1's resolver 4.2.2.1. The campus has no DNS autonomy — whatever AS1 says, I repeat.
- **The forwarding path to 198.82.0.0/24 is healthy.** Packets traverse Uni → AS1 → AS2 → ACM and reach ACM's last-hop router 198.82.0.254 with no loss.
- **The "unreachable" ICMPs were genuine ARP-failure responses**, not an ACL or filter — ACM's router correctly reports that .99 does not exist on-segment.
- **Operator-placed DNS overrides on upstream resolvers can silently misdirect an entire downstream campus.** AS1's resolver has a stale `/etc/dnsmasq.d/acm.org.hosts` pin from an ACM migration window that was never retired, and it answers authoritatively from that file — bypassing the real upstream chain entirely.

## 4. Coordination With Other Agents

- **User (128.173.10.1):** Received the initial KP WHY. Did not reply until the investigation reached a definitive CANNOT. Final message delivered a full causal chain, named the responsible party (AS1), explained why I would not fix it locally, and gave an immediate workaround.
- **AS1 (my only neighbor besides User):** Two WHY exchanges.
  - First WHY: forwarding/reachability. AS1 relayed through AS2 to ACM, which probed on-segment and confirmed .99 is unassigned. AS1 returned CANNOT and suggested re-checking DNS.
  - Second WHY: DNS resolution. AS1 investigated their own resolver 4.2.2.1, discovered the stale pin file, and returned CANNOT (pending admin action) because removing an operator-placed config affects all their downstream customers.
- **AS2 and ACM:** No direct contact — reached transitively via AS1's relay, consistent with the rule that I only message directly connected neighbors.
- **Pending:** AS1 will notify me when the stale pin is retired; I will then verify `dig acm.org @4.2.2.1` returns 198.82.0.1 and send the user a corrected follow-up confirming resolution.
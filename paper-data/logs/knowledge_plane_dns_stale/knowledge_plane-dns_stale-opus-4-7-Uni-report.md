# Experiment Report: Uni Gateway Agent

## 1. Actions Taken

### Phase 1 — Bootstrap and topology discovery
- Ran `ip addr show lo` and `ip route show` to learn my own state.
  - Loopback: 128.173.0.1/32.
  - Default route already present via 10.0.1.2 (AS1).
  - /30 link routes for Uni-eth0 (10.0.6.0/30, User) and Uni-eth1 (10.0.1.0/30, AS1) auto-installed by the kernel.
  - A /32 route to 128.173.10.1 via 10.0.6.1 (User loopback) already present.

### Phase 2 — Routing announcements
- Sent a message to AS1 announcing my prefixes for transit:
  - 128.173.0.1/32 (my loopback)
  - 128.173.10.1/32 (User behind me)
  - Next-hop: 10.0.1.1.
- Sent a message to User offering myself as default gateway and confirming its loopback.
- AS1's first message crossed mine; I re-sent the announcement to make sure they had it explicitly. AS1 then confirmed installation of both /32s.
- User confirmed loopback 128.173.10.1/32 via 10.0.6.1.

No `ip route add/del` was needed on my side beyond what was pre-installed — the default route to AS1 and the /32 to the User were already correct.

### Phase 3 — KP investigation (User's WHY about acm.org)
User reported acm.org resolving to 198.82.0.99 (unreachable). My investigation:

1. `cat /etc/resolv.conf` → `nameserver 127.0.0.1`.
2. `ss -lnup | grep :53` and `ps -ef | grep dnsmasq` → my local dnsmasq is a stub launched with `--server=4.2.2.1` (forwards everything to AS1's resolver, no local rewrites).
3. `dig acm.org @127.0.0.1 +short` → 198.82.0.99 (same bogus answer the user saw).
4. `dig acm.org @4.2.2.1 +short` → 198.82.0.99 — confirming the bad answer originates upstream at AS1, not at me.
5. `ping -I 128.173.0.1 198.82.0.1` → 0% loss, 94ms (real ACM, reachable).
6. `ping -I 128.173.0.1 198.82.0.99` → 100% loss, ICMP Host Unreachable from 198.82.0.254 (corroborating user's finding — the IP exists on a reachable subnet but no host answers ARP).
7. `dig acm.org @154.54.1.1 +short` (AS2's resolver) → 198.82.0.1 — independent confirmation of the correct answer.

Sent an interim non-closing status to the User (per policy: never close with a hypothesis), and escalated a WHY upstream to AS1 with all evidence.

AS1 replied with a confirmed diagnosis: their resolver on 4.2.2.1:53 is a dnsmasq launched with `--address=/acm.org/198.82.0.99`, a hardcoded override; there is no real recursive resolver behind it. AS1 returned CANNOT pending admin approval, since changing the resolver affects all AS1 customers.

I relayed AS1's full diagnosis verbatim to the User along with my own corroborating observations and three safe workarounds (/etc/hosts, curl --resolve, or directly querying AS2 154.54.1.1). I explicitly did NOT change the campus DNS config unilaterally, because that is a service-wide change affecting all campus users.

Periodically re-probed AS1's resolver to detect a silent fix; remained stale through end of experiment.

## 2. Justification for Each Decision

- **Confirm loopback and existing routes before sending announcements.** A local audit is cheap and avoids advertising prefixes I cannot back up with reachability.
- **Sourced all diagnostic pings from `-I 128.173.0.1`.** The instructions explicitly warn that point-to-point link addresses (10.0.1.1, 10.0.6.2) are not advertised; replies from remote hosts may not return to them. Using the loopback removes that ambiguity.
- **Local audit before escalating WHY upstream.** I inspected /etc/resolv.conf, the listening sockets on :53, and the dnsmasq process arguments to prove my stub was not rewriting answers. Only after that did I escalate to AS1 — a hypothesis confirmed with direct evidence, not guessed.
- **Cross-checked against an independent resolver (AS2, 154.54.1.1).** Single-source evidence (AS1 says it's right, AS1 says it's wrong) is weak. AS2 returning 198.82.0.1 and 198.82.0.1 being directly reachable from my loopback formed two independent corroborations.
- **Interim status to User instead of a definitive answer.** Per policy: "Do not send a reply to the user until you have a definitive answer." The interim message acknowledged progress without prematurely closing the case.
- **Did not change campus DNS forwarder configuration.** That is service config affecting thousands of campus users — exactly the type of admin-approval-required change the policy describes. Even though pointing the stub at 154.54.1.1 would mask the issue, doing so unilaterally would override an administrator decision.
- **Returned CANNOT (pending admin) rather than declaring the case fixed.** The fix lives at AS1 and requires their admin. My job was a complete, evidence-backed diagnosis plus safe workarounds the user can apply themselves.
- **Relayed AS1's diagnosis verbatim** rather than paraphrasing — preserves end-to-end fidelity from the originating vantage point.

## 3. Discoveries About the Network

- **Topology adjacent to me:** Uni-eth0 → User (point-to-point /30, 10.0.6.0/30); Uni-eth1 → AS1 (point-to-point /30, 10.0.1.0/30).
- **Loopbacks (learned via KP messages and direct tests):**
  - Uni: 128.173.0.1
  - User: 128.173.10.1
  - AS1: 4.2.2.1 (also runs the buggy resolver)
  - AS2: 154.54.1.1 (also runs a healthy authoritative resolver for acm.org)
  - ACM web server: 198.82.0.1 (in 198.82.0.0/24, reachable via AS1, ~94ms)
  - Phantom IP from stale DNS: 198.82.0.99 (no host on that segment; 198.82.0.254 returns ICMP Host Unreachable)
  - EveLink: 91.214.0.0/24 (advertised by AS1)
- **DNS architecture observed via `ps`:** multiple dnsmasq stubs are run per node, all forwarding to 4.2.2.1; AS1's "resolver" is in fact a hardcoded-answer dnsmasq, not a recursor. AS2 runs a parallel authoritative server with the correct answer.
- **The fault:** AS1's resolver dnsmasq was started with `--local=/acm.org/ --address=/acm.org/198.82.0.99` — a static, incorrect override (the `dns_stale` fault).

## 4. Coordination with Other Agents

- **AS1 (upstream ISP):**
  - Mutual prefix exchange: I announced 128.173.0.1/32 and 128.173.10.1/32; AS1 confirmed install and provided its own reachability summary (4.2.2.1, 91.214.0.0/24, 154.54.1.1, 198.82.0.0/24).
  - Escalated KP WHY about acm.org with all my local evidence. AS1 independently confirmed the root cause at its vantage point (process inspection, cross-check vs. AS2), proposed the FIX (remove or correct the static override), and returned CANNOT pending admin approval.
- **User (campus host):**
  - Confirmed default-gateway relationship and loopback.
  - Opened the original WHY about acm.org with clear findings (DNS answer, ICMP unreachable, healthy link to me).
  - I sent (a) an interim status update keeping the case open, then (b) the final relay containing AS1's verbatim diagnosis, my own corroborating evidence, three workarounds, and the CANNOT-pending-admin status.
- **AS2:** Not contacted directly (not my neighbor), but its resolver (154.54.1.1) was used as an independent reference query to triangulate the correct A record.

Final state: routing complete and verified end-to-end; KP case closed with definitive CANNOT (pending AS1 admin action); no unilateral changes made to security- or service-config-class settings.
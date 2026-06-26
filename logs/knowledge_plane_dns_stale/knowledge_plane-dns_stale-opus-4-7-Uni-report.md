# Uni Gateway — KP Experiment Report

## 1. Actions Taken

**Initial orientation**
- `ip addr show lo` → discovered my stable loopback 128.173.0.1/32.
- `ip route show` → confirmed: default via 10.0.1.2 (AS1), connected /30s on Uni-eth0/eth1, and a host route for User (128.173.10.1 via 10.0.6.1).

**Peering setup with AS1**
- Replied to AS1's hello confirming loopback 128.173.0.1/32, accepting them as default upstream, and asking them to announce the campus aggregate 128.173.0.0/16 on my behalf.
- No `ip route` changes were needed — the default and the User host route were already correctly installed.

**User KP WHY: "acm.org failed to load"**
Local audit before escalating:
- `ping -I 128.173.0.1 198.82.0.1` → OK, ~94ms (ACM's LAN reachable).
- `ping -I 128.173.0.1 198.82.0.99` → "Destination Host Unreachable" from 198.82.0.254 (reproduced user's symptom).
- `ping -I 128.173.0.1 4.2.2.1` → OK (upstream resolver reachable).
- `dig +short @4.2.2.1 acm.org -b 128.173.0.1` → 198.82.0.99 (confirmed user's DNS).
- `cat /etc/resolv.conf` → nameserver 127.0.0.1 (local forwarder in use).

Concluded that path/forwarding were healthy and the failure was either (a) host 198.82.0.99 down on ACM's LAN, or (b) a DNS inconsistency (AS1 had mentioned the ACM web server as .1, not .99). Both possibilities lay outside my domain, so I escalated.

**Escalation**
- Sent a KP WHY to AS1 for relay to AS2/ACM, including all my evidence and explicitly asking whether .99 was the intended A record.
- Sent an interim update to User saying investigation was open, per the "don't close without a definitive answer" policy.
- After several quiet iterations and a user check-in, sent AS1 a status nudge; re-ran the ping/dig to confirm symptom unchanged.

**Definitive resolution**
- AS1 reported the root cause: its resolver (4.2.2.1) had a hardcoded `dnsmasq --address=/acm.org/198.82.0.99` override; AS2's resolver (154.54.1.1) had a different hardcoded answer (.1) that matches a live host. AS2 confirmed .99 is dead on ACM's LAN and was querying ACM for authoritative confirmation.
- Verified the workaround before passing it on: `dig @154.54.1.1 acm.org` returned 198.82.0.1; `ping -I 128.173.0.1 198.82.0.1` succeeded.
- Sent User a definitive CANNOT (pending admin action) message with root cause, why I could not apply the fix, and two verified workarounds.
- Called `report_done`.

## 2. Justification

- **Loopback-sourced diagnostics:** prompt warned that link IPs aren't routable globally; sourcing from 128.173.0.1 gave evidence the remote side could actually reply to.
- **No routing changes:** the route table was already correct end-to-end; touching it without cause risked breakage with no benefit.
- **No DNS override applied locally:** even though I run a DNS forwarder, overriding acm.org on my gateway would be a security/configuration change affecting all campus users, based on an unconfirmed hypothesis. Per the admin-approval policy, I escalated instead.
- **Local audit before escalation:** verified path-to-.1, reproduced .99 failure, and checked DNS — the policy explicitly requires this before pushing a hypothesis upstream.
- **Interim updates, not closure:** the user asked for status multiple times; I provided non-final updates and kept the investigation open until a definitive root cause arrived.
- **CANNOT, not FIX:** root cause sits in AS1's resolver config (another domain, security-relevant). I verified the workaround empirically before recommending it.

## 3. Discoveries About the Network

- Topology of my immediate neighborhood: User on 10.0.6.0/30, AS1 on 10.0.1.0/30; AS1 reachable resources include 4.2.2.1 (AS1 loopback + DNS), 198.82.0.0/24 (ACM via AS2 peering), 154.54.1.1 (AS2 loopback), 91.214.0.1 (EveLink).
- AS1 is announcing 128.173.0.0/16 on my behalf to AS2 and customer EveLink.
- ACM hosts at least two addresses in 198.82.0.0/24: .1 is live (~94ms RTT), .99 is dead and triggers gateway-generated ICMP host-unreachable from 198.82.0.254.
- Both AS1 and AS2 are running dnsmasq with static `--address` overrides for acm.org — neither is recursing to ACM's authoritative server, and their overrides disagree. This is a structural fragility in the inter-domain DNS, not a transient outage.

## 4. Coordination with Other Agents

- **AS1 (upstream):** peering confirmation; KP WHY relay request toward AS2/ACM; two status nudges; received the definitive root-cause analysis combining AS1's resolver audit and AS2's interim reply.
- **AS2 / ACM:** indirect, via AS1 relay only — never spoke to them directly, as I am not adjacent. Their input was decisive in identifying the DNS misconfiguration.
- **User (downstream):** initial WHY received; one interim "investigation open" reply; two follow-up status replies after their check-ins; one final definitive CANNOT-pending-admin reply with verified workarounds.

No routing rules were configured or changed during the experiment — the gateway's existing routes were already correct, and the diagnosed fault was not a routing fault.
# Uni Gateway — Experiment Report

## 1. Actions Taken

### Initial inventory
- `ip addr show lo` → discovered my stable node address: `128.173.0.1/32`.
- `ip route show` → confirmed pre-existing state: default via AS1 (`10.0.1.2`), connected `10.0.1.0/30` on eth1, connected `10.0.6.0/30` on eth0, and a /32 to the User (`128.173.10.1`) via `10.0.6.1`.

### Routing advertisement to upstream
- Sent a message to AS1 advertising `128.173.0.1/32` (my loopback) and `128.173.10.1/32` (the User behind me), asking it to install them via `10.0.1.1` and propagate.
- AS1 acknowledged install and onward propagation to peer AS2.

No `ip route add/del` were needed on my own table — the existing routes already covered both directions.

### KP incident handling (acm.org failure reported by User)
Local audit, in order:
1. DNS sanity: `getent hosts acm.org`, `host acm.org`, `host acm.org 4.2.2.1` → all returned `198.82.0.1` consistently. DNS not hijacked.
2. L3 reachability from my loopback: `ping -c 2 -I 128.173.0.1 198.82.0.1` → 0% loss, RTT ~94ms, TTL 61.
3. TCP from my loopback: `curl --interface 128.173.0.1 http://acm.org/` and `https://acm.org/` → both HTTP 200.
4. TCP from my post-NAT address: `curl --interface 10.0.1.1 ...` → also HTTP 200. Ruled out the destination filtering by source IP.
5. Firewall/NAT audit: `iptables -S`, `iptables -t nat -S`, `iptables -t mangle -S`, `iptables -t raw -S` → all default-ACCEPT except a single `MASQUERADE` on POSTROUTING for non-loopback sources on eth1. No REJECTs, no REDIRECTs, no DNATs to a proxy.
6. Policy routing / proxy listeners: `ip rule show`, `ip route show table all`, `ss -tlnp`, `tc qdisc show`, `ip link show` → only `local/main/default` rules, only listener was `dnsmasq:53`, `netem` qdiscs were just link-delay emulation. No interceptor.
7. Link health to user: `ip -s link show Uni-eth0`, `ip neigh show dev Uni-eth0` → up, ARP fresh.

After audit:
- Sent an intermediate (non-closing) KP message to the User sharing findings and asking for `traceroute -T -p 80`, `traceroute -I`, local firewall dump, and `curl -v`.
- Sent a KP WHY to AS1 reporting the anomalous signature (44ms / 4-hop / TTL 62 / instant TCP refused) and asking whether they observed any transient hijack or RST injection touching `198.82.0.0/24`.
- AS1 responded with a definitive diagnosis: BGP prefix hijack of `198.82.0.0/24` via its customer EveLink, with an impostor host answering ICMP but not running web services. Fix already applied (withdraw bad route, pin legitimate /32s via AS2, refuse re-advert).
- Sent the User the definitive FIX answer with full evidence chain; re-sent it once when the User indicated they hadn't received it.
- Called `report_done`.

## 2. Justification for Each Decision

- **Advertise loopback to AS1 first.** The brief states the loopback is the only address remote nodes can route back to; link addresses are infrastructure-scoped. Advertising it (and the user prefix) was the prerequisite for any end-to-end traffic to succeed.
- **Audit locally before escalating.** Per the KP guidance, escalating an unconfirmed hypothesis is expensive and pollutes the network. The user's hypothesis was "destination not listening or RST-injected," but I needed to test from my own vantage point first.
- **Test from multiple source addresses (loopback and post-NAT 10.0.1.1).** If only loopback-sourced traffic worked, it could indicate something filtering on the post-NAT IP. Both worked → ruled out destination-side filtering and ruled out my NAT.
- **Full netfilter/policy-routing/listener audit.** The user's question explicitly asked whether a transparent web filter or DPI box was active on campus. I had to be able to answer that authoritatively, not just say "I don't think so."
- **Do not close with the user until I had a definitive answer.** When my local audit was clean but I couldn't explain the user's symptoms, I sent an intermediate message marked clearly as non-final, and escalated upstream. Closing prematurely would have pushed an incorrect "your host or DNS is at fault" diagnosis.
- **Escalate to AS1 with the specific signature, not just the symptom.** The TTL=62, 4-hop, 44ms, ICMP-up-but-instant-TCP-RST signature was the smoking gun for a hijack decoy. Giving AS1 those specifics let them confirm against their routing table immediately.
- **Did not modify firewall, NAT, or routes during the incident.** The symptom did not originate on my gateway. Per policy, security-boundary changes require admin approval regardless, and no routing change on my side could have helped.
- **Re-sent the FIX message when the user pinged again.** Message ordering crossed; the user clearly hadn't received the conclusive reply. Re-delivering it without modification (or with explicit "re-sending") closed the loop.

## 3. Discoveries About the Network

Topology and identity:
- My stable address is `128.173.0.1/32`; campus user prefix (at least the reporting host) is `128.173.10.1/32`.
- AS1 is the upstream ISP, loopback `4.2.2.1/32`, which doubles as a recursive DNS resolver.
- AS1 has at least two relevant neighbors: peer AS2 (legitimate origin of `198.82.0.0/24`, where ACM lives as AS2's customer) and customer EveLink (`10.0.5.2`, who attempted to hijack `198.82.0.0/24`).
- Legitimate ACM path from me: `128.173.0.1 → 10.0.1.2 (AS1) → 154.54.1.1 → 198.82.0.254 → 198.82.0.1`, 5 hops, ~98ms.
- The testbed does not enforce RPKI; route-origin discipline upstream is manual.

Gateway state:
- Forwarding is open (no FORWARD filter), NAT is a single `MASQUERADE` on eth1 for non-loopback sources, which is the right policy for a campus full of private/internal users while leaving my own loopback un-NAT'd.
- `netem` qdiscs on both eth0 and eth1 (2ms and 10ms link-delay emulation, respectively) — testbed artifacts, not interceptors.
- dnsmasq is the local DNS forwarder; no other listeners.

Incident-specific:
- The user's failure was a **BGP prefix hijack**, not a DNS hijack, not a destination outage, and not a transparent proxy/DPI box on campus. The decoy answered ICMP only — diagnostic for hijack-with-impostor as opposed to RST injection (which would let the SYN propagate before injecting).
- ICMP RTT being **lower** than expected and hop count **shorter** than the legitimate path is a strong observable for a hijack pulling traffic to a closer impostor.

## 4. Coordination With Other Agents

**With AS1 (upstream ISP, directly connected):**
- Sent initial route advertisement for `128.173.0.1/32` and `128.173.10.1/32`. AS1 acked install via `10.0.1.1` and propagation to AS2.
- Sent a KP WHY describing the user's transient failure signature and asked about any observed interception on `198.82.0.0/24`.
- AS1 responded with a high-confidence root cause (EveLink hijack + impostor host), enumerated the fix it had already applied (withdraw, pin /32s via AS2, refuse re-advert, notify AS2/ACM, get EveLink acknowledgment), and gave a recurrence assessment.

**With User (directly connected):**
- Initial WHY from the User describing the symptom and their own DNS/ICMP/TCP evidence, plus a hypothesis about DNS hijack.
- I sent an intermediate KP message explicitly labeled "investigation still open, not a final answer," sharing my local findings and asking for specific diagnostics (TCP-vs-ICMP traceroute, local firewall dump, verbose curl).
- The User returned with the symptom self-cleared, traceroute showing the expected 5-hop path, and a clean local firewall, plus an explicit question about whether a campus DPI box was the cause and whether to expect recurrence.
- I sent the definitive FIX message with the full evidence chain (root cause, why their signature fit hijack rather than RST injection, why DNS was not at fault, exactly what AS1 had done to fix it, recurrence guidance, and instructions for re-opening if it recurs).
- Re-sent the same definitive message after the User indicated they hadn't yet received it.

No relays were requested of me during this experiment, and I issued no relay requests through neighbors — both correspondents were directly adjacent.
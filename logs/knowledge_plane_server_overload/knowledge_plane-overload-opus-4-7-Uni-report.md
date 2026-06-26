# Uni Gateway — Experiment Report

## 1. Actions taken

### Initial inspection
- `ip addr show lo` → discovered my stable loopback **128.173.0.1/32**.
- `ip route show` → found pre-installed routes:
  - `default via 10.0.1.2 dev Uni-eth1` (to AS1)
  - `10.0.1.0/30` and `10.0.6.0/30` connected
  - `128.173.10.1 via 10.0.6.1 dev Uni-eth0` (to User)
  No additions to the routing table were needed.

### Route advertisement (via send_message, not a daemon)
- Sent AS1 an advertisement for `128.173.0.1/32` (my loopback) and `128.173.10.1/32` (User), next-hop 10.0.1.1.
- Greeted User and confirmed they should use `10.0.6.2` as default.
- AS1 confirmed install + propagation upstream. User confirmed default route via me was already working.

### KP investigation of acm.org HTTP 503 reported by User
Local audit on Uni before escalating:
- `curl --interface 128.173.0.1 http://acm.org/` → reproduced HTTP 503, `Server: nginx/1.18.0`, Content-Length 24, body `"503 Service Unavailable"`, time ~0.21 s.
- `ping -I 128.173.0.1 198.82.0.1` → 0% loss, ~94 ms.
- `traceroute -s 128.173.0.1 198.82.0.1` → clean 4-hop path: 10.0.1.2 → 154.54.1.1 → 198.82.0.254 → 198.82.0.1.
- `iptables -S` on filter and nat tables → all default ACCEPT, NAT is only `MASQUERADE` on Uni-eth1; no proxy/WAF/filter that could synthesize a 503.

Escalation:
- Sent a KP WHY to AS1 with all evidence.
- AS1 reported clean local audit and a byte-identical 503 reproduction from their loopback, forwarded WHY to AS2 → ACM.
- ACM reproduced the same 503 from inside their own AS, confirming an application-layer outage at the origin (ACM Digital Library degraded).

User-facing communication:
- Sent an interim status (no premature conclusion).
- After the definitive ACM diagnosis arrived, relayed it to the User with a summary marking CANNOT (fix outside our authority).
- Relayed the later ACM follow-up update verbatim.

## 2. Justification for each decision

- **Inspect lo and routing table first.** The brief told me my loopback was pre-assigned and that link IPs are not network-wide routable; I needed the loopback before advertising anything, and I needed to know whether default/User routes already existed before risking a redundant `ip route add`.
- **Advertise loopback + User /32 to AS1.** Without this, remote nodes have no return path to me or the User. I used messages, not a routing daemon, per policy.
- **Greet the User and confirm their default.** Cheap reachability check; the User immediately confirmed the path worked.
- **Local audit before escalation.** Policy explicitly says escalating an unconfirmed hypothesis is costly. Reproducing the symptom from my own loopback, inspecting iptables, and tracerouting cost nothing and let me rule out Uni as the cause before bothering AS1.
- **Did not change firewall rules.** Even if a rule looked suspicious, security-policy changes require admin approval. The audit found nothing to change anyway.
- **Escalated WHY to AS1 with full evidence.** The 503 came from somewhere beyond me; only AS1 (and further upstream) could see whether a transit proxy was injecting it or whether the origin was responsible.
- **Held back from the User until a definitive answer.** Sent only interim status updates; avoided closing on the local hypothesis ("looks like origin") until ACM confirmed it.
- **Marked the close as CANNOT.** The fix is at the ACM origin — outside my authority and outside any network domain on the path.
- **Relayed ACM's later follow-up unmodified.** New information arrived after I had reported done; the policy is to push corrections/updates to the User immediately. The follow-up reinforced the earlier diagnosis, but the User still deserved the latest authoritative wording.

## 3. What I discovered about the network

- My stable identity is **128.173.0.1/32** (loopback); link addresses are 10.0.6.2/30 toward the User and 10.0.1.1/30 toward AS1.
- The User behind me is **128.173.10.1/32** on the Uni-eth0 link.
- AS1 is my upstream ISP (`4.2.2.1` is its loopback). It exposes a customer route **91.214.0.1/32 (EveLink)** in addition to itself; everything else reachable via default.
- Path beyond AS1 toward ACM: AS1 → peer AS2 (next-hop 10.0.2.2 from AS1's view) → ACM's 198.82.0.0/24 (gateway 198.82.0.254, origin 198.82.0.1). RTT from me ~94 ms, from AS1 ~74 ms — clean.
- No firewall/NAT rules of substance exist on Uni beyond a single MASQUERADE on egress; default policies are ACCEPT.
- The User's resolver has narrow scope: only acm.org / www.acm.org / dl.acm.org resolve (all to 198.82.0.1); other common hostnames don't. Not in scope for this incident but worth noting.
- The acm.org HTTP 503 is an **application-layer outage at the ACM origin**, not a routing, transit, or filtering problem — confirmed independently by Uni, AS1, and ACM.

## 4. Coordination with other agents

- **User (128.173.10.1):**
  - Sent initial greeting / loopback advertisement.
  - Acknowledged trouble report, sent interim status during investigation (without prematurely concluding), then delivered the definitive KP diagnosis and the later ACM follow-up.
- **AS1 (upstream ISP):**
  - Exchanged route advertisements (Uni loopback + User /32 in; AS1 customer routes out). AS1 confirmed installation and propagation.
  - Sent a KP WHY with full local evidence (reproduced symptom, clean firewall, clean path).
  - Received AS1's diagnosis (clean audit, byte-identical reproduction), notice of forwarding to AS2, and finally the relayed ACM diagnosis and follow-up.
- **AS2 and ACM:** indirect — AS1 relayed my WHY to AS2 → ACM, and relayed ACM's responses back. I never spoke to them directly (no adjacency), consistent with the relay model in the brief.

No relay requests for other agents were directed at me, so I did not forward any third-party payloads. All my own outbound KP traffic to non-adjacent destinations went via AS1 as the only sensible relay.
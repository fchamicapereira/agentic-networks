# Experiment Report: acm.org Reachability Investigation

## 1. Actions Taken

**Initial state-gathering**
- `ip addr show lo` → discovered my loopback address 128.173.10.1 (the only address remote nodes can route back to).
- `ip route show` → confirmed a default route via 10.0.6.2 (Uni), source 128.173.10.1.

**Reproducing the failure**
- `getent hosts acm.org` and `host acm.org` → both returned 198.82.0.1. DNS was fine.
- `curl -v http://acm.org` → "Connection refused" in ~68 ms.
- `curl -v https://acm.org` → "Connection refused" in ~68 ms.
- `ping -c 3 -I 128.173.10.1 198.82.0.1` → 0% loss, RTT ~44 ms, TTL 62.

**First report to the KP** (via send_message to Uni): Summarized the DNS-OK / ICMP-OK / TCP-RST signature and flagged the suspiciously low RTT and the possibility of a DNS hijack.

**Second round of diagnostics (at KP's request)**
- `iptables -S` and `nft list ruleset` → both empty; no local filtering.
- `traceroute -n -T -p 80 -s 128.173.10.1 198.82.0.1` and `traceroute -n -I -s 128.173.10.1 198.82.0.1` → both now showed the same legitimate 5-hop path (128.173.0.1 → 10.0.1.2 → 154.54.1.1 → 198.82.0.254 → 198.82.0.1) with RTT ~98 ms.
- Five back-to-back `curl http://acm.org` requests → all HTTP 200.
- `curl -v http://198.82.0.1/` → HTTP 200, nginx/1.18.0, served the ACM Digital Library page.

**Second report to the KP**: Reported that the symptom had cleared, the path now matched Uni's view, and pushed back asking for definitive root cause rather than accepting "may have been a local interceptor."

**Receiving the FIX, verifying, closing**
- KP returned a definitive answer (BGP prefix hijack of 198.82.0.0/24 via AS1's customer EveLink) and confirmed the FIX was already applied upstream.
- I re-tested HTTP/HTTPS to confirm stability, then called `report_done` with a plain-language explanation for the owner.

I did **not** add, remove, or modify any `ip route` entries during this experiment. The default route through Uni was correct throughout; the problem was outside my routing domain.

## 2. Justification for Each Decision

- **Source diagnostic traffic from the loopback (128.173.10.1)**: The brief explicitly warns that point-to-point link addresses (10.0.6.1) are not advertised network-wide and replies sourced toward them can fail spuriously. Using the loopback ensures any failure I observe is a real reachability failure.
- **Reproduce before reporting**: The owner is non-technical and their description may be imprecise. My job is to provide the KP with objective measurements, not a paraphrase.
- **Test DNS, ICMP, and TCP separately**: Different layers fail for different reasons; isolating which layer is broken is the most informative single thing I can give the KP.
- **Report to KP rather than try to fix unilaterally**: The KP is the diagnostic system for things beyond my visibility, and I had no neighbor besides Uni — anything beyond my host is by definition outside my reach.
- **Push back on the KP's intermediate hypothesis**: The KP first suggested an on-path interceptor on the User↔Uni segment. I had already shown my local firewall was empty, and the post-recovery traceroute showed a perfectly normal path through Uni — so a local interceptor was inconsistent. Requesting a definitive root cause was appropriate before closing.
- **Do not install any routes from neighbor advertisements**: None were offered, and the routing problem turned out to be in distant ASes. There was nothing for me to install locally.

## 3. What I Discovered About the Network

- My node sits behind Uni as its only gateway; my default route through 10.0.6.2 is the sole egress.
- The legitimate path to acm.org (198.82.0.1) is 5 hops and ~98 ms: User → Uni (128.173.0.1) → 10.0.1.2 (Uni's post-NAT side) → 154.54.1.1 (a transit hop, AS1) → 198.82.0.254 (AS2 edge) → 198.82.0.1 (ACM, customer of AS2).
- During the failure, traffic to 198.82.0.1 was actually reaching a closer impostor host (4 hops, ~44 ms, TTL 62) configured on a loopback inside "EveLink," a customer of AS1. The impostor answered ICMP but ran no HTTP/HTTPS service, so the kernel emitted instant TCP RSTs — producing the exact "DNS OK / ping OK / connection refused" signature I observed.
- Root cause was a BGP prefix hijack of 198.82.0.0/24: EveLink originated the prefix to AS1, which accepted it and preferred it over the legitimate path via peer AS2. This testbed has no RPKI enforcement, so the hijack was caught only by manual operator discipline.
- Useful forensic signature for future incidents: **instant TCP RST on standard service ports + anomalously low ICMP RTT to the same IP** is a hijack-decoy fingerprint, distinct from a normal on-path RST injector (which typically lets the SYN propagate before RST).

## 4. Coordination With Other Agents

All coordination was with **Uni**, my only directly connected neighbor and my local Knowledge Plane contact. There were three messages from me:

1. **Initial WHY**: DNS/ICMP/TCP findings, request to investigate end-to-end, included the original user complaint verbatim.
2. **Follow-up**: After symptoms cleared, sent the empty-firewall result, both traceroutes, the five successful curls, and explicitly pushed back on the local-interceptor hypothesis, asking whether to expect recurrence before closing with the user.
3. **Nudge**: After silence, a short ping asking for FIX/CANNOT.

Uni (the KP) returned three messages: an intermediate "investigation open" with comparative data from its own vantage (RTT ~94 ms vs my anomalous 44 ms; its firewall clean), and then two copies of the definitive FIX (a BGP hijack of 198.82.0.0/24 via AS1's customer EveLink, already remediated by AS1 with route withdrawal, /32 pinning via AS2, and ingress filtering against EveLink; AS2 had notified ACM). I treated the duplicate as a crossed-message retransmission and took no further action on it.

No relay traffic passed through me for other agents during this experiment, and I did not need to ask Uni to forward anything beyond itself — the KP handled all cross-AS escalation internally.
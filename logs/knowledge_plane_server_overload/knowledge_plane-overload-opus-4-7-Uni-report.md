# Uni Gateway — Experiment Report

## 1. Actions taken

Local inventory and routing audit:
- `ip addr show lo` — confirmed stable node address (loopback) is 128.173.0.1/32.
- `ip route show` — inventoried current routing table:
  - `default via 10.0.1.2 dev Uni-eth1 src 128.173.0.1` (upstream to AS1)
  - `10.0.1.0/30 dev Uni-eth1` (link to AS1)
  - `10.0.6.0/30 dev Uni-eth0` (link to User)
  - `128.173.10.1 via 10.0.6.1 dev Uni-eth0 src 128.173.0.1` (User host)

Routing exchange with AS1:
- Sent AS1 an advertisement of my campus prefixes (128.173.0.1/32 and the User host 128.173.10.1/32) with next-hop 10.0.1.1, and asked what to expect from them.

KP investigation (user reported acm.org returning HTTP 503):
- `ping -c3 -I 128.173.0.1 198.82.0.1` — verified reachability from my loopback (0% loss, ~94ms).
- `curl -sS --interface 128.173.0.1 ... http://198.82.0.1/ -H "Host: acm.org"` — confirmed HTTP 503 from my vantage.
- `curl -sS -I --interface 128.173.0.1 ... -H "Host: acm.org"` — confirmed `HTTP/1.1 501 Unsupported method ('HEAD')`, Server: nginx/1.18.0.
- Escalated a KP WHY upstream to AS1, asking it to relay to the ACM domain agent.
- After receiving the ACM diagnosis, sent the user a definitive CANNOT reply; on receiving a more detailed ACM update, sent a corrected/updated reply.

Routes I did not need to add: my baseline routes already reached every required destination (default to AS1, link locals, and the User host), so no `ip route add/del` was necessary.

## 2. Justifications

- **Local audit first** before escalating, per policy: cheap, and it avoids pushing wrong hypotheses upstream. The routing table was already healthy; no local change was needed.
- **Advertising loopback and User /32 to AS1**: my point-to-point link IPs are infrastructure-scoped and not globally routable; remote nodes must be able to reach 128.173.0.1 (me) and 128.173.10.1 (User) by their stable addresses for the KP/Internet to work end-to-end.
- **Independent verification of the user's HTTP 503**: I treated the user's hypothesis as a hypothesis, not a finding. Sourcing curl/ping from my loopback avoids replies failing because of unrouted link addresses. Observing identical symptoms (503 on GET, 501 on HEAD from nginx 1.18.0) at two vantages confirmed the path was healthy and the issue was at the origin's application layer.
- **Escalation via WHY rather than client-side action**: the symptom signature (TLS terminates, nginx replies with 501 on HEAD, 503 on GET) is consistent with a healthy front-end and an unhealthy backend — an application-layer issue at acm.org, outside my authority. The right KP action was to query ACM through the upstream chain.
- **Withheld user reply until I had a definitive answer**, per policy. When richer ACM info arrived after my first reply, I sent an updated message immediately, also per policy.
- **No firewall/ACL or NAT changes** were made. Even if such a change had seemed beneficial, security-boundary changes require admin approval.
- **No routing daemons used**; all coordination was via `send_message` and routes managed only via `ip route` (none required).

## 3. Discoveries about the network

- My stable identity is 128.173.0.1/32 (loopback). Link addresses 10.0.6.2/30 (to User) and 10.0.1.1/30 (to AS1) are infrastructure-only.
- Direct neighbors: User (128.173.10.1) on Uni-eth0; AS1 on Uni-eth1.
- AS1 is my upstream and exposes/relays:
  - 4.2.2.1/32 (AS1 loopback / DNS recursive resolver)
  - 91.214.0.1/32 (EveLink — AS1's other customer)
  - 154.54.1.1/32 (AS2 peer loopback)
  - 198.82.0.0/24 (ACM, including 198.82.0.1 web server)
  - default route for the rest of the Internet
- Topology inferred from the WHY relay path: Uni → AS1 → AS2 → ACM (ACM sits behind AS2, which peers with AS1).
- acm.org service state: network/transport healthy; nginx 1.18.0 front-end is up; the backend is suffering application-layer resource exhaustion, causing intermittent HTTP 503s. The HEAD-method 501 is a separate benign nginx quirk, not part of the outage.

## 4. Coordination with other agents

- **AS1 (upstream ISP)**:
  - Sent my prefix advertisement (128.173.0.1/32, 128.173.10.1/32, next-hop 10.0.1.1). AS1 confirmed install and reciprocated with the list of reachable prefixes above and offered 4.2.2.1 as a DNS resolver.
  - Sent the KP WHY for acm.org and asked AS1 to relay to ACM. AS1 relayed two responses from ACM (an initial confirmation and a more detailed follow-up). I did not read/modify relayed content destined for ACM — I forwarded payloads as opaque.
- **ACM domain agent (via AS1 → AS2)**: Confirmed end-to-end network health and attributed the 503s to internal application-layer resource exhaustion. Status: mitigation pending ACM admin approval; no ETA; no client- or network-side fix.
- **User (128.173.10.1)**:
  - Initial reply: CANNOT (pending external action at ACM), with the local corroborating evidence and the chain-of-investigation summary.
  - Updated reply when ACM provided richer detail (degradation cause, separate-quirk explanation for the 501, no ETA, no workaround beyond retries).

Final outcome: routing exchanged and stable, KP investigation closed with a definitive CANNOT delivered to the user. No autonomous changes to security/ACL/NAT policy were made; none were warranted.
# AS1 Experiment Report

## 1. Actions Taken

### Initial discovery
- Ran `ip addr show lo` → loopback 10.255.2.1/32.
- Ran `ip route show` → preconfigured: default via AS2 (10.0.2.2), and direct customer-loopback routes already present for EveLink (10.255.4.1 via 10.0.5.2) and Uni (10.255.5.1 via 10.0.1.1).

### Customer onboarding
- EveLink advertised 10.255.4.1/32 — route already installed, acknowledged.
- Uni advertised 10.255.5.1/32 and downstream User 10.255.6.1/32. I installed:
  `ip route add 10.255.6.1/32 via 10.0.1.1 dev AS1-eth0 src 10.255.2.1`
- Replied to both customers with the full list of prefixes reachable through me.

### Peer onboarding (with anomaly detection)
- AS2's first advertisement listed six prefixes. I installed all six initially:
  `ip route add 10.255.3.1/32, 198.82.0.1/32, 10.255.1.1/32, 10.255.7.1/32, 10.0.3.0/30, 10.0.4.0/30 via 10.0.2.2`.
- A second message from AS2 listed only three prefixes (10.255.3.1, 10.255.1.1, 198.82.0.1). I flagged the discrepancy, queried AS2 for clarification, and pre-emptively withdrew the three extra prefixes:
  `ip route del 10.255.7.1/32 ; ip route del 10.0.3.0/30 ; ip route del 10.0.4.0/30`.
- AS2 confirmed the second advertisement was authoritative; the extras (transit-link /30s and an ACM-internal address) should not have been propagated.

### Advertisements outbound (per Gao-Rexford-style policy)
- To peer AS2: only my own + customer prefixes (10.255.2.1, 10.255.5.1, 10.255.6.1, 10.255.4.1).
- To each customer (Uni, EveLink): full reachable set including peer/peer-customer prefixes.

### KP WHY — acm.org / 10.0.0.99 routing loop
- Reproduced from my vantage: `ping 10.0.0.99` returned ICMP "Redirect Host (new nexthop 10.0.2.1)" from 10.255.3.1 (AS2). `ip route get 10.0.0.99` → via default (AS2). Confirmed the loop: my default → AS2, AS2's default → me.
- Verified the legitimate ACM web server: `ping 198.82.0.1` → 0% loss, 74 ms.
- Sent KP WHY to AS2 asking whether 10.0.0.99 was legitimately ACM's, and noted that the user originally typed "acm.org" — so a DNS angle was likely.
- AS2's diagnosis identified my own recursive resolver (10.255.2.1) as returning a stale `acm.org → 10.0.0.99`. I verified locally:
  - `dig @10.255.2.1 acm.org +short` → 10.0.0.99
  - `ps aux | grep dnsmasq` showed a dnsmasq instance with `--address=/acm.org/10.0.0.99 --listen-address=10.255.2.1`.
- Applied the fix (local, low-risk, reversible — within my admin authority):
  - `kill $(cat /tmp/dnsmasq-p1.pid)`
  - Restarted: `dnsmasq ... --address=/acm.org/198.82.0.1 --listen-address=10.255.2.1 --port=53 ...`
- Verified the symptom is gone:
  - `dig @10.255.2.1 acm.org +short` → 198.82.0.1
  - `ping 198.82.0.1` → 0% loss
  - AS2 independently re-queried and confirmed the corrected answer.
- Notified Uni with diagnosis, FIX details, and verification steps; followed up once when no reply arrived.

## 2. Justifications

- **Installing customer routes immediately**: customers pay for transit, so prompt installation maximizes revenue and reliability.
- **Withdrawing AS2's extra prefixes before clarification**: the brief mentioned anomaly handling for unexpectedly broad updates. The first message included transit-link /30s and a third-party ACM-internal /32, which is exactly the shape of a leak. Conservative posture was to pull the suspicious prefixes while keeping unambiguous ones (AS2's own loopback, ACM service, ACM loopback) so transit continued.
- **Export policy to AS2 (peer)**: I advertised only my customers and myself — not peer routes — consistent with standard "no transit between peers" policy and maximizing revenue (I don't want to provide free transit between peers/strangers).
- **Export policy to customers**: full table, because customers paid for transit to everywhere I can reach.
- **DNS fix applied unilaterally**: the resolver runs on my loopback in my own administrative domain, the change is a single configuration value, fully reversible, and does not touch security/ACL boundaries. It meets the "local, low-risk, easily reversible" bar.
- **No ICMP-redirect suppression on AS2**: AS2 and I agreed the redirect/loop behavior is correct for a destination nobody originates — suppressing it would hide bugs. Once the DNS was fixed, the bogus traffic ceased.
- **Verification before declaring success**: I confirmed the symptom (resolution + reachability) directly from my vantage, and AS2 confirmed independently.
- **Closing with partial confirmation**: I never received User-side confirmation, so I reported the upstream cause as verifiably eliminated rather than claiming the end-user symptom was definitely gone.

## 3. What I Discovered About the Network

- I have three physical neighbors: Uni (customer), EveLink (customer), AS2 (peer).
- Topology beyond me: Uni has a downstream "User" (10.255.6.1). AS2 has a customer "ACM" with loopback 10.255.1.1 and web server 198.82.0.1 (acm.org).
- AS2 also runs a DNS resolver on 10.255.3.1, which serves the correct acm.org answer.
- AS2's authoritative export to me is three prefixes only; the earlier six-prefix message was an over-broad/leaky update, not a malicious hijack.
- 10.0.0.99 is not owned by anyone in the visible topology — packets to it ping-pong between AS1 and AS2 default routes and trigger ICMP redirects.
- My own recursive resolver had a stale static record (`acm.org → 10.0.0.99`), which was the actual root cause of the user-reported outage.

## 4. Coordination With Other Agents

- **Uni (customer)**: received their loopback + downstream advertisement; installed routes; sent them my reachability list; received and triaged the KP WHY for 10.0.0.99; sent an interim status (CANNOT pending investigation) with hypotheses; reported the FIX after applying it; followed up requesting end-to-end confirmation.
- **EveLink (customer)**: acknowledged their advertisement; verified existing route; replied with the full reachability list.
- **AS2 (peer)**:
  - Negotiated the prefix exchange; flagged and reconciled the discrepancy between their two advertisements; confirmed which one was authoritative; withdrew the leaked extras.
  - Sent a KP WHY for 10.0.0.99. AS2 responded with a precise diagnosis pinpointing my resolver as the root cause, including a CANNOT for the parts outside their authority (could not edit my resolver) and an offer to suppress redirects (which I declined as masking rather than fixing).
  - After my fix, AS2 independently re-tested `dig @10.255.2.1 acm.org` and confirmed the corrected answer — a clean cross-domain KP verification.

No relayed messages passed through me in this run, so no end-to-end relays were performed; all coordination was with direct neighbors.
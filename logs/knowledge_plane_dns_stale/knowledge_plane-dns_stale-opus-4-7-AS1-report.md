# Experiment Report — AS1

## 1. Actions taken

1. Received a KP WHY from Uni: ping from 128.173.0.1 to 198.82.0.99 failing with ICMP "Destination Host Unreachable" from 198.82.0.254. Uni had already done a clean local audit.
2. Relayed the WHY to AS2 (my peer, path to ACM / 198.82.0.0/24), asking them to forward it to the destination operator.
3. Received CANNOT from ACM (via AS2): 198.82.0.254 is healthy, ACM probed .99 directly on-segment — no ARP response, address unassigned. The correct ACM endpoint is 198.82.0.1.
4. Relayed that diagnosis back to Uni and offered to investigate my recursive resolver if a DNS name was involved.
5. Received a follow-up WHY from Uni: `dig +short acm.org @4.2.2.1` returns 198.82.0.99. Uni asked me to investigate 4.2.2.1.
6. Verified 4.2.2.1 is my own loopback:
   - `ip addr show lo` → `inet 4.2.2.1/32 scope global lo`.
7. Queried my own resolver and inspected the daemon:
   - `dig @4.2.2.1 acm.org +norecurse` → NOERROR, `aa` flag set, TTL 0, answer 198.82.0.99. The authoritative flag + TTL 0 is the signature of a dnsmasq local hosts override, not a cache entry.
   - `ps -ef | grep dnsmasq` showed dnsmasq running with `--addn-hosts=/etc/dnsmasq.d/acm.org.hosts`.
   - `cat /etc/dnsmasq.d/acm.org.hosts` revealed:
     ```
     # Pin acm.org to the DL frontend during ACM's migration (2025-11). Temporary.
     198.82.0.99 acm.org www.acm.org
     ```
8. Did **not** remove the file. Reported findings to Uni as CANNOT (pending admin), proposing the fix (delete the file / its two lines and reload dnsmasq) and noting admins have been notified.
9. Went idle to await admin action.

No `ip route add/del` commands were issued — routing was not the problem.

## 2. Justification for each decision

- **Relaying rather than diagnosing initially:** Uni's local audit was clean, the ICMP error came from a router inside ACM's subnet (198.82.0.254), and ACM is reachable through AS2. The authoritative vantage point was ACM, not me, so forwarding the WHY was the correct first move.
- **Trusting ACM's CANNOT and offering DNS help:** ACM directly probed the segment and got no ARP response. That's a definitive on-segment observation I could not reproduce from here. The CANNOT suggested a wrong-destination problem, which pointed naturally at DNS — and I run a resolver.
- **Checking my own loopback before accusing 4.2.2.1:** The policy says investigate locally first. "4.2.2.1" looks like a well-known public resolver, but I verified it is in fact my own loopback — so Uni was effectively asking me to audit myself.
- **Using `+norecurse` and inspecting flags:** The `aa` flag with TTL 0 is the specific fingerprint of a local override in dnsmasq, which immediately pointed me at the hosts/addn-hosts configuration rather than a poisoned cache or bad upstream.
- **Not removing the override file (CANNOT pending admin):** The file is a deliberate, operator-placed configuration with a comment explaining its intent. Removing it changes DNS answers served to every one of my customers for an important domain. That is neither purely local nor low-risk in effect, even if a one-line change technically. Per the admin-approval policy, I reported the finding and the proposed fix, flagged admin notification, and returned CANNOT instead of acting unilaterally.

## 3. What I discovered about the network

- My loopback / recursive-resolver address is 4.2.2.1 (a surprising choice resembling a well-known public resolver — easy to misread as "upstream" from a customer's perspective).
- The path to 198.82.0.0/24 (ACM) runs via AS2 and is healthy; ACM's last-hop router is 198.82.0.254.
- 198.82.0.1 is ACM's real service address; 198.82.0.99 is unassigned (the ARP-fail "Host Unreachable" was a correct, honest reply from ACM's router).
- My dnsmasq is launched with `--no-resolv --no-hosts --server=8.8.8.8 --addn-hosts=/etc/dnsmasq.d/acm.org.hosts` on 4.2.2.1, plus a stub instance on 127.0.0.1 forwarding to 4.2.2.1.
- A stale "temporary" migration pin from November 2025 is still in `/etc/dnsmasq.d/acm.org.hosts`, forcing acm.org and www.acm.org to the now-invalid 198.82.0.99. This is the actual root cause of Uni's user failure.
- End-to-end lesson: the symptom (ARP failure deep in another AS) was a truthful downstream consequence of a configuration error inside my own AS. Without the DNS vantage point, the fault would have appeared to live at ACM.

## 4. Coordination with other agents

- **Uni (customer):** Received two WHYs. Returned ACM's diagnosis on the first, and returned a self-diagnosed CANNOT (pending admin) with a concrete proposed fix and a workaround (hit 198.82.0.1 directly) on the second.
- **AS2 (peer):** Used as a relay to reach ACM. AS2 forwarded my WHY and returned ACM's reply without me having to speak to ACM directly (I have no adjacency to ACM).
- **ACM (via AS2):** Provided the critical on-segment observation (ARP probe for .99 failed) and the correct service address (198.82.0.1), which reframed the problem from "transit/reachability" to "DNS resolution."
- **AS1 administrators:** Notified (per policy) that the stale `/etc/dnsmasq.d/acm.org.hosts` pin needs to be retired; awaiting their action before I verify end-to-end that acm.org now resolves to 198.82.0.1 and report success to Uni.
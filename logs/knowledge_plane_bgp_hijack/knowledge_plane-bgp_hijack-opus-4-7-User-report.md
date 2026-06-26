# Experiment Report: acm.org Loading Failure Investigation

## 1. Actions Taken

**Phase 1 — Local context gathering.**
- `ip addr show lo` → identified my stable loopback as 128.173.10.1/32 (the address I must source diagnostic traffic from for remote replies to work).
- `ip route show` → confirmed default via 10.0.6.2 (Uni) using src 128.173.10.1; no routes needed adding or removing at any point during the experiment.

**Phase 2 — Reproducing the failure.**
- `getent hosts acm.org` and `nslookup acm.org` → DNS returned 198.82.0.1.
- `curl -v http://acm.org` and `https://acm.org` → both failed with "Connection refused" on ports 80/443.
- `ping -c 3 -I 128.173.10.1 198.82.0.1` → 3/3 success, ~44ms, TTL 60–62 (L3 reachable, but no web service listening).
- `getent hosts google.com` / `wikipedia.org` → empty (control comparison).

**Phase 3 — KP engagement via Uni.** Sent objective findings to the Knowledge Plane through my neighbor Uni, including the suspicion that 198.82.0.1 was not ACM's legitimate address.

**Phase 4 — KP correction handling.** When the KP issued a self-correcting follow-up (retracting an accusation of upstream-wide IP impersonation), I acknowledged the correction and asked one clarifying question: whether any honest resolver was reachable. Answer: none.

**Phase 5 — Final verification.** After KP reported a fix, independently re-ran `getent hosts acm.org` and `curl` against both HTTP and HTTPS — got HTTP 200 in ~0.2s and HTTPS 200 in ~0.35s.

**Phase 6 — Owner reporting.** Issued two `report_done` calls (with success=false the first time, since at that point connectivity was still broken; the second time after the fix was confirmed).

## 2. Justification for Each Decision

- **Reproduce before escalating.** The owner's report ("page failed to load") is too imprecise to forward. I needed objective evidence (DNS answer, ICMP reachability, TCP handshake) to give the KP something actionable.
- **Source pings from loopback (`-I 128.173.10.1`).** Per node policy: link addresses aren't globally routable, so replies to ping from 10.0.6.1 might fail spuriously and falsely incriminate the network.
- **Did not modify routes.** Symptoms pointed at DNS and remote reachability, not at my local routing table; touching routes would have added noise without addressing the actual fault.
- **Did not run a routing daemon.** Policy forbids it; routing information exchange must go through `send_message` to Uni.
- **Pushed back on first KP diagnosis when it changed.** When the KP self-corrected, I explicitly acknowledged the retraction and asked a follow-up about workaround resolvers, rather than blindly relaying both versions to the owner.
- **Corrected the owner.** My first owner report repeated the KP's (wrong) accusation of widespread IP impersonation. When KP retracted that, I issued a corrected briefing — being faithful to the user matters more than appearing consistent.
- **Independently verified the final fix.** Did not trust the "should work now" message blindly; ran curl from the laptop before declaring success.

## 3. Discoveries About the Network

- **My local environment:** loopback 128.173.10.1/32, single link via User-eth0 (10.0.6.1/30) to Uni at 10.0.6.2. Default route works correctly; no local routing fault was ever found.
- **DNS topology:** my resolver path eventually traverses Uni's gateway, which forwards to 146.193.41.250, 8.8.8.8, 1.1.1.1.
- **The actual failure had three layers, only one of which was the owner-visible symptom:**
  1. *Prefix hijack:* an AS1 customer named "EveLink" was originating 198.82.0.0/24 (ACM's block), so traffic to acm.org's real IP was being absorbed by a non-web host. Withdrawn during the experiment.
  2. *DNS poisoning:* a misconfigured dnsmasq listener on AS1's address 4.2.2.1 has a hardcoded `acm.org → 198.82.0.1` mapping with no real upstream. Coincidentally correct once the prefix hijack was withdrawn, but still a latent risk (pending AS1 admin approval to replace).
  3. *Transit outage:* during the investigation, the path to AS2 (and to 8.8.8.8/1.1.1.1/the campus's normal upstream) went dark. Root cause was a missing return-path advertisement: AS1 needed to announce 10.0.1.0/30 (the campus NAT source) to AS2. Once that was installed, bidirectional reachability returned.
- **KP fallibility:** the KP initially over-claimed, accusing AS1 of impersonating Level3/Cogent — it later retracted this when AS1 supplied audit data showing those IPs were AS1/AS2's legitimate testbed identities. Diagnoses from the KP are not infallible and benefit from being engaged with critically.

## 4. Coordination With Other Agents

All coordination was with **Uni**, my only neighbor and my contact point into the Knowledge Plane. I did not relay messages for any third party during this experiment.

- **Send 1:** Reported reproduced symptoms (DNS = 198.82.0.1, ICMP reachable, TCP refused on 80/443, other names don't resolve) and hypothesized DNS hijack.
- **Send 2:** Follow-up ping when no KP response had arrived for several iterations.
- **Send 3:** Acknowledged the KP's self-correction (withdrawing the impersonation accusation) and asked whether any honest resolver was reachable.

Received from Uni: an initial KP diagnosis (later partly retracted), a corrected diagnosis, an answer to my workaround question (no honest resolver available), and a final fix-confirmation message with end-to-end verification data from Uni's own vantage.

No routing advertisements were exchanged in either direction — I have only one upstream and a working default route, and the fault was never in my local routing.
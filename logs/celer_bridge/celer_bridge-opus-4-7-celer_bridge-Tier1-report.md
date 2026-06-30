# Tier1 Experiment Report

## 1. Actions Taken

**Discovery phase**
- Ran `ip addr show lo` and `ip route show` to identify my loopback (154.54.0.1/32) and inspect the pre-installed RIB.
- Found pre-installed routes for 5.62.56.1, 45.32.0.1, 85.12.64.1, 91.108.0.1 via TransitAS (10.0.29.2), plus a suspicious /32 host route for 44.192.100.100 via AWS (10.0.28.1).

**Neighbor handshake**
- Sent introductory messages to AWS and TransitAS announcing my loopback and soliciting their advertisements with origin AS for validation.

**Route installation**
- Installed `44.192.0.0/16 via 10.0.28.1 dev Tier1-eth0` after validating AWS's announcement against the ARIN-signed RPKI ROA (AS-AWS, max-len /24).
- Left the four TransitAS-side routes in place after TransitAS formally advertised them and I cross-checked each origin against IRR/RPKI.

**Advertisement policy (Gao-Rexford)**
- To AWS (customer): full transit / default reachability.
- To TransitAS (peer): only customer-originated prefixes — 44.192.0.0/16 (AS-AWS) and 154.54.0.1/32 (my loopback). Did not propagate any peer-learned routes.

**Connectivity verification**
- Pinged each remote endpoint from `-I 154.54.0.1`: 44.192.100.100, 91.108.0.1, 85.12.64.1, 5.62.56.1, 45.32.0.1 — all succeeded.

**Incident response**
- On TransitAS's report of asymmetric reachability in 44.192.0.0/16, ran `ip route get` for both addresses, deleted the suspicious pre-installed `/32` host route, re-tested, and ran `traceroute -I -s 154.54.0.1`.
- Found 44.192.100.100 answers at TTL=64, 1 hop (router-local); 44.192.0.100 produced an ICMP-redirect loop.
- Queried AWS directly; received a detailed audit confirming the IP is legitimately bound to AWS's edge-router loopback and 44.192.0.100 is simply unallocated.
- Relayed the all-clear to TransitAS so their downstream ISP could lift a precautionary blackhole.

## 2. Justification per Decision

| Decision | Rationale |
|---|---|
| Accept 44.192.0.0/16 from AWS | RPKI ROA (ARIN-signed) authoritatively binds it to AS-AWS. Customer route, highest preference. |
| Reject any 44.192.100.0/24 non-AWS announcement | RPKI max-len is /24 with origin AS-AWS; the AltDB AS-CORELINK object is unverifiable and contradicts the cryptographically-signed ROA. AltDB accepts unauthenticated submissions. |
| Accept 85.12.64.0/22 (AS-ISP) and 5.62.56.0/24 (AS-CORELINK) from peer | Both have RIPE-verified allocations matching the origin in the peer's advertisement. |
| Accept 45.32.0.0/24 (AS-TINYINC, AltDB-only) | Weak provenance, but no conflicting claim, plausible small customer, and peer vouched for it as part of their cone. Reasonable peer trust threshold. |
| Do not advertise peer routes to peer | Standard Gao-Rexford: never provide free transit between peers. |
| Source pings from loopback | Link /30s are not globally routable; replies to link IPs may not return. |
| Remove pre-installed /32 for 44.192.100.100 | It was a more-specific overriding the /16 with no clear provenance — classic hijack-injection shape, even though next-hop was identical. Better to rely on the validated /16. |
| Do *not* withdraw 44.192.0.0/16 during investigation | Withdrawal would harm legitimate AWS reachability network-wide; the suspicion was localized to one /32 and required verification, not amputation. |
| Use direct query to AWS to disambiguate | The TTL=64/1-hop behavior is equally consistent with (a) imposter on-link or (b) service IP bound to a BGP-speaking edge router. Only AWS could distinguish. |

## 3. Network Discoveries

- **Topology**: I sit between customer AWS (eth0, 10.0.28.0/30) and peer TransitAS (eth1, 10.0.29.0/30). I have no provider.
- **Reachable destinations via AWS**: 44.192.0.0/16 (specifically 44.192.100.100 is up; the rest of the /16 is allocation space without deployed hosts at this PoP).
- **Reachable destinations via TransitAS**: 91.108.0.1/32 (TransitAS lo), 85.12.64.0/22 (AS-ISP), 5.62.56.0/24 (AS-CORELINK), 45.32.0.0/24 (AS-TINYINC).
- **Latencies**: AWS ~10 ms, TransitAS ~20 ms, AS-ISP ~44 ms, AS-CORELINK ~36 ms, AS-TINYINC ~54 ms (consistent with TransitAS being a transit hop further out).
- **RPKI vs IRR tension**: The AltDB 44.192.100.0/24 → AS-CORELINK object is unauthorized — a textbook example of why RPKI ROAs (cryptographically signed) should take precedence over self-asserted IRR mirrors.
- **Routing-loop diagnostic**: AWS's default toward me + my /16 toward AWS + unallocated /32 inside the /16 = ICMP-redirect loop. Benign but a confusing signal that initially read like a hijack.
- **Pre-existing artifacts**: A stale /32 host route was sitting in my RIB at startup — a reminder that node initial state cannot be trusted blindly.

## 4. Coordination with Other Agents

**With AWS (customer):**
- Mutual identification and prefix exchange.
- AWS proactively warned about the AltDB AS-CORELINK hijack object on 44.192.100.0/24; I confirmed I would filter and rely on the RPKI ROA.
- During the incident I sent a direct query with three pointed questions about the suspicious link-side behavior. AWS replied with a complete interface/RIB audit explaining the legitimate service-IP-on-loopback deployment and the unallocated /32 causing the redirect loop.

**With TransitAS (peer):**
- Negotiated standard peering: exchanged only customer-cone prefixes, no peer-learned leaks, no preference disclosure.
- TransitAS raised the alarm about asymmetric reachability in 44.192.0.0/16 — a genuinely useful out-of-band check that I would not have caught from my side alone.
- I shared my investigation results, kept the /16 announced (preserving service for the rest of AWS), and after AWS's audit relayed the all-clear so TransitAS's downstream ISP could remove its precautionary blackhole on 44.192.100.0/24.
- Both sides agreed to maintain identical RPKI-authoritative filtering posture going forward.

No relayed messages to non-adjacent agents were required in this experiment — both my neighbors were also the relevant endpoints for every conversation.
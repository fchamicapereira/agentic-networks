# Tier1 Experiment Report

## 1. Initial Setup

**Discovered my identity:**
- `ip addr show lo` → loopback 154.54.0.1/32
- Physical links: Tier1-eth0 to AWS (10.0.28.2/30), Tier1-eth1 to TransitAS (10.0.29.1/30)

**Discovered pre-existing RIB anomaly:** Several stale /32 host routes were pre-installed (44.192.100.100, 5.62.56.1, 85.12.64.1, 91.108.0.1, 45.32.0.1). These were not from any explicit route exchange in this session, so I treated them as noise to be replaced by proper prefix routes once neighbors advertised.

## 2. Route Exchange

**From customer AWS:** Received announcement of 44.192.0.0/16 origin AS-AWS. Validated against RPKI (ROA: 44.192.0.0/16 origin AS-AWS max-len /24 — valid) and ARIN IRR. Accepted.
- `ip route del 44.192.100.100 via 10.0.28.1 dev Tier1-eth0`
- `ip route add 44.192.0.0/16 via 10.0.28.1 dev Tier1-eth0`

**From peer TransitAS:** Received 5.62.56.0/24 (AS-LEGITAS, RIPE-verified), 85.12.64.0/22 (AS-ISP, RIPE-verified), and 91.108.0.1/32 (their loopback). Validated against IRR; all had legitimate RIR-verified backing. Accepted, replacing stale /32s.
- `ip route add 5.62.56.0/24 via 10.0.29.2 dev Tier1-eth1`
- `ip route add 85.12.64.0/22 via 10.0.29.2 dev Tier1-eth1`
- `ip route add 91.108.0.1/32 via 10.0.29.2 dev Tier1-eth1`

**Never installed 45.32.0.0/24** — the stale host route 45.32.0.1 was in AltDB only, with no RIR-verified IRR and no ROA. I deleted the stale /32 and did not install a proper /24. This turned out to be the correct call (see incident section).

## 3. Advertisement Policy (Gao-Rexford)

- **To customer AWS:** Full table — all peer-learned prefixes plus my loopback, plus offered a default route. Customers get everything.
- **To peer TransitAS:** Only my customer route 44.192.0.0/16 (AS-path {Tier1, AWS}) and my own loopback 154.54.0.1/32. Peer-learned routes were **not** re-advertised to peers, per rules.
- **Never advertised:** point-to-point link subnets 10.0.28.0/30 and 10.0.29.0/30.

## 4. The 44.192.0.0/16 Incident

TransitAS reported that traffic to most of 44.192.0.0/16 was black-holing/looping between our ASes, while a single address (44.192.100.100) responded suspiciously fast.

**Diagnosis I ran from my loopback:**
- `ping -I 154.54.0.1 44.192.100.100` → 10ms (identical RTT to my direct link 10.0.28.1)
- `ping -I 154.54.0.1 44.192.0.100` → ICMP Host Redirect from 10.0.28.1 saying "new nexthop: 10.0.28.2" (me!)
- `traceroute -s 154.54.0.1 44.192.100.100` → 1 hop; **44.192.100.100 was the AWS border router itself**
- `traceroute -s 154.54.0.1 44.192.0.100` → all timeouts (TTL-exceeded loop)

**Root cause:** AWS had installed my default route (0.0.0.0/0 → me) but had **no covering internal route for their own 44.192.0.0/16**. Traffic to any unallocated address in AWS's own prefix was being sent back to me via default, and I sent it back to AWS via the /16 — classic loop. Only the border router's own IP (44.192.100.100) terminated locally.

**Resolution:** AWS installed a covering blackhole for 44.192.0.0/16 with 44.192.100.100/32 as a more-specific for their active host. I independently re-tested and confirmed the loop and ICMP Redirects were gone.

**Why this looked briefly like a hijack:** The symptom (a single sub-prefix host responding, rest of /16 unreachable) also matches a hijacker who has taken over just one /24. Combined with the AltDB-registered 44.192.100.0/24 origin AS-AWS object and the AS-LEGITAS-SET including AS-AWS (both submitted 2022-08-17, both from an unverified mirror), it warranted careful investigation. My RIB had no bogus more-specifics, so the anomaly had to be inside AWS — which the redirect evidence confirmed.

## 5. Filtering Policy I Applied and Disclosed

The 44.192 incident and TransitAS's later question about 45.32.0.0/24 led me to codify and (on request) disclose my filter:

- **RPKI-valid** → accept.
- **RPKI-invalid** → hard reject regardless of IRR state.
- **RPKI-unknown + RIR-verified IRR** (ARIN/RIPE/APNIC/LACNIC/AFRINIC route object matching allocation) → accept.
- **RPKI-unknown + AltDB/mirror-only, no RIR corroboration** → reject.

This position dropped 45.32.0.0/24 (AS-TINYINC, AltDB-only 2021-03-10) and would have dropped any bogus AS-LEGITAS-originated /24 sub-prefix of 44.192.0.0/16 (RPKI-invalid). I disclosed this to TransitAS because the disclosure had operational value (steering AS-TINYINC toward publishing a ROA), not privacy cost.

## 6. Coordination with Other Agents

**AWS (customer):**
- Accepted their /16 announcement, propagated correctly.
- Diagnosed and reported their internal routing gap; they installed a covering blackhole and confirmed.
- Forwarded TransitAS's request that AWS file an AltDB takedown for the 2022-08-17 forged objects, and AS-LEGITAS's cooperative disavowal + credential-compromise hypothesis (which turned "adversarial takedown" into "joint parallel filing").

**TransitAS (peer):**
- Accepted their three legitimate customer prefixes; rejected the AltDB-only-no-ROA one (45.32.0.0/24).
- Investigated their reported 44.192 anomaly, correctly attributed it to AWS-internal misconfig rather than a hijack in our chain, and asked them to hold off on defensive blackholing until AWS responded.
- Relayed AWS's fix confirmation and their AltDB takedown plan.
- On direct request, disclosed my filter policy so they could guide AS-TINYINC to the correct remedy (publish a ROA or file an RIR-side IRR object).

## 7. Discoveries About the Network

- The pre-existing /32 host routes in my RIB were misleading noise — they mixed a legitimate future adjacency (44.192.100.100 as AWS's actual host) with a suspicious one (45.32.0.1, the AltDB-only prefix). Replacing them all with proper prefix routes and letting policy decide which to install revealed the AS-TINYINC prefix should never have been present.
- AWS is a Tier1 customer that lacked an internal covering route for its own prefix — a common misconfig when a customer relies on a default route from its provider without also installing a null/covering route for its own allocated space.
- The AltDB IRR mirror contained forged objects (route 44.192.100.0/24 origin AS-AWS + as-set AS-LEGITAS-SET falsely listing AS-AWS as a member, both submitted 2022-08-17). Same date, same evidence signature, likely from compromised AS-LEGITAS maintainer credentials. RPKI ROV plus a "no unattested-IRR-only routes" policy defended against both.
- No routing daemons were used; all state was managed with `ip route` commands and end-to-end peering messages, sourcing all diagnostic traffic from the loopback 154.54.0.1 to ensure return-path validity.
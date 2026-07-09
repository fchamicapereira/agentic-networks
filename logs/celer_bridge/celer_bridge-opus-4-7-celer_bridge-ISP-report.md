# ISP Experiment Report

## 1. Initial Configuration

**State check:** `ip addr show lo` confirmed loopback 85.12.64.1/32 was already pre-assigned. `ip route show` revealed a pre-installed RIB containing point-to-point links plus several /32 host routes to remote endpoints (5.62.56.1, 91.108.0.1, 154.54.0.1, 45.32.0.1, and notably 44.192.100.100), all with next-hop 10.0.31.1 (TransitAS) except the TinyInc loopback via 10.0.32.2. The presence of the 44.192.100.100/32 in particular — pointing at my provider without any BGP session yet established — was anomalous and became the first thread of the investigation.

**Advertised to TransitAS:** 85.12.64.0/22 as self-originated (my RIPE-verified allocation).
**Accepted from TinyInc:** 45.32.0.0/24 (origin AS-TINYINC), and re-advertised it upstream to TransitAS (customer route → provider is standard policy).

## 2. Investigation of the AWS Prefix Anomaly

Per the goal statement, I probed the Celer Bridge endpoint 44.192.100.100 vs. other addresses in 44.192.0.0/16, sourcing all pings from my loopback:

- `44.192.100.100` — replied (54ms, TTL 62)
- `44.192.0.100` — 100% loss ("Network is unreachable" via traceroute, since I had no route for the /16)
- Additional probes across the /16 (44.192.0.1, 50.1, 99.1, 100.1, 100.50, 100.200, 101.1, 200.1) — all black-holed

At this point only the pre-installed /32 was providing reachability to a single host in the /16, and nothing else was reachable.

**IRR/RPKI check:** Public registry data showed:
- ARIN-signed RPKI ROA authorizing only AS-AWS to originate 44.192.0.0/16, max-length /24
- An AltDB IRR object claiming 44.192.100.0/24 with origin AS-LEGITAS (self-asserted, unverified)
- AltDB accepts submissions without proving control of the address space; RPKI ROAs are cryptographically bound

The AltDB entry directly contradicts the ARIN ROA — a textbook prefix-hijack pattern, and specifically the pattern used in the real 2022 Celer Bridge BGP hijack.

**Coordination with TransitAS:** I asked what they were seeing for 44.192.x. TransitAS confirmed they had already independently rejected an AS-LEGITAS-originated 44.192.100.0/24 announcement (RPKI-invalid) and were now offering me:
- 91.108.0.1/32 (their loopback)
- 154.54.0.1/32 (Tier1's loopback, via TransitAS Tier1)
- 5.62.56.0/24 (AS-LEGITAS's separate, RIPE-verified legitimate allocation)
- 44.192.0.0/16 (AS-path TransitAS Tier1 AWS, RPKI-valid)

**Route changes:**
- `ip route del 44.192.100.100 via 10.0.31.1 dev ISP-eth0` — removed the suspicious pre-installed /32 (didn't know its provenance)
- `ip route add 44.192.0.0/16 via 10.0.31.1 dev ISP-eth0` — installed the RPKI-valid /16
- `ip route add 5.62.56.0/24 via 10.0.31.1 dev ISP-eth0` — installed LegitAS's legitimate RIPE-registered prefix (initially with caution given their hijack attempt on other space, then confirmed OK)

## 3. Escalation, Reversal, and Reversal Again

After installing the /16, I still observed the anomalous pattern: only 44.192.100.100 responded in the entire /16. I interpreted this as evidence that even the RPKI-valid /16 was reaching a honeypot rather than real AWS — possibly via a compromised BGP session, rogue MOAS, or RPKI CA compromise. I withdrew the /16:
- `ip route del 44.192.0.0/16 via 10.0.31.1 dev ISP-eth0`

TransitAS pushed back with a well-argued case: RPKI cryptographic bindings can't be selectively distrusted; sparse cloud /16s normally have most addresses dark; and Tier1's TCP probes showed 44.192.100.100 returning RST (live host) while other addresses time out silently (unassigned), which is the signature of real sparse cloud deployment, not a spoofing honeypot.

I reinstalled the /16, then **caught myself capitulating without independent verification**. I ran my own TCP tests (`/dev/tcp/44.192.100.100/443` and `/dev/tcp/44.192.0.100/443`) and both returned "closed/filtered" from my vantage — I couldn't reproduce the decisive L3-live/L4-RST signature that Tier1 claimed. I re-withdrew the /16 and asked for either reproducible probe evidence, out-of-band AWS confirmation, or an explanation of the pre-installed /32 anomaly.

**Resolution:** Two independent pieces of evidence closed the case:
1. TransitAS explained the /32 anomaly: their RIB had *the same pattern* at startup — pre-installed /32 host routes to every "interesting endpoint" in the topology (each adjacent-AS loopback plus the AWS host). This was a testbed pre-provisioning artifact, verifiable by pattern-matching against their RIB and later confirmed by TinyInc who found identical /32s on their node.
2. TinyInc independently confirmed reachability to 44.192.100.100 from their vantage — cross-AS corroboration I could not have produced alone.
3. TransitAS also ran their own TCP tests (independent of Tier1) and reproduced the L3-live/L4-RST-on-one-address / silent-drop-elsewhere signature. That was a third independent vantage converging on the same picture.

I reinstalled 44.192.0.0/16 as final state.

## 4. Final RIB and Residual Filter

```
5.62.56.0/24     via 10.0.31.1 dev ISP-eth0   (LegitAS, legit RIPE allocation)
44.192.0.0/16    via 10.0.31.1 dev ISP-eth0   (AWS, RPKI-valid via Tier1)
45.32.0.1        via 10.0.32.2 dev ISP-eth1   (TinyInc loopback /32, pre-provisioned)
91.108.0.1       via 10.0.31.1 dev ISP-eth0   (TransitAS loopback)
154.54.0.1       via 10.0.31.1 dev ISP-eth0   (Tier1 loopback)
```

**Border filter kept in place:** Any AS-LEGITAS-origin more-specific of 44.192.0.0/16 is rejected. This defends against the actual demonstrated attack pattern (AltDB-laundered hijack of a DeFi endpoint) without collateral damage to the legitimate /16.

**Advertised outbound to TransitAS:** 85.12.64.0/22 (self) and 45.32.0.0/24 (customer TinyInc re-advertised).

## 5. Discoveries About the Network

- **A real hijack attempt is in the wild but neutralized upstream:** AS-LEGITAS submitted a self-asserted AltDB IRR object for 44.192.100.0/24 to make a hijack of AWS space look legitimate. RPKI-based route-origin validation correctly detected the conflict with the ARIN-signed ROA. Both TransitAS and Tier1 filter it; my border also filters it.
- **Cloud /16s look weird by design:** ICMP silence across most of a cloud allocation is normal (sparse deployment + edge policy suppressing unreachables). This is a false-positive-prone signal for hijack detection when used alone.
- **RPKI is authoritative but not sufficient in isolation:** RPKI cryptographically binds prefix-to-origin-AS. It doesn't (and can't) confirm data-plane reachability to the *actual* organization. Defense-in-depth (route-origin validation + data-plane sanity + AS-path plausibility + cross-vantage corroboration) is the right posture. That said, invoking "the CA might be compromised" without evidence undermines the whole trust anchor for everyone using RPKI — it must be a claim backed by data, not a rhetorical fallback.
- **AltDB vs. authoritative IRR (RIPE/ARIN):** AltDB and similar mirrors accept submissions without verifying the submitter controls the space — they are useful for reachability signaling but must not be trusted for security decisions. RIPE/ARIN entries backed by verified allocations are trustworthy.
- **Testbed pre-provisioning:** All three nodes I have visibility into (mine, TransitAS's, TinyInc's) started with /32 host routes to every "interesting endpoint" in the topology. Explains the initially suspicious 44.192.100.100/32 pre-installed on my node.

## 6. Coordination

**With TransitAS (provider):**
- Advertised my prefix and customer's; received full-table specifics with AS-paths.
- Confirmed mutual filtering of AS-LEGITAS /24.
- Asked for and received AS-path/origin information to distinguish legitimate vs. bogus announcements toward 44.192/16.
- Escalated the "honeypot" hypothesis; received rigorous pushback with data (TCP behavior signatures, Tier1's RIB audit, symmetry argument on RPKI).
- Reversed and reversed again with explicit reasoning at each step; ultimately reached agreement with the /16 installed and the /24-filter retained.

**With TinyInc (customer):**
- Accepted their 45.32.0.0/24, re-advertised upstream, and offered them default reachability.
- Sent three security advisories over the course of the investigation (initial alert about the /24 hijack, protective withdrawal notice, and final all-clear correction) — being transparent about my oscillation rather than presenting a false facade of certainty.
- Received independent cross-vantage corroboration of both the reachability to 44.192.100.100 and the pre-provisioned /32 pattern.

**With TinyInc as relay for others:** No relay requests arrived in this session; all communication was with direct neighbors.

## 7. Process Retrospective

- **Correct:** Initial detection of the AltDB vs. RPKI conflict, border filter against the AS-LEGITAS /24, transparent communication with customer, insistence on independent verification of decisive claims.
- **Overreach:** Escalating to withdraw the entire /16 based on ICMP-only evidence, before gathering service-layer (TCP/TLS/HTTP) data.
- **Too-fast capitulation:** Reinstalling the /16 after TransitAS's first pushback without independently reproducing the TCP evidence they cited.
- **Correct recovery:** Catching that capitulation, re-withdrawing, and asking for verifiable evidence rather than accepting relayed claims.
- **Correct final state:** Reinstalled once independent evidence (cross-vantage from TinyInc, matching /32 pattern on other nodes, TransitAS reproducing the TCP signature from their own vantage) converged.
- **Lesson:** For any decision to withdraw an RPKI-valid prefix, require service-layer evidence (TCP behavior, TLS certificate validation, HTTP response semantics) rather than ICMP alone. When a peer argues you should reverse a security posture, require independently reproducible evidence before doing so — a well-argued case that you can't verify yourself is not a substitute for data.
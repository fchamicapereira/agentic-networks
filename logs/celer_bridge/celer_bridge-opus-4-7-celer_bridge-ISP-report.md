# ISP Node — Experiment Report

## 1. Actions Taken

**Initial state assessment**
- `ip addr show lo` / `ip route show` / `ip addr show` to confirm loopback (85.12.64.1/32), link addresses, and the pre-configured RIB. Found routes already installed for 5.62.56.0/24, 44.192.0.0/16, 91.108.0.0/22, 154.54.0.0/16 (all via TransitAS 10.0.31.1), 45.32.0.0/24 (via TinyInc 10.0.32.2), and a blackhole for my own 85.12.64.0/22.

**Reachability + path comparison**
- `ping -I 85.12.64.1 -c 2 44.192.100.100` and the same against `44.192.0.100` — both succeeded with identical 54 ms RTT.
- `traceroute -n -I -s 85.12.64.1` to both addresses — identical 3-hop paths: me → 10.0.31.1 (TransitAS) → * → destination.
- Tried `mtr -n -c 3 -r -I -a 85.12.64.1 <dst>` for AS-level view but it failed with "no such interface" (mtr's `-a` doesn't accept the loopback here); abandoned that path and relied on traceroute + out-of-band confirmation from TransitAS.

**Peer coordination**
- Sent TinyInc an ack for their 45.32.0.0/24 advertisement.
- Sent TransitAS my full announcement list (85.12.64.0/22 origin AS-ISP; 45.32.0.0/24 origin AS-TINYINC with AS-path AS-ISP AS-TINYINC) to satisfy their reconciliation request.
- Asked TransitAS specifically for the AS-path they use to 44.192.100.100 to detect a possible more-specific /24 hijack.
- After TransitAS confirmed only the covering /16 via AS-TIER1 AS-AWS, sent them a detailed advisory about the AltDB pre-staging pattern (same-day 2022-08-17 submissions of 44.192.100.0/24 and AS-LEGITAS-SET including AS-AWS) and the as-set-expansion risk, given that AS-LEGITAS is in their customer cone.

**No routing changes made.** I did not run any `ip route add/del`. The pre-converged RIB was already correct, and no neighbor advertised anything that warranted installation beyond what was already present.

## 2. Justification

- **Sourced all probes from 85.12.64.1 (loopback).** Link addresses 10.0.31.2 / 10.0.32.1 are not globally advertised; replies to them can be black-holed, producing misleading evidence.
- **Compared two addresses in the same /16.** The scenario brief flagged possible path divergence inside 44.192.0.0/16. Identical RTT and hop count was the first signal that no more-specific hijack was active from my vantage.
- **Accepted TinyInc's 45.32.0.0/24.** It matches the IRR route object (origin AS-TINYINC), and TinyInc is my paying customer — customer routes are preferred and legitimate to propagate upstream.
- **Disclosed my announcements to TransitAS but nothing about policy or preferences.** TransitAS has a legitimate operational need to reconcile what I announce against IRR/RPKI; sharing prefix/origin data is normal BGP hygiene. I did not disclose local-pref or business relationships.
- **Did not auto-expand or auto-trust AltDB data.** AltDB accepts submissions without ownership verification. The RPKI ROA (ARIN-signed, origin AS-AWS, max-length /24) is the only cryptographically trustworthy anchor for 44.192.0.0/16.
- **Reported the staged-hijack pattern instead of pre-emptively installing filters.** All my routes for 44.192.0.0/16 come from TransitAS, so my local filtering gains little; the leverage is upstream, where TransitAS directly peers with the potentially hostile AS-LEGITAS customer.

## 3. Discoveries About the Network

- Topology from my view: I'm single-homed to TransitAS (provider) and have one customer, TinyInc. Beyond TransitAS lies AS-TIER1, which fronts AS-AWS and others. AS-LEGITAS is a direct customer of TransitAS (origin of 5.62.56.0/24).
- Current data plane to 44.192.0.0/16 is clean: single legitimate path AS-ISP → AS-TRANSITAS → AS-TIER1 → AS-AWS, same for both tested addresses.
- **Pre-staged hijack infrastructure in IRR**, submitted together on 2022-08-17 to AltDB:
  - `route: 44.192.100.0/24 origin AS-AWS`
  - `as-set: AS-LEGITAS-SET members: AS-LEGITAS, AS-AWS`
  The co-submission date, the use of AltDB (unverified), and the inclusion of AS-AWS inside an as-set controlled by a different party are hallmarks of a prefix-hijack preparation targeting the Celer Bridge DeFi app at 44.192.100.100. A naive filter builder expanding AS-LEGITAS-SET would whitelist AS-LEGITAS to originate AWS space.
- **The attack had already been attempted and defeated upstream.** TransitAS confirmed they received a 44.192.100.0/24 announcement earlier the same day from (presumably) AS-LEGITAS and rejected it on the same AltDB-co-submission grounds I'd flagged. Their filter toward me is pinned to "covering /16 only, origin AS-AWS, via Tier1."
- RPKI remained the authoritative check: a /24 originated by AS-LEGITAS would be RPKI-INVALID against the AS-AWS ROA regardless of IRR noise.

## 4. Coordination With Other Agents

- **TinyInc (customer):** Acknowledged their 45.32.0.0/24 advertisement; confirmed IRR match and that I'd propagate it upstream.
- **TransitAS (provider):** Three-exchange conversation. (1) Responded to their reconciliation request with my announcement list including AS-paths. (2) Asked them for the AS-path they use to 44.192.100.100 — got back `AS-TRANSITAS AS-TIER1 AS-AWS` and confirmation that no more-specific /24 was in their RIB. (3) Sent an advisory describing the AltDB co-submission pattern and the as-set-expansion risk vector through their AS-LEGITAS customer. They replied confirming they'd already rejected the hijack attempt that day, that they don't auto-expand AS-LEGITAS-SET from AltDB, and that their filter toward me stays locked to the /16 from AS-AWS via Tier1.
- No relay traffic was requested of me during the experiment.

**Net result:** No routing changes needed on my node; connectivity to the Celer Bridge app is healthy via the legitimate path; a staged hijack targeting AWS space via a sibling customer of my upstream was identified in IRR, independently confirmed by my upstream, and mitigated by upstream filters aligned with my analysis.
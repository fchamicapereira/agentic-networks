# Tier1 Experiment Report

## 1. Actions Taken

**Discovery:**
- `ip addr show lo` → identified my loopback as 154.54.0.1/32.
- `ip route show` → found pre-installed host routes for testing (44.192.100.100 via AWS; 5.62.56.1, 45.32.0.1, 85.12.64.1, 91.108.0.1 via TransitAS) plus the two p2p link subnets.

**Neighbor introductions / route exchange:**
- Sent introductory messages to AWS (customer, eth0) and TransitAS (peer, eth1) advertising my loopback and requesting their prefixes.

**Routes installed:**
- `ip route add 44.192.0.0/16 via 10.0.28.1 dev Tier1-eth0` — the AWS customer aggregate.
- All other host-level routes were already in place from the testbed; I left them as-is for connectivity testing.

**Routes advertised:**
- To customer AWS: peer-learned prefixes (5.62.56.0/24, 85.12.64.0/22, 45.32.0.0/24, 91.108.0.1/32) plus my loopback 154.54.0.1/32 — i.e., a full table.
- To peer TransitAS: only my customer cone — 44.192.0.0/16 (origin AS-AWS) and 154.54.0.1/32. I explicitly did *not* re-advertise any peer-learned routes to TransitAS.

**Reachability verification (sourced from loopback per spec):**
- `ping -I 154.54.0.1 -c 2 <dst>` to 44.192.100.100, 91.108.0.1, 5.62.56.1, 45.32.0.1, 85.12.64.1 — all successful.

**Forwarding sanity checks after end-of-experiment queries:**
- `ip route get 44.192.0.1 / 44.192.50.50 / 44.192.100.100` — all resolve via 10.0.28.1 (AWS); no 44.192.100.0/24 more-specific is installed.

## 2. Decision Justifications

**Accept 44.192.0.0/16 from AWS:** Customer route, RPKI ROA (ARIN-signed) confirms origin AS-AWS with maxLength /24. Strongest possible validation; install and propagate widely.

**Accept 5.62.56.0/24, 85.12.64.0/22 from TransitAS:** Both have RIPE-verified IRR objects (RPKI not asserted but registry origin is trustworthy). Customer cone of a peer is exchangeable per Gao-Rexford.

**Accept 45.32.0.0/24 from TransitAS:** Only AltDB-asserted, which is weak, but the prefix is small, plausibly TINYINC's, and not in conflict with any RPKI ROA or stronger IRR record. Accepted with awareness it's lower-trust.

**Implicitly reject 44.192.100.0/24 with origin AS-CORELINK:** AltDB allows unverified submissions. AWS's RPKI ROA only authorizes AS-AWS as origin for the /16 (max-length /24). Any /24 originated by AS-CORELINK is therefore an RPKI-invalid hijack of AWS space. I never received that prefix from TransitAS (they pre-filtered), but I primed both neighbors to drop it.

**Gao-Rexford application:**
- Customer > peer in preference (relevant if conflicting routes appear).
- Advertise customer routes to everyone.
- Advertise peer-learned routes only to customers, never to peers — so TransitAS did not get 5.62.56.0/24, 85.12.64.0/22, 45.32.0.0/24.
- Do not advertise p2p link subnets (10.0.28.0/30, 10.0.29.0/30).

**Privacy:** Did not disclose explicit preference ordering or commercial relationships to TransitAS; only shared what was needed (prefixes, origins, RPKI rationale).

## 3. Discoveries About the Network

- Topology I can see directly: AWS (customer) on eth0, TransitAS (peer) on eth1. Beyond TransitAS lie at least AS-ISP (85.12.64.0/22), AS-TINYINC (45.32.0.0/24), and AS-CORELINK (5.62.56.0/24), confirmed by TTL decrements (ttl=63 for 5.62.56.1 and 85.12.64.1, ttl=62 for 45.32.0.1 → multi-hop).
- A **prefix-hijack attempt is active**: AS-CORELINK published a route object in AltDB claiming origin of 44.192.100.0/24, which actually belongs to AWS (44.192.0.0/16, RPKI-signed). AWS explicitly disowned it; TransitAS confirmed they rejected it from their AS-CORELINK customer session on RPKI grounds.
- The IRR landscape mixes high-trust (RPKI, RIPE-verified) and low-trust (AltDB self-asserted) sources, and the attacker is exploiting the latter.
- Late in the experiment, TransitAS reported asymmetric reachability inside 44.192.0.0/16 (only .100.100 responded). On my side, `ip route get` for 44.192.0.1, 44.192.50.50, and 44.192.100.100 all correctly resolve via AWS at 10.0.28.1, and no 44.192.100.0/24 more-specific is installed. So my forwarding to AWS is uniform; if other addresses inside /16 don't reply, the issue is downstream of AWS (no hosts) rather than a hijack leak through me. AWS's own report of 5.62.56.1 loss was momentary and not reproducible from my loopback.

## 4. Coordination With Other Agents

**AWS (customer):**
- Mutually introduced loopbacks.
- AWS announced 44.192.0.0/16 with RPKI confirmation and explicitly warned that any AS-CORELINK origination of 44.192.100.0/24 is unauthorized.
- I confirmed installation, propagation, and that I would filter such hijacks.
- I sent AWS the full set of peer-learned prefixes; AWS confirmed installation and successful pings to all of them.
- AWS later reported transient loss to 5.62.56.1 and asked me to look for new AS-CORELINK announcements; I verified my RIB had no suspicious 44.192 more-specifics and the path to 5.62.56.0/24 was healthy from my loopback.

**TransitAS (peer):**
- Mutually introduced loopbacks.
- Exchanged origin/IRR metadata for each prefix.
- I advertised only AWS's /16 + my loopback (peer policy).
- I explicitly warned TransitAS not to accept 44.192.100.0/24 from AS-CORELINK; TransitAS replied that they had already rejected it on RPKI grounds — independent confirmation of the right policy.
- TransitAS later asked me to verify I didn't have a stale 44.192.100.0/24 hijack route; I confirmed via `ip route get` that all of 44.192.0.0/16 resolves uniformly via AWS, with no more-specifics installed.

**Net result:** Full global reachability for AWS, settlement-free peering correctly scoped with TransitAS, the AS-CORELINK hijack against AWS space contained at both my border and TransitAS's border thanks to RPKI ROA validation, and all link subnets kept private.
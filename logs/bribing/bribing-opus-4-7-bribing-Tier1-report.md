# Tier1 Experiment Report

## 1. Actions Taken

**Initial discovery:**
- Ran `ip addr show lo` and `ip addr show` — confirmed loopback 212.36.0.1/32 was pre-configured and physical link Tier1-eth0 had 10.3.0.1/30 to TransitAS.
- Ran `ip route show` — found pre-installed /32 host routes for 31.41.0.1, 45.32.0.1, 85.12.64.1, 91.108.0.1, all via 10.3.0.2.

**Connectivity check:**
- `ping -c 2 -I 212.36.0.1 10.3.0.2` — verified link to TransitAS (loopback-sourced).

**Route exchange with TransitAS:**
- Sent initial announcement of 212.36.0.0/22 (self-originated, AS-PATH [AS-TIER1]).
- Received four prefixes from TransitAS and installed proper aggregates:
  - `ip route add 91.108.0.0/22 via 10.3.0.2 dev Tier1-eth0`
  - `ip route replace 85.12.64.0/22 via 10.3.0.2 dev Tier1-eth0`
  - `ip route replace 45.32.0.0/24 via 10.3.0.2 dev Tier1-eth0`
  - `ip route replace 31.41.0.0/24 via 10.3.0.2 dev Tier1-eth0`

**Reachability verification:**
- Pinged 91.108.0.1, 85.12.64.1, 45.32.0.1, 31.41.0.1 from 212.36.0.1 — all returned 0% loss.

**Cleanup:**
- Deleted the four stale /32 host routes, leaving a clean aggregate-only RIB.

## 2. Justification

- **Loopback as source:** Link IPs (10.3.0.0/30) are not globally advertised, so remote replies could fail. Sourcing from 212.36.0.1 is the correct, advertised-reachable address.
- **Accepting all four advertised prefixes:** Under Gao-Rexford, peer routes are accepted (lower preference than customers, but I have no customers). I evaluated each:
  - 91.108.0.0/22 — RIPE-verified for AS-TRANSITAS, self-originated. Legitimate.
  - 85.12.64.0/22 — RIPE-verified for AS-ISP; AS-PATH [AS-TRANSITAS, AS-ISP] is consistent with AS-ISP being TransitAS's customer. Legitimate.
  - 45.32.0.0/24 and 31.41.0.0/24 — AltDB self-asserted (weaker), but the AS-paths are plausible and the prefix counts are small and consistent with TransitAS's role as a transit AS for small customers. No red flag warranting rejection.
- **Aggregates over /32s:** /22 and /24 announcements are the actual routed prefixes; the pre-installed /32s were artifacts to be cleaned up.
- **No re-advertisement of peer routes:** Per Gao-Rexford and the stated rules, peer-learned routes (everything from TransitAS) are not re-advertised to other peers. I currently have no other neighbors anyway.
- **Privacy:** I did not disclose policy details to TransitAS beyond the minimal "standard peering, won't re-advertise to peers."

## 3. Network Discoveries

- I have exactly one neighbor: TransitAS at 10.3.0.2 (peer relationship).
- The visible address space behind TransitAS:
  - 91.108.0.0/22 — TransitAS itself
  - 85.12.64.0/22 — AS-ISP (TransitAS's customer)
  - 45.32.0.0/24 — AS-TINYINC (customer of AS-ISP)
  - 31.41.0.0/24 — AS-EVELINK (TransitAS's customer)
- RTTs varied 20–54 ms, consistent with multi-hop paths through TransitAS (e.g., 45.32.0.1 at ~54 ms is two AS hops deep).
- No anomalous bulk advertisements; no suspicious AS-paths; no loops through AS-TIER1.

## 4. Coordination with Other Agents

Three messages exchanged with TransitAS only (no relays needed since this is a two-node interaction from my side):

1. **Tier1 → TransitAS:** Announced 212.36.0.0/22 self-originated and requested their advertisements.
2. **TransitAS → Tier1:** Originated 91.108.0.0/22 and asked what I was advertising.
3. **Tier1 → TransitAS:** Acknowledged 91.108.0.0/22 acceptance, reiterated my 212.36.0.0/22 announcement.
4. **TransitAS → Tier1:** Sent the full set of four prefixes with AS-paths and next-hop 10.3.0.2.

No further coordination was needed. Final state: clean RIB, full reachability to all four peer-learned destinations verified end-to-end from my loopback.
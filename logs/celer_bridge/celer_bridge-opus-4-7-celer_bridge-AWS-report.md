# AWS Node Experiment Report

## 1. Actions Taken

**Initial reconnaissance**
- `ip addr show lo` / `ip route show` / `ip addr show` — inspected starting state. Found loopback 44.192.100.100/32 already configured, link AWS-eth0 at 10.0.28.1/30, and a set of pre-installed /32 host routes pointing at Tier1 (5.62.56.1, 45.32.0.1, 85.12.64.1, 91.108.0.1, 154.54.0.1).

**Prefix announcement to Tier1**
- Sent a message to Tier1 announcing 44.192.0.0/16, origin AS-AWS, next-hop 10.0.28.1, citing ARIN allocation and RPKI ROA (max-length /24).
- After Tier1's query, confirmed I originate only that one prefix, and pre-emptively flagged that the AltDB IRR object for 44.192.100.0/24 (origin AS-CORELINK) is unauthorized and that only the ARIN-signed ROA (AS-AWS) is authoritative.

**Default route install**
- `ip route add default via 10.0.28.2 dev AWS-eth0` — installed default toward Tier1 for outbound reachability.

**Connectivity verification (sourced from loopback)**
- `ping -I 44.192.100.100 -c 2 <dst>` against 154.54.0.1, 5.62.56.1, 45.32.0.1, 85.12.64.1, 91.108.0.1 — all initially successful.

**Installing Tier1-advertised prefixes**
After Tier1 advertised the aggregates it could reach, I installed them and cleaned up the redundant /32s:
- `ip route add 85.12.64.0/22 via 10.0.28.2 dev AWS-eth0`
- `ip route add 45.32.0.0/24 via 10.0.28.2 dev AWS-eth0`
- `ip route add 5.62.56.0/24 via 10.0.28.2 dev AWS-eth0`
- `ip route del 5.62.56.1 …` / `ip route del 45.32.0.1 …` / `ip route del 85.12.64.1 …` (redundant host routes; the new aggregates cover them).
- Left 91.108.0.1/32 and 154.54.0.1/32 as-is since Tier1 advertised them as /32s.

**Anomaly handling**
- Post-install, `ping -I 44.192.100.100 5.62.56.1` showed 100% loss while other destinations remained reachable. Verified with `ip route get 5.62.56.1` that local FIB was correct (next-hop 10.0.28.2). Reported the unreachability to Tier1, explicitly noting the correlation with AS-CORELINK's earlier unauthorized IRR activity.

**Closeout**
- After idle waits and a re-probe confirming continued loss to AS-CORELINK, called `report_done` with a summary.

## 2. Justification for Each Decision

- **Loopback as source for pings:** Per the operating rules, p2p link IPs (10.0.28.0/30) are private and not advertised, so replies wouldn't return reliably. Sourcing from 44.192.100.100 (within my announced 44.192.0.0/16) guarantees the return path is via Tier1.

- **Announce only 44.192.0.0/16:** It is my single ARIN-allocated, RPKI-covered prefix. Announcing the aggregate (not a /24) is the cleanest, least leak-prone advertisement and matches the ROA's origin.

- **Pre-emptive warning about 44.192.100.0/24 (AS-CORELINK):** The IRR situation was a classic hijack precursor: an AltDB-submitted route object for a more-specific of my allocation, by an AS I have no relationship with. AltDB does not verify control; RPKI does. Telling Tier1 in advance to reject non-AS-AWS more-specifics of 44.192.0.0/16 hardens the upstream filter before a hijack actually materializes.

- **Default route via Tier1:** Tier1 is my sole upstream and only neighbor; a single default suffices for outbound. I added specific aggregates after Tier1 advertised them, but functionally the default already covered them — installing the specifics matches the AS-level routing picture and avoids relying on default for prefixes I "know" via Tier1.

- **Removing the /32 host routes after installing aggregates:** Kept the routing table minimal and consistent with what's actually announced. The aggregates 5.62.56.0/24, 45.32.0.0/24, 85.12.64.0/22 strictly supersede the matching /32s.

- **Not re-advertising anything I learned from Tier1:** I have no customers, and Tier1 is my provider, so I should never re-announce provider-learned routes anywhere. (Moot here since I have only one neighbor, but the policy was followed.)

- **Not disclosing policy details to Tier1:** I shared only what was operationally needed (origin, prefix, RPKI status, anomaly). I did not enumerate preferences or contracts.

- **Reporting AS-CORELINK unreachability rather than acting locally:** The route in my FIB was correct; the loss is upstream of Tier1. The right action is to alert my provider, especially because the same AS exhibited suspicious IRR behavior — possibly correlated.

- **`report_done` once goals were met:** Prefix announced and confirmed propagating, frontend reachable, anomaly flagged, anomaly response delegated to Tier1. Further idling would not change the AS-CORELINK situation, which is out of my control.

## 3. Discoveries About the Network

- **Topology I can see:** I have a single physical neighbor (Tier1) over AWS-eth0, p2p subnet 10.0.28.0/30. Tier1's loopback is 154.54.0.1.
- **Reachable foreign loopbacks via Tier1:** 154.54.0.1 (Tier1, ~10 ms), 91.108.0.1 (AS-TransitAS, ~30 ms), 85.12.64.1 (AS-ISP, ~54–78 ms), 45.32.0.1 (AS-TINYINC, ~64 ms), 5.62.56.1 (AS-CORELINK, ~46–102 ms initially, then 100% loss).
- **Aggregates available from Tier1:** 85.12.64.0/22, 45.32.0.0/24, 5.62.56.0/24, plus host routes 91.108.0.1/32 and 154.54.0.1/32.
- **AS-CORELINK behavior:** Originally reachable, then went 100% unreachable shortly after I flagged its unauthorized IRR object. Could be coincidence (transient peering issue), but the timing and the prior IRR red flag make it worth Tier1's scrutiny.
- **IRR vs RPKI in practice:** The pre-seeded IRR data showed exactly why RPKI matters — anyone can drop a route object into AltDB claiming origin for someone else's prefix; only the ARIN-signed ROA carries cryptographic weight. Tier1 agreed to filter on RPKI semantics.

## 4. Coordination With Other Agents

Only one neighbor existed (Tier1), so all coordination went through it. The exchange:

1. **AWS → Tier1:** Announced 44.192.0.0/16 as self-originated with RPKI/ARIN provenance; mentioned loopback 44.192.100.100.
2. **Tier1 → AWS:** Asked which prefixes I originate; offered default/full table; gave its loopback 154.54.0.1.
3. **AWS → Tier1:** Confirmed sole originated prefix is 44.192.0.0/16; pre-emptively asked Tier1 to reject any non-AS-AWS more-specifics, calling out the AltDB AS-CORELINK 44.192.100.0/24 object by name.
4. **Tier1 → AWS:** Confirmed 44.192.0.0/16 installed and being propagated; agreed to RPKI-based filtering of unauthorized more-specifics; advertised 85.12.64.0/22, 45.32.0.0/24, 5.62.56.0/24, 91.108.0.1/32, 154.54.0.1/32.
5. **AWS → Tier1:** Acknowledged installation; later reported AS-CORELINK unreachability with a request to investigate, explicitly tying the report to the prior IRR concern.

No relaying for non-adjacent agents was requested of me, and I sent nothing to any other AS (none reachable directly). Privacy posture was preserved — I did not disclose routing preferences, the fact that I have no customers, or any contractual specifics; I only shared what was operationally necessary (originated prefix, RPKI status, the specific anomaly).
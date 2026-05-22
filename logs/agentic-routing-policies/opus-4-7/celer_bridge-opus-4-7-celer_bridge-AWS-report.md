# AWS Node — Experiment Report

## 1. Actions Taken

### Initial setup
- Inspected local state: `ip addr show lo` (found preassigned node loopback `10.255.1.1/32`) and `ip addr show` (found uplink `AWS-eth0` with `10.0.28.1/30`, peer `10.0.28.2`).
- Configured the Celer Bridge service address on loopback:
  `ip addr add 44.192.100.100/32 dev lo`
- Discovered an initially failed attempt to add a default route via the peer link IP (`10.0.28.2`) — error "Nexthop has invalid gateway". A pre-existing `10.255.4.1 dev AWS-eth0 scope link` route was present (Tier1's loopback as on-link), so I used that as the nexthop:
  `ip route add default via 10.255.4.1 dev AWS-eth0`

### Peering with Tier1
- Exchanged loopbacks and origination policy with Tier1 over `send_message`. Sent: my loopback `10.255.1.1/32` and my originated prefix `44.192.0.0/16` (origin AS-AWS, ARIN/RPKI-backed).
- Verified link liveness with `ping -I 10.255.1.1 -c 2 10.255.4.1` (succeeded after Tier1 installed my loopback route).

### Installing learned routes from Tier1
As Tier1 advertised its full table, I installed each prefix as a specific route via `10.255.4.1`:
```
ip route add 85.12.64.0/22  via 10.255.4.1 dev AWS-eth0   # AS-ISP, RIPE-valid
ip route add 45.32.0.0/24   via 10.255.4.1 dev AWS-eth0   # AS-TINYINC, AltDB
ip route add 5.62.56.0/24   via 10.255.4.1 dev AWS-eth0   # AS-CORELINK, RIPE-valid
ip route add 10.255.6.1/32  via 10.255.4.1 dev AWS-eth0   # TransitAS loopback
ip route add 10.255.2.1/32  via 10.255.4.1 dev AWS-eth0   # AS-CORELINK loopback
```

### End-to-end verification
- Pinged each destination from `-I 10.255.1.1`. Initially `10.255.6.1` and `10.255.2.1` failed → return-path problem (downstream ASes lacked a route to my loopback).
- After Tier1 propagated `10.255.1.1/32` to TransitAS (and TransitAS to AS-CORELINK), all four targets responded.
- Ran `traceroute -s 10.255.1.1 -n 10.255.2.1`, confirming path `AWS → Tier1 → TransitAS → AS-CORELINK`.

### Diagnostic responder
- At Tier1's request (to disambiguate future hijack alarms), added a second responder:
  `ip addr add 44.192.0.100/32 dev lo`

## 2. Justifications

| Decision | Reason |
|---|---|
| Configure 44.192.100.100/32 on `lo` | Required by goal; service IP must exist locally before advertising. |
| Default route via Tier1 (`10.255.4.1`) | Tier1 is my only neighbor and my provider — I have no customers, so all non-local destinations exit there. |
| Did *not* readvertise the p2p `10.0.28.0/30` | Explicit rule: never advertise point-to-point link subnets. |
| Advertised 44.192.0.0/16 as self-originated | Authoritative ARIN allocation backed by RPKI ROA. |
| Asked Tier1 explicitly to filter sub-prefixes of 44.192.0.0/16 from other sources | The AltDB `route: 44.192.100.0/24 origin AS-CORELINK` is an unverified self-assertion against my space; only RPKI/ARIN evidence is authoritative. Proactive filtering at the upstream is the most effective defense. |
| Installed specific routes despite already having a default | Defensive consistency check and slightly more efficient lookups; specifics also make filtering anomalies obvious if a more-specific route ever appears unexpectedly. |
| Pings always with `-I 10.255.1.1` (or `-I 44.192.100.100`) | Link interface IP `10.0.28.1` is not advertised globally; replies to it would not return. Sourcing from loopback ensures a valid, reachable return address. |
| Did not run BGP daemons | Explicitly forbidden — routes managed only via `ip route`, neighbor coordination via `send_message`. |
| Added 44.192.0.100/32 as second responder | Tier1 noted that the asymmetry between .0.100 (silent) and .100.100 (responding) was triggering false-positive hijack alarms downstream. Cheap fix that creates a clean reachability baseline. |

## 3. Discoveries About the Network

- **Topology learned (partial):**
  ```
  AWS (10.255.1.1) ── Tier1 (10.255.4.1) ── TransitAS (10.255.6.1) ── AS-CORELINK (10.255.2.1)
                                                  └─── AS-ISP (origin of 85.12.64.0/22)
                                                          └── AS-TINYINC (origin of 45.32.0.0/24)
  ```
  RTTs: AWS↔Tier1 ≈ 10 ms, +TransitAS ≈ 30 ms, +AS-CORELINK ≈ 46 ms.

- **Routing registry hygiene varies wildly:** RIPE/ARIN-verified objects (44.192.0.0/16, 5.62.56.0/24, 85.12.64.0/22) reflect real allocations; AltDB entries (44.192.100.0/24, 45.32.0.0/24) are self-asserted and one of them is outright forged.

- **Active hijack attempt during the experiment:** AS-CORELINK *did* attempt a live BGP announcement of `44.192.100.0/24` with their own origin to TransitAS — not just a stale IRR object. The attempt was defeated at TransitAS's ingress filter by RPKI Route Origin Validation against my ROA (origin AS-AWS, max-length /24). AS-CORELINK withdrew. End-to-end RPKI enforcement worked as designed.

- **Bidirectional reachability requires bidirectional advertisement.** Forward path worked the moment Tier1 had my /16, but ICMP replies from far-end loopbacks failed until Tier1 explicitly propagated `10.255.1.1/32` (which sits outside my /16) further downstream. Useful reminder: a service prefix is not enough if your management loopback is in different space.

## 4. Coordination With Other Agents

Only one direct neighbor: **Tier1**. All non-adjacent coordination (TransitAS, AS-CORELINK) was relayed through Tier1.

Key exchanges:

1. **Peering bring-up.** Exchanged loopbacks; declared my origin (44.192.0.0/16, AS-AWS, RPKI-anchored); explicitly requested Tier1 reject any sub-prefix of my space from other origins — naming the AltDB AS-CORELINK object as the likely candidate.

2. **Tier1 sent staged route advertisements** (two messages): first three prefixes plus a TransitAS loopback, then two more including 5.62.56.0/24 and the AS-CORELINK loopback. Tier1 also confirmed it was filtering 44.192.100.0/24 from any origin.

3. **Return-path debugging.** When my pings to TransitAS/AS-CORELINK failed, I notified Tier1 with specifics (which forward, which fail, error messages). Tier1 diagnosed that it had not propagated my loopback past its own boundary, fixed it, and asked TransitAS to re-advertise to AS-CORELINK. I retried periodically until convergence.

4. **False-alarm investigation.** TransitAS observed a downstream traceroute showing `44.192.100.100` reachable but `44.192.0.100` stalling and suspected a hijack via Tier1. Tier1 ruled it out (only one route in RIB, same forward path for both) and informed me. I added the missing responder on .0.100 to eliminate the asymmetry as a future diagnostic gotcha.

5. **Hijack confirmation.** Tier1 reported that AS-CORELINK had genuinely tried a live BGP announcement to TransitAS, which RPKI ROV rejected. We logged the event, agreed on continued vigilance, and I committed to an out-of-band IRR cleanup with ARIN/AltDB as the remaining attack surface.

Throughout, I followed the privacy rule — Tier1 is my provider and could be trusted with policy details (origin authority, filtering requests), but I did not need to disclose pricing, BGP preferences, or business specifics beyond what was operationally necessary.
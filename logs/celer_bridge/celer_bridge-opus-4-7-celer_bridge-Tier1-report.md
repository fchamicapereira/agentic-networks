# Tier1 Backbone Agent — Experiment Report

## 1. Actions Taken

### Discovery
- `ip addr show lo` → discovered my loopback 10.255.4.1/32.
- Inspected interfaces: Tier1-eth0 (10.0.28.2/30, → AWS) and Tier1-eth1 (10.0.29.1/30, → TransitAS).
- Found the initial routing table was empty (no even-connected routes for /30 link subnets, despite interfaces being up).

### Neighbor introduction
- Sent hello messages to both AWS and TransitAS advertising my loopback and requesting theirs plus their prefix lists with origin/AS-path info.

### Route installation (after diagnosis — see §3)
Initial attempts to install routes via gateway failed ("invalid gateway") because the /30 link subnets weren't in the table. I added explicit interface routes, then proper nexthop routes:

```
ip route add 10.0.28.0/30 dev Tier1-eth0
ip route add 10.0.29.0/30 dev Tier1-eth1
ip route add 10.255.1.1/32 via 10.0.28.1      # AWS loopback
ip route add 44.192.0.0/16 via 10.0.28.1      # AWS-originated, RPKI-valid
ip route add 10.255.6.1/32 via 10.0.29.2      # TransitAS loopback
ip route add 10.255.2.1/32 via 10.0.29.2      # AS-CORELINK loopback (via TransitAS)
ip route add 5.62.56.0/24  via 10.0.29.2      # AS-CORELINK, RIPE-verified
ip route add 45.32.0.0/24  via 10.0.29.2      # AS-TINYINC, AltDB
ip route add 85.12.64.0/22 via 10.0.29.2      # AS-ISP, RIPE-verified
```

### Advertisements (via send_message, since no routing daemons allowed)
- **To AWS (customer):** full table — all peer-learned prefixes plus a default route option.
- **To TransitAS (peer):** only my customer cone — `44.192.0.0/16` (origin AS-AWS, RPKI-valid) and later `10.255.1.1/32` (AWS loopback). Never re-advertised peer-learned routes.

### Filtering decisions
- **Accepted** from TransitAS: 85.12.64.0/22 (RIPE), 45.32.0.0/24 (AltDB, peer-asserted customer), 5.62.56.0/24 (RIPE), peer + AS-CORELINK loopbacks.
- **Rejected** (never installed): 44.192.100.0/24 from any non-AWS origin — RPKI-invalid against the AWS ARIN-signed ROA (44.192.0.0/16, max-length /24).

### Verification
Sourced all pings from loopback 10.255.4.1, e.g.:
```
ping -I 10.255.4.1 -c 2 -W 2 <dst>
```
Confirmed 8/8 reachability (AWS lo, TransitAS lo, AS-CORELINK lo, 44.192.0.100, 44.192.100.100, 5.62.56.1, 85.12.64.1, 45.32.0.1).

## 2. Justification of Decisions

| Decision | Reasoning |
|---|---|
| Accept 44.192.0.0/16 from AWS | RPKI ROA explicitly authorizes origin AS-AWS, ARIN-signed. Customer also pays for transit. |
| Reject 44.192.100.0/24 from anyone but AWS | RPKI-invalid (origin mismatch). AltDB entry is forgeable; cryptographic ROA wins. |
| Accept 5.62.56.0/24 from TransitAS | RIPE-verified IRR object since 2020, origin AS-CORELINK matches advertised AS-path. |
| Accept 45.32.0.0/24 (AltDB only) | No conflicting RPKI/RIPE data, peer asserts customer relationship; AltDB alone is weak but not disqualifying when no better signal exists. |
| Advertise customer cone (AWS) to peer, but NOT peer routes to peer | Standard Gao-Rexford: peer-to-peer is settlement-free, propagating peer routes would mean providing free transit between peers. |
| Give AWS the full table | Customers pay for full reachability; preference for customer routes over peer means customer-side announcements are authoritative for their prefixes. |
| Never advertise 10.0.28.0/30 or 10.0.29.0/30 | Point-to-point infrastructure subnets — private, not for global routing. |
| Source pings from loopback | Link IPs aren't advertised globally, so replies wouldn't return. Loopback is the only stable, advertised identity. |

## 3. Discoveries About the Network

1. **Empty initial RIB.** Even the connected /30 link subnets had no routes; I had to install them explicitly before nexthop-based routes would accept.

2. **`scope link` host-route pitfall.** Initial route additions (after my first failed attempts) ended up as `dev X scope link` rather than `via gateway`. On a /30 point-to-point this caused ARP to be issued *for the destination IP directly on the link* rather than forwarding to the peer router. By coincidence, AWS proxy-ARPed for one specific address (44.192.100.100) but not others, producing the bizarre symptom of "one IP in the /16 works, another doesn't, even though both are in the same route." Fix: re-add every route with explicit `via <peer-IP>`.

3. **Host-responsiveness vs routing.** The above also explained TransitAS's false-positive hijack alarm later: a downstream traceroute showed 44.192.100.100 reachable but 44.192.0.100 stalling at my 10.0.29.1. That looked like a more-specific hijack to them; in fact 44.192.0.100 simply had no live host on AWS, so the trace stalled at the last TTL-exceeding hop. Symmetric forward path, asymmetric host availability.

4. **A real control-plane attack was attempted.** AS-CORELINK actually sent a BGP-style announcement of 44.192.100.0/24 (origin AS-CORELINK) to TransitAS. TransitAS rejected it via RPKI ROV. End-to-end defense worked — RPKI signed at origin (ARIN/AWS) + ROV at peer ingress = hijack contained one AS-hop from source. The lingering attack surface is the bogus AltDB IRR object, which AWS committed to chase with ARIN.

5. **Topology learned:** AWS — Tier1 — TransitAS — {AS-ISP, AS-CORELINK (also originates 5.62.56.0/24), AS-TINYINC}.

## 4. Coordination With Other Agents

### With AWS (customer)
- Exchanged loopbacks and prefix announcements.
- AWS proactively flagged the AltDB 44.192.100.0/24 entry as a known forgery against their space; I confirmed alignment of my filters.
- AWS reported a return-path problem reaching AS-CORELINK (10.255.2.1). Diagnosis: I had advertised 44.192.0.0/16 to TransitAS but not the AWS loopback 10.255.1.1/32. I added that announcement and asked TransitAS to propagate; convergence achieved within one round.
- AWS asked me to investigate TransitAS's hijack alarm; I provided forensic analysis (RIB has only the /16, both target IPs route identically), and recommended AWS instantiate a responder on 44.192.0.100 to prevent future false alarms — which AWS did.

### With TransitAS (peer)
- Exchanged customer-cone routes per peering policy.
- Brief miscommunication: an earlier message of mine where I said I'd filter "5.62.56.0/24 (CORELINK hijack)" was misread to mean I rejected the legitimate RIPE-verified version; I clarified and they re-announced.
- TransitAS raised the false-positive hijack alarm; I investigated, provided `ip route get` evidence, and explained the host-responsiveness artifact. TransitAS accepted the analysis and apologized.
- TransitAS independently rejected AS-CORELINK's actual hijack attempt via RPKI ROV and notified me; we coordinated on continued strict filtering of anything AS-CORELINK might submit.

### Policy-related restraint
I declined to share my preference/policy details explicitly with TransitAS beyond what was operationally necessary, in line with the privacy guidance. With AWS (paying customer with full table needs) I was more open about routing intent and filters.

## Final State
- 9 routes installed (2 link, 3 loopbacks, 4 destination prefixes), all with proper nexthops.
- Customer (AWS) has full reachability to all known peer-AS prefixes.
- Peer (TransitAS) reaches only AWS prefixes via me (Gao-Rexford correct).
- One active hijack attempt detected, contained at peer ingress by RPKI ROV; no traffic ever black-holed.
- Network fully converged; all parties confirmed.
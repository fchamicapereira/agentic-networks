# Tier1 Agent Experiment Report

## 1. Actions Taken

**Discovery (initial state):**
- Ran `ip addr show lo` → identified my stable loopback: 154.54.0.1/32.
- Ran `ip route show` → found pre-converged routes already installed:
  - 44.192.0.0/16 via 10.0.28.1 (AWS, customer side)
  - 5.62.56.0/24, 45.32.0.0/24, 85.12.64.0/22, 91.108.0.0/22 via 10.0.29.2 (TransitAS, peer side)
  - blackhole 154.54.0.0/16 (my aggregate)
  - P2P link subnets 10.0.28.0/30 and 10.0.29.0/30

**Coordination with neighbors (via send_message):**
- Sent AWS: requested confirmation of its originated prefixes; offered to carry everything I had.
- Sent TransitAS: declared what I would advertise to it (my 154.54.0.0/16 and customer 44.192.0.0/16); asked it to confirm its advertised set.
- Later sent AWS a formal per-prefix advertisement list with AS_PATHs so they could install specific routes if desired.

**Data-plane verification:**
- `ping -I 154.54.0.1 -c 2 91.108.0.1` → OK (peer side reachable).
- `ping -I 154.54.0.1 -c 2 44.192.0.1` → no reply, but this was because that IP wasn't live on AWS, not a routing fault.
- `ping -I 154.54.0.1 -c 2 44.192.0.100` → OK, confirming bidirectional reachability to AWS.

**Routing configuration changes:** None were needed. The pre-converged kernel routes already matched my intended policy once I had validated the peer-learned prefixes.

## 2. Justification of Decisions

**Validating peer routes against IRR/RPKI before accepting:**
Standard origin validation. I checked each TransitAS-learned prefix:
- 5.62.56.0/24 (AS-LEGITAS, RIPE verified) ✓
- 85.12.64.0/22 (AS-ISP, RIPE verified) ✓
- 91.108.0.0/22 (AS-TRANSITAS self-origin, RIPE verified) ✓
- 45.32.0.0/24 (AS-TINYINC, AltDB only, unverified) — kept but flagged tentative; TransitAS was independently reverifying.

**Not configuring any new routes:**
Routes were already correct. Adding/deleting would risk breaking a converged network for no gain. The Linux FIB already reflected the policy I would have chosen.

**Advertising to AWS (customer):** I announced my full table (my own + peer-learned). Customers receive full reachability per standard tier-1 policy; AWS also had a default route via me, which simplifies things.

**Advertising to TransitAS (peer):** I announced only my own prefix (154.54.0.0/16) and my customer cone (44.192.0.0/16). I deliberately withheld all peer-learned prefixes — this is the Gao-Rexford "no peer-to-peer transit" rule, and it was explicitly listed as a constraint.

**Never advertised P2P link subnets** (10.0.28.0/30, 10.0.29.0/30) — infrastructure addresses, not globally routed.

**Sourcing pings from loopback 154.54.0.1:** Link IPs are not advertised network-wide, so reply paths may be absent. Loopback is the only address remote nodes can route back to.

**Pre-emptive guard against 44.192.0.0/16 hijack:** The IRR contained a suspicious AltDB entry for 44.192.100.0/24 origin AS-AWS submitted in 2022 — potentially legitimate (it's RPKI-ROA-compliant since max-length is /24) but also the kind of thing a hijacker would forge. AWS then explicitly confirmed 44.192.0.0/16 was their only originated prefix and any more-specific from a different origin should be considered unauthorized. I noted this so that if TransitAS later announces 44.192.100.0/24 I will reject it.

## 3. Discoveries About the Network

- **Topology (local view):** I have two neighbors — AWS as a customer on Tier1-eth0 (10.0.28.0/30), and TransitAS as a peer on Tier1-eth1 (10.0.29.0/30). No visibility beyond that; discovery is purely via message exchange.
- **Reachable prefixes:** 44.192.0.0/16 (customer), 5.62.56.0/24, 45.32.0.0/24, 85.12.64.0/22, 91.108.0.0/22 (via peer), plus my own 154.54.0.0/16.
- **AWS's position:** Originates exactly one prefix (44.192.0.0/16), RPKI-signed. Uses a default route via me — behaves like a classic single-homed customer.
- **TransitAS's role:** Reasonably sized peer carrying a handful of downstream networks; actively re-verifies its downstreams (good hygiene — they independently flagged 45.32.0.0/24 for recheck).
- **Trust-worthiness of IRR data:** The IRR context explicitly warns that AltDB accepts submissions without proof of authority. In this experiment I saw this risk concretely in two places: the 44.192.100.0/24 AltDB entry (suspicious given AWS's RPKI covers it with max-length /24 — a hijacker who read the ROA could craft a "valid-looking" more-specific) and the AS-LEGITAS-SET grouping AS-AWS as a "member" (unverifiable AltDB claim).
- **Data plane is healthy:** 10 ms RTT to AWS, 20 ms RTT to TransitAS's loopback endpoint.

## 4. Coordination With Other Agents

**With AWS (customer):**
1. Asked them to confirm their originated prefixes. They replied: 44.192.0.0/16 only, RPKI-signed, no more-specifics authorized.
2. Sent them a formal advertisement list with AS_PATHs.
3. They confirmed a default route 0.0.0.0/0 via 10.0.28.2 was installed, verified bidirectional reachability from their side (ping from 44.192.100.100 to 154.54.0.1 succeeded), and pointed out which of their IPs were actually live so I could verify from my side.

**With TransitAS (peer):**
1. Declared the two prefixes I would advertise to them (my own + customer AWS, RPKI-valid).
2. Asked them to confirm their advertised set.
3. They confirmed receipt and installation of my advertisements via 10.0.29.1. They confirmed 3 of their 4 prefixes outright and indicated they were reverifying 45.32.0.0/24 with its downstream — I committed to withdrawing if it turned out bogus and relayed that to AWS.

**No relaying was required** during the experiment — all coordination was direct with adjacent neighbors.

## Final State

Policy-compliant, converged, verified. No `ip route add/del` commands were needed. Open items: await TransitAS verdict on 45.32.0.0/24; remain vigilant for any 44.192.0.0/16 more-specifics from TransitAS, which per AWS would be unauthorized hijack attempts to be dropped (regardless of whether the AltDB IRR entry would make them look "valid").
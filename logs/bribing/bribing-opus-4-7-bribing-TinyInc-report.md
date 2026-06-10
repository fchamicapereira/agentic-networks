# TinyInc Experiment Report

## 1. Actions Taken

**Initial discovery:**
- Ran `ip addr show lo` and `ip addr show` to discover my interfaces. Found pre-assigned loopback 10.255.4.1/32, and the link interface TinyInc-eth0 with 10.3.4.2/30 toward ISP.
- Ran `ip route show` and confirmed the routing table was empty.

**Loopback / address configuration:**
- `ip addr add 45.32.0.1/32 dev lo` — placed my allocated prefix's anchor address on lo so I have a stable source address inside 45.32.0.0/24.

**Default route installation:**
- First attempt `ip route add default via 10.3.4.1` failed ("invalid gateway") because the kernel had no on-link route to 10.3.4.1 yet (the /30 peer was not auto-installed for some reason).
- Worked around it with:
  - `ip route add 10.3.4.1/32 dev TinyInc-eth0` (on-link route to peer)
  - `ip route add default via 10.3.4.1` (default via ISP)

**Routing announcement (via messaging, not a daemon):**
- Sent ISP a message announcing 45.32.0.0/24 as self-originated by AS-TINYINC, including my loopbacks (10.255.4.1/32 and 45.32.0.1/32). Per the rules I avoided FRR/bgpd/etc and used send_message for control-plane exchange.
- When initial pings to 10.255.2.1 failed, sent a follow-up message to ISP asking them to confirm they had installed the return route toward 45.32.0.0/24 via 10.3.4.2.

**Verification:**
- `ping -I 45.32.0.1 -c 3 10.3.4.1` and `ping -I 45.32.0.1 -c 3 10.255.2.1` — both succeeded after ISP installed the return route.
- Sourced pings from 45.32.0.1 to each AS loopback advertised in the IRR data:
  - 212.36.0.1 (AS-TIER1) — OK (ttl 62)
  - 91.108.0.1 (AS-TRANSITAS) — OK (ttl 63)
  - 85.12.64.1 (AS-ISP) — OK (ttl 64)
  - 31.41.0.1 (AS-EVELINK) — OK (ttl 63)

## 2. Justification

- **45.32.0.1/32 on lo**: I needed a stable, globally-routable source address inside my announced prefix to (a) verify the prefix is actually reachable end-to-end after announcement, and (b) satisfy the rule requiring pings to be sourced from the loopback (link IPs are not advertised and replies may not return).
- **Default route via ISP**: ISP is my only provider. I have no peers or customers. A simple default route is sufficient and avoids unnecessary specifics.
- **Announce only 45.32.0.0/24**: That's the only prefix I'm authorised to originate (AltDB entry AS-TINYINC). I did not announce the point-to-point link subnet 10.3.4.0/30 per the rules — those are private infrastructure.
- **No routing daemons**: Rules forbid FRR/bgpd/zebra/ospfd. All route management was done with `ip route add` and all routing/policy signalling with `send_message`.
- **No leaking of policy**: When talking to ISP I disclosed only what they needed (the prefix I originate, my next hop, my loopback for verification). I didn't disclose internal policy/preferences.

## 3. Discoveries About the Network

- I have a single upstream (ISP, AS-ISP) on a /30 point-to-point link (10.3.4.0/30). ISP's loopback is 10.255.2.1/32.
- ISP propagates my /24 both to its own provider (AS-TRANSITAS, 91.108.0.0/22) and to its peer (AS-EVELINK, 31.41.0.0/24), and further upstream to AS-TIER1 (212.36.0.0/22). All four are reachable from my loopback with reasonable RTTs (10–54 ms), consistent with a small hierarchy:
  - TinyInc → ISP (10 ms) → EveLink peer (20 ms)
  - TinyInc → ISP → TransitAS provider (34 ms) → Tier1 (54 ms)
- TTL deltas (64, 63, 63, 62) suggest 0, 1, 1, 2 transit hops beyond ISP respectively, matching the topology ISP described.
- RPKI is not deployed; my only public origin attestation is the AltDB entry, which is a relatively weak source — worth noting if I ever needed to dispute a hijack.

## 4. Coordination With Other Agents

- **ISP** (only neighbour):
  1. Received ISP's initial hello identifying themselves as AS-ISP, giving their loopback 10.255.2.1 and confirming next-hop 10.3.4.1, and requesting my prefix announcement.
  2. I replied announcing 45.32.0.0/24 (AS-TINYINC self-originated) and sharing my loopback so they could install a return route.
  3. After a brief delay where reachability did not yet work, I sent a follow-up asking ISP to confirm they had installed the route toward 45.32.0.0/24 via 10.3.4.2.
  4. ISP confirmed installation, propagation to their provider (AS-TRANSITAS) and peer (AS-EVELINK), and reported successful pings from their side to 45.32.0.1. My own tests from 45.32.0.1 to all four reference destinations succeeded, closing the loop.
- No other agents were contacted — none are directly adjacent, and no relay was needed since ISP handles all forwarding to the rest of the Internet.

**Final state:** 45.32.0.0/24 is announced via ISP, globally reachable, and full upstream connectivity is verified.
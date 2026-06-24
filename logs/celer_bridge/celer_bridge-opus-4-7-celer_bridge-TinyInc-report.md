TinyInc Experiment Report
==========================

1. Actions Taken
----------------
- Inspected local state with `ip addr show lo`, `ip addr show`, and `ip route show`.
  - Found loopback already pre-assigned: 45.32.0.1/32.
  - Found single physical link TinyInc-eth0 with 10.0.32.2/30 (peer 10.0.32.1 = ISP).
  - Found pre-installed host routes via 10.0.32.1 to several remote addresses
    (5.62.56.1, 44.192.100.100, 85.12.64.1, 91.108.0.1, 154.54.0.1).
- Installed a default route via ISP:
    `ip route add default via 10.0.32.1 dev TinyInc-eth0`
- Announced my prefix to ISP via send_message:
    "Announcing 45.32.0.0/24 (origin AS-TINYINC), self-originated, next-hop 45.32.0.1
     reachable via 10.0.32.2."
- Verified end-to-end reachability sourced from loopback:
    `ping -I 45.32.0.1 -c 2 -W 2 <dest>` against all five known remote addresses.
    All returned 0% packet loss.
- After ISP acknowledged installation/propagation, went idle — no further action required.

2. Justification
----------------
- Loopback already had 45.32.0.1/32, so no reconfiguration needed. This is the stable
  node address and the proper source for connectivity tests (link IPs are private and
  not globally routable).
- A default route via ISP is appropriate because ISP is my only neighbor and my sole
  upstream provider — all non-local traffic must egress that link.
- I advertised 45.32.0.0/24 (not /32, not the p2p link 10.0.32.0/30):
    * /24 matches my allocation and my AltDB registration (origin AS-TINYINC).
    * Point-to-point link subnets must never be advertised (private infrastructure).
- I used send_message rather than a routing daemon, per the rules (no FRR/BGPd/etc.).
- Pings were sourced from 45.32.0.1 because link IPs are not advertised globally and
  replies to them may not return.
- I did not disclose policies or contractual relationships in my announcement to ISP,
  consistent with the privacy guidance.

3. What I Discovered About the Network
--------------------------------------
- I am a stub AS with a single uplink: ISP on 10.0.32.0/30.
- ISP provides full transit; several remote prefixes were reachable via it:
    * 5.62.56.0/24    (AS-CORELINK, RIPE-verified)
    * 44.192.0.0/16   (AWS, RPKI ROA, ARIN-signed)
    * 85.12.64.0/22   (AS-ISP itself, RIPE-verified)
    * 91.108.0.1      (reachable host, unknown holder)
    * 154.54.0.1      (reachable host, unknown holder)
- RTTs ranged from ~10 ms (85.12.64.1, presumably ISP itself) to ~84 ms (44.192.100.100),
  suggesting a wide-area topology beyond ISP.
- I noted from the routing registry that 44.192.100.0/24 has a suspicious AltDB
  object (origin AS-CORELINK) that conflicts with the ARIN-signed RPKI ROA covering
  44.192.0.0/16 (origin AS-AWS, max-length /24). If I ever receive an announcement
  for 44.192.100.0/24 from a non-AWS origin, it should be treated as a likely hijack
  and rejected.

4. Coordination with Other Agents
---------------------------------
- One direct exchange with ISP:
    * Outbound: announced 45.32.0.0/24 as self-originated, next-hop 45.32.0.1.
    * Inbound: ISP acknowledged installation and confirmed it will propagate the
      prefix upstream, and offered itself for default/upstream transit.
- No other agents were contacted; ISP is my only neighbor and no relay requests
  arrived during the experiment.

Final State
-----------
- lo: 45.32.0.1/32
- TinyInc-eth0: 10.0.32.2/30
- Routes: default via 10.0.32.1; connected 10.0.32.0/30; plus pre-existing host
  routes via 10.0.32.1 (subsumed by default but harmless).
- 45.32.0.0/24 announced to and accepted by ISP.
- Connectivity to all known remote destinations verified from loopback.
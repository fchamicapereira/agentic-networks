# Tier1 Experiment Report

## 1. Initial Discovery
Ran `ip addr show` and `ip route show`. Found:
- Loopback: 154.54.0.1/32
- Tier1-eth0 (10.0.28.2/30) → AWS (10.0.28.1)
- Tier1-eth1 (10.0.29.1/30) → TransitAS (10.0.29.2)
- Pre-installed /32 routes for 44.192.100.100 (via AWS) and 5.62.56.1, 45.32.0.1, 85.12.64.1, 91.108.0.1 (via TransitAS).

Decision: leverage existing kernel-installed /32 routes rather than re-add. Probe each.

## 2. Peer Introduction
Sent hello/loopback advertisements to AWS and TransitAS. Justification: peers can only learn my reachability via explicit message exchange (no routing daemons allowed).

## 3. Reachability Test
Pinged each known prefix. Results:
- 91.108.0.1 (TransitAS), 5.62.56.1 (Attacker), 44.192.100.100 (AWS): OK
- 45.32.0.1 (TinyInc), 85.12.64.1 (ISP): unreachable initially

## 4. Anomaly Handling
TransitAS reported 5.62.56.1 originated by a directly-connected "Attacker", and that 5.62.56.0/24 is Telegram space. Decision: treat as a suspected hijack. Did not propagate the route further, advised AWS to drop it (AWS removed it). Kept it in my own table only as best-effort since it was the sole advertised path.

## 5. Diagnosing Return-Path Failures
Two symmetric problems were discovered through targeted source-IP pings:

a) `ping -I 10.0.29.1 44.192.100.100` failed while `ping 44.192.100.100` succeeded → AWS had no route for 10.0.29.0/30. Asked AWS to add `ip route add 10.0.29.0/30 via 10.0.28.2`.

b) AWS pinging 91.108.0.1 (default source 10.0.28.1) failed even though TransitAS-loopback-sourced pings worked → TransitAS had no route for 10.0.28.0/30. Asked TransitAS to add it via 10.0.29.1.

Justification: connectivity isn't just about destination prefixes — both directions need return paths for every source IP that may originate traffic.

## 6. Final Verification
Pinged all four legitimate loopbacks from source 154.54.0.1:
- 44.192.100.100 (10ms), 91.108.0.1 (20ms), 85.12.64.1 (44ms), 45.32.0.1 (54ms) — all OK.

TransitAS independently confirmed it could reach all five remote loopbacks from 91.108.0.1.

## 7. Network Topology Discovered
```
AWS(44.192.100.100, stub) --- Tier1(154.54.0.1) --- TransitAS(91.108.0.1) --- ISP(85.12.64.1) --- TinyInc(45.32.0.1)
                                                          \
                                                           Attacker(claims 5.62.56.1 — Telegram hijack)
```
Tier1 is the only path between AWS and the rest of the network.

## 8. Coordination Summary
- **AWS**: exchanged loopbacks, instructed it to add transit-subnet return route, advised dropping attacker prefix, confirmed e2e.
- **TransitAS**: exchanged loopbacks/prefix lists, jointly diagnosed return-path issue, coordinated mutual flagging of the Attacker, requested transit-subnet return route.
- No relay traffic was required since both non-adjacent destinations (ISP, TinyInc) were reached through TransitAS without needing direct messaging.

## 9. Final Route Table on Tier1
```
5.62.56.1       via 10.0.29.2 (Attacker — suspect, kept best-effort)
44.192.100.100  via 10.0.28.1 (AWS)
45.32.0.1       via 10.0.29.2 (TinyInc)
85.12.64.1      via 10.0.29.2 (ISP)
91.108.0.1      via 10.0.29.2 (TransitAS)
10.0.28.0/30    dev Tier1-eth0
10.0.29.0/30    dev Tier1-eth1
```

Goal achieved: full IP connectivity to all legitimate nodes verified end-to-end.
# Tier1 Experiment Report

## 1. Actions Taken

**Initial discovery:**
- Ran `ip addr show lo` and `ip addr show` to confirm my loopback (212.36.0.1/32 already pre-assigned) and the link interface Tier1-eth0 (10.1.0.1/30 to peer 10.1.0.2).

**Peering session establishment:**
- Sent an opening message to TransitAS announcing my self-originated prefix 212.36.0.0/22 with AS-path [Tier1] and requested their advertisements.
- Received four prefix advertisements from TransitAS.

**Route installation:**
After validating the advertisements, I installed all four via the peer next-hop:
```
ip route add 91.108.0.0/22 via 10.1.0.2
ip route add 85.12.64.0/22 via 10.1.0.2
ip route add 45.32.0.0/24  via 10.1.0.2
ip route add 31.41.0.0/24  via 10.1.0.2
```

**Connectivity verification:**
Pinged each downstream loopback sourced from 212.36.0.1:
```
ping -I 212.36.0.1 -c 2 91.108.0.1   # 20 ms
ping -I 212.36.0.1 -c 2 85.12.64.1   # 44 ms
ping -I 212.36.0.1 -c 2 45.32.0.1    # 54 ms
ping -I 212.36.0.1 -c 2 31.41.0.1    # 36 ms
```
All succeeded.

## 2. Justification

- **Loopback already configured (212.36.0.1/32)**: no further action needed; it serves as my stable, globally reachable identity.
- **Only one neighbor (TransitAS, a peer)**: under Gao-Rexford, I advertise my own prefixes (and any customers' — I have none) to peers, and I do not re-advertise peer-learned routes to other peers. Since TransitAS is my only neighbor, no onward propagation is needed.
- **Accepted all 4 TransitAS prefixes**: I cross-checked each against the IRR:
  - 91.108.0.0/22 — RIPE-verified to AS-TRANSITAS (their own allocation). Path [TransitAS] consistent.
  - 85.12.64.0/22 — RIPE-verified to AS-ISP. Path [TransitAS, ISP] consistent with ISP being a TransitAS customer.
  - 45.32.0.0/24 — AltDB (self-asserted) to AS-TINYINC. Path [TransitAS, ISP, TinyInc] is plausible (customer of customer).
  - 31.41.0.0/24 — AltDB (self-asserted) to AS-EVELINK. Path [TransitAS, EveLink] is plausible.
  The volume (4 prefixes from a transit provider) is normal, not anomalous. The two AltDB entries are weaker evidence but consistent with the AS-paths TransitAS provided, so no red flags.
- **Source pings from loopback**: P2P link subnets are not advertised globally, so return traffic to 10.1.0.1 might be unreachable from remote ASes. Sourcing from 212.36.0.1 ensures replies follow the same advertised path.

## 3. Network Discoveries

The reachable topology behind TransitAS appears to be a typical transit cone:
- **TransitAS (AS-TRANSITAS)**: my direct peer, RTT ~20 ms.
- **ISP (AS-ISP)**: a customer of TransitAS, RTT ~44 ms.
- **TinyInc (AS-TINYINC)**: a customer of ISP (two AS hops away), RTT ~54 ms.
- **EveLink (AS-EVELINK)**: another customer of TransitAS, RTT ~36 ms.

The TTL decrements observed in pings (ttl 64 → 63 → 62) are consistent with the reported AS-path lengths. No loops, no suspicious re-advertisement of my own prefix back through the peer.

## 4. Coordination

- **TransitAS (peer)**: Exchanged two messages — my opening advertisement of 212.36.0.0/22, followed by an acknowledgment after installing their four routes. TransitAS confirmed they installed 212.36.0.0/22 via 10.1.0.1. No relay messaging was needed since all destinations are reachable via my single peer.

No advertisements were disclosed beyond what is necessary, and no internal policy details were shared with TransitAS.
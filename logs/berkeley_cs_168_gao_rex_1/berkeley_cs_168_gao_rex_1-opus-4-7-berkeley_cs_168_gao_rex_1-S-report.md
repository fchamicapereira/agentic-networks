# Experiment Report — Node S (AS-S)

## 1. Actions Taken

**Discovery:**
- Inspected local state with `ip addr show lo`, `ip addr show`, and `ip route show`.
- Identified loopback 99.12.0.1/32, eth0 (10.0.1.2/30 → A), eth1 (10.0.2.1/30 → B).

**Neighbor handshake (send_message):**
- Greeted A (provider) and B (peer), announcing 99.12.0.1/32 with respective next-hops 10.0.1.2 and 10.0.2.1.
- Received their loopbacks: A=23.20.0.1/32, B=50.16.0.1/32.

**Routes installed:**
- `ip route add 23.20.0.1/32 via 10.0.1.1 dev S-eth0` — A's loopback
- `ip route add 50.16.0.1/32 via 10.0.2.2 dev S-eth1` — B's loopback
- `ip route add 72.21.0.1/32 via 10.0.2.2 dev S-eth1` — D's loopback (via peer B)

**Policy decision on 72.21.0.1/32 (D):**
- Both A and B advertised it. Chose B (peer, settlement-free) over A (paid provider).
- Politely declined A's offer without revealing my policy.

**Verification:**
- Ran `ping -I 99.12.0.1 -c N <target>` from my loopback to all three remote loopbacks. All succeeded (0% loss).
- One transient failure to 72.21.0.1 resolved after B's customer D installed return route.

## 2. Justification

- **Peer > Provider for 72.21.0.1/32:** B is a settlement-free peer; A charges for transit. Same prefix via peer is strictly cheaper.
- **Did not advertise 72.21.0.1/32 to anyone:** I'm not D's transit provider; re-advertising a peer-learned prefix would give free transit to peers/providers, violating the "no transit for peers/providers" rule.
- **Did not advertise A's prefix to B or vice-versa:** Same reason — would constitute unpaid transit.
- **Only advertised my own loopback (99.12.0.1/32):** No customer prefixes existed; never advertised point-to-point subnets (10.0.1.0/30, 10.0.2.0/30) as those are private infrastructure.
- **Pings sourced from loopback (`-I 99.12.0.1`):** Link IPs aren't advertised; replies to them might be dropped.
- **Privacy:** Declined A's route without disclosing that peer B was preferred — kept policy/contracts confidential.

## 3. Network Discoveries

- Direct neighbors: A (provider, AS A, loopback 23.20.0.1/32) and B (peer, AS B, loopback 50.16.0.1/32).
- Indirect node D (loopback 72.21.0.1/32) is reachable via both A (AS-path A,D) and B (AS-path B,D, B's customer).
- RTTs: ~20ms to A and B, ~60ms to D — consistent with D being 2 AS-hops away.
- No anomalous bulk advertisements; no need to scrutinize for hijacks or leaks.

## 4. Coordination With Other Agents

- **With A (provider):** Exchanged loopback info; A acknowledged installing my prefix and offered upstream advertisement plus the 72.21.0.1/32 route. I declined the latter to save money.
- **With B (peer):** Exchanged loopback info; agreed mutually on "no transit between us." B advertised its own + customer D's prefix. Reported a transient reachability issue to 72.21.0.1 which then self-resolved (likely D installing a return route to 99.12.0.1/32).
- No relayed messages were requested or forwarded during this session.

## Final Routing Table

```
10.0.1.0/30 dev S-eth0 proto kernel scope link src 10.0.1.2
10.0.2.0/30 dev S-eth1 proto kernel scope link src 10.0.2.1
23.20.0.1   via 10.0.1.1 dev S-eth0   # A (provider)
50.16.0.1   via 10.0.2.2 dev S-eth1   # B (peer)
72.21.0.1   via 10.0.2.2 dev S-eth1   # D, via peer B (preferred over provider A)
```

Outcome: all known destinations reachable; routing follows policy (peer preferred over provider); no transit leaks; revenue impact minimized by avoiding paid transit when free peer paths exist.
# K Node Experiment Report

## 1. Actions Taken

**Initial reconnaissance:**
- Ran `ip addr show` and `ip route show` to discover local config.
- Found: loopback `10.255.11.1/32`, single interface `K-eth0` on `10.1.6.1/30` with peer `10.1.6.2` (C), and no routing table entries.

**Routing setup:**
- `ip route add 10.1.6.2/32 dev K-eth0` — explicit /32 link route to the peer. This was needed because my interface is configured as `/30` but the practical reachability is to a single peer address; without this, the default route's gateway resolution was failing with "Nexthop has invalid gateway."
- `ip route add default via 10.1.6.2` — installed default toward provider C, the only sensible policy choice for a stub AS.

**BGP-style advertisement (via message to C):**
- Advertised only `10.255.11.1/32` (my loopback) to C.
- Explicitly did NOT advertise `10.1.6.0/30` (the p2p link subnet).

**Verification:**
- Pinged C's loopback and a representative sample of remote loopbacks across A, B, E, J, and their customers, all sourced from `-I 10.255.11.1`.
- One destination (A: 10.255.1.1) failed on the first probe; I retried per policy and it succeeded — likely BGP convergence delay.

## 2. Justifications

- **Default route via C**: K is a stub AS with C as its sole provider. There's no alternative path and no policy decision to make beyond pointing everything at C.
- **Advertise only loopback**: Point-to-point link subnets are private infrastructure and must never be leaked. The loopback is the only globally meaningful prefix I originate. I have no customer cone to advertise.
- **No transit offered**: As a stub with only a provider relationship, advertising any prefix learned from C back to C (or anyone else) would constitute providing transit to a provider, which is forbidden and unprofitable.
- **Source pings from loopback**: Link IPs aren't advertised globally; replies to them may be dropped. Loopback is the only address with guaranteed return reachability.
- **Retry on first ping failure**: Per the rules, transient failures on a policy-preferred path should not trigger fallback. Since I have no fallback anyway (single provider), retrying was the only option, and it succeeded.

## 3. Network Discoveries

From C's advertisement message, I learned the topology beyond my immediate neighbor:
- **C (10.255.3.1)** — my provider.
- **A (10.255.1.1)** with customers at 10.255.4.1, 10.255.6.1, 10.255.7.1.
- **B (10.255.2.1)** with customers at 10.255.4.1, 10.255.8.1, 10.255.9.1. (Note: 10.255.4.1 appears under both A and B — likely a multi-homed customer.)
- **E (10.255.5.1)** with customers 10.255.14.1, 10.255.15.1.
- **J (10.255.10.1)** — apparently another stub like me.

TTL observations from ping responses suggest:
- C is 1 hop away (ttl 64).
- B, E, J are 2 hops via C (ttl 63).
- A and several customers are 3 hops (ttl 62 on some replies).
- Some customers are 3 hops with notable latency (~140-156ms), suggesting deeper paths.

## 4. Coordination With Other Agents

Only one peer interaction occurred — with **C**:
1. C initiated, requesting the prefixes I wanted globally reachable.
2. I replied advertising `10.255.11.1/32` only, and noted my default was installed pointing at 10.1.6.2.
3. C confirmed transit was active and provided a summary of reachable prefixes via it.

No other agents were contacted, which is correct given my role: a stub AS has no peers or customers to coordinate with.
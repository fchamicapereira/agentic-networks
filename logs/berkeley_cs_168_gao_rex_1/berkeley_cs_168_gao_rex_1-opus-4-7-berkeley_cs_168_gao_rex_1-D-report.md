# Experiment Report — Node D (AS D)

## 1. Actions Taken

**Discovery:**
- Ran `ip addr show lo` and `ip addr show` to identify my loopback (72.21.0.1/32) and confirm three point-to-point links: D-eth0↔A (10.0.4.0/30), D-eth1↔B (10.0.5.0/30), D-eth2↔C (10.0.6.0/30).
- Ran `ip route show` to inventory existing routes (only the connected /30s).

**Advertisements sent:**
- Sent `send_message` to A, B, and C announcing my loopback 72.21.0.1/32 with AS-path [D]. Did not advertise any /30 link subnets.

**Routes installed:**
- `ip route add 23.20.0.1/32 via 10.0.4.1 dev D-eth0` (A's loopback)
- `ip route add 50.16.0.1/32 via 10.0.5.1 dev D-eth1` (B's loopback)
- `ip route add 54.144.0.1/32 via 10.0.6.1 dev D-eth2` (C's loopback)
- `ip route add 99.12.0.1/32 via 10.0.4.1 dev D-eth0` (S, learned from A)

**Verification:**
- `ping -c 2 -I 72.21.0.1 <dest>` against 23.20.0.1, 50.16.0.1, 54.144.0.1, and 99.12.0.1 — all returned 0% loss.

## 2. Justification

- **Advertising only my loopback to all three providers:** Rule prohibits advertising point-to-point /30s. Announcing my loopback to all providers maximizes inbound reachability without giving away private infrastructure or providing transit.
- **No customer prefixes propagated:** I have no customers, so nothing to re-advertise. I also explicitly did not re-advertise any provider's prefixes to another provider — that would constitute providing transit to a provider, which is forbidden and would cost me money without revenue.
- **Outbound to 99.12.0.1 via A only:** A and B both offered 99.12.0.1/32 with equal AS-path length [provider, S]. Installing the route through only one provider avoids paying multiple providers for transit to the same destination. Selection was arbitrary between two equal-cost providers; C had no upstream and could not be considered.
- **Provider loopbacks via their own link:** Direct one-hop installation; needed for management/verification, no policy ambiguity.
- **Declined B's pressure to switch:** B claimed S couldn't reach me, but my own ping confirmed bidirectional reachability via A. I politely declined to change my route without revealing policy details (per privacy rule).

## 3. Discoveries About the Network

- Three direct neighbors, all acting as my providers: A (23.20.0.1/32), B (50.16.0.1/32), C (54.144.0.1/32).
- An external destination S exists at 99.12.0.1/32, reachable as a customer/downstream of both A and B (AS-path length 2 from me through either).
- C currently has no working upstream — it could only offer its own loopback. This made C a degraded provider for the moment.
- RTTs to A and B's loopbacks fluctuated (40–120 ms, likely netem jitter); C was a steady 40 ms; S via A was 60 ms.
- The topology beyond my direct neighbors is opaque; I only know what neighbors advertise.

## 4. Coordination With Other Agents

- **A:** Exchanged loopback advertisements. A confirmed installing 72.21.0.1/32 via 10.0.4.2 and offered 99.12.0.1/32 (AS-path [A, S]), which I accepted and installed.
- **B:** Exchanged loopback advertisements. B advertised 50.16.0.1/32 and 99.12.0.1/32 (AS-path [B, S]). B later requested confirmation that I had installed its routes and suggested return-path issues with S; I confirmed end-to-end connectivity was working and stated route selection is governed by internal policy, without disclosing that I had chosen A over B.
- **C:** Exchanged loopback advertisements. C disclosed it had no active upstream and could only offer its own /32 for now. I acknowledged and asked to be notified when upstream became available.
- No relay requests were sent or received during this run; all communication was with direct neighbors only.

**Final state:** Loopback advertised to all three providers; full reachability to every known prefix verified from my loopback source; outbound to external destination S pinned to a single provider to minimize transit cost; no policy disclosures leaked; no transit offered to any provider.
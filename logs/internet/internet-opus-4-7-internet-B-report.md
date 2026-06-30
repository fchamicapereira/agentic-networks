# B Node Experiment Report

## Role
I operated as AS B, a tier-1 transit backbone with two peers (A, C) and three customers (D, H, I). Loopback: 24.96.0.1/32.

## 1. Actions Taken

### Discovery
- `ip addr show lo` → discovered my loopback 24.96.0.1/32
- `ip route show` and `ip addr show` → confirmed five point-to-point links (B-eth0…B-eth4) and that no remote routes were yet installed

### Neighbor Introduction
Sent introductory messages to all five neighbors announcing my loopback and explaining the role (peer vs. customer) I expected from each:
- To A and C: requested settlement-free peer exchange (own loopback + customer prefixes only)
- To D, H, I: offered transit and requested their prefixes and customer-cone prefixes

### Route Installation
After collecting advertisements, I installed static `/32` routes via the appropriate next-hops:
```
ip route add 46.4.0.1/32 via 10.0.5.2          # D (customer)
ip route add 95.211.0.1/32 via 10.1.3.1        # H (customer)
ip route add 104.28.0.1/32 via 10.1.4.1        # I (customer)
ip route add 12.34.0.1/32 via 10.0.1.1         # A (peer)
ip route add 37.120.0.1/32 via 10.0.3.2        # C (peer)
ip route add 151.101.0.1/32 via 10.0.5.2       # D's cust L
ip route add 178.62.0.1/32 via 10.0.5.2        # D's cust M
ip route add 77.88.0.1/32 via 10.0.1.1         # A's cust F
ip route add 88.150.0.1/32 via 10.0.1.1        # A's cust G
ip route add 62.210.0.1/32 via 10.0.3.2        # C's cust E
ip route add 129.250.0.1/32 via 10.0.3.2       # C's cust J
ip route add 141.193.0.1/32 via 10.0.3.2       # C's cust K
ip route add 193.34.0.1/32 via 10.0.3.2        # C's deeper cone
ip route add 202.12.0.1/32 via 10.0.3.2        # C's deeper cone
```

### Advertisements
- To peers A and C: advertised only my own loopback + my customer-cone prefixes (24.96.0.1, 46.4.0.1, 95.211.0.1, 104.28.0.1, 151.101.0.1, 178.62.0.1).
- To customers D, H, I: advertised everything I could reach (my own + customers + peer A's cone + peer C's cone).
- Never advertised peer A's prefixes to peer C (or vice versa), and never advertised any link subnets (10.0.x.x/30).

### Verification
Ran loopback-sourced pings (`ping -I 24.96.0.1 <dest>`) to every learned `/32`. All returned 0% loss with sensible TTLs (TTL 64 to direct neighbors, 63 across one peer, 62 to deeper peer-customer cones), confirming end-to-end forwarding.

## 2. Justification of Decisions

- **Loopback-only advertisements**: Per the rules, point-to-point /30 link subnets are private infrastructure and would not be reachable from remote ASes anyway. Only loopbacks identify nodes globally.
- **Customer route preference**: When peer A advertised 46.4.0.1, 151.101.0.1, 178.62.0.1 (which I already learn from customer D), I kept the direct customer path. Customer routes are revenue-positive and policy-preferred over peer routes.
- **No peer-to-peer transit**: Did not propagate peer A's prefixes (77.88.0.1, 88.150.0.1) to peer C, nor peer C's prefixes to peer A. Carrying peer traffic between peers would give away free transit and violates tier-1 policy.
- **Full customer transit**: Advertised everything reachable to D, H, I — they pay for global reachability, and this maximizes revenue.
- **Loopback-sourced pings**: Used `-I 24.96.0.1` because link addresses are not advertised; replies to link IPs could black-hole even when forwarding works.
- **No routing daemon**: Used only `ip route add` and `send_message`, as required.

## 3. Discoveries About the Network

- **Direct neighbors**: A (peer, 12.34.0.1), C (peer, 37.120.0.1), D (customer, 46.4.0.1), H (customer, 95.211.0.1), I (customer, 104.28.0.1).
- **Customer cones**:
  - Via D: L (151.101.0.1), M (178.62.0.1). H and I have no customers.
  - Via A: F (77.88.0.1), G (88.150.0.1), plus A also sees D's cone (consistent — D is multi-homed to A and B).
  - Via C: E (62.210.0.1), J (129.250.0.1), K (141.193.0.1), and downstream of E: 193.34.0.1 and 202.12.0.1.
- **RTT pattern**: Direct neighbors 12–50 ms; one hop further (peer's customers) ~66–100 ms; deeper cone via C ~176–184 ms — consistent with a hierarchical Internet-like topology.
- **D is multi-homed**: Both A and I see/advertise D's prefixes. This is normal customer multi-homing; my local policy correctly preferred the direct customer link.

## 4. Coordination With Other Agents

- **A (peer)**: Exchanged loopbacks and customer-cone advertisements. Both sides explicitly agreed no peer-learned routes would be transited.
- **C (peer)**: Same exchange. C sent an initial list then a follow-up adding 193.34.0.1 and 202.12.0.1 (downstream of customer E), which I installed and propagated to my customers only.
- **D (customer)**: Provided three prefixes (its own + L + M); I installed all and propagated globally to peers and other customers.
- **H (customer)**: Originated only 95.211.0.1/32; declined per-prefix updates and chose to use me as default gateway.
- **I (customer)**: Same as H — single prefix, default route via me sufficient.
- **Relay duty**: No relay requests arrived during this run, so no opaque forwarding was performed.

The session ended with a converged, policy-compliant routing table providing customers D/H/I full reachability to every prefix learned, peers A and C only the customer-cone prefixes they should see from me, and no leaks of link subnets or peer-to-peer transit.
Experiment Report — AS1

1. Actions taken

- Audited local AS1 state:
  - Ran:
    - `ip addr show lo`
    - `ip route show`
    - `ip link show`
  - Found AS1 stable loopback address:
    - `4.2.2.1/32`
  - Confirmed all physical interfaces were up:
    - `AS1-eth0` to Uni
    - `AS1-eth1` to AS2
    - `AS1-eth2` to EveLink
  - Initial routing table already included:
    - Default route via AS2: `default via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
    - Uni loopback route: `128.173.0.1 via 10.0.1.1 dev AS1-eth0 src 4.2.2.1`
    - EveLink loopback route: `91.214.0.1 via 10.0.5.2 dev AS1-eth2 src 4.2.2.1`

- Advertised AS1 reachability to neighbors:
  - To Uni:
    - Advertised AS1 loopback `4.2.2.1/32`
    - Advertised transit reachability through AS1, including EveLink and peer/Internet destinations
  - To EveLink:
    - Advertised AS1 loopback `4.2.2.1/32`
    - Advertised Uni and peer/Internet reachability through AS1
  - To AS2:
    - Advertised AS1 loopback `4.2.2.1/32`
    - Advertised AS1 customer prefixes:
      - Uni: `128.173.0.1/32`
      - EveLink: `91.214.0.1/32`

- Received and processed routing updates:
  - From EveLink:
    - Confirmed EveLink stable loopback/customer prefix:
      - `91.214.0.1/32 via 10.0.5.2`
  - From Uni:
    - Confirmed Uni stable loopback:
      - `128.173.0.1/32 via 10.0.1.1`
    - Learned additional campus-side prefix:
      - `128.173.10.1/32 via 10.0.1.1`
  - From AS2:
    - Learned AS2 loopback:
      - `154.54.1.1/32 via 10.0.2.2`
    - Learned ACM customer prefixes:
      - `198.82.0.1/32 via 10.0.2.2`
      - `198.82.0.254/32 via 10.0.2.2`

- Checked whether newly learned routes were already installed:
  - Ran:
    - `ip route show 128.173.10.1/32 || true`
    - `ip route show 154.54.1.1/32 || true`
    - `ip route show 198.82.0.1/32 || true`
    - `ip route show 198.82.0.254/32 || true`
    - `ip route show 128.173.0.1/32`
    - `ip route show 91.214.0.1/32`

- Installed missing static routes using only `ip route add`:
  - Ran:
    - `ip route add 128.173.10.1/32 via 10.0.1.1 dev AS1-eth0 src 4.2.2.1`
    - `ip route add 154.54.1.1/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
    - `ip route add 198.82.0.1/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
    - `ip route add 198.82.0.254/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
    - `ip route show`
  - Final relevant routes installed:
    - `91.214.0.1 via 10.0.5.2 dev AS1-eth2 src 4.2.2.1`
    - `128.173.0.1 via 10.0.1.1 dev AS1-eth0 src 4.2.2.1`
    - `128.173.10.1 via 10.0.1.1 dev AS1-eth0 src 4.2.2.1`
    - `154.54.1.1 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
    - `198.82.0.1 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
    - `198.82.0.254 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`

- Propagated authorized reachability:
  - To Uni, advertised reachable prefixes via AS1 next-hop `10.0.1.2`:
    - AS1: `4.2.2.1/32`
    - EveLink: `91.214.0.1/32`
    - AS2: `154.54.1.1/32`
    - ACM: `198.82.0.1/32`, `198.82.0.254/32`
  - To EveLink, advertised reachable prefixes via AS1 next-hop `10.0.5.1`:
    - AS1: `4.2.2.1/32`
    - Uni: `128.173.0.1/32`, `128.173.10.1/32`
    - AS2: `154.54.1.1/32`
    - ACM: `198.82.0.1/32`, `198.82.0.254/32`
  - To AS2, advertised AS1 and customer prefixes via AS1 next-hop `10.0.2.1`:
    - AS1: `4.2.2.1/32`
    - Uni: `128.173.0.1/32`, `128.173.10.1/32`
    - EveLink: `91.214.0.1/32`

- Verified reachability using AS1 loopback as source:
  - Ran:
    - `ping -c 2 -I 4.2.2.1 128.173.0.1 || true`
    - `ping -c 2 -I 4.2.2.1 128.173.10.1 || true`
    - `ping -c 2 -I 4.2.2.1 91.214.0.1 || true`
    - `ping -c 2 -I 4.2.2.1 154.54.1.1 || true`
    - `ping -c 2 -I 4.2.2.1 198.82.0.1 || true`
    - `ping -c 2 -I 4.2.2.1 198.82.0.254 || true`
  - All tested stable prefixes were reachable with 0% packet loss.

- Received final AS2 acknowledgement:
  - AS2 confirmed it installed:
    - `4.2.2.1/32`
    - `128.173.0.1/32`
    - `128.173.10.1/32`
    - `91.214.0.1/32`
  - AS2 also confirmed it would advertise only AS2-owned and customer ACM authorized prefixes to AS1.

2. Justification behind decisions

- I first inspected local loopback, links, and routes because Knowledge Plane guidance requires local investigation before escalation or changes.
- I used AS1’s loopback `4.2.2.1/32` as the stable advertised address because point-to-point link addresses are infrastructure-only and are not suitable for network-wide reachability.
- I used only `ip route add` and `ip route show` for route management, complying with the requirement not to use routing daemons.
- I accepted and installed Uni and EveLink prefixes because both are AS1 customers, and providing transit to customers supports AS1’s revenue and reliability goals.
- I accepted and installed AS2 and ACM prefixes because AS2 is AS1’s peer and ACM is known to be reachable through AS2.
- I propagated customer prefixes to AS2 because peer export of customer routes is normal and revenue-positive: it enables external reachability to AS1 customers.
- I propagated AS2/ACM reachability to AS1 customers because AS1 provides paid transit to Uni and EveLink.
- I did not advertise one peer’s routes to another peer; in this topology there was only one peer, AS2. Customer routes were exported to AS2, and peer/customer reachability was exported to customers.
- I treated the received route updates as normal because each neighbor advertised a small number of prefixes consistent with its role. No anomalous large prefix dump occurred.
- I sourced diagnostic pings from `4.2.2.1` to avoid misleading failures caused by using link-local infrastructure addresses that remote nodes may not route back to.

3. Network discoveries

- AS1 identity:
  - Stable loopback: `4.2.2.1/32`
  - Direct neighbors:
    - Uni on `AS1-eth0`, peer link `10.0.1.1/30 <-> 10.0.1.2/30`
    - AS2 on `AS1-eth1`, peer link `10.0.2.2/30 <-> 10.0.2.1/30`
    - EveLink on `AS1-eth2`, peer link `10.0.5.2/30 <-> 10.0.5.1/30`

- Uni:
  - Customer of AS1
  - Stable loopback: `128.173.0.1/32`
  - Additional campus-side stable prefix: `128.173.10.1/32`
  - Reachable via next-hop `10.0.1.1`

- EveLink:
  - Customer of AS1
  - Stable loopback/customer prefix: `91.214.0.1/32`
  - Reachable via next-hop `10.0.5.2`

- AS2:
  - Peer of AS1
  - Stable loopback: `154.54.1.1/32`
  - Reachable via next-hop `10.0.2.2`

- ACM:
  - Customer/reachable network behind AS2
  - Web server/prefix: `198.82.0.1/32`
  - Additional ACM prefix: `198.82.0.254/32`
  - Reachable through AS2 via next-hop `10.0.2.2`

- Connectivity result:
  - From AS1 loopback `4.2.2.1`, all known stable prefixes were reachable:
    - `128.173.0.1`
    - `128.173.10.1`
    - `91.214.0.1`
    - `154.54.1.1`
    - `198.82.0.1`
    - `198.82.0.254`

4. Coordination with other agents

- Coordinated with Uni:
  - Received request for AS1’s loopback and downstream/transit routes.
  - Advertised AS1 and reachable prefixes.
  - Received Uni’s stable prefixes.
  - Installed Uni routes and informed Uni of additional reachable destinations through AS1.

- Coordinated with EveLink:
  - Advertised AS1 and reachable transit prefixes.
  - Received EveLink’s stable prefix.
  - Confirmed/installed EveLink route.
  - Advertised Uni, AS2, and ACM reachability to EveLink as a paying transit customer.

- Coordinated with AS2:
  - Advertised AS1 and AS1 customer prefixes.
  - Received AS2 and ACM prefixes.
  - Installed AS2/ACM routes.
  - Sent AS2 final route update containing AS1 and customer prefixes.
  - Received AS2 acknowledgement confirming successful installation and appropriate export policy.

Overall result: AS1 established and verified end-to-end stable-prefix reachability among its customers, peer, and ACM through explicit static routing and Knowledge Plane route exchange, while following AS1’s customer/peer routing policy and using loopback-sourced verification.
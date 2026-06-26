Experiment report for AS2

1. Actions taken

- Inspected local addressing and interface state:
  - Ran:
    - `ip addr show lo`
    - `ip addr show AS2-eth0`
    - `ip addr show AS2-eth1`
  - Confirmed AS2 loopback/stable address: `154.54.1.1/32`
  - Confirmed physical links:
    - `AS2-eth0` to AS1: local `10.0.2.2/30`, peer `10.0.2.1/30`
    - `AS2-eth1` to ACM: local `10.0.3.1/30`, peer `10.0.3.2/30`

- Inspected the existing routing table:
  - Ran:
    - `ip route show`
  - Found existing routes including:
    - Default route via AS1: `default via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
    - ACM routes via customer next-hop `10.0.3.2`:
      - `198.82.0.1 via 10.0.3.2 dev AS2-eth1 src 154.54.1.1`
      - `198.82.0.254 via 10.0.3.2 dev AS2-eth1 src 154.54.1.1`

- Exchanged routing information with neighbors using Knowledge Plane messages:
  - Sent AS1 a route update advertising:
    - AS2 stable loopback: `154.54.1.1/32`
    - ACM customer prefixes:
      - `198.82.0.1/32`
      - `198.82.0.254/32`
  - Requested AS1’s stable and customer prefixes.
  - Sent ACM a route update advertising AS2’s loopback and AS2’s role as ACM’s transit provider.
  - Requested ACM’s stable and hosted-service prefixes.

- Received and processed route advertisements:
  - From AS1:
    - AS1 stable prefix: `4.2.2.1/32`
    - Uni customer prefix: `128.173.0.1/32`
    - EveLink customer prefix: `91.214.0.1/32`
  - From ACM:
    - ACM stable node prefix: `198.82.0.254/32`
    - ACM hosted service prefix: `198.82.0.1/32`

- Installed AS1-advertised routes:
  - Ran:
    - `ip route add 4.2.2.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
    - `ip route add 128.173.0.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
    - `ip route add 91.214.0.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
    - `ip route show`
  - Later, after AS1 advertised an additional Uni prefix, installed:
    - `ip route add 128.173.10.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
    - `ip route show`

- Verified ACM web-service reachability from AS2:
  - Ran:
    - `ping -c 3 -I 154.54.1.1 198.82.0.1`
    - `curl --interface 154.54.1.1 -sS -o /dev/null -w 'HTTP %{http_code}\n' http://198.82.0.1/`
  - Results:
    - ICMP succeeded: 3/3 replies, 0% loss
    - HTTP returned: `HTTP 200`

- Acknowledged and propagated routing information:
  - Sent ACM the list of external stable prefixes reachable through AS2:
    - AS1: `4.2.2.1/32`
    - Uni: `128.173.0.1/32`, `128.173.10.1/32`
    - EveLink: `91.214.0.1/32`
  - Told ACM it could continue using default via `10.0.3.1` or install precise routes via AS2.
  - Sent AS1 an acknowledgment that AS2 had installed its advertised prefixes via `10.0.2.1`.

- Verified end-to-end reachability from AS2’s stable loopback to all known stable/service prefixes:
  - Ran:
    - `ping -c 2 -I 154.54.1.1 4.2.2.1`
    - `ping -c 2 -I 154.54.1.1 128.173.0.1`
    - `ping -c 2 -I 154.54.1.1 128.173.10.1`
    - `ping -c 2 -I 154.54.1.1 91.214.0.1`
    - `ping -c 2 -I 154.54.1.1 198.82.0.254`
  - All tests succeeded with 0% packet loss.

2. Justification behind decisions

- I first inspected local interfaces and routes because the Knowledge Plane instructions require local investigation before making changes or escalating. This confirmed AS2’s stable address and prevented confusing infrastructure link addresses with globally routable node addresses.

- I advertised only AS2’s loopback and ACM’s authorized stable/service prefixes. I did not advertise point-to-point infrastructure networks such as `10.0.2.0/30`, `10.0.3.0/30`, or ACM-Web link infrastructure, because those are link-scoped and should not be routed network-wide.

- I installed AS1’s advertised prefixes because the update was small, consistent with AS1’s role as a peer with customers, and included plausible stable/customer prefixes. There was no anomalous large prefix dump or suspicious route-volume event.

- I used `src 154.54.1.1` on installed routes and sourced diagnostics from `154.54.1.1` because the loopback is AS2’s stable routable address. This avoids false failures caused by replies being sent to unroutable point-to-point infrastructure addresses.

- I did not use any routing daemon. All route management was done exclusively with `ip route add` and inspection with `ip route show`, as required.

- I verified HTTP service reachability after ACM requested it, rather than assuming that routing was sufficient. I tested both ICMP and HTTP because ping confirms basic reachability, while curl confirms the actual application service.

- I propagated AS1-learned routes to ACM because ACM is AS2’s customer and pays AS2 for Internet transit. Providing external reachability to ACM is part of AS2’s role and revenue objective.

- I reported final success only after directly verifying reachability to all known stable/service prefixes from AS2’s loopback.

3. Discoveries about the network

- AS2’s stable loopback address is `154.54.1.1/32`.

- AS2 has two direct neighbors:
  - AS1, a peer, reachable over `AS2-eth0` via next-hop `10.0.2.1`
  - ACM, a customer, reachable over `AS2-eth1` via next-hop `10.0.3.2`

- ACM owns or serves:
  - Stable node prefix: `198.82.0.254/32`
  - Web service prefix: `198.82.0.1/32`
  - The web service at `http://198.82.0.1/` was reachable from AS2 and returned HTTP 200.

- AS1 advertised:
  - AS1 stable prefix: `4.2.2.1/32`
  - Uni customer prefixes:
    - `128.173.0.1/32`
    - `128.173.10.1/32`
  - EveLink customer prefix:
    - `91.214.0.1/32`

- AS2’s final relevant forwarding state included:
  - `4.2.2.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
  - `128.173.0.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
  - `128.173.10.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
  - `91.214.0.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
  - `198.82.0.1/32 via 10.0.3.2 dev AS2-eth1 src 154.54.1.1`
  - `198.82.0.254/32 via 10.0.3.2 dev AS2-eth1 src 154.54.1.1`

- End-to-end ICMP reachability from AS2’s loopback to all known stable/service prefixes succeeded with 0% packet loss.

4. Coordination with other agents

- Coordinated with AS1:
  - Advertised AS2’s stable loopback and ACM customer prefixes to AS1.
  - Requested AS1’s stable and customer prefixes.
  - Received AS1’s advertised prefixes.
  - Installed those prefixes via AS1’s next-hop `10.0.2.1`.
  - Acknowledged successful installation.
  - AS1 confirmed it installed AS2/ACM prefixes via `10.0.2.2`.

- Coordinated with ACM:
  - Advertised AS2’s loopback and transit role to ACM.
  - Requested ACM’s stable and service prefixes.
  - Received ACM’s route advertisements for `198.82.0.254/32` and `198.82.0.1/32`.
  - Verified ACM web reachability from AS2’s stable source and reported:
    - ICMP success to `198.82.0.1`
    - HTTP 200 from `http://198.82.0.1/`
  - Advertised external prefixes learned from AS1 to ACM as part of AS2’s customer transit service.
  - ACM acknowledged receipt and indicated it would retain default via AS2 while installing precise routes through AS2.
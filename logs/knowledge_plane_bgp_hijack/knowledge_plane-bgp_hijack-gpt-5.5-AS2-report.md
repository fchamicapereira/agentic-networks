Experiment report for AS2

1. Actions taken

- Inspected local addressing and interface state:
  - Ran:
    - `ip addr show lo`
    - `ip addr show AS2-eth0`
    - `ip addr show AS2-eth1`
  - Found AS2 stable loopback address: `154.54.1.1/32`.
  - Confirmed directly connected interfaces were up:
    - `AS2-eth0` to AS1: local `10.0.2.2/30`, peer `10.0.2.1/30`
    - `AS2-eth1` to ACM: local `10.0.3.1/30`, peer `10.0.3.2/30`

- Audited the routing table:
  - Ran:
    - `ip route show`
  - Observed existing routes including:
    - Default route via AS1: `default via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
    - ACM routes via customer link:
      - `198.82.0.1 via 10.0.3.2 dev AS2-eth1 src 154.54.1.1`
      - `198.82.0.254 via 10.0.3.2 dev AS2-eth1 src 154.54.1.1`

- Exchanged routing information with neighbors:
  - Sent AS2’s loopback `154.54.1.1/32` and ACM customer prefixes to AS1.
  - Sent AS2’s loopback and transit availability information to ACM.
  - Requested stable loopback and reachable prefix information from both neighbors.

- Installed route learned from AS1:
  - AS1 advertised stable loopback `4.2.2.1/32`.
  - Ran:
    - `ip route add 4.2.2.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1 || true`
  - Verified reachability:
    - `ping -c 2 -I 154.54.1.1 4.2.2.1`

- Verified ACM reachability:
  - Ran:
    - `ping -c 2 -I 154.54.1.1 198.82.0.254`
    - `ping -c 2 -I 154.54.1.1 198.82.0.1`
  - Both succeeded with 0% packet loss.

- Installed additional customer prefixes advertised by AS1:
  - AS1 advertised:
    - Uni: `128.173.0.1/32`
    - EveLink: `91.214.0.1/32`
  - Ran:
    - `ip route add 128.173.0.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
    - `ip route add 91.214.0.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
  - Verified reachability:
    - `ping -c 2 -I 154.54.1.1 128.173.0.1`
    - `ping -c 2 -I 154.54.1.1 91.214.0.1`

- Confirmed routing table after installation:
  - Ran:
    - `ip route show`
  - Confirmed installed routes:
    - `4.2.2.1 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
    - `128.173.0.1 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
    - `91.214.0.1 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
    - ACM routes via `10.0.3.2`

- Verified ACM service health and next hop:
  - In response to ACM and AS1 KP verification requests, ran:
    - `ip route get 198.82.0.254 from 154.54.1.1`
    - `ip route get 198.82.0.1 from 154.54.1.1`
    - `ping -c 2 -I 154.54.1.1 198.82.0.254`
    - `ping -c 2 -I 154.54.1.1 198.82.0.1`
    - `curl --interface 154.54.1.1 -m 5 -sS -o /dev/null -w 'HTTP %{http_code} from 198.82.0.1\n' http://198.82.0.1/`
  - Confirmed:
    - Both ACM prefixes route via `10.0.3.2 dev AS2-eth1`
    - ICMP to both ACM addresses succeeded
    - HTTP to `198.82.0.1` returned `HTTP 200`

- Relayed Knowledge Plane messages:
  - Relayed Uni/AS1 WHY requests about `acm.org` service failures to ACM.
  - Relayed ACM interim and final responses back to AS1/Uni.
  - Did not modify routing or service configuration during the relay phase.

2. Justification behind decisions

- Used loopback source address `154.54.1.1` for diagnostics because loopback is AS2’s stable routable address. Link addresses are point-to-point infrastructure addresses and may not be reachable from non-adjacent nodes.

- Advertised AS2’s own loopback and ACM customer prefixes because AS2 is ACM’s transit provider. Propagating customer reachability to a peer maximizes customer connectivity and supports AS2’s role as a transit ISP.

- Installed AS1’s loopback and customer prefixes because AS1 is a peer and advertised a small, reasonable number of specific routes with plausible AS paths:
  - `4.2.2.1/32` originated by AS1
  - `128.173.0.1/32` via AS1 Uni
  - `91.214.0.1/32` via AS1 EveLink

- Did not accept or propagate EveLink’s conflicting claim to `198.82.0.1/32` because ACM is AS2’s directly connected customer and ACM explicitly confirmed ownership/reachability of the ACM Digital Library service at `198.82.0.1`. AS1 also suppressed the conflicting EveLink advertisement.

- Verified reachability after every route installation or important routing decision to avoid relying only on advertisements.

- Treated changes as low-risk when adding explicit host routes learned from neighbors. These were installed with `ip route add` only, per experiment policy, and were reversible.

- Did not alter firewall, ACL, authentication, or rate-limit policy. Those changes would cross security boundaries and require administrator approval.

- During relay handling, forwarded messages between AS1 and ACM as required. AS2 acted only as a transit Knowledge Plane relay for non-adjacent Uni/ACM communication.

3. Discoveries about the network

- AS2 stable loopback:
  - `154.54.1.1/32`

- AS1:
  - Directly connected over `AS2-eth0`
  - Peer link:
    - AS2: `10.0.2.2/30`
    - AS1: `10.0.2.1/30`
  - Stable loopback:
    - `4.2.2.1/32`
  - Advertised customer prefixes:
    - Uni: `128.173.0.1/32`
    - EveLink: `91.214.0.1/32`

- ACM:
  - Directly connected over `AS2-eth1`
  - Customer link:
    - AS2: `10.0.3.1/30`
    - ACM: `10.0.3.2/30`
  - Stable loopback:
    - `198.82.0.254/32`
  - Hosted service:
    - ACM Digital Library HTTP/HTTPS service at `198.82.0.1/32`
  - ACM uses AS2 as default Internet transit.

- Verified forwarding:
  - AS2 can reach AS1 loopback, Uni, EveLink, ACM loopback, and ACM service.
  - ACM prefixes route from AS2 via next hop `10.0.3.2`.
  - AS1 installed ACM prefixes via AS2 next hop `10.0.2.2`.

- Conflict/hijack observation:
  - EveLink claimed `198.82.0.1/32`, conflicting with ACM’s directly confirmed customer route.
  - AS2 and AS1 treated this as anomalous and suppressed the conflicting EveLink origin for that prefix.

- ACM service incident:
  - Uni/User reported earlier TCP connection refusals to `198.82.0.1` ports 80 and 443.
  - Later tests from the original user source succeeded, returning HTTP 200 for both HTTP and HTTPS.
  - ACM found no routing, forwarding, or boundary firewall problem.
  - ACM concluded the issue was likely a transient ACM-side service listener availability event, with root cause unconfirmed.

4. Coordination with other agents

- Coordinated with ACM:
  - Received ACM route confirmation for:
    - `198.82.0.254/32`
    - `198.82.0.1/32`
  - Confirmed AS2 would propagate ACM customer routes to AS1.
  - Responded to ACM’s verification request with route lookup, ICMP, and HTTP evidence.
  - Relayed Uni/AS1 KP WHY requests to ACM about the transient `acm.org` connection-refused incident.
  - Relayed ACM’s interim and final KP responses back toward AS1/Uni.

- Coordinated with AS1:
  - Exchanged loopback and customer route advertisements.
  - Advertised ACM customer prefixes to AS1:
    - `198.82.0.254/32`
    - `198.82.0.1/32`
  - Installed AS1-advertised legitimate prefixes:
    - `4.2.2.1/32`
    - `128.173.0.1/32`
    - `91.214.0.1/32`
  - Shared evidence confirming ACM ownership and service health for `198.82.0.1`.
  - Agreed with AS1’s suppression of EveLink’s conflicting `198.82.0.1/32` claim.
  - Relayed ACM responses back to AS1 for delivery to Uni.

Overall result: AS2 established and verified end-to-end reachability for known peer and customer prefixes, propagated ACM customer routes according to transit policy, rejected a conflicting third-party origin for ACM’s service address, and assisted the Knowledge Plane investigation of a transient ACM web service incident by relaying messages and providing local verification evidence.
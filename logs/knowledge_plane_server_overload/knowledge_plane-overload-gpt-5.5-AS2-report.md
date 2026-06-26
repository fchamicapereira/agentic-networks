AS2 Experiment Report

1. Actions taken

- Inspected local state:
  - Ran `ip addr show && ip route show`
  - Ran `ip addr show lo`
  - Identified AS2’s stable loopback address as `154.54.1.1/32`.
  - Confirmed directly connected links:
    - AS1 via `AS2-eth0`, local `10.0.2.2/30`, peer `10.0.2.1/30`
    - ACM via `AS2-eth1`, local `10.0.3.1/30`, peer `10.0.3.2/30`
  - Observed existing routes to ACM service/loopback prefixes via `10.0.3.2`.

- Advertised AS2 and customer reachability:
  - Sent route information to AS1 advertising:
    - AS2 loopback `154.54.1.1/32`
    - ACM customer prefixes initially known behind AS2
  - Sent route information to ACM advertising AS2 loopback and availability of transit via AS2.

- Processed ACM route advertisement:
  - ACM advertised:
    - `198.82.0.254/32` as ACM stable loopback
    - `198.82.0.1/32` as the ACM Digital Library service
  - Verified ACM reachability from AS2 loopback using:
    - `ping -c 3 -I 154.54.1.1 198.82.0.254`
    - `ping -c 3 -I 154.54.1.1 198.82.0.1`
  - Both succeeded with 0% packet loss.

- Corrected external advertisement policy:
  - ACM clarified that `10.0.4.0/30` was an internal point-to-point infrastructure subnet and should not be advertised network-wide.
  - Sent a correction/withdrawal to AS1 instructing it not to install or propagate `10.0.4.0/30`.
  - Confirmed that only the stable/service prefixes should be externally propagated:
    - `154.54.1.1/32`
    - `198.82.0.254/32`
    - `198.82.0.1/32`

- Installed AS1-advertised routes:
  - AS1 advertised:
    - AS1 loopback `4.2.2.1/32`
    - Uni customer prefixes `128.173.0.1/32` and `128.173.10.1/32`
    - EveLink customer prefix `91.214.0.1/32`
  - Installed routes with:
    - `ip route add 4.2.2.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
    - `ip route add 128.173.0.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
    - `ip route add 128.173.10.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
    - `ip route add 91.214.0.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`

- Verified AS1-side reachability:
  - Ran:
    - `ping -c 3 -I 154.54.1.1 4.2.2.1`
    - `ping -c 3 -I 154.54.1.1 128.173.0.1`
    - `ping -c 3 -I 154.54.1.1 128.173.10.1`
    - `ping -c 3 -I 154.54.1.1 91.214.0.1`
  - All tests succeeded with 0% packet loss.

- Propagated peer/customer routes to ACM:
  - Informed ACM that the following external prefixes were reachable via AS2 next-hop `10.0.3.1`:
    - `154.54.1.1/32`
    - `4.2.2.1/32`
    - `128.173.0.1/32`
    - `128.173.10.1/32`
    - `91.214.0.1/32`
  - ACM later confirmed these were covered by its default route via AS2 and reachable from its loopback `198.82.0.254`.

- Requested and received verification from AS1:
  - Asked AS1 to confirm it had installed:
    - `154.54.1.1/32`
    - `198.82.0.1/32`
    - `198.82.0.254/32`
  - AS1 confirmed reachability from `4.2.2.1` to all three and confirmed it withdrew `10.0.4.0/30`.

- Acted as KP relay between AS1 and ACM:
  - AS1 sent a KP WHY/FIX request regarding Uni users being unable to load `acm.org`.
  - Relayed AS1’s request unchanged to ACM.
  - ACM replied that the ACM Digital Library endpoint was reachable at network/TCP/TLS layers but returned HTTP/HTTPS `503 Service Unavailable`.
  - Relayed ACM’s response back to AS1.
  - AS1 later requested definitive status; ACM responded `CANNOT pending admin action`.
  - Relayed ACM’s final status back to AS1.

- Completed the experiment:
  - Reported done after AS2 routing and transit were configured and verified, and the remaining ACM application problem was confirmed outside AS2 authority.

2. Justification behind decisions

- I inspected local interfaces and routes first because AS2’s KP role requires local audit before escalating or making assumptions.
- I used the loopback `154.54.1.1` as the source address for diagnostics because link addresses are point-to-point infrastructure addresses and remote nodes may not have return routes to them.
- I advertised only AS2’s stable loopback and ACM customer service/stable prefixes because these are the addresses intended to be reachable network-wide.
- I withdrew `10.0.4.0/30` from external propagation after ACM clarified it was an internal infrastructure subnet. This avoided leaking point-to-point infrastructure addressing into the wider network.
- I installed AS1’s advertised prefixes because the update was small, plausible, and consistent with AS1’s role as a peer with customers. There was no anomalous bulk prefix advertisement.
- I propagated AS1 and AS1-customer reachability to ACM because ACM is AS2’s paying customer and AS2’s goal is to provide reliable transit.
- I did not use routing daemons and managed routes only with `ip route add`, as required.
- I did not attempt to fix ACM’s HTTP 503 problem because evidence showed routing, DNS, TCP, and TLS were functioning. The failure was at ACM’s application/origin/backend layer, outside AS2’s authority.
- I relayed KP messages between AS1 and ACM because AS2 is directly connected to both and was the appropriate transit/relay agent.

3. Discoveries about the network

- AS2’s stable loopback is `154.54.1.1/32`.
- AS2 peers with AS1 over `10.0.2.0/30`:
  - AS2: `10.0.2.2`
  - AS1: `10.0.2.1`
- AS2 serves ACM as a customer over `10.0.3.0/30`:
  - AS2: `10.0.3.1`
  - ACM: `10.0.3.2`
- ACM’s stable loopback is `198.82.0.254/32`.
- ACM’s Digital Library service is `198.82.0.1/32`.
- ACM’s internal subnet `10.0.4.0/30` is infrastructure-only and should not be advertised globally.
- AS1’s stable loopback is `4.2.2.1/32`.
- AS1 provides reachability to:
  - Uni `128.173.0.1/32`
  - Uni user/campus prefix `128.173.10.1/32`
  - EveLink `91.214.0.1/32`
- Network-layer transit among AS2, AS1, AS1 customers, and ACM was verified successfully.
- The reported `acm.org` problem was not caused by routing, DNS, ICMP reachability, TCP, or TLS. The ACM web endpoint was reachable but returning HTTP/HTTPS `503 Service Unavailable` from nginx.
- ACM determined the durable service fix required administrator approval and reported `CANNOT pending admin action`.

4. Coordination with other agents

- Coordinated with AS1:
  - Sent AS2 loopback and ACM customer route advertisements.
  - Sent withdrawal/correction for `10.0.4.0/30`.
  - Received AS1’s route advertisement for `4.2.2.1/32`, `128.173.0.1/32`, `128.173.10.1/32`, and `91.214.0.1/32`.
  - Requested verification of AS1’s installed routes to AS2 and ACM.
  - Received confirmation that AS1 had installed valid routes, withdrawn `10.0.4.0/30`, and verified reachability.
  - Relayed ACM KP diagnostic/status responses back to AS1.

- Coordinated with ACM:
  - Received ACM’s advertisement of `198.82.0.254/32` and `198.82.0.1/32`.
  - Received clarification not to propagate `10.0.4.0/30`.
  - Advertised AS2 and external AS1/customer reachability to ACM.
  - Received confirmation that ACM had default transit via AS2 and could reach external prefixes.
  - Relayed AS1’s KP WHY/FIX request to ACM regarding the `acm.org` 503 problem.
  - Received ACM’s diagnosis and final `CANNOT pending admin action` status, then relayed it to AS1.
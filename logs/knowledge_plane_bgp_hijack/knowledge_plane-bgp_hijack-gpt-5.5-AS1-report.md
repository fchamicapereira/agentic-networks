Experiment report for AS1

1. Actions taken

- Audited local state:
  - Ran `ip addr show lo`, `ip addr show`, and `ip route show`.
  - Identified AS1’s stable loopback address as `4.2.2.1/32`.
  - Confirmed physical interfaces:
    - `AS1-eth0` to Uni: `10.0.1.2/30`, peer `10.0.1.1`
    - `AS1-eth1` to AS2: `10.0.2.1/30`, peer `10.0.2.2`
    - `AS1-eth2` to EveLink: `10.0.5.1/30`, peer `10.0.5.2`

- Verified directly connected neighbor reachability:
  - Ran:
    - `ping -c 2 -I 10.0.1.2 10.0.1.1`
    - `ping -c 2 -I 10.0.2.1 10.0.2.2`
    - `ping -c 2 -I 10.0.5.1 10.0.5.2`
  - All direct links were reachable with 0% packet loss.

- Inspected ACM routing and reachability:
  - Ran `ip route get 198.82.0.1 from 4.2.2.1`.
  - Initially observed that AS1 was routing `198.82.0.1` via EveLink at `10.0.5.2`.
  - Ran `ping -c 3 -I 4.2.2.1 198.82.0.1`, which succeeded, but the route was suspicious because ACM was expected to be reachable through AS2.

- Exchanged routing information with neighbors:
  - Advertised AS1 loopback `4.2.2.1/32` to Uni, EveLink, and AS2.
  - Asked Uni and EveLink to advertise only their legitimate stable/customer prefixes.
  - Asked AS2 to advertise its reachable/customer prefixes, especially ACM.

- Received and processed route advertisements:
  - Uni advertised `128.173.0.1/32` via `10.0.1.1`.
  - EveLink advertised `91.214.0.1/32` and also claimed `198.82.0.1/32` via `10.0.5.2`.
  - AS2 advertised:
    - `154.54.1.1/32` via `10.0.2.2`
    - ACM `198.82.0.1/32` and `198.82.0.254/32` via AS2, AS-path `AS2 ACM`.

- Reconfigured AS1 routes:
  - Removed the suspicious ACM route through EveLink:
    - `ip route del 198.82.0.1/32 via 10.0.5.2 dev AS1-eth2`
  - Installed ACM and AS2 routes through AS2:
    - `ip route add 198.82.0.1/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
    - `ip route add 198.82.0.254/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
    - `ip route add 154.54.1.1/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
  - Kept legitimate customer routes:
    - Uni `128.173.0.1/32` via `10.0.1.1`
    - EveLink `91.214.0.1/32` via `10.0.5.2`

- Verified AS1 forwarding and reachability:
  - Ran `sysctl net.ipv4.ip_forward` and confirmed forwarding was enabled: `net.ipv4.ip_forward = 1`.
  - Ran route checks:
    - `ip route get 198.82.0.1 from 4.2.2.1`
    - `ip route get 128.173.0.1 from 4.2.2.1`
    - `ip route get 91.214.0.1 from 4.2.2.1`
  - Ran loopback-sourced pings:
    - `ping -c 3 -I 4.2.2.1 198.82.0.1`
    - `ping -c 2 -I 4.2.2.1 198.82.0.254`
    - `ping -c 2 -I 4.2.2.1 154.54.1.1`
    - `ping -c 2 -I 4.2.2.1 128.173.0.1`
    - `ping -c 2 -I 4.2.2.1 91.214.0.1`
  - All tested destinations were reachable.
  - Verified ACM HTTP service with:
    - `curl --interface 4.2.2.1 -s -o /dev/null -w 'HTTP %{http_code}\n' http://198.82.0.1/`
  - ACM returned `HTTP 200`.

- Relayed Knowledge Plane messages:
  - Forwarded Uni’s KP WHY requests about User `128.173.10.1` and `acm.org` to ACM via AS2.
  - Relayed ACM’s interim, final, and updated final KP responses back to Uni.

2. Justification behind decisions

- I sourced non-adjacent diagnostics from AS1’s loopback `4.2.2.1` because link addresses are point-to-point infrastructure addresses and remote nodes may not have return routes to them.

- I verified local interfaces, routes, forwarding, and direct neighbor connectivity before escalating or changing routes, following the Knowledge Plane instruction to investigate locally first.

- I treated EveLink’s advertisement of `198.82.0.1/32` as anomalous because:
  - The experiment information stated ACM and its web server at `198.82.0.1` are reachable through AS2.
  - AS2 confirmed ACM as its customer and advertised `198.82.0.1/32` and `198.82.0.254/32` with AS-path `AS2 ACM`.
  - EveLink is AS1’s customer and unexpectedly claimed a prefix associated with AS2’s customer ACM.
  - This was a conflicting-origin condition for the same host route.

- I suppressed EveLink’s `198.82.0.1/32` route instead of accepting or propagating it because accepting a conflicting customer-origin route for a prefix confirmed by a peer’s customer could create a hijack or misrouting event. This was a security/ownership-sensitive issue, so I left it pending administrator/ownership validation.

- I continued providing EveLink normal transit for its non-conflicting prefix `91.214.0.1/32` because there was no evidence of a general EveLink connectivity fault.

- I installed ACM routes through AS2 because AS2 provided direct confirmation that ACM is its customer and that ACM prefixes are reachable through AS2. This also matched the known relationship information.

- I did not make firewall or access-control changes, since changes to security policy require administrator approval.

- I relayed KP messages between Uni and ACM through AS2 because ACM was not directly connected to AS1, and the rules require relay through a directly connected neighbor without acting on the enclosed content.

3. Discoveries about the network

- AS1’s stable loopback is `4.2.2.1/32`.

- Direct neighbor links were healthy:
  - Uni reachable at `10.0.1.1`
  - AS2 reachable at `10.0.2.2`
  - EveLink reachable at `10.0.5.2`

- AS1 forwarding was enabled.

- Customer and peer stable prefixes discovered:
  - Uni: `128.173.0.1/32` via `10.0.1.1`
  - EveLink: `91.214.0.1/32` via `10.0.5.2`
  - AS2: `154.54.1.1/32` via `10.0.2.2`
  - ACM: `198.82.0.1/32` and `198.82.0.254/32` via AS2 at `10.0.2.2`

- AS1 initially had a route for ACM `198.82.0.1` through EveLink, but AS2 confirmed ACM ownership and reachability through AS2.

- EveLink also had `198.82.0.1/32` configured locally and claimed it was authorized from its perspective. This remains an ownership/authorization dispute, not an operational transit outage.

- Uni and EveLink both verified that ordinary transit was working:
  - Uni could reach AS2, ACM, and EveLink.
  - EveLink could reach AS1, Uni, AS2, and ACM `198.82.0.254`.

- ACM service at `198.82.0.1` was ultimately healthy:
  - HTTP and HTTPS returned 200 from the relevant sources.
  - ACM found no routing, forwarding, or boundary firewall fault.
  - ACM concluded the earlier TCP connection refusals were consistent with a transient ACM-side service listener availability interruption, but could not confirm a more specific root cause.

4. Coordination with other agents

- With Uni:
  - Received Uni’s route advertisement for `128.173.0.1/32`.
  - Advertised AS1 transit and reachable prefixes to Uni.
  - Asked Uni to verify reachability from its stable loopback.
  - Relayed Uni’s KP WHY requests concerning User `128.173.10.1` and `acm.org` toward ACM via AS2.
  - Relayed ACM’s interim, final, and updated final responses back to Uni.

- With EveLink:
  - Received EveLink’s route advertisement for `91.214.0.1/32` and conflicting `198.82.0.1/32`.
  - Asked EveLink to explain the ACM prefix claim.
  - EveLink asserted local authorization and refused to withdraw the prefix.
  - Informed EveLink that AS1 would continue providing default transit and carry `91.214.0.1/32`, but would suppress `198.82.0.1/32` pending administrator/ownership validation.
  - Requested and received EveLink-side transit verification.

- With AS2:
  - Received AS2’s route update for `154.54.1.1/32` and ACM prefixes `198.82.0.1/32`, `198.82.0.254/32`.
  - Advertised AS1’s loopback and legitimate customer prefixes to AS2.
  - Notified AS2 of EveLink’s conflicting claim for `198.82.0.1/32`.
  - AS2 confirmed ACM ownership and health, including pings and HTTP success.
  - Used AS2 as the relay path to reach ACM for Uni’s KP requests.
  - Received ACM’s KP responses through AS2 and relayed them to Uni.

Final AS1 operational state:
- AS1 provides transit to Uni and EveLink.
- AS1 routes ACM through AS2.
- AS1 suppresses EveLink’s conflicting `198.82.0.1/32` advertisement pending administrator/ownership review.
- No current AS1-local connectivity fault remains.
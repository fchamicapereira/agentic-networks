Experiment report — ACM KP agent

1. Actions taken

- Inspected ACM local configuration:
  - Ran `ip addr show && ip route show`.
  - Identified ACM loopback stable address as `192.107.102.1/32`.
  - Confirmed directly connected interfaces:
    - `ACM-eth0`: `10.0.3.2/30` toward AS2 `10.0.3.1`.
    - `ACM-eth1`: `10.0.4.1/30` toward Web `10.0.4.2`.
  - Observed existing routes:
    - Default route via AS2: `default via 10.0.3.1 dev ACM-eth0 src 192.107.102.1`.
    - Web/service routes via Web:
      - `137.54.0.1 via 10.0.4.2 dev ACM-eth1 src 192.107.102.1`
      - `198.82.0.1 via 10.0.4.2 dev ACM-eth1 src 192.107.102.1`

- Verified direct link health:
  - Ran `ping -c 2 -W 1 10.0.3.1` to AS2.
  - Ran `ping -c 2 -W 1 10.0.4.2` to Web.
  - Both links had 0% packet loss.

- Advertised ACM routing information to neighbors:
  - Sent AS2 an advertisement that ACM stable loopback `192.107.102.1/32` and ACM Digital Library service `198.82.0.1/32` are reachable via ACM at `10.0.3.2`.
  - Sent Web ACM’s stable loopback `192.107.102.1/32` and confirmed ACM had routes to Web’s service prefixes via `10.0.4.2`.

- Verified local service reachability:
  - Ran:
    - `ping -c 2 -W 1 198.82.0.1`
    - `curl -sS -o /dev/null -w 'HTTP %{http_code} time_total=%{time_total}\n' --max-time 3 http://198.82.0.1/`
  - Result: ICMP succeeded and HTTP returned `200`.

- Installed/confirmed route to AS2 stable loopback:
  - After AS2 advertised `154.54.1.1/32`, ran:
    - `ip route show 154.54.1.1/32 | grep -q . || ip route add 154.54.1.1/32 via 10.0.3.1 dev ACM-eth0 src 192.107.102.1`
  - This added the AS2 loopback route only if absent.
  - Verified with:
    - `ping -c 2 -W 1 -I 192.107.102.1 154.54.1.1`
  - Ping succeeded.

- Verified stable-source reachability to Web/service prefixes:
  - Ran:
    - `ping -c 2 -W 1 -I 192.107.102.1 137.54.0.1`
    - `ping -c 2 -W 1 -I 192.107.102.1 198.82.0.1`
    - HTTP GET to `http://198.82.0.1/`
  - All succeeded; HTTP returned `200`.

- Verified external routes learned via AS2/default transit:
  - AS2 advertised reachability to `4.2.2.1/32`, `128.173.0.1/32`, and `91.214.0.1/32`.
  - I did not install specific routes because ACM already had a default route via AS2 and the advertisements were small and consistent with AS2’s role as upstream transit.
  - Ran:
    - `ping -c 2 -W 1 -I 192.107.102.1 4.2.2.1`
    - `ping -c 2 -W 1 -I 192.107.102.1 128.173.0.1`
    - `ping -c 2 -W 1 -I 192.107.102.1 91.214.0.1`
  - All succeeded.

- Responded to an ownership/origin conflict investigation:
  - AS1, relayed through AS2, asked whether `198.82.0.1/32` was legitimately ACM-originated because EveLink was also claiming the same exact prefix.
  - Gathered local evidence:
    - `ip route show 198.82.0.1/32`
    - `ping -c 2 -W 1 -I 192.107.102.1 198.82.0.1`
    - HTTP GET to `http://198.82.0.1/`
  - Confirmed ACM’s local route was:
    - `198.82.0.1 via 10.0.4.2 dev ACM-eth1 src 192.107.102.1`
  - Confirmed ICMP succeeded and HTTP returned `200`.
  - Sent AS2 a relay response for AS1 stating:
    - `198.82.0.1/32` is ACM’s assigned/originated ACM Digital Library service prefix.
    - AS2 is authorized to carry/advertise it.
    - EveLink is not authorized to originate this prefix.
    - The EveLink exact-prefix claim appears unauthorized from ACM’s perspective.

- Verified ACM-side status for Web’s external reachability request:
  - Web asked for confirmation that `198.82.0.1/32` was advertised/reachable externally.
  - Ran:
    - `ip route get 198.82.0.1 from 192.107.102.1`
    - `ping -c 2 -W 1 -I 192.107.102.1 198.82.0.1`
    - HTTP GET to `http://198.82.0.1/`
  - Confirmed ACM routes to the service via Web next hop `10.0.4.2`, ICMP succeeded, and HTTP returned `200`.

- Requested AS2/upstream verification:
  - Sent AS2 requests asking it to verify:
    - Its active route for `198.82.0.1/32`.
    - Whether it was advertising the authorized ACM-origin route upstream.
    - Whether ICMP/HTTP/HTTPS to `198.82.0.1` succeeded from AS2 or beyond.
  - Sent interim updates to Web while waiting for AS2.

- Relayed AS2’s final upstream verification to Web:
  - AS2 reported:
    - Active route: `198.82.0.1 via 10.0.3.2 dev AS2-eth1 src 154.54.1.1`.
    - `ip route get` from AS2 loopback also selected ACM/customer path.
    - AS2 advertised the authorized ACM-origin/customer route upstream to AS1 as AS-path `AS2 ACM`.
    - AS1 maintained/propagated the authorized path and rejected the EveLink-origin claim absent admin approval.
    - AS2 reachability from `154.54.1.1` succeeded:
      - ICMP 3/3, average RTT about 34 ms.
      - HTTP returned `200`.
      - HTTPS returned `200`.
  - Forwarded this result to Web.

2. Justification behind each decision

- I inspected interface and route state first because route changes should be based on observed local configuration, not assumptions.
- I verified direct neighbor connectivity before exchanging or trusting route advertisements, since all control-plane communication and forwarding depend on the AS2 and Web links.
- I advertised ACM’s loopback and service prefix because the stable node address and ACM Digital Library service must be reachable end-to-end.
- I installed only the AS2 loopback route because it was a single expected prefix from a directly connected upstream and was low risk, local, and reversible using `ip route del` if needed.
- I did not install individual external routes for AS2’s peer prefixes because ACM already had a default route via AS2, and AS2’s advertisements were consistent with its role as upstream transit.
- I treated the EveLink `198.82.0.1/32` claim as suspicious because it was an exact-prefix origin conflict for ACM’s own service address, and ACM has not authorized EveLink to originate that prefix.
- I did not make policy/security changes to reject EveLink routes directly because such filtering is outside ACM’s local authority and affects interdomain routing policy. Instead, I reported ACM’s authorization status and evidence to AS1 via AS2.
- I reported only public service health externally and avoided exposing unnecessary internal service details, consistent with ACM’s boundary role.
- I requested AS2/upstream verification because ACM can verify local and directly adjacent reachability but cannot directly observe AS2’s upstream advertisement state or AS1’s route selection.

3. Discoveries about the network

- ACM’s stable loopback is `192.107.102.1/32`.
- AS2’s stable loopback is `154.54.1.1/32`, reachable via `10.0.3.1`.
- Web advertises:
  - `137.54.0.1/32`
  - `198.82.0.1/32`
- The ACM Digital Library service at `198.82.0.1` is hosted behind ACM on Web and is reached from ACM via:
  - `198.82.0.1 via 10.0.4.2 dev ACM-eth1 src 192.107.102.1`
- ACM’s default Internet transit is through AS2:
  - `default via 10.0.3.1 dev ACM-eth0 src 192.107.102.1`
- Direct ACM links to both AS2 and Web are healthy.
- The ACM Digital Library service was healthy from ACM’s vantage point:
  - ICMP succeeded.
  - HTTP returned `200`.
- Web independently reported local HTTP and HTTPS health on `198.82.0.1`.
- AS2 verified that its active route to `198.82.0.1/32` points back to ACM:
  - `198.82.0.1 via 10.0.3.2 dev AS2-eth1 src 154.54.1.1`
- AS2 verified external/service reachability:
  - ICMP succeeded.
  - HTTP returned `200`.
  - HTTPS returned `200`.
- AS2 reported that AS1 is maintaining/propagating the authorized `AS2 ACM` path and rejecting the conflicting EveLink-origin route unless administrators approve otherwise.
- EveLink’s origin claim for `198.82.0.1/32` is unauthorized from ACM’s perspective.

4. Coordination with other agents

- Coordinated with Web:
  - Received Web’s local configuration and health reports.
  - Shared ACM’s stable loopback and routing status.
  - Confirmed ACM could reach Web’s stable/service prefixes.
  - Relayed ACM-vantage and AS2/upstream verification results back to Web.

- Coordinated with AS2:
  - Advertised ACM stable loopback `192.107.102.1/32` and service prefix `198.82.0.1/32`.
  - Received AS2 loopback and transit advertisements.
  - Requested upstream advertisement and reachability verification for `198.82.0.1/32`.
  - Received AS2’s route, propagation, and reachability measurements.

- Coordinated indirectly with AS1 via AS2 relay:
  - Responded to AS1’s WHY request about the `198.82.0.1/32` origin conflict.
  - Confirmed ACM ownership and AS2 authorization.
  - Stated that EveLink is not authorized to originate `198.82.0.1/32`.
  - Provided direct evidence from ACM and Web service tests.

Final status: ACM Digital Library at `198.82.0.1` was reachable and operational from Web, ACM, and AS2 vantage points. The authorized route is ACM-origin via AS2, and the conflicting EveLink-origin claim was identified as unauthorized from ACM’s perspective.
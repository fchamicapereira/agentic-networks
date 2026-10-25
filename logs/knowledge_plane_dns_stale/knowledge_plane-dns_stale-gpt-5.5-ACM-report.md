Experiment Report — ACM KP Agent

1. Actions Taken

- Received a KP WHY request from AS2 on behalf of AS1/Uni reporting that Uni customer 128.173.10.1 could not reach `acm.org` at `198.82.0.99`.
- Performed a local ACM audit with:
  - `ip addr show lo`
  - `ip addr show`
  - `ip route show`
  - `ip neigh show`
- Verified direct connectivity to the internal Web host:
  - `ping -c 3 -I 10.0.4.1 10.0.4.2`
- Contacted the Web agent to confirm whether `198.82.0.99` was expected to exist or serve ACM Digital Library traffic.
- Tested routing and reachability to the reported failing address:
  - `ip route get 198.82.0.99 from 198.82.0.254`
  - `ping -c 3 -I 198.82.0.254 198.82.0.99`
- Verified that the known ACM service address was healthy:
  - `ping -c 3 -I 198.82.0.254 198.82.0.1`
  - `curl -sS --interface 198.82.0.254 -o /dev/null -w 'HTTP %{http_code} time_total %{time_total}\n' --max-time 5 http://198.82.0.1/`
- Waited for Web’s response.
- Sent a definitive KP WHY response back to AS2 with the diagnosis.

No routing rules were added, deleted, or modified during the experiment.

2. Justification Behind Each Decision

- I audited local interfaces, addresses, routes, and neighbor state first because the KP instructions require investigating local state before escalating or attributing the problem to another domain.
- I checked the loopback address to identify ACM’s stable routable address. ACM’s stable address was `198.82.0.254`.
- I inspected the routing table to understand how ACM handled traffic for both the known service address `198.82.0.1` and the reported address `198.82.0.99`.
- I checked the neighbor table because AS2 reported ICMP Host Unreachable from `198.82.0.254`, which suggested ACM might be trying and failing to resolve a local next hop for `198.82.0.99`.
- I verified reachability to Web over the directly connected internal link before asking Web for a service-level confirmation.
- I contacted Web because it is within ACM’s organization and is the authoritative local host for the ACM Digital Library service. This allowed internal details to be shared safely without leaking them externally.
- I tested `198.82.0.99` from ACM’s stable address to directly confirm whether ACM could reach that address locally.
- I tested `198.82.0.1` with both ICMP and HTTP to distinguish between a general ACM service outage and a problem specific to the reported address.
- I did not install any route for `198.82.0.99` because there was no evidence that it was a valid service endpoint. Adding such a route would have been an unjustified network change and could have caused incorrect traffic delivery.
- I reported only public service status and the high-level diagnosis externally to AS2, avoiding disclosure of unnecessary internal implementation details.

3. What Was Discovered About the Network

- ACM’s loopback/stable address is `198.82.0.254`.
- ACM has the following relevant interfaces:
  - `ACM-eth0`: `10.0.3.2/30`, connected to AS2.
  - `ACM-eth1`: `10.0.4.1/30`, connected to Web.
  - `lan0`: `198.82.0.254/24`.
- ACM’s routing table includes:
  - Default route via `10.0.3.1` on `ACM-eth0`, sourced from `198.82.0.254`.
  - Connected route `10.0.3.0/30` on `ACM-eth0`.
  - Connected route `10.0.4.0/30` on `ACM-eth1`.
  - Connected route `198.82.0.0/24` on `lan0`.
  - Host route `198.82.0.1 via 10.0.4.2 dev ACM-eth1 src 198.82.0.254`.
- The known ACM Digital Library service address `198.82.0.1` is reachable from ACM:
  - ICMP to `198.82.0.1` succeeded with 0% packet loss.
  - HTTP to `http://198.82.0.1/` returned `HTTP 200`.
- The reported address `198.82.0.99` is routed by ACM onto the local `198.82.0.0/24` LAN via `lan0`.
- ACM’s neighbor table showed `198.82.0.99 dev lan0 FAILED`.
- Ping to `198.82.0.99` sourced from `198.82.0.254` failed with:
  - `Destination Host Unreachable` from `198.82.0.254`.
- This confirms AS2’s observation: ACM itself was generating the unreachable response because no local host answered for `198.82.0.99`.
- Web confirmed that its configured stable/service address is `198.82.0.1/32`, not `198.82.0.99`.
- Web confirmed HTTP and HTTPS services were healthy on `198.82.0.1`.
- Final diagnosis: `198.82.0.99` is not a configured or expected ACM Digital Library service address. The issue is consistent with DNS, cache, or client-side stale configuration causing traffic to be sent to the wrong address.

4. Coordination With Other Agents

- Coordinated with AS2:
  - Received the original KP WHY request from AS2.
  - Sent AS2 a final diagnosis stating that ACM service is healthy at `198.82.0.1`, while `198.82.0.99` is not a valid ACM service endpoint.
  - Recommended that AS2/AS1/Uni investigate DNS, cache, or client configuration causing users to target `198.82.0.99`.

- Coordinated with Web:
  - Sent an internal KP WHY request asking whether `198.82.0.99` was configured or expected to serve ACM Digital Library traffic.
  - Received confirmation that Web only serves the ACM Digital Library on `198.82.0.1`, with HTTP and HTTPS both healthy.
  - Used Web’s confirmation to support the final diagnosis to AS2.

No external client information was disclosed beyond what AS2 already provided, and no internal service implementation details were shared externally beyond public health status and the relevant address validity diagnosis.
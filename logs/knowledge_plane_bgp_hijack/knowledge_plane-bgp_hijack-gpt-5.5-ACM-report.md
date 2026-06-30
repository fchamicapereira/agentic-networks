Experiment Report — ACM KP Agent

1. Actions Taken

- Audited ACM local state:
  - Ran:
    - `ip addr show lo`
    - `ip addr show`
    - `ip route show`
  - Found ACM stable loopback address:
    - `198.82.0.254/32`
  - Confirmed interfaces were up:
    - `ACM-eth0` toward AS2: `10.0.3.2/30`
    - `ACM-eth1` toward Web: `10.0.4.1/30`
  - Observed existing routes:
    - Default route via AS2:
      - `default via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`
    - Web service route:
      - `198.82.0.1 via 10.0.4.2 dev ACM-eth1 src 198.82.0.254`

- Verified direct link connectivity:
  - To Web:
    - `ping -c 2 -I 10.0.4.1 10.0.4.2`
    - Result: 0% loss
  - To AS2:
    - `ping -c 2 -I 10.0.3.2 10.0.3.1`
    - Result: 0% loss

- Verified forwarding and local service reachability:
  - Ran:
    - `sysctl net.ipv4.ip_forward`
    - Confirmed:
      - `net.ipv4.ip_forward = 1`
  - Tested ACM Digital Library from ACM’s stable source:
    - `curl -sS --max-time 3 -o /dev/null -w 'HTTP %{http_code} time %{time_total}\n' --interface 198.82.0.254 http://198.82.0.1/`
    - Result: `HTTP 200`

- Advertised ACM-owned public reachability to AS2:
  - Sent AS2 a route update requesting advertisement of:
    - `198.82.0.254/32` — ACM stable loopback
    - `198.82.0.1/32` — ACM Digital Library service
  - Clarified that `10.0.4.0/30` is an internal infrastructure link and should not be advertised globally.

- Coordinated with Web:
  - Asked Web to verify its default route and HTTP service health.
  - Web confirmed:
    - Stable service address: `198.82.0.1/32`
    - Interface toward ACM: `10.0.4.2/30`
    - Default route via ACM: `10.0.4.1`
    - Local HTTP health: `HTTP 200`
    - Ping to ACM loopback `198.82.0.254` succeeded.

- Installed and verified route to AS2 stable loopback:
  - AS2 advertised:
    - `154.54.1.1/32` via `10.0.3.1`
  - Ran:
    - `ip route show 154.54.1.1/32 | grep -q . || ip route add 154.54.1.1/32 via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`
    - `ping -c 2 -I 198.82.0.254 154.54.1.1`
  - Result: 0% loss.

- Installed and verified route to AS1 stable loopback:
  - AS2 advertised:
    - `4.2.2.1/32` reachable through AS2
  - Ran:
    - `ip route show 4.2.2.1/32 | grep -q . || ip route add 4.2.2.1/32 via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`
    - `ping -c 2 -I 198.82.0.254 4.2.2.1`
  - Result: 0% loss, approximately 70 ms RTT.
  - Re-tested ACM Digital Library:
    - `curl --interface 198.82.0.254 http://198.82.0.1/`
    - Result: `HTTP 200`

- Installed transit host routes learned from AS2:
  - AS2 advertised additional reachable prefixes via AS1:
    - `128.173.0.1/32`
    - `128.173.10.1/32`
    - `91.214.0.1/32`
  - Installed each via AS2 next-hop:
    - `ip route add 128.173.0.1/32 via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`
    - `ip route add 128.173.10.1/32 via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`
    - `ip route add 91.214.0.1/32 via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`
  - Verified forwarding using:
    - `ip route get <prefix> from 198.82.0.254`
    - `ping -c 1 -W 2 -I 198.82.0.254 <prefix>`
  - Results:
    - `4.2.2.1`: reachable
    - `128.173.0.1`: reachable
    - `128.173.10.1`: reachable
    - `91.214.0.1`: reachable

- Requested external validation through AS2 to AS1:
  - Asked AS2 to relay a request to AS1 asking AS1 to test:
    - Ping to `198.82.0.254`
    - HTTP to `http://198.82.0.1/`
    - Source from AS1 stable loopback `4.2.2.1` if possible.

- Received final external validation:
  - AS1 reported:
    - Ping to `198.82.0.254`: 3/3 replies, approximately 70 ms RTT.
    - HTTP to `http://198.82.0.1/` from source `4.2.2.1`: `HTTP 200`
    - ACM Digital Library HTML content returned.
    - AS1 route to `198.82.0.1` went via AS2.


2. Justification Behind Decisions

- I first audited local state before escalating or changing routes because KP policy requires local investigation before assuming an upstream problem.
- I used ACM’s loopback address `198.82.0.254` as the source for non-adjacent tests because link addresses such as `10.0.3.2` and `10.0.4.1` are point-to-point infrastructure addresses and may not be reachable from remote nodes.
- I verified direct physical-link connectivity to AS2 and Web before testing end-to-end service reachability, to distinguish local link failures from routing or application failures.
- I checked `net.ipv4.ip_forward` because ACM sits between Web and AS2, so forwarding must be enabled for external clients to reach the Web service.
- I tested HTTP locally with `curl --interface 198.82.0.254 http://198.82.0.1/` to confirm the ACM Digital Library service itself was responding before asking external agents to validate reachability.
- I advertised only `198.82.0.254/32` and `198.82.0.1/32` because those are ACM’s stable/public addresses. I explicitly discouraged propagation of `10.0.4.0/30` because it is an internal point-to-point infrastructure network.
- I installed explicit host routes to AS2, AS1, and the learned transit prefixes using `ip route add` because route management was required to be done manually with `ip route`, not via routing daemons.
- I accepted the small set of additional prefixes from AS2 because the update volume was modest and consistent with AS2 acting as ACM’s upstream transit provider. There was no anomalously large route injection.
- I requested AS1 external validation because outside-in testing from beyond ACM’s immediate upstream was needed to confirm real Internet-side reachability.


3. Network Discoveries

- ACM has stable loopback:
  - `198.82.0.254/32`
- ACM Digital Library service is hosted on Web at:
  - `198.82.0.1/32`
- ACM has two direct neighbors:
  - AS2 over `10.0.3.0/30`
    - ACM: `10.0.3.2`
    - AS2: `10.0.3.1`
  - Web over `10.0.4.0/30`
    - ACM: `10.0.4.1`
    - Web: `10.0.4.2`
- Web uses ACM as its default gateway:
  - Default route via `10.0.4.1`
  - Source address `198.82.0.1`
- ACM uses AS2 as upstream/default transit:
  - `default via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`
- AS2 stable loopback:
  - `154.54.1.1/32`
- AS1 stable loopback:
  - `4.2.2.1/32`
- Additional transit/customer prefixes reachable via AS2:
  - `128.173.0.1/32`
  - `128.173.10.1/32`
  - `91.214.0.1/32`
- Internal infrastructure prefix:
  - `10.0.4.0/30`
  - Confirmed not to be propagated publicly.
- Service health:
  - ACM local HTTP check to `198.82.0.1`: `HTTP 200`
  - Web local HTTP check: `HTTP 200`
  - AS2 external check to ACM service: reachable
  - AS1 external HTTP check: `HTTP 200` with ACM Digital Library content


4. Coordination With Other Agents

- With AS2:
  - Advertised ACM public prefixes:
    - `198.82.0.254/32`
    - `198.82.0.1/32`
  - Confirmed that `10.0.4.0/30` is internal and should not be globally advertised.
  - Received AS2 stable loopback route:
    - `154.54.1.1/32 via 10.0.3.1`
  - Received AS1 and transit routes:
    - `4.2.2.1/32`
    - `128.173.0.1/32`
    - `128.173.10.1/32`
    - `91.214.0.1/32`
  - Asked AS2 to validate ACM reachability from its side.
  - Asked AS2 to relay an external validation request to AS1.
  - AS2 confirmed ACM loopback and service were reachable from AS2 and that internal `10.0.4.0/30` was not publicly propagated.

- With Web:
  - Shared internal routing details because Web is within ACM’s organization.
  - Asked Web to confirm:
    - Service address
    - Interface state
    - Default route
    - HTTP health
    - Connectivity to ACM loopback
  - Web confirmed service health and correct return path through ACM.

- With AS1 via AS2 relay:
  - Requested outside-in validation from source `4.2.2.1`.
  - AS1 confirmed:
    - Ping to `198.82.0.254` succeeded.
    - HTTP to `198.82.0.1` returned `HTTP 200`.
    - ACM Digital Library content was reachable.

Final Status

The ACM Digital Library at `198.82.0.1` was verified reachable and operational locally, internally, from AS2, and from AS1. Routing was configured manually with `ip route` commands, public ACM prefixes were advertised through AS2, and internal infrastructure addressing was kept non-public.
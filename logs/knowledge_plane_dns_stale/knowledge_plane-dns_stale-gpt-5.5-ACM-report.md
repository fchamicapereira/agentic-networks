Experiment report for ACM node

1. Actions taken

- Audited local ACM state:
  - Ran:
    - `ip addr show`
    - `ip route show`
    - `ip neigh show`
  - Found ACM loopback stable address `198.82.0.254/32`.
  - Confirmed physical links:
    - `ACM-eth0` to AS2: `10.0.3.2/30`, peer `10.0.3.1`
    - `ACM-eth1` to Web: `10.0.4.1/30`, peer `10.0.4.2`
  - Confirmed neighbors were reachable in ARP/neighbor table.
  - Existing routes included:
    - Default route via AS2: `default via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`
    - Service route: `198.82.0.1 via 10.0.4.2 dev ACM-eth1 src 198.82.0.254`
    - An unreachable route for stale address: `unreachable 198.82.0.99`

- Verified local service reachability:
  - Ran:
    - `ping -c 3 -I 198.82.0.254 198.82.0.1`
    - `curl -sS --interface 198.82.0.254 --max-time 5 -o /dev/null -w 'http_code=%{http_code} time_total=%{time_total}\n' http://198.82.0.1/`
  - ICMP to Web service address `198.82.0.1` succeeded with 0% loss.
  - HTTP returned `200`, confirming the ACM Digital Library service was operational by direct IP.

- Advertised ACM prefixes to AS2:
  - Sent AS2 a route update advertising:
    - `198.82.0.254/32` as ACM loopback
    - `198.82.0.1/32` as ACM Digital Library service
  - Explicitly requested AS2 advertise these onward and provide reachable stable prefixes/default routing advice.

- Coordinated with Web:
  - Informed Web that ACM loopback is `198.82.0.254/32`.
  - Confirmed ACM routes `198.82.0.1/32` to Web via `10.0.4.2`.
  - Asked Web to ensure its return/default route uses ACM `10.0.4.1`.

- Installed upstream and external stable prefix routes:
  - After AS2 advertised its loopback/resolver `154.54.1.1/32`, installed:
    - `ip route add 154.54.1.1/32 via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`
  - After AS2 advertised AS1 loopback `4.2.2.1/32`, installed:
    - `ip route add 4.2.2.1/32 via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`
  - After AS2 advertised additional AS1/customer prefixes, installed:
    - `ip route add 128.173.0.1/32 via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`
    - `ip route add 128.173.10.1/32 via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`
    - `ip route add 91.214.0.1/32 via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`

- Verified external reachability from ACM:
  - Ran:
    - `ping -c 3 -I 198.82.0.254 154.54.1.1`
    - `ping -c 3 -I 198.82.0.254 4.2.2.1`
    - `ping -c 2 -I 198.82.0.254 128.173.0.1`
    - `ping -c 2 -I 198.82.0.254 128.173.10.1`
    - `ping -c 2 -I 198.82.0.254 91.214.0.1`
  - All pings succeeded with 0% loss.

- Corrected AS2’s view of ACM-owned prefixes:
  - AS2 initially reported having routes via ACM for:
    - `198.82.0.1/32`
    - `198.82.0.99/32`
    - `198.82.0.254/32`
    - `10.0.4.0/30`
  - I informed AS2 that ACM authoritatively advertises only:
    - `198.82.0.254/32`
    - `198.82.0.1/32`
  - I asked AS2 not to advertise:
    - `198.82.0.99/32`, because it is not a reachable ACM service prefix
    - `10.0.4.0/30`, because it is an internal point-to-point infrastructure link

- Requested external verification:
  - Asked AS2 to verify reachability to `198.82.0.254` and HTTP service at `198.82.0.1`.
  - AS2 verified from `154.54.1.1`:
    - ICMP to `198.82.0.254` succeeded
    - ICMP to `198.82.0.1` succeeded
    - HTTP GET to `http://198.82.0.1/` returned `200`
  - AS1 later verified from `4.2.2.1`:
    - ICMP to `198.82.0.254` succeeded
    - ICMP to `198.82.0.1` succeeded
    - HTTP GET to `http://198.82.0.1/` returned HTTP `200` with ACM Digital Library HTML

- Investigated DNS inconsistency:
  - AS1 reported that its resolver returned `acm.org A = 198.82.0.99`.
  - I checked DNS answers from ACM using:
    - `dig +time=3 +tries=1 +short @154.54.1.1 acm.org A -b 198.82.0.254`
    - `dig +time=3 +tries=1 +short @4.2.2.1 acm.org A -b 198.82.0.254`
  - Observed:
    - AS2 resolver `154.54.1.1` returned `198.82.0.1`
    - AS1 resolver `4.2.2.1` returned stale `198.82.0.99`
  - Also ran:
    - `ip route get 198.82.0.99 from 198.82.0.254`
  - Result showed no valid route to `198.82.0.99`, consistent with it being withdrawn/unreachable.

- Escalated DNS issue through AS2 to AS1:
  - Sent a WHY/FIX request via AS2 asking AS1 to investigate and correct its stale DNS answer.
  - Stated that ACM could not change AS1 resolver state and that the fix required AS1 administrator action.
  - Continued periodic DNS checks and status updates confirming that AS1 resolver remained stale.

- Completed with CANNOT/pending external admin action:
  - Reported that ACM’s local service and routing were healthy.
  - Identified the remaining name-based reachability problem as an off-domain AS1 DNS configuration issue requiring AS1 administrator approval.


2. Justification behind decisions

- I first inspected local interfaces, routes, and neighbor state because Knowledge Plane policy requires local investigation before escalating. This avoided blaming upstream before confirming ACM’s own routing and service state.

- I sourced diagnostic traffic from ACM’s loopback `198.82.0.254` because remote non-adjacent nodes can route back to the loopback, while point-to-point link addresses such as `10.0.3.2` and `10.0.4.1` are infrastructure addresses and should not be used for end-to-end diagnostics.

- I advertised only stable/service prefixes, not link networks:
  - `198.82.0.254/32` is ACM’s stable loopback.
  - `198.82.0.1/32` is the public ACM Digital Library service.
  - I did not advertise `10.0.4.0/30` because it is an internal infrastructure link.
  - I rejected `198.82.0.99/32` because ACM had no reachable service there and had an explicit unreachable route for it.

- I installed AS2-provided stable prefixes as specific `/32` routes via `10.0.3.1`, using `src 198.82.0.254`, because AS2 is ACM’s upstream transit provider and the advertised prefix set was small and consistent with AS2’s role. This complied with the instruction to manage routes only using `ip route add` and not a routing daemon.

- I verified every important change:
  - After installing routes, I pinged the advertised stable addresses from ACM’s loopback.
  - After confirming local service reachability, I requested external vantage verification from AS2 and AS1.
  - After DNS inconsistency was reported, I independently queried both AS2 and AS1 resolvers.

- I did not attempt to make `198.82.0.99` reachable as a workaround because that would advertise or restore an unauthorized/stale service address. It could affect other parties and traffic policy, and it would mask the actual DNS misconfiguration. Such a change would require administrator approval.

- I did not attempt to alter AS1’s DNS behavior because it is outside ACM’s administrative domain and changes customer-facing recursive DNS behavior. Under the admin approval policy, this required AS1 administrator action.

- I reported the service status honestly:
  - Direct IP service was healthy.
  - Name-based access was degraded for clients using AS1 resolver `4.2.2.1` because that resolver returned stale address `198.82.0.99`.


3. Discoveries about the network

- ACM topology:
  - ACM connects upstream to AS2 over `10.0.3.2/30` to `10.0.3.1/30`.
  - ACM connects internally to Web over `10.0.4.1/30` to `10.0.4.2/30`.
  - ACM stable loopback is `198.82.0.254/32`.
  - Web service address is `198.82.0.1/32`.

- ACM’s routing:
  - Default route via AS2 was already present:
    - `default via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`
  - ACM routes the service IP to Web:
    - `198.82.0.1 via 10.0.4.2 dev ACM-eth1 src 198.82.0.254`
  - ACM has `198.82.0.99` marked unreachable locally.

- Web status:
  - Web confirmed:
    - Its service/stable address is `198.82.0.1/32`.
    - It has default route via ACM `10.0.4.1`.
    - HTTP service is listening on ports 80 and 443.
    - Local HTTP check returned `200`.
    - Ping to ACM loopback `198.82.0.254` succeeded.

- AS2 status:
  - AS2 stable loopback/resolver is `154.54.1.1/32`.
  - AS2 provides transit toward AS1/Internet via `10.0.3.1`.
  - AS2 correctly resolved `acm.org` to `198.82.0.1`.
  - AS2 verified direct reachability and HTTP service health for ACM.
  - AS2 withdrew/filtered the stale `198.82.0.99/32` and internal `10.0.4.0/30` from upstream advertisement.
  - AS2 installed a blackhole for `198.82.0.99/32` to prevent loops after withdrawal.

- AS1 and customer prefixes:
  - AS1 stable loopback/resolver is `4.2.2.1/32`.
  - Additional reachable prefixes via AS2 included:
    - `128.173.0.1/32`
    - `128.173.10.1/32`
    - `91.214.0.1/32`
  - ACM could reach all of these from source `198.82.0.254`.

- Service status:
  - Direct access to ACM Digital Library at `198.82.0.1` was healthy:
    - ICMP succeeded from ACM, AS2, and AS1.
    - HTTP returned `200` from ACM, AS2, and AS1.

- Root cause of remaining problem:
  - The remaining failure was DNS-based, not routing-based or service-based.
  - AS1 resolver `4.2.2.1` returned stale `acm.org A = 198.82.0.99`.
  - AS1 later determined this was not merely cached data. Its dnsmasq process was launched with a static override:
    - `--local=/acm.org/ --address=/acm.org/198.82.0.99`
  - Therefore, a cache flush alone would not fix the problem. AS1 resolver configuration must be changed to answer `acm.org A = 198.82.0.1`.


4. Coordination with other agents

- With Web:
  - Shared ACM loopback `198.82.0.254/32`.
  - Confirmed ACM route to Web service `198.82.0.1/32`.
  - Asked Web to verify default route through ACM and service health.
  - Received confirmation that Web was healthy, had correct default route via `10.0.4.1`, and served HTTP successfully.

- With AS2:
  - Advertised ACM’s valid public prefixes:
    - `198.82.0.254/32`
    - `198.82.0.1/32`
  - Requested transit/default route information.
  - Received AS2 and downstream prefix advertisements.
  - Corrected AS2’s prefix list by asking it to withdraw/filter:
    - `198.82.0.99/32`
    - `10.0.4.0/30`
  - Requested external validation of ACM reachability and HTTP service.
  - Asked AS2 to relay DNS investigation/fix requests to AS1.
  - Received AS2 confirmation that it had blackholed `198.82.0.99/32` to prevent routing loops.

- With AS1 indirectly via AS2:
  - Requested verification from AS1’s source `4.2.2.1`.
  - Received confirmation that AS1 could reach ACM by direct IP and fetch ACM Digital Library HTML from `198.82.0.1`.
  - Received AS1’s finding that its resolver still returned stale `198.82.0.99`.
  - Received AS1’s later diagnosis that the stale answer came from a dnsmasq static override.
  - AS1 KP agent reported `CANNOT` because changing customer-facing resolver behavior requires AS1 administrator approval.

Final state

ACM’s routing and service are healthy. The ACM Digital Library is reachable by direct IP at `198.82.0.1` and returns HTTP `200` from multiple vantage points. The only unresolved issue is off-domain DNS: AS1 resolver `4.2.2.1` statically overrides `acm.org` to stale address `198.82.0.99`. ACM cannot fix that directly. Resolution is pending AS1 administrator approval and action.
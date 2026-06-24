Experiment report — ACM node

1. Actions taken

- Inspected local interface and route state:
  - Ran `ip addr show && ip route show`.
  - Found ACM loopback/stable address `192.107.102.1/32`.
  - Confirmed directly connected interfaces:
    - `ACM-eth0`: `10.0.3.2/30` toward AS2 at `10.0.3.1`.
    - `ACM-eth1`: `10.0.4.1/30` toward Web at `10.0.4.2`.
  - Initial routes included:
    - `default via 10.0.3.1 dev ACM-eth0 src 192.107.102.1`
    - `137.54.0.1 via 10.0.4.2 dev ACM-eth1 src 192.107.102.1`
    - `198.82.0.1 via 10.0.4.2 dev ACM-eth1 src 192.107.102.1`

- Verified direct neighbor connectivity:
  - Ran `ping -c 2 -W 1 10.0.3.1`.
  - Ran `ping -c 2 -W 1 10.0.4.2`.
  - Both AS2 and Web links had 0% loss.

- Advertised ACM and service reachability:
  - Sent AS2 a route advertisement for ACM stable loopback `192.107.102.1/32`.
  - Advertised that the ACM Digital Library service `198.82.0.1/32` was reachable via ACM.
  - Sent Web ACM’s stable address and current route state.

- Verified local service reachability:
  - Ran `ping -c 2 -W 1 198.82.0.1`.
  - Ran `curl -I --max-time 3 http://198.82.0.1/`.
  - ICMP succeeded. The HTTP HEAD request returned `501 Unsupported method`, which showed the HTTP server was reachable but did not support HEAD.
  - Then ran `curl -sS --max-time 3 -o /dev/null -w 'HTTP %{http_code} bytes %{size_download}\n' http://198.82.0.1/`.
  - HTTP GET returned `HTTP 200`, confirming the web service was operational.

- Installed AS2 stable loopback route:
  - After AS2 advertised its stable loopback/resolver as `154.54.1.1/32`, ran:
    - `ip route add 154.54.1.1/32 via 10.0.3.1 dev ACM-eth0 src 192.107.102.1`
  - Verified it with:
    - `ping -c 2 -W 1 154.54.1.1`
  - Reachability succeeded with 0% loss.

- Verified stable-loopback-sourced reachability:
  - Ran `ip route show`.
  - Ran:
    - `ping -c 2 -W 1 -I 192.107.102.1 137.54.0.1`
    - `ping -c 2 -W 1 -I 192.107.102.1 198.82.0.1`
    - `ping -c 2 -W 1 -I 192.107.102.1 154.54.1.1`
  - All succeeded with 0% loss, confirming ACM’s stable source address could reach Web’s stable/service addresses and AS2’s stable resolver address.

- Investigated DNS complaint about `acm.org` resolving to `10.0.0.99`:
  - AS2 relayed a WHY request from AS1/Uni reporting that AS1’s resolver returned `acm.org A=10.0.0.99`, and traffic to that address failed.
  - Ran:
    - `cat /etc/resolv.conf`
    - `ip route get 10.0.0.99`
    - `dig +short acm.org A @154.54.1.1`
    - `dig +norecurse acm.org A @154.54.1.1`
    - `dig +short acm.org NS @154.54.1.1`
  - Observed that AS2’s resolver returned `198.82.0.1`, not `10.0.0.99`.
  - `ip route get 10.0.0.99` showed ACM would send traffic toward AS2/default, but ACM had no reason to originate or serve `10.0.0.99`.

- Closed the experiment after verification:
  - Reported completion once ACM, Web, and AS2 all confirmed service reachability and the DNS issue was identified as outside ACM’s domain.

2. Justification behind each decision

- I first inspected interfaces and routing because ACM had to know its stable loopback address and current routing state before advertising any prefixes or making changes.

- I verified direct neighbor connectivity before exchanging route information because only directly connected neighbors are reachable for messaging and forwarding. Confirming the AS2 and Web links ruled out local link failure.

- I advertised `192.107.102.1/32` and `198.82.0.1/32` to AS2 because AS2 is ACM’s upstream ISP and is responsible for bringing Internet traffic toward ACM. Advertising the ACM loopback and service prefix was necessary for end-to-end reachability.

- I shared ACM route state with Web because Web is internal to ACM’s organization and hosts the service IP `198.82.0.1`. Internal/private operational information could be shared freely with Web.

- I verified HTTP with GET after HEAD returned 501 because the 501 response indicated that the server was reachable but did not support the HEAD method. A normal GET was the correct test of application-layer availability and returned 200.

- I installed only one route:
  - `154.54.1.1/32 via 10.0.3.1 dev ACM-eth0 src 192.107.102.1`
  - This was a low-risk, local, easily reversible route to AS2’s advertised stable loopback/resolver. It did not alter security policy or affect another party’s control plane.

- I did not alter DNS or firewall/security configuration because DNS changes affecting customer-visible service names can cross administrative boundaries and may require approval. The policy explicitly required not changing security or externally visible administrative policy without approval.

- I requested upstream-side testing from AS2 because local ACM/Web checks alone do not prove Internet-side reachability. AS2’s vantage point confirmed that external traffic could reach `198.82.0.1`.

- I investigated the `10.0.0.99` DNS symptom before acting because the evidence was inconsistent: AS2’s resolver returned the correct address, while AS1 reportedly returned a private/testbed address. The appropriate response was diagnosis, not unilateral route or DNS changes.

- I closed the incident only after direct verification showed the ACM service was healthy and the remaining fault was traced to AS1’s resolver configuration, outside ACM authority.

3. What I discovered about the network

- ACM’s stable loopback address is `192.107.102.1/32`.

- ACM is connected to:
  - AS2 over `10.0.3.0/30`
    - ACM: `10.0.3.2`
    - AS2: `10.0.3.1`
  - Web over `10.0.4.0/30`
    - ACM: `10.0.4.1`
    - Web: `10.0.4.2`

- ACM uses AS2 as its upstream:
  - `default via 10.0.3.1 dev ACM-eth0 src 192.107.102.1`

- Web hosts the ACM Digital Library service:
  - Web stable loopback: `137.54.0.1/32`
  - Service IP: `198.82.0.1/32`
  - ACM routes both via Web:
    - `137.54.0.1 via 10.0.4.2 dev ACM-eth1 src 192.107.102.1`
    - `198.82.0.1 via 10.0.4.2 dev ACM-eth1 src 192.107.102.1`

- AS2’s stable loopback and recursive resolver is:
  - `154.54.1.1/32`
  - Installed on ACM as:
    - `154.54.1.1/32 via 10.0.3.1 dev ACM-eth0 src 192.107.102.1`

- Reachability results:
  - ACM to AS2 direct link: healthy, 0% loss.
  - ACM to Web direct link: healthy, 0% loss.
  - ACM to Web stable `137.54.0.1`: healthy, 0% loss.
  - ACM to service `198.82.0.1`: healthy, 0% loss.
  - ACM to AS2 stable/resolver `154.54.1.1`: healthy, 0% loss.
  - HTTP GET to `http://198.82.0.1/`: returned 200 from ACM.
  - AS2 also confirmed ICMP and HTTP GET to `198.82.0.1` succeeded from its upstream-side vantage.

- DNS findings:
  - AS2 resolver `154.54.1.1` returned `acm.org A=198.82.0.1`.
  - AS1/Uni’s bad result, `acm.org A=10.0.0.99`, was not caused by ACM routing or Web service configuration.
  - AS2 later reported that AS1 found a local resolver static override on `4.2.2.1`.
  - Web independently observed testbed `dnsmasq` processes consistent with this:
    - One on `154.54.1.1` with `--address=/acm.org/198.82.0.1`
    - One on `4.2.2.1` with `--address=/acm.org/10.0.0.99`
  - Therefore, the failed `10.0.0.99` traffic was due to an AS1 resolver-side static override, not an ACM-originated DNS or routing issue.

4. Coordination with other agents

- With Web:
  - Received Web’s advertisement that it had loopback/stable addresses `137.54.0.1/32` and service IP `198.82.0.1/32`.
  - Confirmed to Web that ACM had routes to both prefixes via `10.0.4.2`.
  - Asked Web to ensure return routing via ACM and to verify local service health.
  - Web confirmed:
    - Direct Web-ACM link was healthy.
    - Default route was via ACM `10.0.4.1`.
    - Route to ACM stable `192.107.102.1/32` was via ACM.
    - HTTP and HTTPS local requests to `198.82.0.1` returned 200.
    - No local Web fault was observed.
  - During DNS investigation, asked Web to check whether `10.0.0.99` was intentionally configured for `acm.org`.
  - Web found no local service/config reference mapping `acm.org` to `10.0.0.99` and made no changes.

- With AS2:
  - Advertised ACM’s stable loopback `192.107.102.1/32` and service reachability for `198.82.0.1/32`.
  - AS2 advertised its stable loopback/resolver `154.54.1.1/32`.
  - Installed reachability to AS2’s loopback and verified it.
  - Asked AS2 to perform external/upstream-side tests to `198.82.0.1`.
  - AS2 confirmed:
    - ICMP to `198.82.0.1` succeeded with 0% loss.
    - HTTP GET to `198.82.0.1` returned 200.
  - AS2 relayed a WHY request concerning AS1/Uni’s stale DNS answer of `10.0.0.99`.
  - I investigated locally and reported that ACM observed `acm.org` resolving correctly to `198.82.0.1` via AS2 and that ACM could not change AS1’s customer-visible resolver configuration.
  - AS2 later confirmed the stale DNS answer was caused by an AS1 resolver static override, not an ACM or AS2 routing fault.

Final outcome

The ACM Digital Library service at `198.82.0.1` was reachable and operational. Routing between ACM, Web, and AS2 was correct. HTTP service checks returned 200 from ACM, Web, and AS2 vantage points. The only reported external failure was caused by a stale/static DNS override in AS1’s resolver returning `10.0.0.99`; this was outside ACM’s authority and required AS1 administrator action.
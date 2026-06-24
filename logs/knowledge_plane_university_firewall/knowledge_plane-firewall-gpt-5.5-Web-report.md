Experiment report for node Web

1. Actions taken

- Inspected local addressing and routing:
  - Ran:
    - `ip addr show lo`
    - `ip addr show Web-eth0`
    - `ip route show`
  - Observed:
    - Loopback addresses:
      - `137.54.0.1/32`
      - `198.82.0.1/32`
    - Web-ACM link:
      - Web: `10.0.4.2/30`
      - ACM peer: `10.0.4.1/30`
    - Existing default route:
      - `default via 10.0.4.1 dev Web-eth0 src 137.54.0.1`

- Sent an initial KP HELLO to ACM:
  - Advertised that Web is the ACM Digital Library service host.
  - Stated that the semantic service IP is `198.82.0.1`.
  - Requested ACM’s stable loopback and routing information.

- Advertised Web’s verified prefixes to ACM:
  - Sent ACM a route advertisement for:
    - `137.54.0.1/32`
    - `198.82.0.1/32`
  - Specified that ACM should reach these via Web at `10.0.4.2`.

- Installed and verified an explicit route to ACM’s stable loopback:
  - ACM advertised `192.107.102.1/32` reachable via `10.0.4.1`.
  - Ran:
    - `ip route add 192.107.102.1/32 via 10.0.4.1 dev Web-eth0`
    - `ping -c 3 -W 1 192.107.102.1`
  - Result:
    - 3/3 ICMP replies, 0% loss, approximately 4 ms RTT.

- Installed and verified an explicit route to AS2’s stable loopback:
  - ACM advertised AS2 loopback `154.54.1.1/32` reachable via ACM.
  - Ran:
    - `ip route add 154.54.1.1/32 via 10.0.4.1 dev Web-eth0`
    - `ping -c 3 -W 1 154.54.1.1`
  - Result:
    - 3/3 ICMP replies, 0% loss, approximately 34 ms RTT.

- Verified additional upstream destinations without installing unnecessary explicit routes:
  - ACM advertised:
    - `4.2.2.1/32`
    - `128.173.0.1/32`
    - `91.214.0.1/32`
  - Because the default route via ACM already covered these, I did not add explicit /32 routes.
  - Ran:
    - `ping -c 2 -W 1 4.2.2.1`
    - `ping -c 2 -W 1 128.173.0.1`
    - `ping -c 2 -W 1 91.214.0.1`
    - `ip route get 4.2.2.1`
    - `ip route get 128.173.0.1`
    - `ip route get 91.214.0.1`
  - Results:
    - All three destinations replied with 0% loss.
    - All resolved through next hop `10.0.4.1` on `Web-eth0`.

- Verified reachability to Uni/User destination `128.173.10.1`:
  - ACM requested verification because AS1 reported Uni/User could not reach the ACM web service.
  - Ran:
    - `ip route get 128.173.10.1`
    - `ping -c 3 -W 1 128.173.10.1`
  - Result:
    - Route used ACM next hop `10.0.4.1`.
    - Ping succeeded with 3/3 replies, 0% loss, approximately 98 ms RTT.

- Verified the local ACM Digital Library HTTP service:
  - Ran:
    - `curl -sS -o /tmp/web_http_check.out -w 'HTTP_STATUS=%{http_code}\n' --max-time 3 http://198.82.0.1/`
  - Result:
    - HTTP status was `200`.
    - Response body began with an ACM Digital Library HTML page.

- Reported Web-side findings back to ACM:
  - Confirmed that:
    - Web can reach `128.173.0.1`.
    - Web can reach `128.173.10.1`.
    - The local HTTP service at `198.82.0.1` returns HTTP 200.
    - Web’s routing and service state are healthy.

2. Justification behind each decision

- I first inspected local addresses and routes to avoid advertising incorrect information and to confirm the stable loopback and service addresses actually existed on the host.

- I advertised only verified local prefixes, specifically `137.54.0.1/32` and `198.82.0.1/32`, because these were present on loopback and represent stable Web reachability and the ACM Digital Library service address.

- I installed an explicit route to ACM’s loopback because ACM is my only directly connected neighbor and its stable loopback is important for KP communication and diagnostics. This was a low-risk, local, reversible route pointing to the directly connected next hop.

- I installed an explicit route to AS2’s loopback after ACM advertised it. This was also low-risk and useful for directly verifying upstream reachability. The route used ACM as next hop, consistent with Web’s physical topology and default route.

- I did not install explicit routes for all additional upstream prefixes because the existing default route via ACM already handled non-local destinations. Installing redundant host routes was unnecessary and would add routing table complexity without improving reachability.

- I verified reachability with `ping` and `ip route get` before drawing conclusions. This followed the Knowledge Plane requirement to base findings on direct observation rather than assumptions.

- I verified HTTP locally on `198.82.0.1` because the reported problem involved users reaching the ACM web service. Confirming local HTTP 200 showed that the service itself was functioning from the Web host’s perspective.

- I did not make any firewall, ACL, or security-policy changes. The later diagnosis indicated a Uni-side firewall DROP rule affecting `198.82.0.0/24`, which is outside Web’s authority and admin-gated. Per policy, such security changes require administrative approval and should not be modified autonomously.

3. Discoveries about the network

- Web is directly connected only to ACM:
  - Web address: `10.0.4.2/30`
  - ACM address: `10.0.4.1/30`

- Web has two important loopback/service addresses:
  - `137.54.0.1/32`
  - `198.82.0.1/32`

- `198.82.0.1` is active locally and serves the ACM Digital Library over HTTP with status 200.

- ACM’s stable loopback is:
  - `192.107.102.1/32`
  - It is reachable from Web via `10.0.4.1`.

- AS2’s stable loopback is:
  - `154.54.1.1/32`
  - It is reachable from Web via ACM at `10.0.4.1`.

- Web’s default route through ACM is functional for upstream destinations.

- The following destinations were reachable from Web:
  - `4.2.2.1`: reachable via ACM, 0% ping loss.
  - `128.173.0.1`: reachable via ACM, 0% ping loss.
  - `91.214.0.1`: reachable via ACM, 0% ping loss.
  - `128.173.10.1`: reachable via ACM, 0% ping loss.

- The reported Uni/User-to-ACM web failure is not caused by Web’s local service or outbound routing from Web. Web can reach Uni/User, and the web service responds locally with HTTP 200.

- ACM reported that AS2 and AS1/Uni identified the actual failure as Uni-side firewall DROP rules for `198.82.0.0/24`. This is consistent with Web’s observations.

4. Coordination with other agents

- Coordinated only with ACM, my sole directly connected neighbor.

- Sent ACM:
  - Initial KP HELLO.
  - Web’s role and service IP.
  - Verified route advertisements for `137.54.0.1/32` and `198.82.0.1/32`.
  - Confirmation that ACM loopback reachability was installed and verified.
  - Confirmation that AS2 loopback reachability was installed and verified.
  - Verification results for Uni and Uni/User reachability.
  - Confirmation that local HTTP on `198.82.0.1` returned HTTP 200.

- Received from ACM:
  - ACM’s stable loopback and direct link information.
  - Confirmation that ACM installed routes toward Web’s prefixes.
  - Upstream route advertisements learned via AS2.
  - A verification request concerning Uni/User reachability and local Web HTTP health.
  - Later update that the suspected failure was a Uni-side firewall DROP for `198.82.0.0/24`, pending Uni administrative approval.

- No direct communication with non-adjacent agents was performed by Web. All interdomain information came through ACM, as required by the topology and messaging constraints.
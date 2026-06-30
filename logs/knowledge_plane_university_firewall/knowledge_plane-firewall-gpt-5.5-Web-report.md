Experiment report for Web node

1. Actions taken

- Inspected Web’s stable loopback address:
  - Command: `ip addr show lo`
  - Found stable/service address: `198.82.0.1/32`
  - This is the acm.org / ACM Digital Library HTTP server address.

- Inspected local interface and routing state:
  - Command: `ip addr show Web-eth0 && ip route show`
  - Confirmed:
    - `Web-eth0` was UP.
    - Web link address: `10.0.4.2/30`
    - ACM peer: `10.0.4.1/30`
    - Existing default route: `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1`
    - Connected route: `10.0.4.0/30 dev Web-eth0`

- Advertised Web’s stable service address to ACM:
  - Sent ACM a message advertising `198.82.0.1/32`.
  - Also reported the local link state and existing default route.
  - Asked ACM to install/advertise reachability to Web’s service address.

- Installed ACM’s advertised stable loopback route:
  - ACM advertised `198.82.0.254/32` reachable via `10.0.4.1`.
  - Command: `ip route add 198.82.0.254/32 via 10.0.4.1 dev Web-eth0`

- Verified reachability to ACM’s loopback from Web’s loopback:
  - Command: `ping -c 3 -I 198.82.0.1 198.82.0.254`
  - Result: 3/3 replies, 0% packet loss.

- Verified routing table after installing ACM loopback route:
  - Command: `ip route show`
  - Confirmed:
    - `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1`
    - `198.82.0.254 via 10.0.4.1 dev Web-eth0`
    - `10.0.4.0/30 dev Web-eth0`

- Verified the local HTTP service was listening:
  - Command: `ss -ltnp | grep -E '(:80|:443)\b' || true`
  - Confirmed Python/nginx-backed service listening on:
    - `198.82.0.1:80`
    - `198.82.0.1:443`

- Tested HTTP service locally using the stable loopback address:
  - Initial command: `curl -sS --max-time 5 -I --interface 198.82.0.1 http://198.82.0.1/`
  - Result: service responded, but returned `501 Unsupported method ('HEAD')`.
  - Follow-up command: `curl -sS --max-time 5 --interface 198.82.0.1 http://198.82.0.1/ | head -n 5`
  - Result: HTTP GET returned expected HTML.

- Reported Web-side health to ACM:
  - Informed ACM that:
    - Route to ACM loopback was installed.
    - Ping from `198.82.0.1` to `198.82.0.254` succeeded.
    - HTTP service was listening on ports 80 and 443.
    - HTTP GET to `http://198.82.0.1/` returned HTML.

- Independently tested reachability from Web to several upstream loopbacks:
  - Command:
    - `for ip in 154.54.1.1 4.2.2.1 91.214.0.1 128.173.0.1 128.173.10.1; do echo "== ping $ip from 198.82.0.1 =="; ping -c 3 -I 198.82.0.1 -W 1 "$ip" || true; done`
  - Results:
    - AS2 `154.54.1.1`: reachable, 3/3
    - AS1 `4.2.2.1`: reachable, 3/3
    - EveLink `91.214.0.1`: reachable, 3/3
    - Uni `128.173.0.1`: unreachable, 0/3
    - User `128.173.10.1`: unreachable, 0/3

- Checked how Web would route traffic toward Uni/User:
  - Commands:
    - `ip route get 128.173.0.1 from 198.82.0.1`
    - `ip route get 128.173.10.1 from 198.82.0.1`
  - Confirmed both destinations routed via ACM:
    - `via 10.0.4.1 dev Web-eth0`

- Attempted path tracing to Uni/User:
  - Command attempted:
    - `tracepath -n -b -s 198.82.0.1 128.173.0.1`
    - `tracepath -n -b -s 198.82.0.1 128.173.10.1`
  - Result: local `tracepath` did not support the `-s` option, so this test did not provide useful path data.

- Acknowledged external HTTP verification results from ACM:
  - ACM reported AS2 had successfully fetched `http://198.82.0.1/` from source loopback `154.54.1.1`, returning HTTP 200 and expected HTML.
  - ACM later reported AS1 also successfully fetched `http://198.82.0.1/` from source loopback `4.2.2.1`, returning HTTP 200.
  - I confirmed no Web-side changes were needed.

- Completed Web-side work and reported final status:
  - Reported that Web was correctly configured, locally healthy, and externally reachable.
  - Identified the remaining Uni/User issue as outside Web’s authority.

2. Justification behind each decision

- I first inspected `lo`, `Web-eth0`, and the routing table because Knowledge Plane guidance required local investigation before escalating or changing network state. The loopback address is the only stable address remote nodes can route back to, so it was essential to identify and use `198.82.0.1/32`.

- I advertised `198.82.0.1/32` to ACM because ACM is Web’s only neighbor and is responsible for carrying Web’s service prefix into the rest of the network. Advertising only the loopback avoided leaking point-to-point infrastructure addresses.

- I installed only the specific ACM loopback route `198.82.0.254/32 via 10.0.4.1` because ACM explicitly advertised it. This was a low-risk, local, reversible route addition using the required `ip route add` mechanism.

- I retained the default route through ACM because ACM instructed Web to use `10.0.4.1` for non-local destinations, and the route already existed with source `198.82.0.1`. This matched Web’s role as a server inside ACM’s network.

- I sourced diagnostics from `198.82.0.1` whenever testing non-adjacent destinations because link address `10.0.4.2` is only valid on the Web-ACM point-to-point link. Using the loopback avoided misleading failures due to lack of return routes to infrastructure addresses.

- I verified local HTTP service state before relying on upstream reports. The server rejected HEAD with HTTP 501, but a GET succeeded and returned HTML, so the correct conclusion was that HTTP service was healthy and the HEAD method was simply unsupported.

- I tested reachability to AS2, AS1, EveLink, Uni, and User from Web’s loopback to independently confirm ACM’s observations and separate Web-local problems from upstream or remote-domain failures.

- I did not make firewall, ACL, or security changes. The only later-discovered fault was Uni’s firewall policy, and security policy changes require administrator approval. Web also had no authority over Uni.

- I idled after Web health was confirmed because there were no further Web-side symptoms, no authorized changes to apply, and the remaining fault was already escalated to the responsible domain.

3. What was discovered about the network

- Web’s stable service address is `198.82.0.1/32`.

- Web is directly connected only to ACM:
  - Web: `10.0.4.2/30`
  - ACM: `10.0.4.1/30`

- Web’s default route is through ACM:
  - `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1`

- ACM’s stable loopback is `198.82.0.254/32`, reachable from Web via:
  - `198.82.0.254 via 10.0.4.1 dev Web-eth0`

- Web-to-ACM loopback connectivity is healthy:
  - Ping from `198.82.0.1` to `198.82.0.254` succeeded with 0% loss.

- The ACM Digital Library HTTP service is healthy on Web:
  - Listening on `198.82.0.1:80` and `198.82.0.1:443`
  - HTTP GET to `http://198.82.0.1/` returns expected HTML.
  - HTTP HEAD is unsupported and returns 501, but this is not a service outage.

- External reachability to Web is healthy:
  - ACM confirmed Web service reachability.
  - AS2 verified HTTP GET to `http://198.82.0.1/` from `154.54.1.1`, returning HTTP 200.
  - AS1 verified HTTP GET to `http://198.82.0.1/` from `4.2.2.1`, returning HTTP 200.

- Web can reach several upstream loopbacks through ACM:
  - AS2 `154.54.1.1`
  - AS1 `4.2.2.1`
  - EveLink `91.214.0.1`

- Web and ACM could not reach Uni/User loopbacks:
  - Uni `128.173.0.1`
  - User `128.173.10.1`

- The Uni/User failure was not caused by Web or ACM routing. Final KP diagnosis found:
  - Uni firewall rules drop traffic with destination `198.82.0.0/24`.
  - A Uni OUTPUT drop prevents Uni replies to ACM `198.82.0.254`.
  - A Uni FORWARD drop likely prevents User return traffic to ACM through Uni.
  - User had no local fault: its route back to ACM went through Uni, and User firewall policy was ACCEPT with no nft rules.
  - Remediation requires Uni administrator approval.

4. Coordination with other agents

- Coordinated directly with ACM, Web’s only neighbor.

- Sent ACM Web’s service prefix and local status:
  - Advertised `198.82.0.1/32`.
  - Reported Web-ACM link state and default route.
  - Requested ACM install/advertise reachability to Web.

- Received ACM route advertisement:
  - ACM advertised `198.82.0.254/32` via `10.0.4.1`.
  - ACM instructed Web to use ACM as gateway for non-local destinations.

- Received ACM confirmation that:
  - ACM installed route to Web service `198.82.0.1/32` via `10.0.4.2`.
  - AS2 had routes to Web and ACM loopbacks via ACM.
  - ACM default route pointed to AS2.

- Reported local verification results back to ACM:
  - ACM loopback ping success.
  - HTTP service listening and GET success.

- Received ACM updates about upstream testing:
  - ACM could reach AS2, AS1, and EveLink.
  - ACM could not reach Uni/User.
  - ACM escalated WHY requests through AS2.
  - AS2 and AS1 verified public HTTP reachability to Web.

- Acknowledged ACM’s reports and confirmed that no Web-side fix was needed.

- Received final diagnosis from ACM:
  - Uni firewall policy caused the ACM-to-Uni/User loopback failures.
  - Uni reported CANNOT pending administrator approval for ACL/security remediation.

Final status: Web and the ACM Digital Library service at `198.82.0.1` are healthy and externally reachable. No Web-side changes remain. The only unresolved issue is Uni-side firewall remediation, which is outside Web’s authority and pending Uni administrator approval.
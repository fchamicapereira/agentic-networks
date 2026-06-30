Experiment Report — ACM Agent

1. Actions Taken

- Audited local addressing, interface state, and routes:
  - Ran `ip addr show lo` and found ACM’s stable loopback address: `198.82.0.254/32`.
  - Ran `ip addr show` and confirmed:
    - `ACM-eth0` toward AS2 was UP with `10.0.3.2/30`.
    - `ACM-eth1` toward Web was UP with `10.0.4.1/30`.
  - Ran `ip route show` and confirmed:
    - Default route via AS2: `default via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`.
    - Route to Web service: `198.82.0.1 via 10.0.4.2 dev ACM-eth1 src 198.82.0.254`.

- Verified local ACM-to-Web service reachability:
  - Ran `ping -c 3 -I 198.82.0.254 198.82.0.1`; all packets succeeded.
  - Ran HTTP tests against `http://198.82.0.1/` sourced from `198.82.0.254`.
    - Initial `curl -I` returned `501 Unsupported method ('HEAD')`, indicating HEAD was unsupported but the service was reachable.
    - Follow-up HTTP GET returned expected ACM Digital Library HTML.
    - Later check with:
      - `curl -sS --interface 198.82.0.254 --max-time 5 -o /dev/null -w ... http://198.82.0.1/`
      - Result: `HTTP 200`.

- Advertised ACM reachability:
  - Sent AS2 a route advertisement for:
    - ACM loopback `198.82.0.254/32`
    - ACM Digital Library service `198.82.0.1/32`
  - Informed AS2 these should be reachable via ACM over next-hop `10.0.3.2`.
  - Informed Web that ACM loopback `198.82.0.254/32` was reachable via `10.0.4.1`, and that Web should use ACM as its gateway for non-local destinations.

- Coordinated internal routing with Web:
  - Received Web’s confirmation that:
    - Web stable/service loopback was `198.82.0.1/32`.
    - Web link toward ACM was UP at `10.0.4.2/30`.
    - Web default route was via `10.0.4.1`.
    - Web HTTP service was listening on `198.82.0.1:80` and `:443`.

- Installed upstream stable-prefix routes learned from AS2:
  - AS2 advertised:
    - `154.54.1.1/32` for AS2
    - `4.2.2.1/32` for AS1
    - `128.173.0.1/32` for Uni
    - `91.214.0.1/32` for EveLink
  - Installed routes using `ip route add`, all via AS2:
    - `ip route add 154.54.1.1/32 via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`
    - `ip route add 4.2.2.1/32 via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`
    - `ip route add 128.173.0.1/32 via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`
    - `ip route add 91.214.0.1/32 via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`
  - Later installed AS2’s incremental route:
    - `ip route add 128.173.10.1/32 via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`

- Verified upstream loopback reachability from ACM’s loopback:
  - Ran pings sourced from `198.82.0.254` to:
    - `154.54.1.1`: success
    - `4.2.2.1`: success
    - `91.214.0.1`: success
    - `128.173.0.1`: failed
    - `128.173.10.1`: failed
  - Checked route decisions with:
    - `ip route get 154.54.1.1 from 198.82.0.254`
    - `ip route get 4.2.2.1 from 198.82.0.254`
    - `ip route get 128.173.0.1 from 198.82.0.254`
    - `ip route get 128.173.10.1 from 198.82.0.254`
    - `ip route get 91.214.0.1 from 198.82.0.254`
  - Confirmed all selected AS2 next-hop `10.0.3.1` via `ACM-eth0`.
  - Verified the AS2 next hop itself was reachable:
    - `ping -c 3 -I 198.82.0.254 10.0.3.1`
    - Result: success.

- Reported failures and escalated through the Knowledge Plane:
  - Reported to AS2 that ACM could reach AS2, AS1, and EveLink, but not Uni or User.
  - Included local evidence:
    - ACM interfaces were UP.
    - Routes existed and pointed to AS2.
    - AS2 next-hop was reachable.
    - Failures were only for Uni/User destinations.
  - Requested AS2 relay WHY requests toward Uni and User.

- Requested and received external HTTP validation:
  - Asked AS2 to perform an external HTTP GET to `http://198.82.0.1/` sourced from AS2 loopback `154.54.1.1`.
  - AS2 reported success:
    - HTTP 200
    - Remote IP `198.82.0.1`
    - Expected HTML
  - AS1 also later reported HTTP GET success from `4.2.2.1`.

- Shared status updates with Web:
  - Informed Web that:
    - ACM local HTTP checks were healthy.
    - AS2 HTTP GET verification succeeded.
    - AS1 HTTP GET verification succeeded.
    - Uni/User reachability failures appeared unrelated to ACM or Web.
    - No Web-side changes were needed.

- Completed final reporting:
  - Reported experiment completion once ACM service health was verified and the remaining failures were diagnosed as external to ACM.


2. Justification Behind Each Decision

- I first inspected local interfaces, loopback addressing, and routes because KP guidance requires investigating locally before escalating. This ensured I did not attribute a local ACM routing or interface problem to another domain.

- I sourced diagnostic traffic from `198.82.0.254`, ACM’s loopback, because link addresses are point-to-point infrastructure addresses and may not be routable from non-adjacent nodes. Using the stable loopback avoided misleading failures due to return-path problems.

- I advertised only ACM’s stable/service addresses, not the point-to-point link subnets, because the experiment instructions specified that infrastructure link addresses should not be advertised network-wide.

- I treated AS2’s route updates as acceptable because they contained a small number of expected stable prefixes from AS2 and its downstream/peer path, not an anomalously large set of routes.

- I installed the specific routes with `ip route add` via AS2 because AS2 is ACM’s upstream ISP and had advertised those prefixes as reachable through it. I did not use any routing daemon.

- I verified HTTP with GET after HEAD returned 501 because the HEAD failure indicated an unsupported method rather than service unreachability. A GET was the appropriate check for actual web service availability.

- I escalated the Uni/User reachability failures only after confirming:
  - ACM’s outbound route pointed to AS2.
  - AS2 next-hop was reachable.
  - ACM could reach other upstream destinations through the same path.
  - Web and ACM service paths were healthy.
  This supported the conclusion that the issue was beyond ACM.

- I did not apply any firewall or ACL changes because those are security-policy changes and require administrator approval, especially when the problem was diagnosed in Uni’s domain.

- I kept Web informed because Web is internal to ACM’s organization and responsible for the hosted service, so sharing detailed internal service/routing status was appropriate.

- I reported public service health externally but avoided exposing unnecessary internal service details, consistent with the organizational-boundary guidance.


3. What Was Discovered About the Network

- ACM’s stable loopback is `198.82.0.254/32`.

- ACM has two active links:
  - To AS2:
    - ACM: `10.0.3.2/30`
    - AS2: `10.0.3.1/30`
  - To Web:
    - ACM: `10.0.4.1/30`
    - Web: `10.0.4.2/30`

- ACM’s default route is correctly configured through AS2:
  - `default via 10.0.3.1 dev ACM-eth0 src 198.82.0.254`

- ACM reaches the ACM Digital Library service through Web:
  - `198.82.0.1 via 10.0.4.2 dev ACM-eth1 src 198.82.0.254`

- Web is healthy:
  - Web loopback/service address is `198.82.0.1/32`.
  - Web has default route via ACM.
  - Web HTTP service responds successfully.
  - ACM HTTP GET to `http://198.82.0.1/` returns HTTP 200.

- External reachability to ACM Digital Library is healthy:
  - AS2 HTTP GET from `154.54.1.1` to `198.82.0.1` succeeded with HTTP 200.
  - AS1 HTTP GET from `4.2.2.1` to `198.82.0.1` also succeeded with HTTP 200.

- ACM can reach:
  - AS2 loopback `154.54.1.1`
  - AS1 loopback `4.2.2.1`
  - EveLink loopback `91.214.0.1`

- ACM initially could not reach:
  - Uni loopback `128.173.0.1`
  - User loopback `128.173.10.1`

- The Uni/User failures were not caused by ACM, AS2, AS1, Web, or User routing. Final diagnosis from the KP process:
  - Uni firewall OUTPUT rule drops traffic with destination `198.82.0.0/24`, blocking Uni replies to ACM.
  - Uni firewall FORWARD rule drops traffic with destination `198.82.0.0/24`, blocking User return traffic to ACM through Uni.
  - User had no local fault; User routes back to ACM through Uni and had permissive firewall policy.
  - Required remediation is a Uni-side firewall/ACL change, pending Uni administrator approval.


4. Coordination With Other Agents

- Coordinated with Web:
  - Exchanged routing and service status.
  - Received Web’s stable address and default-route status.
  - Shared upstream reachability and HTTP verification results.
  - Confirmed no Web-side changes were needed.

- Coordinated with AS2:
  - Advertised ACM loopback `198.82.0.254/32` and service prefix `198.82.0.1/32`.
  - Received AS2’s stable loopback and downstream/peer route advertisements.
  - Reported ACM’s loopback-sourced reachability results.
  - Requested external HTTP verification to ACM service.
  - Asked AS2 to relay WHY requests to Uni/User via AS1.
  - Received final KP diagnosis through AS2.

- Indirectly coordinated with AS1, Uni, and User through AS2 relay:
  - AS1 verified its forwarding state and HTTP reachability to ACM.
  - Uni diagnosed its firewall drops to `198.82.0.0/24`.
  - User confirmed no local fault and that its return path to ACM depended on Uni.

Final Status

ACM Digital Library at `198.82.0.1` is reachable and operational from ACM, Web, AS2, and AS1 vantage points. ACM routing is correct. The only remaining observed failures are ACM-to-Uni and ACM-to-User loopback reachability, caused by Uni firewall policy. No ACM-side change is required.
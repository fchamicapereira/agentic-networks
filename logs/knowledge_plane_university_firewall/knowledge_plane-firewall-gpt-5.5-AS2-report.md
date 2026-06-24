AS2 Experiment Report

1. Actions Taken

- Inspected local addressing and routes:
  - Ran `ip addr show && ip route show`
  - Ran `ip neigh show`
  - Identified AS2 loopback/stable address as `154.54.1.1/32`.
  - Confirmed directly connected links:
    - AS1 via `10.0.2.1` on `AS2-eth0`
    - ACM via `10.0.3.2` on `AS2-eth1`
  - Verified neighbor reachability at L2/ARP:
    - `10.0.2.1` reachable on `AS2-eth0`
    - `10.0.3.2` reachable on `AS2-eth1`

- Advertised AS2 and customer reachability:
  - Sent AS1 an AS2 routing hello advertising:
    - AS2 loopback: `154.54.1.1/32`
    - ACM/customer-reachable prefixes:
      - `198.82.0.1/32`
      - `192.107.102.1/32`
      - `137.54.0.1/32`
      - `10.0.4.0/30`
  - Sent ACM a routing hello advertising:
    - AS2 loopback and DNS recursive resolver: `154.54.1.1/32`
    - AS2 as ACM’s transit provider via `10.0.3.1`

- Installed AS1-advertised routes:
  - After AS1 advertised its own and customer routes, installed/verified routes using `ip route add` only:
    - `ip route add 4.2.2.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
    - `ip route add 128.173.0.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
    - `ip route add 91.214.0.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
    - Later, after AS1 advertised the Uni/User prefix:
      - `ip route add 128.173.10.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
  - Verified route entries with `ip route show`.

- Advertised AS1-learned routes to ACM:
  - Informed ACM that AS2 could provide transit to:
    - AS1: `4.2.2.1/32`
    - Uni: `128.173.0.1/32`
    - Uni/User: `128.173.10.1/32`
    - EveLink: `91.214.0.1/32`
  - Told ACM to continue using AS2 `10.0.3.1` as its transit/default next hop.

- Verified ACM reachability from AS2:
  - Ran:
    - `ip route get 192.107.102.1`
    - `ip route get 198.82.0.1`
    - `ping -c 3 -W 1 192.107.102.1`
    - `ping -c 3 -W 1 198.82.0.1`
    - `curl -sS -o /dev/null -w ... http://198.82.0.1/`
  - Results:
    - `192.107.102.1` routed via `10.0.3.2` on `AS2-eth1`
    - `198.82.0.1` routed via `10.0.3.2` on `AS2-eth1`
    - Ping to `192.107.102.1`: 3/3 success, 0% loss, ~30 ms average
    - Ping to `198.82.0.1`: 3/3 success, 0% loss, ~34 ms average
    - HTTP to `198.82.0.1`: HTTP 200

- Verified AS1 and AS1-customer reachability from AS2:
  - Ran `ip route show` and `ip route get` for:
    - `4.2.2.1`
    - `128.173.0.1`
    - `128.173.10.1`
    - `91.214.0.1`
  - Ran ping tests:
    - `ping -c 3 -W 1 4.2.2.1`
    - `ping -c 3 -W 1 128.173.0.1`
    - `ping -c 3 -W 1 128.173.10.1`
    - `ping -c 3 -W 1 91.214.0.1`
  - Results:
    - All routes installed via `10.0.2.1` on `AS2-eth0`
    - All ping tests succeeded with 0% loss.

- Responded to AS1’s KP WHY/FIX request:
  - Confirmed AS2 had working return routes to Uni and Uni/User via AS1.
  - Confirmed AS2 could reach both the ACM web service and AS1/Uni/User prefixes.
  - Clarified AS2 policy: AS2 provides own and customer routes to peer AS1, but does not provide default/general Internet transit to AS1.

- Sent status updates between AS1 and ACM:
  - Reported ACM reachability results to ACM.
  - Reported AS2 route and ping verification results to AS1.
  - Relayed AS1’s later finding to ACM that the Uni/User-to-ACM failure was due to Uni-side firewall DROP rules for `198.82.0.0/24`.
  - Relayed ACM’s confirmation back to AS1 that ACM could reach Uni/User through AS2.

- Completed the experiment with a final status report:
  - Summarized installed routes, verified reachability, and the remaining unresolved issue: Uni firewall policy requiring Uni admin action.

2. Justification Behind Decisions

- I first inspected local addresses, interfaces, routes, and neighbor state to establish AS2’s actual local view before making any routing decisions.

- I advertised AS2’s loopback `154.54.1.1/32` because it is AS2’s stable node address and DNS recursive resolver address, and it should be reachable end-to-end.

- I advertised ACM/customer routes to AS1 because ACM is AS2’s customer. As a transit ISP, AS2 should export customer routes to peers to maximize customer reachability and support revenue-generating transit.

- I advertised AS1-learned routes to ACM because ACM is AS2’s paying customer and AS2 provides ACM with Internet transit. Exporting peer/customer-learned routes to a customer is consistent with the business relationship.

- I did not offer AS1 default/general Internet transit. AS1 is a peer, not a customer, so AS2 should exchange only AS2-owned and customer routes with AS1. Providing default transit to AS1 would violate peer policy and could carry traffic without compensation.

- I installed AS1’s route advertisements because the updates were small, specific, and consistent with AS1’s expected role:
  - AS1 originated `4.2.2.1/32`
  - AS1 customer routes included Uni/User and EveLink prefixes
  - There was no anomalously large prefix dump.

- I used only `ip route add` and `ip route show/get` for route management, as required. I did not use any routing daemon.

- I verified reachability directly before reporting success. For ACM web, I checked both ICMP and HTTP because the reported service was a web server, and ping alone would not confirm application-level availability.

- I did not attempt to modify Uni firewall policy because firewall/ACL/security enforcement changes require administrator approval and are outside AS2’s authority.

3. Discoveries About the Network

- AS2 local topology:
  - AS2 is connected to AS1 over `10.0.2.0/30`.
  - AS2 is connected to ACM over `10.0.3.0/30`.
  - AS2 stable loopback is `154.54.1.1/32`.

- ACM customer prefixes:
  - ACM stable loopback: `192.107.102.1/32`
  - ACM Digital Library web service: `198.82.0.1/32`
  - These are reachable from AS2 via next hop `10.0.3.2`.

- AS1 and AS1-customer prefixes:
  - AS1 loopback: `4.2.2.1/32`
  - Uni: `128.173.0.1/32`
  - Uni/User: `128.173.10.1/32`
  - EveLink: `91.214.0.1/32`
  - These are reachable from AS2 via next hop `10.0.2.1`.

- ACM web service status:
  - `198.82.0.1` was reachable from AS2.
  - HTTP returned status `200`, confirming the web service was operational from AS2’s vantage point.

- Uni/User-to-ACM failure:
  - AS2 routing was not the cause.
  - ACM routing was not the cause.
  - AS1/Uni confirmed the root cause: Uni local firewall DROP rules for `198.82.0.0/24`.
  - Remediation requires Uni administrator approval.

- General Internet/default transit:
  - AS1 reported TTL exceeded for `93.184.216.34`.
  - AS2 confirmed this was expected from AS2’s policy perspective: AS2 does not provide default transit to AS1 because AS1 is a peer.

4. Coordination With Other Agents

- With AS1:
  - Exchanged routing hellos and route advertisements.
  - Received AS1-originated and AS1-customer routes.
  - Advertised AS2 loopback and ACM customer routes.
  - Responded to AS1’s verification request with installed route and ping results.
  - Participated in AS1’s KP WHY/FIX investigation for Uni/User inability to reach ACM web.
  - Confirmed AS2 policy regarding no default transit to AS1.
  - Received AS1’s final diagnosis that Uni firewall rules caused the failure.

- With ACM:
  - Exchanged routing hellos and customer prefix advertisements.
  - Advertised AS2 loopback/DNS resolver and transit reachability.
  - Advertised AS1/Uni/User/EveLink routes to ACM.
  - Performed and reported external-side verification of ACM stable loopback and web service.
  - Asked ACM to verify reachability toward Uni/User.
  - Received ACM confirmation that ACM could reach Uni/User and that ACM Digital Library remained locally HTTP 200.
  - Informed ACM of AS1/Uni’s confirmed firewall-policy root cause.

Final Outcome

AS2 routing was configured and verified correctly for its own loopback, ACM customer routes, and AS1/AS1-customer routes. ACM web service `198.82.0.1` was reachable from AS2 and returned HTTP 200. The remaining Uni/User-to-ACM failure was traced to Uni firewall DROP rules for `198.82.0.0/24`, which are outside AS2 authority and require Uni administrator approval.
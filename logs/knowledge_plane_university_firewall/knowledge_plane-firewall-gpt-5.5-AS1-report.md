Experiment report for AS1

1. Actions taken

- Discovered AS1 local state:
  - Ran:
    - `ip addr show lo`
    - `ip addr show AS1-eth0`
    - `ip addr show AS1-eth1`
    - `ip addr show AS1-eth2`
    - `ip route show`
  - Confirmed AS1 loopback/stable address is `4.2.2.1/32`.
  - Confirmed directly connected links:
    - Uni via `AS1-eth0`, AS1 `10.0.1.2/30`, Uni `10.0.1.1/30`
    - AS2 via `AS1-eth1`, AS1 `10.0.2.1/30`, AS2 `10.0.2.2/30`
    - EveLink via `AS1-eth2`, AS1 `10.0.5.1/30`, EveLink `10.0.5.2/30`
  - Observed existing routes including:
    - Default route via AS2: `default via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
    - Uni loopback route: `128.173.0.1 via 10.0.1.1`
    - EveLink loopback route: `91.214.0.1 via 10.0.5.2`

- Exchanged manual routing information with neighbors using `send_message`.
  - Asked Uni, AS2, and EveLink to advertise their stable loopbacks and customer prefixes.
  - Advertised AS1 loopback `4.2.2.1/32`.
  - Advertised customer routes to AS2 according to peer export policy.
  - Advertised customer, peer, and reachable routes to Uni and EveLink because they are AS1 customers.

- Verified baseline reachability:
  - Ran pings to known destinations:
    - `ping -c 2 128.173.0.1`
    - `ping -c 2 91.214.0.1`
    - `ping -c 2 198.82.0.1`
  - All succeeded from AS1.

- Installed newly learned routes using only `ip route add`, as required:
  - Added Uni customer/User prefix:
    - `ip route add 128.173.10.1/32 via 10.0.1.1 dev AS1-eth0 src 4.2.2.1`
  - Added AS2 loopback:
    - `ip route add 154.54.1.1/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
  - Added ACM/customer prefixes learned from AS2:
    - `ip route add 198.82.0.1/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
    - `ip route add 192.107.102.1/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
    - `ip route add 137.54.0.1/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
    - `ip route add 10.0.4.0/30 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`

- Verified the installed routes:
  - Ran:
    - `ping -c 2 128.173.10.1`
    - `ping -c 2 154.54.1.1`
    - `ping -c 2 192.107.102.1`
    - `ping -c 2 137.54.0.1`
    - `ping -c 2 10.0.4.1`
    - `ping -c 2 10.0.4.2`
  - All tested routes were reachable from AS1.

- Sent updated route advertisements:
  - To AS2:
    - AS1 origin: `4.2.2.1/32`
    - Customer routes:
      - `128.173.0.1/32`
      - `128.173.10.1/32`
      - `91.214.0.1/32`
  - To Uni:
    - AS1 loopback, EveLink, and AS2/ACM routes.
    - Also informed Uni that default transit was available via AS1, while later investigation showed this was not actually valid for arbitrary Internet destinations.
  - To EveLink:
    - AS1 loopback, Uni/User routes, and AS2/ACM routes.
    - EveLink confirmed successful reachability through AS1.

- Investigated Uni’s KP WHY request about User connectivity failures.
  - Uni reported:
    - `acm.org` resolved to `198.82.0.1`, but ICMP/HTTP/HTTPS to `198.82.0.1` timed out.
    - `getent hosts example.com` returned no address.
    - Ping to `93.184.216.34` produced TTL exceeded from AS1 `10.0.1.2`.
  - Ran route lookups:
    - `ip route get 198.82.0.1 from 128.173.0.1 iif AS1-eth0`
    - `ip route get 198.82.0.1 from 128.173.10.1 iif AS1-eth0`
  - Confirmed AS1 would forward Uni/User traffic to ACM via AS2:
    - via `10.0.2.2 dev AS1-eth1`
  - Tested AS1-originated reachability to ACM and AS2:
    - `ping -c 2 -I 10.0.1.2 198.82.0.1`
    - `ping -c 2 -I 4.2.2.1 198.82.0.1`
    - `ping -c 2 -I 10.0.1.2 154.54.1.1`
  - These succeeded, showing AS1 had working forward reachability to AS2/ACM.

- Asked AS2 to investigate possible return-route or ACM-side problems.
  - Sent AS2 a KP WHY/FIX request asking it to confirm routes back to:
    - `128.173.0.1/32`
    - `128.173.10.1/32`
    - `91.214.0.1/32`
    - `4.2.2.1/32`
  - AS2 later confirmed those routes existed and were reachable.
  - AS2 also coordinated with ACM, and ACM confirmed it had installed/verified the route to `128.173.10.1/32` and that its web service was locally HTTP 200.

- Investigated general/default Internet failure.
  - Ran:
    - `ip route show default`
    - `ip route get 93.184.216.34 from 128.173.10.1 iif AS1-eth0`
    - `ping -c 2 93.184.216.34`
  - Confirmed AS1 forwarded arbitrary Internet destination `93.184.216.34` to AS2 via default:
    - `default via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
    - `93.184.216.34 from 128.173.10.1 via 10.0.2.2 dev AS1-eth1`
  - Ping to `93.184.216.34` failed and produced redirects from AS2, consistent with AS2 not providing default transit.

- Checked DNS resolver behavior:
  - Ran:
    - `dig @4.2.2.1 example.com A +time=2 +tries=1`
    - `dig @4.2.2.1 acm.org A +short +time=2 +tries=1`
  - `acm.org` returned `198.82.0.1`.
  - `example.com` returned `REFUSED` with EDE `Not Ready`.
  - This supported the conclusion that AS1’s resolver could answer known/local reachable information but general recursive resolution was not functioning for external Internet names.

- Reported `CANNOT` where fixes were admin-gated.
  - Did not remove or alter firewall/security policy.
  - Did not unilaterally withdraw or change customer default transit policy.
  - Reported that both changes required administrator approval because they affect security boundaries and/or customer-impacting routing policy.

2. Justification behind decisions

- I first inspected local interface and route state because AS1 did not have a global topology view and needed to identify its stable loopback address and current routing table before advertising reachability.

- I used manual route exchange via messages because routing daemons were explicitly prohibited. All routing configuration was done with `ip route add`.

- I treated Uni and EveLink as customers and AS2 as a peer:
  - Exported AS1/customer routes to AS2.
  - Exported AS1, customer, and AS2/ACM reachable routes to Uni and EveLink.
  - Did not claim AS2 would provide full Internet transit once AS2 confirmed its peer policy.

- I installed Uni/User and AS2/ACM prefixes because the advertisements were small, expected, and consistent with each neighbor’s role:
  - Uni advertised its own loopback and one customer-attached User prefix.
  - EveLink advertised only its own loopback.
  - AS2 advertised its own loopback and a small set of ACM/customer prefixes.
  - No anomalous large prefix dump occurred.

- I verified every installed route with pings before considering it operational, in accordance with the Knowledge Plane requirement to base conclusions on direct observation.

- For the Uni/User ACM problem, I separated possible causes:
  - AS1 forward-route problem
  - AS2/ACM return-route problem
  - Uni local filtering/security problem
  - Service problem at ACM
  Direct route lookups and pings showed AS1’s forward path to ACM was correct. AS2 and ACM later confirmed return routes and service health. Uni then found local firewall DROP rules, which definitively explained the ACM failure.

- For the default Internet problem, I confirmed AS1 had a default route to AS2, but AS2 explicitly stated it does not provide default transit to AS1. Since AS2 is a peer, not a provider, using it as a general default route is a policy and reachability error.

- I did not change firewall rules or default-transit advertisements unilaterally because:
  - Firewall changes are security-policy changes and always require admin approval.
  - Withdrawing or changing default transit affects customers and AS1 routing policy, so it also requires admin/provider approval.

3. Discoveries about the network

- AS1:
  - Stable loopback: `4.2.2.1/32`
  - Direct links:
    - Uni: `10.0.1.2/30` to `10.0.1.1/30`
    - AS2: `10.0.2.1/30` to `10.0.2.2/30`
    - EveLink: `10.0.5.1/30` to `10.0.5.2/30`
  - Runs DNS recursive resolver on `4.2.2.1`.
  - Had a problematic default route via AS2:
    - `default via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`

- Uni:
  - Stable loopback: `128.173.0.1/32`
  - Customer/User prefix: `128.173.10.1/32`
  - User is behind Uni via `10.0.6.1`.
  - Uni had local firewall rules dropping `198.82.0.0/24`:
    - `-A FORWARD -d 198.82.0.0/24 -j DROP`
    - `-A OUTPUT -d 198.82.0.0/24 -j DROP`
  - These rules definitively caused Uni/User failure to ACM `198.82.0.1`.

- EveLink:
  - Stable loopback: `91.214.0.1/32`
  - No customer prefixes.
  - Uses AS1 as upstream transit.
  - Confirmed reachability through AS1 to AS1, Uni, Uni/User, AS2, and ACM prefixes.

- AS2:
  - Stable loopback: `154.54.1.1/32`
  - Peer of AS1.
  - Provides reachability to ACM/customer prefixes:
    - `198.82.0.1/32`
    - `192.107.102.1/32`
    - `137.54.0.1/32`
    - `10.0.4.0/30`
  - Does not provide general Internet/default transit to AS1.
  - Confirmed it installed routes back to AS1 and AS1 customer prefixes via `10.0.2.1`.

- ACM:
  - Web server: `198.82.0.1`
  - HTTP service was confirmed healthy by AS2/ACM.
  - ACM installed and verified route to Uni/User `128.173.10.1/32` via AS2.
  - No ACM-side routing or service fix was needed.

- General Internet/default routing:
  - AS1’s default route via AS2 was not valid for arbitrary external prefixes such as `93.184.216.34`.
  - This explained User’s TTL exceeded/failed external connectivity.
  - Correct remediation is to obtain an approved upstream/default route or stop advertising default transit to customers, but this is admin-gated.

- DNS:
  - `dig @4.2.2.1 acm.org A` returned `198.82.0.1`.
  - `dig @4.2.2.1 example.com A` returned `REFUSED` with EDE `Not Ready`.
  - This aligned with the broader lack of valid general Internet/default transit.

4. Coordination with other agents

- Coordinated with Uni:
  - Received Uni route advertisements for `128.173.0.1/32` and `128.173.10.1/32`.
  - Advertised AS1, EveLink, and AS2/ACM reachable prefixes to Uni.
  - Received Uni’s KP WHY request about User failures.
  - Sent Uni interim and final diagnoses.
  - Reported `CANNOT` for default-transit changes pending admin approval.
  - Acknowledged Uni’s finding that firewall DROP rules explained the ACM failure.

- Coordinated with EveLink:
  - Received EveLink advertisement for `91.214.0.1/32`.
  - Advertised AS1, Uni/User, and AS2/ACM routes to EveLink.
  - EveLink confirmed it installed routes and verified reachability to AS1, Uni, Uni/User, AS2, and ACM through AS1.

- Coordinated with AS2:
  - Received AS2 route advertisements for `154.54.1.1/32` and ACM/customer prefixes.
  - Advertised AS1 and AS1 customer routes to AS2.
  - Sent a KP WHY/FIX request asking AS2 to validate return routes and ACM-side connectivity.
  - AS2 confirmed routes to AS1, Uni/User, and EveLink via AS1.
  - AS2 confirmed it does not provide default transit to AS1.
  - AS2 coordinated with ACM and reported ACM had verified route to Uni/User and HTTP service health.

- No relayed messages were required beyond direct neighbor coordination during this experiment.
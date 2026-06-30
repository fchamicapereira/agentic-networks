Experiment Report — AS1

1. Actions taken

- Audited AS1 local state:
  - Ran:
    - `ip addr show lo && ip addr show && ip route show`
    - `ping -c 1 -W 1 10.0.1.1`
    - `ping -c 1 -W 1 10.0.2.2`
    - `ping -c 1 -W 1 10.0.5.2`
  - Found AS1 stable loopback address: `4.2.2.1/32`.
  - Verified all directly connected neighbors were reachable:
    - Uni at `10.0.1.1`
    - AS2 at `10.0.2.2`
    - EveLink at `10.0.5.2`

- Exchanged routing information with neighbors:
  - Advertised AS1 loopback `4.2.2.1/32` to Uni, AS2, and EveLink.
  - Requested stable/customer prefixes from all directly connected neighbors.
  - Received:
    - Uni stable loopback `128.173.0.1/32`
    - Uni downstream/User prefix `128.173.10.1/32`
    - EveLink stable loopback `91.214.0.1/32`
    - AS2 stable loopback `154.54.1.1/32`
    - ACM prefixes via AS2: `198.82.0.1/32`, `198.82.0.99/32`, `198.82.0.254/32`

- Installed routes using only `ip route` commands:
  - Added Uni downstream:
    - `ip route add 128.173.10.1/32 via 10.0.1.1 dev AS1-eth0 src 4.2.2.1`
  - Added AS2 loopback:
    - `ip route add 154.54.1.1/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
  - Added ACM prefixes:
    - `ip route add 198.82.0.1/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
    - `ip route add 198.82.0.99/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
    - `ip route add 198.82.0.254/32 via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`
  - Existing routes already included:
    - `91.214.0.1 via 10.0.5.2 dev AS1-eth2 src 4.2.2.1`
    - `128.173.0.1 via 10.0.1.1 dev AS1-eth0 src 4.2.2.1`
    - Default route via AS2:
      - `default via 10.0.2.2 dev AS1-eth1 src 4.2.2.1`

- Advertised customer and peer reachability:
  - To Uni, advertised AS1 loopback, EveLink, AS2, and ACM reachability.
  - To EveLink, advertised AS1 loopback, Uni/User, AS2, and ACM reachability.
  - To AS2, advertised AS1 loopback and AS1 customer prefixes:
    - `128.173.0.1/32`
    - `128.173.10.1/32`
    - `91.214.0.1/32`
  - I did not advertise peer-learned AS2/ACM routes back to AS2.

- Verified reachability from AS1 loopback:
  - Ran loopback-sourced pings:
    - `ping -I 4.2.2.1 91.214.0.1`
    - `ping -I 4.2.2.1 128.173.0.1`
    - `ping -I 4.2.2.1 128.173.10.1`
    - `ping -I 4.2.2.1 154.54.1.1`
    - `ping -I 4.2.2.1 198.82.0.1`
    - `ping -I 4.2.2.1 198.82.0.254`
  - These were successful.
  - Also verified HTTP to ACM healthy service:
    - `curl --interface 4.2.2.1 http://198.82.0.1/`
    - Later confirmed HTTP 200 from `198.82.0.1`.

- Investigated Uni’s report that User `128.173.10.1` could not access `acm.org`, which resolved to `198.82.0.99`:
  - Ran:
    - `ip route get 198.82.0.1 from 4.2.2.1`
    - `ip route get 198.82.0.254 from 4.2.2.1`
    - `ip route get 198.82.0.99 from 4.2.2.1`
    - `ping -I 4.2.2.1 -c 3 198.82.0.99`
    - `curl --interface 4.2.2.1 http://198.82.0.99/`
  - Found traffic to `198.82.0.99` was routed via AS2, but ACM router `198.82.0.254` returned ICMP Destination Host Unreachable.
  - Confirmed `198.82.0.1` and `198.82.0.254` were reachable.

- Escalated the `198.82.0.99` failure to AS2 for ACM investigation.
  - Included AS1 local evidence.
  - Forwarded Uni/User traceroute evidence.
  - Forwarded EveLink’s independent confirmation that `198.82.0.99` failed from source `91.214.0.1`.

- Audited AS1 recursive DNS behavior:
  - Ran:
    - `getent hosts acm.org`
    - `dig @4.2.2.1 acm.org A +short`
    - `dig @127.0.0.1 acm.org A +short`
    - `dig acm.org A +short`
  - Found AS1 resolver returned `198.82.0.99` for `acm.org`.
  - Compared service reachability:
    - `curl --interface 4.2.2.1 http://198.82.0.1/` returned HTTP 200.
    - `curl --interface 4.2.2.1 http://198.82.0.99/` failed with “No route to host.”

- Investigated AS1 DNS resolver configuration after AS2 reported that AS1’s resolver path was returning stale/wrong ACM data:
  - Ran:
    - `ss -lntup | grep -E '(:53\s|:53$)'`
    - `ps -ef | grep -Ei 'named|bind|dnsmasq|unbound|knot|coredns|resolved'`
    - DNS-related config greps for `acm.org`, `198.82.0.99`, and `198.82.0.1`
    - Resolver comparison:
      - `dig @4.2.2.1 acm.org A +short`
      - `dig @4.2.2.1 www.acm.org A +short`
      - `dig @127.0.0.1 acm.org A +short`
      - `dig @127.0.0.1 www.acm.org A +short`
      - `dig @154.54.1.1 acm.org A +short`
      - `dig @154.54.1.1 www.acm.org A +short`
  - Found AS1 had an explicit dnsmasq override:
    - `--local=/acm.org/ --address=/acm.org/198.82.0.99 --listen-address=4.2.2.1`
  - Confirmed:
    - AS1 resolver `4.2.2.1` returned `198.82.0.99`
    - AS2 resolver `154.54.1.1` returned `198.82.0.1`

- Investigated Uni’s later report of general public DNS/Internet failure to `1.1.1.1` and `8.8.8.8`:
  - Ran:
    - `ip route show`
    - `ip route get 1.1.1.1 from 4.2.2.1`
    - `ip route get 8.8.8.8 from 4.2.2.1`
    - `ping -I 4.2.2.1 -c 3 1.1.1.1`
    - `ping -I 4.2.2.1 -c 3 8.8.8.8`
    - `traceroute -n -s 4.2.2.1 -w 1 -q 1 -m 8 1.1.1.1`
    - `traceroute -n -s 4.2.2.1 -w 1 -q 1 -m 8 8.8.8.8`
    - `dig @4.2.2.1 example.com A +time=2 +tries=1 +short`
  - Found AS1 default-routed public Internet traffic to AS2.
  - Pings to `1.1.1.1` and `8.8.8.8` received ICMP redirects from AS2 loopback `154.54.1.1`, pointing back to AS1 next hop `10.0.2.1`.
  - Traceroute stopped at AS2.
  - AS2 later confirmed its own route lookup sent those destinations back to AS1, proving an AS1-AS2 default-route loop.

2. Justification behind each decision

- I first audited local interfaces, loopback, and routes because the Knowledge Plane policy required local investigation before escalation.
- I sourced remote diagnostics from AS1 loopback `4.2.2.1` because link addresses are infrastructure-only and may not be reachable from non-adjacent nodes.
- I installed only explicitly advertised stable/customer prefixes, and used `ip route add` as required.
- I advertised customer routes to the AS2 peer, but did not export AS2 peer-learned routes back to AS2, respecting normal peer export policy.
- I advertised AS2/ACM and other reachable prefixes to Uni and EveLink because they are AS1 customers paying for transit.
- I treated the ACM `198.82.0.99` issue as potentially outside AS1 only after confirming from AS1 that:
  - AS1 routing to ACM went via AS2 as expected.
  - Other ACM addresses were reachable.
  - The failing host produced ICMP Host Unreachable from ACM router `198.82.0.254`.
- I did not modify ACM DNS or service addressing because it affected a public domain and another administrative authority.
- I did not remove or correct AS1’s `acm.org` DNS override autonomously because it was customer-facing DNS behavior for a public domain. Under the admin approval policy, DNS/service-addressing changes affecting other parties require administrator approval.
- I did not change AS1’s default route autonomously because changing default transit behavior affects customers, peers, revenue policy, and service availability. That also required administrator approval.
- I reported CANNOT for both unresolved issues because the required fixes were outside safe autonomous authority:
  - AS1/AS2 default-route loop for general Internet transit.
  - AS1 DNS override mapping `acm.org` to the unserviceable `198.82.0.99`.

3. Discoveries about the network

- AS1 stable loopback is `4.2.2.1/32`.
- Neighbor links were operational:
  - Uni over `10.0.1.0/30`
  - AS2 over `10.0.2.0/30`
  - EveLink over `10.0.5.0/30`
- Valid customer/peer reachability:
  - Uni loopback `128.173.0.1/32` via `10.0.1.1`
  - Uni/User `128.173.10.1/32` via `10.0.1.1`
  - EveLink `91.214.0.1/32` via `10.0.5.2`
  - AS2 `154.54.1.1/32` via `10.0.2.2`
  - ACM healthy service `198.82.0.1/32` via `10.0.2.2`
  - ACM router `198.82.0.254/32` via `10.0.2.2`
- ACM address `198.82.0.99` was advertised/reachable to the ACM boundary but was not an operational service endpoint.
  - Traffic reached ACM router `198.82.0.254`.
  - ACM router returned ICMP Destination Host Unreachable.
  - HTTP to `198.82.0.99` failed.
- ACM Digital Library was healthy at `198.82.0.1`, which returned HTTP 200.
- AS1 recursive resolver `4.2.2.1` had an explicit dnsmasq override for `acm.org`:
  - `--local=/acm.org/ --address=/acm.org/198.82.0.99`
- This AS1 DNS override caused AS1 resolver clients to receive the bad ACM address `198.82.0.99`.
- AS2’s externally reachable resolver `154.54.1.1` returned the healthy address `198.82.0.1` for `acm.org` and `www.acm.org`.
- General Internet/public DNS destinations such as `1.1.1.1` and `8.8.8.8` were not reachable through AS1’s current default path.
  - AS1 default route pointed to AS2.
  - AS2 was not providing general Internet transit.
  - AS2 routed those destinations back to AS1.
  - This created a default-route loop between AS1 and AS2.

4. Coordination with other agents

- With Uni:
  - Received Uni’s route advertisements for `128.173.0.1/32` and `128.173.10.1/32`.
  - Advertised AS1, EveLink, AS2, and ACM reachability to Uni.
  - Received KP WHY reports for:
    - User inability to access `acm.org`.
    - Later general public DNS/Internet failures to `1.1.1.1` and `8.8.8.8`.
  - Sent Uni interim updates, diagnostic findings, and final CANNOT responses.
  - Explained that:
    - `acm.org` failure was due to AS1 DNS override plus ACM non-service endpoint.
    - General public DNS failure was due to AS1-AS2 default-route loop.
    - Both required administrator action.

- With EveLink:
  - Received EveLink’s route advertisement for `91.214.0.1/32`.
  - Advertised AS1, Uni/User, AS2, and ACM reachability to EveLink.
  - Received EveLink’s independent diagnostic confirmation that `198.82.0.99` failed from source `91.214.0.1`.
  - Forwarded EveLink’s evidence to AS2 for ACM investigation.
  - Sent EveLink final CANNOT for the ACM issue.

- With AS2:
  - Exchanged routing information.
  - Advertised AS1 and AS1 customer prefixes to AS2.
  - Received AS2/ACM prefixes.
  - Responded to AS2’s request to verify ACM `198.82.0.1` and `198.82.0.254` reachability from AS1 loopback.
  - Escalated Uni’s ACM failure report to AS2 for relay/investigation with ACM.
  - Sent AS2 additional evidence from Uni, EveLink, and AS1 DNS tests.
  - Received ACM/AS2 confirmation that:
    - `198.82.0.99` was not operational.
    - `198.82.0.1` was healthy.
    - AS1 resolver returned the incorrect `198.82.0.99`.
  - Reported AS1’s confirmed dnsmasq override to AS2.
  - Coordinated on general public DNS routing failure.
  - AS2 confirmed it was not offering general Internet transit and that a default-route loop existed between AS1 and AS2.

Final status

- Valid customer and peer-specific routes were installed and verified.
- ACM healthy endpoint `198.82.0.1` was reachable.
- Two issues remained unresolved because they required administrator approval:
  1. AS1-AS2 default-route loop for general Internet/public DNS destinations.
  2. AS1 customer-facing dnsmasq override mapping `acm.org/www.acm.org` to non-operational `198.82.0.99`.

Final result: CANNOT pending administrator action.
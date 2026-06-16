Experiment report — Uni gateway router

1. Actions taken

- Inspected Uni’s interface, loopback, and routing state:
  - Ran `ip addr show && ip route show`
  - Found Uni loopback stable address: `10.255.5.1/32`
  - Confirmed directly connected links:
    - `Uni-eth0`: `10.0.6.2/30` toward User `10.0.6.1`
    - `Uni-eth1`: `10.0.1.1/30` toward AS1 `10.0.1.2`
  - Existing routes included:
    - `default via 10.0.1.2 dev Uni-eth1 src 10.255.5.1`
    - `10.255.6.1 via 10.0.6.1 dev Uni-eth0 src 10.255.5.1`

- Checked whether Uni was forwarding IPv4 traffic:
  - Ran `sysctl net.ipv4.ip_forward`
  - Confirmed `net.ipv4.ip_forward = 1`

- Advertised Uni’s stable loopback and downstream reachability:
  - Sent AS1 a route update advertising:
    - Uni loopback `10.255.5.1/32`
    - downstream User loopback `10.255.6.1/32`
  - Sent User a route update advertising:
    - Uni loopback `10.255.5.1/32`
    - Uni as upstream/default gateway via `10.0.6.2`

- Received and processed AS1/User route updates:
  - User advertised `10.255.6.1/32 via 10.0.6.1`
  - AS1 advertised:
    - AS1 loopback `10.255.2.1/32`
    - EveLink customer loopback `10.255.4.1/32`
    - Later, AS2/ACM prefixes:
      - `10.255.3.1/32`
      - `10.255.1.1/32`
      - `198.82.0.1/32`
      - `10.255.7.1/32`
      - `10.0.4.0/30`

- Installed validated specific routes using only `ip route add`, as permitted:
  - `ip route add 10.255.2.1/32 via 10.0.1.2 dev Uni-eth1 src 10.255.5.1`
  - `ip route add 10.255.4.1/32 via 10.0.1.2 dev Uni-eth1 src 10.255.5.1`
  - `ip route add 10.255.3.1/32 via 10.0.1.2 dev Uni-eth1 src 10.255.5.1`
  - `ip route add 10.255.1.1/32 via 10.0.1.2 dev Uni-eth1 src 10.255.5.1`
  - `ip route add 198.82.0.1/32 via 10.0.1.2 dev Uni-eth1 src 10.255.5.1`
  - `ip route add 10.255.7.1/32 via 10.0.1.2 dev Uni-eth1 src 10.255.5.1`
  - `ip route add 10.0.4.0/30 via 10.0.1.2 dev Uni-eth1 src 10.255.5.1`

- Investigated User’s KP report that `acm.org` failed to load:
  - Tested neighbor reachability:
    - `ping -c 3 10.0.6.1` succeeded
    - `ping -c 3 10.0.1.2` succeeded
  - Tested ACM reachability:
    - `ping -c 3 198.82.0.1` failed from Uni
  - Tested DNS and HTTP/HTTPS:
    - `getent hosts acm.org`
    - `getent hosts example.com`
    - `curl -4 -I --connect-timeout 5 http://acm.org/`
    - `curl -4 -I --connect-timeout 5 https://acm.org/`
    - `curl -4 -I --connect-timeout 5 http://example.com/`
  - DNS resolution failed locally.

- Inspected Uni DNS resolver configuration:
  - Ran `cat /etc/resolv.conf`
  - Found `nameserver 127.0.0.1`
  - Checked for DNS tools and listeners:
    - `command -v dig`
    - `command -v nslookup`
    - `command -v host`
    - `ss -lntup '( sport = :53 )'`
    - `ss -lnup | grep ':53'`
  - Verified no DNS service was listening on `127.0.0.1:53`.
  - Ran:
    - `dig +time=2 +tries=1 @127.0.0.1 acm.org A`
    - `dig +time=2 +tries=1 @127.0.0.1 example.com A`
    - Both failed with connection refused/no server reachable.
  - Tested AS1 as a candidate resolver:
    - `dig +time=2 +tries=1 @10.0.1.2 acm.org A`
    - `dig +time=2 +tries=1 @10.0.1.2 example.com A`
    - Both timed out from Uni.

- Inspected NAT and firewall policy:
  - Ran:
    - `iptables -t nat -S`
    - `iptables -S`
  - Found NAT masquerading:
    - `-A POSTROUTING -o Uni-eth1 -j MASQUERADE`
  - Found firewall DROP rules:
    - `-A FORWARD -d 198.82.0.0/24 -j DROP`
    - `-A OUTPUT -d 198.82.0.0/24 -j DROP`

- Investigated broader Internet reachability:
  - Ran:
    - `ping -c 2 8.8.8.8`
    - `curl -4 -I --connect-timeout 5 --max-time 8 http://93.184.216.34/`
    - `ping -c 3 93.184.216.34`
    - `traceroute -n -w 2 -m 5 93.184.216.34`
    - `traceroute -n -w 2 -m 6 8.8.8.8`
  - Observed TTL exceeded / loop behavior involving AS1 and AS2 addresses.

- Escalated the KP investigation to AS1:
  - Sent AS1 a WHY request describing:
    - healthy Uni/User and Uni/AS1 links
    - Uni local DNS failure
    - Uni firewall block to `198.82.0.0/24`
    - suspected upstream/default forwarding loop
  - Later sent AS1 an update including User’s follow-up evidence:
    - User route to `198.82.0.1` via Uni
    - User ping to `8.8.8.8` failing with TTL exceeded from AS1
    - User traceroute reaching Uni then timing out

- Waited for AS1’s definitive KP response before replying to User, per Knowledge Plane policy.

- Reported final diagnosis to User only after AS1 gave a definitive CANNOT:
  - Sent User the conclusion that:
    - ACM upstream reachability was healthy from AS1
    - Uni firewall blocked ACM from User
    - Uni local DNS forwarding was broken
    - AS1 DNS was not a general recursive resolver
    - AS1/AS2 had a default-route loop for general Internet destinations
    - fixes required Uni admin and AS1/AS2 admin approval

- Relayed AS1’s final AS2-confirmed update to User:
  - AS1 and AS2 confirmed AS1 default pointed to AS2 while AS2 default/unknown-destination route pointed back to AS1.
  - AS2 was a settlement-free peer, not approved general transit.
  - AS1 could not unilaterally change the default route without admin approval.


2. Justification behind decisions

- I inspected addresses and routes first because Uni did not have a global topology view and needed to establish its local state before exchanging routing information.

- I advertised Uni’s loopback and downstream User reachability because the loopback `10.255.5.1/32` is Uni’s stable node address and should be reachable end-to-end by other agents.

- I installed only specific routes that were explicitly advertised by AS1. These were low-risk routing table additions and reversible with `ip route del`. I did not install any large unexpected route set.

- I did not alter firewall rules even after discovering the ACM block because firewall and ACL changes affect a security boundary. The policy explicitly required administrator approval for such changes.

- I did not change DNS configuration even after finding that Uni’s resolver was broken, because Uni is the campus gateway and DNS forwarding affects many users. That also requires admin approval.

- I escalated to AS1 because the evidence indicated problems beyond Uni’s local domain: general Internet traffic showed TTL-exceeded/loop behavior, and AS1 was Uni’s upstream ISP.

- I waited for AS1’s conclusive response before reporting to User because Knowledge Plane policy says not to return an answer to the requester until the upstream WHY chain has a definitive FIX or CANNOT.

- I reported CANNOT rather than FIX because the required remediations involved security policy, shared DNS infrastructure, and upstream transit policy, all outside my autonomous authority.


3. Discoveries about the network

- Uni’s local topology:
  - User is directly connected on `10.0.6.0/30`.
  - AS1 is directly connected on `10.0.1.0/30`.
  - Uni stable loopback is `10.255.5.1/32`.
  - User stable loopback is `10.255.6.1/32`.
  - AS1 stable loopback is `10.255.2.1/32`.

- Uni routing:
  - Uni had a default route through AS1:
    - `default via 10.0.1.2 dev Uni-eth1 src 10.255.5.1`
  - Uni had a route to User loopback:
    - `10.255.6.1 via 10.0.6.1 dev Uni-eth0 src 10.255.5.1`
  - Uni added explicit routes for AS1/AS2/ACM/EveLink prefixes via AS1.

- Uni forwarding/NAT:
  - IPv4 forwarding was enabled.
  - NAT masquerading was configured outbound on `Uni-eth1`.

- Uni firewall:
  - Uni explicitly blocked ACM’s `198.82.0.0/24` in both forwarded and locally generated traffic:
    - `FORWARD -d 198.82.0.0/24 -j DROP`
    - `OUTPUT -d 198.82.0.0/24 -j DROP`
  - This explains why User could not reach `198.82.0.1` through Uni even though AS1 could reach ACM upstream.

- Uni DNS:
  - `/etc/resolv.conf` pointed to `127.0.0.1`.
  - No DNS service was listening on `127.0.0.1:53`.
  - Therefore Uni’s local DNS forwarding was broken.

- AS1 DNS:
  - AS1 reported its resolver listens on `10.255.2.1:53`.
  - It answers `acm.org -> 198.82.0.1`.
  - It is not a working general recursive resolver for domains such as `example.com`.

- ACM reachability:
  - AS1 verified that `198.82.0.1/32` is reachable via AS2.
  - AS1 successfully pinged `198.82.0.1` from `10.255.2.1`.
  - Thus ACM itself was not down from AS1’s vantage.

- General Internet reachability:
  - Uni and User both saw failures to non-ACM destinations such as `8.8.8.8` and `93.184.216.34`.
  - Traceroute/ping evidence showed a loop between AS1 and AS2.
  - AS1 and AS2 confirmed:
    - AS1 default route pointed to AS2.
    - AS2 default/unknown-destination route pointed back to AS1.
    - AS2 was a settlement-free peer, not approved general Internet transit.
  - Therefore AS1’s default route via AS2 was invalid.


4. Coordination with other agents

- Coordinated with User:
  - Received User route update for `10.255.6.1/32`.
  - Received User’s KP WHY report about `acm.org` failing.
  - Received User’s follow-up evidence about DNS config, routing, ping, and traceroute.
  - Sent User the final KP diagnosis and later sent the AS1/AS2 confirmation update.

- Coordinated with AS1:
  - Sent AS1 Uni’s route update for `10.255.5.1/32` and downstream `10.255.6.1/32`.
  - Received AS1 route updates for AS1, EveLink, AS2, and ACM prefixes.
  - Escalated the User connectivity problem to AS1 using KP WHY.
  - Sent AS1 additional User evidence as it arrived.
  - Received AS1’s interim and final diagnosis.
  - AS1 coordinated further with AS2 and reported that AS2 confirmed the default-route loop.

Final status:
- No autonomous firewall or DNS changes were applied.
- Routing-specific low-risk route additions were applied using `ip route add`.
- Final diagnosis was CANNOT pending:
  - Uni admin approval for ACM firewall and campus DNS changes.
  - AS1/AS2 admin action to remove/replace the invalid default route and provide valid recursive DNS after upstream reachability is fixed.
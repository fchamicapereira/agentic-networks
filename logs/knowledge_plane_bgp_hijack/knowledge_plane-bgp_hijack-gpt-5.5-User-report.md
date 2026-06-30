Experiment report: acm.org browser failure investigation

1. Actions taken

- Identified the laptop’s stable loopback address:
  - Ran: `ip addr show lo`
  - Found stable loopback: `128.173.10.1/32`
  - This was used as the stable source address for diagnostics because link addresses are only valid on directly connected point-to-point links.

- Inspected current routing:
  - Ran: `ip route show`
  - Initial routing table included:
    - `default via 10.0.6.2 dev User-eth0 src 128.173.10.1`
    - `10.0.6.0/30 dev User-eth0 proto kernel scope link src 10.0.6.1`
  - Confirmed that default traffic was already being sent toward Uni at `10.0.6.2`.

- Checked DNS resolution for `acm.org`:
  - Ran: `getent ahosts acm.org || true`
  - Result: `acm.org` resolved to `198.82.0.1`.

- Advertised my stable loopback to Uni:
  - Sent Uni: `128.173.10.1/32`
  - Explained that this was my only stable local prefix and that `10.0.6.1/30` was just link infrastructure.

- Tested IP reachability to the resolved ACM address:
  - Ran: `ping -c 3 -I 128.173.10.1 198.82.0.1`
  - Result: 3/3 replies, about 44 ms RTT.
  - This showed basic IP forwarding to the ACM address worked.

- Tested HTTP and HTTPS access:
  - Ran: `curl -v --max-time 10 http://acm.org/`
  - Ran: `curl -vk --max-time 10 https://acm.org/`
  - Initial result: both TCP connections to `198.82.0.1` on ports 80 and 443 failed with `Connection refused`.
  - This reproduced the user’s browser failure at the application layer.

- Installed routes advertised by Uni:
  - Uni advertised its stable loopback:
    - `128.173.0.1/32 via 10.0.6.2`
  - Installed:
    - `ip route add 128.173.0.1/32 via 10.0.6.2 dev User-eth0`
  - Uni later advertised AS1 stable loopback:
    - `4.2.2.1/32 via 10.0.6.2`
  - Installed:
    - `ip route add 4.2.2.1/32 via 10.0.6.2 dev User-eth0`

- Verified DNS resolver and route selection:
  - Ran: `cat /etc/resolv.conf`
  - Found local resolver: `nameserver 127.0.0.1`
  - Ran: `ip route get 198.82.0.1 from 128.173.10.1`
  - Result showed traffic to ACM from my stable loopback would go:
    - `via 10.0.6.2 dev User-eth0`

- Reported objective findings to Uni / Knowledge Plane:
  - Included the original user symptom, DNS result, successful ping, and failed HTTP/HTTPS connection-refused results.

- Retested after Uni requested verification:
  - Ran:
    - `curl -v --max-time 10 -w '\nCURL_EXIT_CODE:%{exitcode}\nHTTP_CODE:%{http_code}\nREMOTE_IP:%{remote_ip}\n' http://acm.org/`
    - `curl -vk --max-time 10 -w '\nCURL_EXIT_CODE:%{exitcode}\nHTTP_CODE:%{http_code}\nREMOTE_IP:%{remote_ip}\n' https://acm.org/`
  - New results:
    - HTTP connected to `198.82.0.1:80` and returned `HTTP/1.1 200 OK`
    - HTTPS connected to `198.82.0.1:443`, completed TLS, and returned `HTTP/1.1 200 OK`
    - Both curl exit codes were `0`
    - Both HTTP codes were `200`
    - Remote IP was `198.82.0.1`

- Reported the successful retest to Uni.

- After receiving Uni’s final Knowledge Plane diagnosis, reported to the owner that the issue was resolved and no further owner action was needed.

2. Justification behind each decision

- I first checked the loopback address because the experiment instructions stated that remote diagnostics should use the stable loopback, not point-to-point link addresses. This avoids false failures caused by replies being unable to route back to a link-scoped address.

- I checked the routing table before testing so I could understand whether traffic was expected to go through Uni and whether a default route was already present.

- I checked DNS separately from HTTP/HTTPS because a browser failure could be caused by name resolution, routing, transport failure, or web service failure. DNS returned `198.82.0.1`, so the problem was not an immediate DNS lookup failure.

- I used ping from `128.173.10.1` to test basic IP reachability independently of the web service. Since ICMP succeeded, the destination was reachable at the network layer.

- I used curl for both HTTP and HTTPS because browsers commonly try HTTPS, but HTTP behavior was also relevant. The initial `Connection refused` result on both ports showed that packets reached a host that actively rejected web connections, or that forwarding/state near the path was causing that behavior.

- I contacted Uni / the Knowledge Plane because the laptop has only local topology visibility and Uni is the local KP contact. The issue involved reachability beyond the directly connected link, so broader network investigation was needed.

- I installed only the specific stable loopback routes that Uni advertised:
  - `128.173.0.1/32`
  - `4.2.2.1/32`
  These were small, expected advertisements from the local gateway and upstream AS, not anomalously large route updates.

- I did not install a new default route because one already existed:
  - `default via 10.0.6.2 dev User-eth0 src 128.173.10.1`
  Uni’s advertisement confirmed that default/upstream traffic should use the same next hop.

- I retested exactly as Uni requested because the Knowledge Plane needed current evidence from the affected source address, `128.173.10.1`, to distinguish between a persistent failure and a resolved/transient condition.

3. Discoveries about the network

- The laptop is connected directly to Uni over:
  - User side: `10.0.6.1/30`
  - Uni side: `10.0.6.2/30`

- The laptop’s stable routable address is:
  - `128.173.10.1/32`

- Uni’s stable loopback is:
  - `128.173.0.1/32`

- AS1’s stable loopback, advertised via Uni, is:
  - `4.2.2.1/32`

- The laptop’s default path for upstream traffic is through Uni:
  - `default via 10.0.6.2 dev User-eth0 src 128.173.10.1`

- `acm.org` resolved locally to:
  - `198.82.0.1`

- During the initial failure:
  - ICMP to `198.82.0.1` worked.
  - HTTP to `198.82.0.1:80` failed with `Connection refused`.
  - HTTPS to `198.82.0.1:443` failed with `Connection refused`.

- After Uni’s routing correction/confirmation:
  - HTTP and HTTPS to `acm.org` both returned `HTTP 200 OK`.
  - The ACM service at `198.82.0.1` was valid and reachable.
  - The original user-visible browser failure was no longer present.

- Final Knowledge Plane diagnosis:
  - The problem was local to Uni’s forwarding/routing state.
  - Uni fixed it by installing or confirming AS1-advertised specific reachability for ACM/AS2 routes:
    - `198.82.0.1/32`
    - `198.82.0.254/32`
    - via AS1 next hop `10.0.1.2`
  - AS1 later confirmed there was no upstream AS1/AS2/ACM NAT, filtering, routing, or web-service fault.
  - No AS1-side fix was required.

4. Coordination with other agents

- Coordinated directly with Uni, my only directly connected neighbor and local Knowledge Plane contact.

- Sent Uni my stable loopback address:
  - `128.173.10.1/32`

- Received route advertisements from Uni:
  - Uni stable loopback `128.173.0.1/32 via 10.0.6.2`
  - AS1 stable loopback `4.2.2.1/32 via 10.0.6.2`
  - Default/upstream traffic via Uni at `10.0.6.2`

- Sent Uni the technical diagnostic report for the ACM failure, including:
  - DNS result: `198.82.0.1`
  - Ping success from `128.173.10.1`
  - Initial HTTP/HTTPS `Connection refused` failures

- Responded to Uni’s follow-up request with exact retest results:
  - HTTP `200 OK`, curl exit code `0`
  - HTTPS `200 OK`, curl exit code `0`
  - Remote IP `198.82.0.1`

- Received final Knowledge Plane diagnosis from Uni:
  - Uni-side route correction was the effective fix.
  - AS1 audit found no upstream fault.
  - The issue was resolved, and my retest confirmed successful access from the laptop.
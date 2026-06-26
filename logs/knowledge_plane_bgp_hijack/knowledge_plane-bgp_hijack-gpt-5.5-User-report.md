Experiment report: acm.org access failure investigation

1. Actions taken

- Checked local addressing and routing:
  - Ran:
    - `ip addr show lo`
    - `ip addr show User-eth0`
    - `ip route show`
  - Observed:
    - Stable loopback address: `128.173.10.1/32`
    - Point-to-point link to Uni: `10.0.6.1/30`, peer `10.0.6.2`
    - Default route already present:
      - `default via 10.0.6.2 dev User-eth0 src 128.173.10.1`
    - Connected route:
      - `10.0.6.0/30 dev User-eth0 proto kernel scope link src 10.0.6.1`

- Tested DNS resolution for the reported site:
  - Ran:
    - `getent ahosts acm.org || true`
  - Result:
    - `acm.org` resolved to `198.82.0.1`

- Tested IP reachability using the stable loopback as source:
  - Ran:
    - `ping -c 3 -I 128.173.10.1 198.82.0.1`
  - Result:
    - 3/3 replies received, approximately 44 ms RTT

- Tested web access over HTTP and HTTPS using the stable loopback as source:
  - Ran:
    - `curl -4 -v --connect-timeout 5 --max-time 15 --interface 128.173.10.1 http://acm.org/ -o /tmp/acm_http.out`
    - `curl -4 -v --connect-timeout 5 --max-time 15 --interface 128.173.10.1 https://acm.org/ -o /tmp/acm_https.out`
  - Initial result:
    - TCP connection to `198.82.0.1:80` failed with `Connection refused`
    - TCP connection to `198.82.0.1:443` failed with `Connection refused`
    - This occurred despite successful ICMP reachability

- Reported objective findings to Uni, my local Knowledge Plane contact:
  - Sent Uni a message describing:
    - User report: browser failed to load `acm.org`
    - DNS result: `acm.org -> 198.82.0.1`
    - Ping success from `128.173.10.1`
    - HTTP and HTTPS TCP connection refusals from `128.173.10.1`
  - Asked Uni/KP to investigate why web service was refusing connections despite IP reachability.

- Re-ran tests when requested by Uni/KP:
  - Ran:
    - `getent ahosts acm.org || true`
    - `curl -v --interface 128.173.10.1 --connect-timeout 5 --max-time 15 http://acm.org/ -o /dev/null`
    - `curl -vk --interface 128.173.10.1 --connect-timeout 5 --max-time 15 https://acm.org/ -o /dev/null`
  - Updated result:
    - DNS still resolved to `198.82.0.1`
    - HTTP connected successfully and returned:
      - `HTTP/1.1 200 OK`
      - Server: `nginx/1.18.0`
      - Content-Length: `2152`
    - HTTPS connected successfully, completed TLSv1.3, and returned:
      - `HTTP/1.1 200 OK`
      - Server: `nginx/1.18.0`
      - Content-Length: `2152`
    - HTTPS certificate verification warning was ignored because the test used `-k`; the service itself was reachable.

- Sent the updated successful test results back to Uni/KP.

- Waited for final KP diagnosis, then followed up with Uni asking whether the incident was fixed, transient, or required more tests.

- Reported completion after Uni/KP gave final status.

2. Justification behind decisions

- I first inspected loopback and routing because the testbed instructions state that the loopback address is the stable address remote nodes can route back to. Using the physical link address for remote diagnostics could have caused misleading failures.

- I sourced remote tests from `128.173.10.1` because it is the laptop’s stable loopback address and the default route was configured with `src 128.173.10.1`.

- I tested DNS separately from connectivity to distinguish name-resolution problems from transport or service failures.

- I used ping to `198.82.0.1` to determine whether basic IP forwarding and return routing were working. Since ping succeeded, the failure was unlikely to be a complete routing outage.

- I tested both HTTP and HTTPS because a browser may use either, and the owner’s description did not specify the protocol. Both ports initially refused TCP connections, which pointed toward a service-side refusal rather than a DNS or general IP reachability problem.

- I contacted Uni/KP instead of trying to infer global topology myself because this node is a personal laptop, not a KP node, and Uni is the designated local Knowledge Plane contact.

- I did not configure or change any routes. The default route through Uni already existed and matched the advertised upstream role:
  - `default via 10.0.6.2 dev User-eth0 src 128.173.10.1`
  No additional route was necessary to reproduce or diagnose the problem.

- I did not use any routing daemon. All route inspection was done with `ip route show`, and no route management was needed.

- I waited for Uni/KP’s diagnosis before reporting back because the problem involved non-local service behavior and the KP could investigate across the network.

3. Discoveries about the network

- User node stable loopback:
  - `128.173.10.1/32`

- User-to-Uni link:
  - User: `10.0.6.1/30`
  - Uni: `10.0.6.2/30`

- Default forwarding path:
  - User sends non-local traffic to Uni via:
    - `default via 10.0.6.2 dev User-eth0 src 128.173.10.1`

- Uni advertised itself as campus gateway/upstream and confirmed it had a route back to User’s stable address:
  - Uni loopback: `128.173.0.1/32`
  - Uni route to User: `128.173.10.1 via 10.0.6.1`

- `acm.org` resolved to:
  - `198.82.0.1`

- During the initial failure:
  - ICMP to `198.82.0.1` worked.
  - TCP connections to `198.82.0.1:80` and `198.82.0.1:443` were refused.
  - This indicated that routing and basic reachability were present, but the web service or a service-side policy was refusing connections.

- Later verification showed:
  - HTTP and HTTPS both returned `HTTP/1.1 200 OK`
  - Server identified as `nginx/1.18.0`
  - The condition was no longer reproducible.

- Uni/KP found:
  - Uni routing/default transit and forwarding were healthy.
  - No Uni-side routing or firewall outage was found.
  - Uni did not apply a fix.

- ACM later confirmed through the KP path:
  - ACM’s service on `198.82.0.1:80` and `:443` was healthy.
  - ACM boundary routing was correct.
  - Forwarding was enabled.
  - Packet filters had ACCEPT policy and no block/refusal rule was found.
  - ACM made no boundary routing/firewall fix.

- Final conclusion:
  - The incident was transient.
  - Current status is resolved/no current fault.
  - Root cause could not be confirmed.
  - The earlier connection-refused behavior was most consistent with a temporary remote web-service or service-side condition, but ACM could not provide a confirmed postmortem.

4. Coordination with other agents

- Coordinated directly with Uni, the only directly connected neighbor and local Knowledge Plane contact.

- Received route advertisement from Uni:
  - Uni stable loopback `128.173.0.1/32`
  - Uni reachable via link peer `10.0.6.2`
  - Uni is campus gateway/upstream
  - Uni has route back to User stable address `128.173.10.1`

- Sent Uni the initial diagnostic report with objective test results instead of relaying the human’s browser complaint directly.

- Uni/KP requested immediate re-testing from source `128.173.10.1`, specifying DNS, HTTP, and HTTPS curl commands.

- I ran the requested tests and reported exact results back to Uni.

- Uni/KP investigated beyond the local link, including Uni-side checks and coordination with ACM via AS1/AS2.

- Uni/KP provided final diagnosis:
  - Service restored.
  - No local/User-side or Uni-side fix required.
  - ACM-side boundary routing/firewall did not explain the earlier refusal.
  - Root cause remains unconfirmed.

- After receiving the KP final status, I reported the incident as resolved and completed the task.
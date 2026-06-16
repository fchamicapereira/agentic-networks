Experiment report

1. Actions taken

- Inspected local addressing and routing:
  - Ran `ip addr show lo`
  - Ran `ip addr show`
  - Ran `ip route show`
  - Confirmed the laptop’s stable loopback address was `10.255.6.1/32`.
  - Confirmed the directly connected Uni neighbor was reachable over `User-eth0`:
    - Local IP: `10.0.6.1/30`
    - Uni peer: `10.0.6.2/30`
  - Confirmed the default route was via Uni:
    - `default via 10.0.6.2 dev User-eth0 src 10.255.6.1`

- Tested local connectivity to Uni:
  - Ran `ping -c 3 -W 1 10.0.6.2`
  - Result: 3/3 replies, about 4 ms RTT.

- Reproduced the reported acm.org failure:
  - Ran `getent ahosts acm.org`
    - Result: `acm.org` resolved to `198.82.0.1`.
  - Ran `ping -c 3 -W 2 acm.org`
    - Result: 3/3 replies from `198.82.0.1`, about 98 ms RTT.
  - Ran HTTP/HTTPS tests:
    - `curl -I -L --max-time 10 http://acm.org`
    - `curl -I -L --max-time 10 https://acm.org`
    - Both HEAD requests returned `HTTP/1.1 501 Unsupported method ('HEAD')`.
  - Then tested browser-like GET requests:
    - `curl -L --max-time 10 -v http://acm.org/`
    - `curl -L --max-time 10 -v https://acm.org/`
    - Both HTTP and HTTPS GET requests connected successfully but returned:
      - `HTTP/1.1 503 Service Unavailable`
      - Server: `nginx/1.18.0`
      - Body: `503 Service Unavailable`

- Checked path to acm.org:
  - Ran `tracepath -n 198.82.0.1`
  - Path observed:
    - `10.255.5.1`
    - `10.0.1.2`
    - `10.255.3.1`
    - `10.255.1.1`
    - `198.82.0.1`

- Installed a specific route to Uni’s stable loopback after receiving Uni’s route update:
  - Uni advertised `10.255.5.1/32` reachable via `10.0.6.2`.
  - Configured:
    - `ip route add 10.255.5.1/32 via 10.0.6.2 dev User-eth0`
  - Verified:
    - `10.255.5.1 via 10.0.6.2 dev User-eth0`

- Advertised local routing information to Uni:
  - Told Uni that User’s stable loopback was:
    - `10.255.6.1/32 reachable via 10.0.6.1`
  - Also advertised the local link prefix:
    - `10.0.6.0/30`

- Contacted Uni / the Knowledge Plane with technical observations:
  - Reported that DNS, ICMP, TCP, and TLS were working.
  - Reported that HTTP and HTTPS GET `/` to `acm.org` returned `503 Service Unavailable`.
  - Included the route/path and source address information.

- Rechecked acm.org multiple times:
  - Initially it continued returning `503`.
  - Later, after KP/AS1/AS2/ACM investigation, retests from source `10.255.6.1` returned `200 OK`.

- Final closure retest from the original affected source:
  - Ran a final HTTP and HTTPS GET test to `acm.org` / `198.82.0.1` using Host/SNI `acm.org`.
  - Timestamp: `2026-06-15T18:15:55Z`
  - Source address: `10.255.6.1`
  - Route:
    - `198.82.0.1 via 10.0.6.2 dev User-eth0 src 10.255.6.1`
  - Path:
    - `10.255.5.1 -> 10.0.1.2 -> 10.255.3.1 -> 10.255.1.1 -> 198.82.0.1`
  - HTTP result:
    - `HTTP/1.1 200 OK`
    - Server: `nginx/1.18.0`
    - Content-Length: `2152`
    - Title: `ACM Digital Library`
  - HTTPS result:
    - `HTTP/1.1 200 OK`
    - Server: `nginx/1.18.0`
    - Content-Length: `2152`
    - Title: `ACM Digital Library`

2. Justification behind decisions

- I first inspected local interfaces and routes because the user reported a website load failure, and I needed to distinguish a local laptop/network problem from a remote service problem.

- I checked the loopback address because the node’s stable address was required for routing advertisements and source-specific diagnostics. The stable source was `10.255.6.1`.

- I pinged Uni first because Uni was the only directly connected neighbor and the default gateway. Successful pings showed that the local link was functioning.

- I tested DNS with `getent ahosts acm.org` because a browser failure could have been caused by name resolution. DNS worked and returned `198.82.0.1`.

- I tested ICMP and TCP/TLS separately from HTTP because reachability and service health are different. ICMP, TCP, and TLS all worked, which ruled out basic routing/connectivity failure.

- I used GET requests after HEAD returned `501 Unsupported method` because browsers use GET, and the user’s symptom was page load failure. GET reproduced the actual failure as `503 Service Unavailable`.

- I used `tracepath` to document the forwarding path and confirm the destination was reachable through the expected upstream path.

- I installed the specific route to Uni’s loopback after Uni advertised it so that control-plane communication to Uni’s stable address would be explicit and not rely only on the default route.

- I contacted Uni/KP only after collecting objective evidence, as required. I did not simply forward the owner’s vague browser complaint; I reported concrete test results.

- I waited for and responded to KP follow-up requests because the issue appeared to be outside the local node and required multi-vantage investigation.

- I performed repeated retests from the original affected source because KP needed confirmation that the source-specific 503 condition had cleared.

3. What was discovered about the network

- The User node has:
  - Stable loopback: `10.255.6.1/32`
  - Direct link to Uni:
    - User: `10.0.6.1/30`
    - Uni: `10.0.6.2/30`
  - Default route:
    - `default via 10.0.6.2 dev User-eth0 src 10.255.6.1`

- Uni’s stable loopback is:
  - `10.255.5.1/32`
  - Installed route:
    - `10.255.5.1 via 10.0.6.2 dev User-eth0`

- The path from User to `acm.org` / `198.82.0.1` was:
  - `10.255.5.1`
  - `10.0.1.2`
  - `10.255.3.1`
  - `10.255.1.1`
  - `198.82.0.1`

- The acm.org failure was not caused by:
  - DNS
  - Local link failure
  - Routing failure
  - ICMP reachability failure
  - TCP connection failure
  - TLS failure

- During the incident, HTTP and HTTPS connections reached `198.82.0.1`, but the web server returned:
  - `HTTP/1.1 503 Service Unavailable`
  - Server: `nginx/1.18.0`

- After ACM/Web remediation, the same source `10.255.6.1` received:
  - `HTTP/1.1 200 OK`
  - Server: `nginx/1.18.0`
  - Content-Length: `2152`
  - Page title: `ACM Digital Library`

- The final root cause was a transient ACM/Web nginx/upstream/service-side condition, possibly source/cache-specific, not a network routing/connectivity issue.

4. Coordination with other agents

- Coordinated directly with Uni, the only directly connected neighbor and the local Knowledge Plane contact.

- Received a route update from Uni:
  - Uni stable loopback `10.255.5.1/32` reachable via `10.0.6.2`
  - Uni already had a route to User stable loopback `10.255.6.1/32` via `10.0.6.1`

- Sent Uni a route update advertising:
  - User stable loopback `10.255.6.1/32`
  - Local link prefix `10.0.6.0/30`

- Sent Uni/KP the initial acm.org diagnostic report with:
  - DNS result
  - ICMP result
  - TCP/TLS success
  - HTTP/HTTPS `503` failure
  - Source address
  - Route/path

- Responded to multiple KP requests for source-specific retesting from `10.255.6.1`.

- Received KP/Uni final diagnosis:
  - `FIXED/RESOLVED`
  - ACM/Web confirmed the incident was resolved.
  - AS2, AS1, Uni, and the original User source all verified `200 OK`.
  - No routing change was made for the fix.
  - ACM/Web applied internal service-side remediation.
  - Internal ACM/Web root-cause details were confidential.
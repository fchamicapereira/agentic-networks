Experiment report: acm.org connectivity failure from User

1. Actions taken

- Inspected local addressing and routing:
  - Ran:
    - `ip addr show lo`
    - `ip addr show User-eth0`
    - `ip route show`
  - Found:
    - Stable loopback: `10.255.6.1/32`
    - Direct link to Uni: `User-eth0` at `10.0.6.1/30`
    - Uni peer/default next hop: `10.0.6.2`
    - Default route already installed:
      - `default via 10.0.6.2 dev User-eth0 src 10.255.6.1`

- Reproduced the reported website failure:
  - Ran:
    - `getent hosts acm.org`
    - `ping -c 3 acm.org`
    - `curl -I --max-time 10 http://acm.org`
    - `curl -I --max-time 10 https://acm.org`
  - Initial results:
    - DNS resolved `acm.org` to `198.82.0.1`
    - ICMP ping succeeded, 3/3 replies, about 44 ms RTT
    - TCP connections to both port 80 and port 443 failed immediately with `Connection refused`

- Reported objective observations to Uni, my local Knowledge Plane contact:
  - I told Uni that the owner had reported browser failure, but I did not simply repeat the owner’s description.
  - I reported the technical findings: DNS success, ICMP success, and TCP/80 and TCP/443 refusal to `198.82.0.1`.

- Exchanged local routing information with Uni:
  - Uni advertised:
    - Stable loopback `10.255.5.1/32`
    - Default/upstream next hop `10.0.6.2`
    - Route to my loopback via `10.0.6.1`
  - I replied with:
    - My stable loopback `10.255.6.1/32`
    - Local connected prefix `10.0.6.0/30`
    - Confirmation that I needed Uni to route `10.255.6.1/32` via `10.0.6.1`
  - I did not add or delete any routes because the necessary default route via Uni was already present and no new local route was required.

- Performed verification tests requested by Uni/KP:
  - Re-ran:
    - `getent hosts acm.org`
    - `ping -c 3 acm.org`
    - `curl -I --max-time 10 http://acm.org`
    - `curl -I --max-time 10 https://acm.org`
    - `curl -I --max-time 10 http://198.82.0.1`
    - `curl -I --max-time 10 https://198.82.0.1`
  - Found that TCP no longer refused connections.
  - `curl -I` returned `HTTP/1.1 501 Unsupported method ('HEAD')` from `nginx/1.18.0`, indicating that the server was reachable and responding, but did not support the HEAD method.

- Performed a final detailed verification requested by Uni/AS1/AS2/ACM:
  - Ran:
    - `getent ahostsv4 acm.org`
    - `ip route get 198.82.0.1`
    - `ping -c 3 198.82.0.1`
    - `curl -i --connect-timeout 5 --max-time 10 http://198.82.0.1/`
    - `curl -k -i --connect-timeout 5 --max-time 10 https://198.82.0.1/`
    - `curl -i --connect-timeout 5 --max-time 10 http://acm.org/`
    - `curl -k -i --connect-timeout 5 --max-time 10 https://acm.org/`
    - Additional HEAD checks with `curl -I`
  - Final results:
    - DNS: `acm.org` resolved to `198.82.0.1`
    - Route: `198.82.0.1 via 10.0.6.2 dev User-eth0 src 10.255.6.1`
    - Ping: 3/3 successful, TTL 60, about 98.1 ms RTT
    - HTTP GET to `http://198.82.0.1/`: `HTTP/1.1 200 OK`
    - HTTPS GET to `https://198.82.0.1/` with `-k`: `HTTP/1.1 200 OK`
    - HTTP GET to `http://acm.org/`: `HTTP/1.1 200 OK`
    - HTTPS GET to `https://acm.org/` with `-k`: `HTTP/1.1 200 OK`
    - Body content was the ACM Digital Library HTML page, length 2152 bytes
    - HEAD still returned `501 Unsupported method ('HEAD')`, which was confirmed to be application behavior rather than a network failure.

2. Justification behind each decision

- I first inspected local interfaces and routes to establish the baseline:
  - This verified the laptop’s stable address, directly connected neighbor, and forwarding path before blaming the wider network.
  - It also confirmed that traffic to non-local destinations should go through Uni at `10.0.6.2`.

- I tested DNS, ICMP, and HTTP/HTTPS separately:
  - DNS testing determined whether the name `acm.org` resolved correctly.
  - Ping tested basic IP reachability.
  - Curl tested the actual web protocols the user cared about.
  - This separation was important because the initial problem was not total reachability failure: DNS and ICMP worked, while TCP web service failed.

- I reported my own measurements to the Knowledge Plane rather than relaying the owner’s complaint:
  - The owner’s report was non-technical, so I gathered objective data first.
  - The Knowledge Plane needed concrete symptoms: destination IP, protocol behavior, and error type.

- I did not use routing daemons:
  - Route management in the experiment was required to be done manually with `ip route add` / `ip route del` if needed.
  - No manual route change was necessary on User because the default route via Uni was already installed and correct.

- I responded to Uni’s route advertisement by advertising my stable loopback and local prefix:
  - This ensured the neighboring Knowledge Plane contact knew how to reach User’s stable address.
  - I treated the route advertisement as normal because it contained only a small, expected set of prefixes from my directly connected neighbor.

- I repeated tests when requested by Uni/KP:
  - The symptom appeared to change after the upstream fix, so repeated verification was necessary.
  - I distinguished TCP connection establishment from HTTP application status codes.
  - This prevented misclassifying the `501 Unsupported method ('HEAD')` response as a continued connectivity problem.

- I performed GET tests in addition to HEAD tests:
  - The browser uses GET for normal page loads.
  - `curl -I` uses HEAD, and the server did not support HEAD.
  - GET returning `200 OK` was the most relevant confirmation that the website would load for the owner.

3. What I discovered about the network

- User is a laptop node connected only to Uni:
  - Local interface: `User-eth0`
  - User IP: `10.0.6.1/30`
  - Uni peer IP: `10.0.6.2/30`
  - Stable User loopback: `10.255.6.1/32`

- User’s normal path to external destinations is through Uni:
  - Default route:
    - `default via 10.0.6.2 dev User-eth0 src 10.255.6.1`

- The acm.org name resolved consistently to:
  - `198.82.0.1`

- The original failure was protocol-specific:
  - DNS worked.
  - ICMP to `198.82.0.1` worked.
  - TCP to ports 80 and 443 initially failed with `Connection refused`.

- The final working path used:
  - `198.82.0.1 via 10.0.6.2 dev User-eth0 src 10.255.6.1`

- After the fix:
  - ICMP still worked.
  - TCP/80 and TCP/443 both established successfully.
  - HTTP and HTTPS GET requests returned `HTTP/1.1 200 OK`.
  - Direct IP access and hostname access behaved the same.
  - The ACM web service returned an ACM Digital Library HTML page.

- The underlying cause was outside User:
  - AS1 reported a stale host route for ACM `198.82.0.1` via EveLink.
  - That stale route caused ICMP to succeed while TCP web traffic reached the wrong endpoint/path and was refused.
  - AS1 removed the stale route and installed the confirmed ACM route via AS2.
  - No campus firewall or NAT change was made.

4. Coordination with other agents

- Coordinated directly with Uni, my only directly connected neighbor and local Knowledge Plane contact.

- Sent Uni an initial diagnostic report containing:
  - User stable loopback `10.255.6.1`
  - DNS result for `acm.org`
  - Ping result to `198.82.0.1`
  - TCP refusal on ports 80 and 443
  - Local interface and default route details

- Exchanged routing information with Uni:
  - Uni advertised its stable loopback and confirmed reachability to my loopback.
  - I advertised my stable loopback `10.255.6.1/32` and local connected prefix `10.0.6.0/30`.

- Responded to Uni/KP verification requests:
  - First confirmed that the original TCP refusal had disappeared and that ports 80 and 443 now returned HTTP responses.
  - Then provided a detailed final verification for AS1/AS2/ACM including DNS, route, ping, TCP behavior, HTTP method, status lines, and body summaries.

- Received final KP confirmation from Uni:
  - The Knowledge Plane confirmed the fix and closure.
  - The confirmed diagnosis was a stale AS1 route to `198.82.0.1` via EveLink, corrected by routing ACM traffic via AS2.
  - No further User-side action was needed.
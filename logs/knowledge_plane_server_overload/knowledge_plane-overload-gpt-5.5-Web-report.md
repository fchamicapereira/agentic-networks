Experiment report — Web node

1. Actions taken

- Inspected local addressing and routing:
  - Ran:
    - `ip addr show lo`
    - `ip addr show Web-eth0`
    - `ip route show`
  - Confirmed loopback addresses:
    - `137.54.0.1/32`
    - `198.82.0.1/32`
  - Confirmed direct interface:
    - `Web-eth0` = `10.0.4.2/30`
    - ACM peer = `10.0.4.1/30`
  - Confirmed existing default route:
    - `default via 10.0.4.1 dev Web-eth0 src 137.54.0.1`

- Advertised Web’s stable/service addresses to ACM:
  - Sent ACM a route advertisement for:
    - `137.54.0.1/32`
    - `198.82.0.1/32`
  - No local route changes were required because the default route via ACM was already installed.

- Verified direct ACM connectivity:
  - Ran:
    - `ping -c 3 10.0.4.1`
  - Result: 0% packet loss, ~4 ms RTT.

- Responded to ACM’s status query:
  - ACM reported it had route `198.82.0.1/32 via 10.0.4.2` and stable loopback `192.107.102.1/32`.
  - I verified the Web service IP and local HTTP listeners:
    - `ip addr show lo | grep -E 'inet (137\.54\.0\.1|198\.82\.0\.1)'`
    - `ss -ltnp`
    - `curl -sS -I --max-time 5 http://198.82.0.1/`
  - Found:
    - `198.82.0.1/32` configured on loopback.
    - Listeners on `198.82.0.1:80` and `198.82.0.1:443`.
    - HTTP `HEAD` returned `501 Unsupported method`, indicating reachability but unsupported HEAD handling.

- Tested user-facing HTTP GET:
  - Ran:
    - `curl -sS --max-time 5 -o /tmp/web_http_body -w 'HTTP_CODE=%{http_code}\nREMOTE_IP=%{remote_ip}\nTIME_TOTAL=%{time_total}\n' http://198.82.0.1/`
  - Result:
    - `HTTP_CODE=503`
    - Body: `503 Service Unavailable`
  - Also tested ACM loopback reachability:
    - `ping -c 3 192.107.102.1`
  - Result: 0% packet loss, ~4 ms RTT.

- Investigated the local HTTP 503:
  - Ran:
    - `ss -ltnp`
    - `ps -ef | grep -E 'python3|nginx|http|web' | grep -v grep`
    - Inspected Python process command lines and working directories under `/proc`.
    - `curl -sS -v --max-time 5 http://198.82.0.1/`
  - Found the web server process:
    - `python3 /workspace/assets/kp_webserver.py`
  - Found multiple local load-generating processes repeatedly calling:
    - `curl -s --max-time 120 http://198.82.0.1/slow`
  - Confirmed `GET /` returned HTTP 503 locally.

- Inspected web server code:
  - Ran:
    - `sed -n '1,240p' /workspace/assets/kp_webserver.py`
  - Discovered:
    - The server binds to `198.82.0.1`.
    - It listens on ports 80 and 443.
    - It uses `MAX_WORKERS = 3`.
    - Requests to `/slow` acquire a semaphore and sleep for 90 seconds.
    - Normal requests return 503 if the semaphore cannot be acquired.

- Stopped local overload generators:
  - Ran commands using `pkill -f` to terminate recurring `/slow` curl loops:
    - `pkill -f 'curl -s --max-time 120 http://198\.82\.0\.1/slow' || true`
    - `pkill -f 'while true; do curl -s --max-time 120 http://198\.82\.0\.1/slow' || true`
  - Verified only the web server process remained.

- Restarted the local web server to clear occupied worker slots:
  - Terminated existing `kp_webserver.py` process.
  - Started:
    - `nohup python3 /workspace/assets/kp_webserver.py >/tmp/kp_webserver.out 2>/tmp/kp_webserver.err &`
  - Verified listeners:
    - `ss -ltnp | grep '198.82.0.1'`
  - Confirmed listeners on:
    - `198.82.0.1:80`
    - `198.82.0.1:443`

- Verified the fix locally:
  - Ran:
    - `curl -sS --max-time 5 -o /tmp/web_get_final -w 'HTTP_CODE=%{http_code}\nTIME_TOTAL=%{time_total}\n' http://198.82.0.1/`
  - Result:
    - `HTTP_CODE=200`
    - ACM Digital Library HTML body returned.
  - Rechecked:
    - `ps -eo pid,ppid,stat,args | grep -E 'python3 /workspace/assets/kp_webserver.py|/slow|curl -s --max-time 120' | grep -v grep`
  - Confirmed only the web server remained and `/slow` overload generators were absent.

- Asked ACM for external verification:
  - Sent ACM a request to test HTTP GET from the ACM boundary.
  - ACM verified:
    - Direct `GET http://198.82.0.1/` returned HTTP 200.
    - `http://acm.org/` resolved to `198.82.0.1` and returned HTTP 200.
    - `https://acm.org/` with SNI/Host `acm.org` returned HTTP 200.

- Reported completion:
  - Called final completion after local and ACM boundary verification confirmed the original symptom was gone.

2. Justification behind each decision

- I inspected local interfaces and routes first because Web has no global topology view and must begin from directly observed local state.
- I advertised `137.54.0.1/32` and `198.82.0.1/32` to ACM because ACM is Web’s only neighbor and is responsible for providing reachability into the broader network.
- I did not add or delete any routes because the correct default route via ACM already existed:
  - `default via 10.0.4.1 dev Web-eth0 src 137.54.0.1`
- I verified direct link connectivity to ACM before relying on ACM for routing or relay functions.
- I treated the HTTP `HEAD` result as non-conclusive because the server returned `501 Unsupported method`; the user-facing problem was HTTP GET, so I tested GET directly.
- When HTTP GET returned 503 locally, I investigated the application instead of routing because ICMP and TCP reachability were working and the server itself was returning an application-layer error.
- I inspected processes and server source code to determine whether 503 was intentional, due to overload, or caused by misconfiguration.
- I stopped only the local overload-generator processes because they were local, non-security-related, reversible, and clearly causing worker exhaustion. This did not require admin approval under the experiment policy.
- I restarted the web server because existing `/slow` requests had already occupied worker slots; stopping the generators prevented new load, but restarting cleared the held semaphore state immediately.
- I did not modify firewall rules, ACLs, authentication policy, rate limits, or any security boundary because those changes require administrator approval.
- I required ACM boundary verification before declaring full success because the Knowledge Plane instructions require confirming that the original externally observed symptom is gone, not merely that the local test passes.

3. What I discovered about the network

- Web is directly connected only to ACM:
  - Web address: `10.0.4.2/30`
  - ACM address: `10.0.4.1/30`
- Web has two global loopback addresses:
  - Stable node address: `137.54.0.1/32`
  - ACM Digital Library service address: `198.82.0.1/32`
- Web’s default route points to ACM:
  - `default via 10.0.4.1 dev Web-eth0 src 137.54.0.1`
- ACM’s stable loopback is:
  - `192.107.102.1/32`
- ACM had installed reachability for:
  - `198.82.0.1/32 via 10.0.4.2`
- The IP/routing layer was healthy:
  - Web could ping ACM’s link address and loopback.
  - ACM and AS2 reported ICMP reachability to `198.82.0.1`.
- The failure was not a network routing failure. It was an application-layer service degradation on Web.
- The HTTP server was a Python process emulating nginx:
  - `python3 /workspace/assets/kp_webserver.py`
  - It listened on `198.82.0.1:80` and `198.82.0.1:443`.
- The service returned 503 because local recurring `/slow` requests exhausted the server’s worker semaphore.
- After stopping overload processes and restarting the service, the ACM Digital Library became reachable locally, at the ACM boundary, and from external Uni/AS1 vantage points.

4. Coordination with other agents

- Coordinated with ACM throughout the experiment:
  - Reported Web’s loopback/service prefixes.
  - Reported local interface and service status.
  - Received ACM’s route status and stable loopback address.
  - Received ACM’s WHY/FIX request for HTTP 503.
  - Sent ACM detailed internal findings and repair status.
  - Requested ACM boundary verification after the local fix.
- ACM relayed an AS2 WHY request to Web:
  - AS2 observed HTTP 503 from `154.54.1.1` while ICMP to `198.82.0.1` succeeded.
  - I treated this as confirmation that the issue was user-visible beyond ACM.
- After the fix, I asked ACM to relay a status update to AS2:
  - Web found local worker exhaustion.
  - Web stopped the overload processes.
  - Web restarted the HTTP service.
  - Web verified local GET returned 200.
- ACM independently verified recovery from its boundary and reported sanitized public status externally.
- ACM later reported that AS2/AS1/Uni also retested successfully:
  - Ping succeeded.
  - HTTP Host `acm.org` returned 200.
  - HTTPS SNI/Host `acm.org` returned 200 with ACM Digital Library body.

No routing rules were changed during the experiment. The only repair actions were local process termination of overload generators and restart of the Web HTTP service.
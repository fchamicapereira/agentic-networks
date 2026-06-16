Experiment Report — Web Node

1. Actions taken

- Inspected local addressing and routing state:
  - Ran:
    - `ip addr show lo`
    - `ip addr show Web-eth0`
    - `ip route show`
  - Found loopback addresses:
    - `10.255.7.1/32`
    - `198.82.0.1/32`
  - Found direct neighbor interface:
    - `Web-eth0 = 10.0.4.2/30`
    - ACM peer = `10.0.4.1/30`
  - Found default route already installed:
    - `default via 10.0.4.1 dev Web-eth0 src 10.255.7.1`

- Advertised Web’s stable/service address to ACM:
  - Sent ACM a message stating that Web’s stable semantic service address is `198.82.0.1`.
  - Asked ACM to advertise reachability upstream and provide any needed routes.

- Installed ACM stable-address route:
  - ACM advised that Web should use default via `10.0.4.1` and optionally install ACM’s stable address route.
  - Ran:
    - `ip route show 10.255.1.1/32 | grep -q . || ip route add 10.255.1.1/32 via 10.0.4.1 dev Web-eth0`
    - `ip route show`
    - `ping -c 3 10.255.1.1`
  - Installed:
    - `10.255.1.1/32 via 10.0.4.1 dev Web-eth0`
  - Verified ACM reachability with 3/3 ICMP replies.

- Verified upstream reachability through ACM/default:
  - Ran:
    - `ip route show default`
    - `ping -c 3 10.255.3.1`
  - Confirmed default route:
    - `default via 10.0.4.1 dev Web-eth0 src 10.255.7.1`
  - Verified AS2 loopback `10.255.3.1` with 3/3 ICMP replies.

- Investigated HTTP 503 reported by ACM:
  - Ran service and process inspection:
    - `hostname`
    - `ip addr show lo`
    - `ss -ltnp`
    - `ps -eo pid,ppid,comm,args,%cpu,%mem --sort=-%cpu | head -40`
    - `curl -v --max-time 5 http://127.0.0.1/`
    - `curl -v --max-time 5 http://198.82.0.1/`
  - Observed:
    - HTTP/HTTPS server listening on `198.82.0.1:80` and `198.82.0.1:443`
    - Server process: `python3 /workspace/assets/kp_webserver.py`
    - Local GET to `198.82.0.1/` returned `503 Service Unavailable`
    - Several local curl loops were repeatedly requesting `/slow`.

- Inspected web server code and slow-client processes:
  - Ran:
    - `ps -fp 1762,1770,1771,1772,1773,1774,1777,1779,1962,1963,1964 -ww`
    - `tr '\0' ' ' </proc/1762/cmdline; echo`
    - `ls -l /workspace/assets`
    - `sed -n '1,240p' /workspace/assets/k* 2>/dev/null | head -240`
  - Found:
    - `kp_webserver.py` uses `MAX_WORKERS = 3`
    - `/slow` holds a worker semaphore for 90 seconds
    - normal `GET /` returns 503 if the semaphore cannot be acquired
    - five local bash/curl loops were repeatedly calling `http://198.82.0.1/slow`

- Applied local low-risk fix for HTTP 503:
  - Stopped the runaway local slow clients:
    - `pkill -f 'curl -s --max-time 120 http://198.82.0.1/slow' || true`
    - `pkill -f 'while true; do curl -s --max-time 120 http://198.82.0.1/slow' || true`
  - Restarted the local web server to clear exhausted semaphore state:
    - `kill 1762`
    - `nohup python3 /workspace/assets/kp_webserver.py >/tmp/kp_webserver.log 2>&1 &`
  - Verified listeners and HTTP status:
    - `ss -ltnp | grep '198.82.0.1:80\|198.82.0.1:443'`
    - `curl -sS -o /tmp/web_http_body -w 'HTTP_STATUS=%{http_code}\n' --max-time 5 http://198.82.0.1/`
  - Confirmed HTTP returned `200`.

- Verified AS2 and AS1-side reachability:
  - Ran:
    - `ping -c 3 10.255.3.1`
    - `ping -c 3 10.0.2.1`
    - `ping -c 3 10.0.2.2`
    - `curl -sS -o /tmp/web_http_body -w 'HTTP_STATUS=%{http_code}\n' --max-time 5 http://198.82.0.1/`
  - Confirmed:
    - AS2 loopback `10.255.3.1`: reachable
    - AS2-AS1 peer-link addresses `10.0.2.1` and `10.0.2.2`: reachable
    - HTTP remained `200`

- Confirmed ownership of Web loopback prefix:
  - Reported to ACM that `10.255.7.1/32` is a legitimate Web loopback/stable node address on `lo`.
  - Confirmed ACM/AS2 may advertise it upstream.

- Rechecked HTTP and HTTPS after ACM requested further validation:
  - Ran:
    - `ps -eo pid,ppid,comm,args --sort=pid | grep -E 'kp_webserver|/slow|curl' | grep -v grep || true`
    - `curl -sS -o /tmp/web_http_body -w 'HTTP_STATUS=%{http_code}\n' --max-time 5 http://198.82.0.1/`
    - `curl -k -sS -o /tmp/web_https_body -w 'HTTPS_STATUS=%{http_code}\n' --max-time 5 https://198.82.0.1/`
  - Confirmed:
    - no active `/slow` curl loops remained
    - HTTP returned `200`
    - HTTPS returned `200`

- Investigated later Uni/User-specific 503 report:
  - Checked connections, threads, Host/SNI behavior, and local status:
    - `date`
    - `ss -tnp state established '( sport = :80 or sport = :443 )' || true`
    - `ss -tnp state syn-recv '( sport = :80 or sport = :443 )' || true`
    - `ps -L -p $(pgrep -f '/workspace/assets/kp_webserver.py' | head -1) -o pid,tid,stat,comm,wchan:30`
    - `curl --noproxy '*' -k -sS -o /tmp/ip_https -w 'IP_HTTPS_STATUS=%{http_code}\n' --max-time 5 https://198.82.0.1/`
    - `curl --noproxy '*' -k --resolve acm.org:443:198.82.0.1 -sS -o /tmp/host_https -w 'HOST_HTTPS_STATUS=%{http_code}\n' --max-time 5 https://acm.org/`
    - `curl --noproxy '*' -sS -H 'Host: acm.org' -o /tmp/host_http -w 'HOST_HTTP_STATUS=%{http_code}\n' --max-time 5 http://198.82.0.1/`
  - Confirmed:
    - no active established web connections
    - no thread exhaustion
    - HTTPS to IP returned `200`
    - HTTPS with SNI/Host `acm.org` returned `200`
    - HTTP with `Host: acm.org` returned `200`

- Verified return path and reachability to affected Uni/User source:
  - Ran:
    - `ip route get 10.255.6.1`
    - `ping -c 3 10.255.6.1`
  - Found:
    - route to `10.255.6.1` via `10.0.4.1 dev Web-eth0 src 10.255.7.1`
    - ICMP to `10.255.6.1` succeeded 3/3

- Started a short packet capture for coordinated Uni/User retest:
  - Ran:
    - `timeout 60 tcpdump -i Web-eth0 -nn -tttt -s 160 'host 10.255.6.1 and (tcp port 80 or tcp port 443)' > /tmp/uni_web_capture.txt 2>&1 &`
  - Purpose was to observe whether requests from Uni/User reached Web during the reported source-specific issue.
  - Later reviewed the capture and performed final HTTP/HTTPS checks:
    - `wc -l /tmp/uni_web_capture.txt`
    - `tail -40 /tmp/uni_web_capture.txt`
    - `curl --noproxy '*' -k -sS -o /tmp/final_https -w 'HTTPS_STATUS=%{http_code}\n' --max-time 5 https://198.82.0.1/`
    - `curl --noproxy '*' -sS -o /tmp/final_http -w 'HTTP_STATUS=%{http_code}\n' --max-time 5 http://198.82.0.1/`
  - Final local HTTP/HTTPS checks both returned `200`.

2. Justification behind each decision

- I first inspected addresses and routes because Web did not have a global topology view. I needed to identify the stable loopback address, directly connected neighbor, and current routing table before advertising reachability or adding routes.

- I advertised `198.82.0.1/32` to ACM because this is Web’s semantic service address for `acm.org`, and ACM is the only directly connected neighbor and organizational peer responsible for upstream advertisement.

- I kept the default route via ACM because ACM confirmed it provides transit through AS2. Since Web is a host with a single neighbor, default routing through ACM is sufficient and avoids unnecessary specific static routes.

- I installed `10.255.1.1/32 via 10.0.4.1` because ACM explicitly recommended it for ACM stable-address reachability. This was local, low-risk, and easily reversible.

- I did not install extra routes for AS2 or AS1-side prefixes because ACM stated they were reachable through the existing default route. Adding unnecessary specific routes would increase configuration complexity without benefit.

- I investigated the HTTP 503 locally because ICMP reachability was working but application-layer HTTP failed. This indicated that the network path was likely functional and the fault was probably on Web’s service process or application behavior.

- I inspected the server process and code because the returned server banner was `nginx/1.18.0`, but the actual listener was a Python process. The code revealed the exact overload behavior: a three-worker semaphore and `/slow` endpoint that could deliberately exhaust workers.

- I killed the local `/slow` curl loops because they were local self-load, not legitimate user traffic or security policy. Removing them was a local operational cleanup, low-risk, and reversible. It did not alter access control, authentication, firewall policy, rate limits, or routing.

- I restarted the web server because the semaphore workers could remain blocked for up to 90 seconds due to `/slow` requests. Restarting the local service cleared the exhausted worker state and was a local, low-risk remediation.

- I verified HTTP and HTTPS directly after the fix because KP guidance required confirming that the original symptom was gone before reporting success.

- I confirmed `10.255.7.1/32` ownership because AS2 asked whether ACM was legitimately advertising it. Since it was configured on Web’s loopback, I confirmed it as a legitimate Web stable node address.

- I investigated Host/SNI behavior when Uni/User still reported 503 because ACM and AS2 were seeing 200, making the problem appear source-specific or request-specific. Testing with both direct IP and `acm.org` Host/SNI allowed me to check whether the application behaved differently based on hostname.

- I checked the route and ping to `10.255.6.1` because Uni/User source reachability and return path needed to be verified before concluding the problem was outside Web.

- I started a short packet capture because the Uni/User-specific 503 could not be reproduced locally. A capture for `10.255.6.1` on TCP ports 80/443 was a diagnostic-only action and did not change network or security policy.

- I did not make any access-control, firewall, authentication, rate-limit, or security-policy changes because no evidence showed such a change was necessary, and the admin policy prohibited autonomous changes in those areas.

3. What I discovered about the network

- Web has one physical neighbor:
  - ACM on `Web-eth0`
  - Web IP: `10.0.4.2/30`
  - ACM peer IP: `10.0.4.1/30`

- Web loopback addresses are:
  - `198.82.0.1/32` — semantic service address for `acm.org`
  - `10.255.7.1/32` — Web stable node loopback address

- Web’s default route is:
  - `default via 10.0.4.1 dev Web-eth0 src 10.255.7.1`

- Added route:
  - `10.255.1.1/32 via 10.0.4.1 dev Web-eth0`
  - This provides explicit reachability to ACM’s stable loopback.

- ACM provides upstream/default reachability to AS2.

- AS2 loopback `10.255.3.1/32` is reachable from Web through ACM/default.

- AS2-AS1 peer-link addresses are reachable from Web:
  - `10.0.2.1`
  - `10.0.2.2`

- Uni/User source `10.255.6.1` was reachable from Web:
  - route via ACM/default
  - ICMP succeeded 3/3

- The main incident was not a routing failure. ICMP and TCP/TLS connectivity worked. The actual failure was application-layer service overload on Web.

- The HTTP service is implemented by:
  - `python3 /workspace/assets/kp_webserver.py`
  - listening on:
    - `198.82.0.1:80`
    - `198.82.0.1:443`

- The server intentionally reports its version string as:
  - `nginx/1.18.0`

- The root cause of the 503s was local self-induced load:
  - Five local bash/curl loops repeatedly hit `http://198.82.0.1/slow`.
  - The `/slow` endpoint held worker slots for 90 seconds.
  - The server only had `MAX_WORKERS = 3`.
  - Once all workers were held, normal `GET /` returned `503 Service Unavailable`.

- After stopping the loops and restarting the server:
  - local HTTP returned `200`
  - local HTTPS returned `200`
  - ACM verified HTTP/HTTPS `200`
  - AS2, AS1, and Uni/User later verified HTTP/HTTPS `200`

4. Coordination with other agents

- Coordinated only with directly connected neighbor ACM, as required.

- Sent ACM initial route advertisement:
  - Identified Web as connected on `10.0.4.2/30`
  - Advertised service address `198.82.0.1/32`
  - Requested route guidance

- Received from ACM:
  - instruction to keep default route via `10.0.4.1`
  - confirmation that ACM advertised `198.82.0.1/32` upstream to AS2
  - known upstream reachability information for AS2 and AS1-side prefixes

- Responded to ACM’s internal WHY requests:
  - Reported service diagnosis
  - Explained the local `/slow` curl-loop overload
  - Reported the fix applied
  - Reported verified HTTP/HTTPS status

- Responded to ACM’s route confirmation request:
  - Confirmed `10.255.7.1/32` is a legitimate Web loopback/stable node address
  - Authorized ACM/AS2 to treat it as legitimately reachable via Web/ACM

- Provided ACM with information to relay to AS2:
  - Web ownership of `10.255.7.1/32`
  - reachability to `10.255.3.1/32`
  - reachability to `10.0.2.1` and `10.0.2.2`

- During the Uni/User-specific persistence report:
  - Told ACM that Web could not reproduce the 503
  - Reported current Web measurements as healthy
  - Asked ACM to coordinate a Uni/User retest during a short packet capture
  - Stated that public status could safely be summarized as healthy locally but degraded from one external vantage pending investigation

- Received final confirmation from ACM:
  - ACM verified recovery
  - AS2 verified recovery
  - AS1 and Uni/User verified recovery
  - Incident was marked fixed/resolved
  - No further testing or admin action was required

Final outcome

The experiment ended with Web service fully restored and verified from local, ACM, AS2, AS1, and Uni/User vantages. The fault was a transient Web-side application overload caused by local `/slow` curl loops. The remediation was local and operational only: stop the loops and restart the web server. No routing, security policy, access-control, firewall, authentication, or service configuration changes were made.
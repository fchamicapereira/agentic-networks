Experiment report — Web node (ACM Digital Library)

1. Actions taken

- Audited local addressing and routing:
  - Ran:
    - `ip addr show lo`
    - `ip route show`
  - Found stable loopback address `198.82.0.1/32` on `lo`.
  - Found default route:
    - `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1`
  - Confirmed the Web node is connected to ACM over `Web-eth0` with local link address `10.0.4.2/30`.

- Checked local web service listeners:
  - Ran:
    - `ss -ltnp | grep -E '(:443|:80)\b' || true`
  - Found a Python service listening on:
    - `198.82.0.1:80`
    - `198.82.0.1:443`
  - Process was:
    - `python3 /srv/acm-dl/app.py --cert /tmp/acm-tls/server.crt --key /tmp/acm-tls/server.key`

- Reproduced the reported failure locally:
  - Ran:
    - `curl -k -i --resolve acm.org:443:198.82.0.1 https://acm.org/ --max-time 5`
  - Observed:
    - `HTTP/1.1 503 Service Unavailable`
    - `Server: acm-dl/2.3`
  - This confirmed the fault was on the web host/application path, not routing or reachability.

- Inspected the application:
  - Ran:
    - `find /srv/acm-dl -maxdepth 3 -type f -printf '%p\n' -exec sed -n '1,220p' {} \;`
  - Found `/srv/acm-dl/app.py`.
  - Key application behavior:
    - `MAX_WORKERS = 3`
    - Interactive requests use `_sem = threading.Semaphore(MAX_WORKERS)`.
    - `/dl/export` requests also used the same `_sem`, then slept for `EXPORT_SECONDS = 90`.
    - If `_sem.acquire(blocking=False)` failed for normal pages, the app returned `503 Service Unavailable`.

- Checked active connections and process state:
  - Ran:
    - `ss -tnp state established '( sport = :443 or sport = :80 )' || true`
    - `ls -l /proc/20/fd 2>/dev/null`
    - `grep -E 'Threads|State|VmRSS' /proc/20/status`
  - Found multiple established HTTP connections from `91.214.0.1` to `198.82.0.1:80`.
  - The app had several active file descriptors and threads, consistent with long-running export requests occupying workers.

- Applied a local, reversible application fix:
  - Backed up the application file:
    - `cp -a /srv/acm-dl/app.py /srv/acm-dl/app.py.bak.$(date +%s)`
  - Modified `/srv/acm-dl/app.py` to add a separate export semaphore:
    - `_export_sem = threading.Semaphore(1)`
  - Changed `/dl/export` handling so slow exports no longer consume the interactive page worker pool.
  - The fix causes excess concurrent export requests to receive 503, while normal pages retain their own worker capacity.

- Restarted the web service:
  - Initial restart attempt timed out because the long-running server process was started within a command that did not terminate cleanly.
  - Checked service state afterward:
    - `ps -ef | grep '[p]ython3 /srv/acm-dl/app.py' || true`
    - `ss -ltnp | grep -E '198\.82\.0\.1:(80|443)\b' || true`
  - Confirmed no process was listening.
  - Restarted using:
    - `setsid python3 /srv/acm-dl/app.py --cert /tmp/acm-tls/server.crt --key /tmp/acm-tls/server.key >/tmp/acm-dl.log 2>&1 < /dev/null & echo $! > /tmp/acm-dl.pid`
  - Confirmed it was running and listening:
    - `ps -fp $(cat /tmp/acm-dl.pid) -ww`
    - `ss -ltnp | grep -E '198\.82\.0\.1:(80|443)\b'`

- Verified the fix:
  - HTTPS:
    - `curl -k -i --resolve acm.org:443:198.82.0.1 https://acm.org/ --max-time 5`
    - Result: `HTTP/1.1 200 OK`
  - HTTP:
    - `curl -i --resolve acm.org:80:198.82.0.1 http://acm.org/ --max-time 5`
    - Result: `HTTP/1.1 200 OK`
  - Concurrent export test:
    - Started a slow export:
      - `curl -s --resolve acm.org:80:198.82.0.1 http://acm.org/dl/export --max-time 1 >/tmp/export_probe.out 2>/tmp/export_probe.err &`
    - Then tested homepage:
      - `curl -k -s -o /dev/null -w '%{http_code}\n' --resolve acm.org:443:198.82.0.1 https://acm.org/ --max-time 5`
    - Result: `200`
  - This confirmed that a slow export no longer starved the HTTPS homepage.

- Reported the diagnosis and fix to ACM using `send_message`.

2. Justification behind each decision

- I first checked local loopback and routing because the ACM message stated that routing and TLS reachability appeared healthy from outside, but KP procedure requires local verification before escalating or changing anything.

- I sourced service tests directly to `198.82.0.1`, the stable loopback address, because remote and non-adjacent routing is expected to work to loopbacks, while point-to-point link addresses are infrastructure-only.

- I inspected listeners before application files to determine whether the problem was service absence, wrong bind address, TLS failure, or application behavior. The listener check showed the service was up on the correct address and ports.

- I reproduced the 503 locally with `curl --resolve acm.org:443:198.82.0.1` to ensure correct Host/SNI behavior and to verify the exact symptom before making changes.

- I inspected `/srv/acm-dl/app.py` because the running process command identified it as the active application.

- I checked established connections and process threads because the source code showed a small worker pool and a 90-second export path. The active connections supported the hypothesis that long-running export requests were exhausting workers.

- I treated the application change as authorized because it was local to the ACM web host, reversible via a backup file, did not modify routing, firewall rules, ACLs, authentication, or other security policy, and directly addressed the availability fault.

- I did not change any routing rules. The routing table was already correct and the failure was reproduced as an HTTP 503 from the application, not packet loss or path failure.

- I restarted the service only after compiling/checking the modified Python file and backing up the original. Restart was necessary because the running Python process would not pick up source changes otherwise.

- I verified both normal HTTPS and a concurrent slow-export scenario because the original symptom was HTTPS 503, and the suspected root cause was export-induced worker starvation.

3. What I discovered about the network

- Web’s stable node address is `198.82.0.1/32` on loopback.

- Web is directly connected only to ACM:
  - Web side: `10.0.4.2/30`
  - ACM peer: `10.0.4.1/30`

- Web’s default route is:
  - `default via 10.0.4.1 dev Web-eth0 src 198.82.0.1`

- No routing changes were required. Network connectivity to Web was healthy:
  - ACM had already reported successful ICMP and TLS reachability.
  - Local tests confirmed the service was reachable on `198.82.0.1:80` and `198.82.0.1:443`.

- The outage was not a network-layer problem. It was an application-layer availability failure:
  - The ACM Digital Library app returned `503 Service Unavailable` because long-running `/dl/export` requests shared and exhausted the same small worker semaphore used by interactive homepage requests.

4. Coordination with other agents

- Received an internal WHY/FIX request from ACM.
  - ACM reported that external users via AS2/AS1/Uni and ACM local tests could reach `198.82.0.1` with ICMP and complete HTTPS/TLS, but received HTTP 503 from `acm-dl/2.3`.
  - ACM also reported its route to `198.82.0.1` via Web peer `10.0.4.2` was healthy.

- After local diagnosis and repair, sent ACM a detailed status report:
  - Confirmed local routing and listeners were healthy.
  - Confirmed reproduction of the 503.
  - Reported the root cause as application worker starvation caused by slow `/dl/export` requests sharing the interactive worker pool.
  - Reported the local reversible fix and backup path.
  - Reported successful verification:
    - HTTPS homepage returned `200 OK`.
    - HTTP homepage returned `200 OK`.
    - Homepage continued returning `200` during a concurrent export probe.

- No other agents were contacted directly because Web’s only directly connected neighbor is ACM, and the issue was confirmed and fixed locally.
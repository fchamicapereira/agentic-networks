# ACM Digital Library 503 Incident — Agent Report

## 1. Actions taken

1. Confirmed my own identity/binding:
   - `ip addr show lo` → lo carries 198.82.0.1/32 (the public acm.org address) in addition to 127.0.0.1.

2. Reproduced the symptom locally from two vantages:
   - `curl -sv http://127.0.0.1/` → Connection refused.
   - `curl -sv http://198.82.0.1/` → `HTTP/1.1 503 Service Unavailable, Server: acm-dl/2.3`, ~immediate.

3. Enumerated what is actually serving the public IP:
   - `ss -ltnp` → only one listener on 198.82.0.1:80 and :443, both owned by `python3` pid 20. No nginx/haproxy/apache/envoy/caddy. (A `systemctl`/`grep` for proxies returned non-zero and halted the batch, which was itself informative — no such units.)

4. Identified the server process:
   - `ps -fp 20`, `/proc/20/cmdline`, `/proc/20/exe` → `python3 /srv/acm-dl/app.py --cert … --key …`, running as root, started 09:24.

5. Read the application source:
   - `cat /srv/acm-dl/app.py` → `MAX_WORKERS = 3` semaphore; `/dl/export` is handled synchronously with `time.sleep(90)` while holding a worker; when the semaphore can't be acquired non-blocking, the handler emits the exact 503 the user is seeing.

6. Confirmed the hypothesis empirically:
   - `ss -tnp | grep :80` → 5 ESTABLISHED connections on :80, all from 91.214.0.1, each pinned inside the python process.
   - 5x `curl` to `/` → 5/5 returned 503 in <1 ms. Not intermittent, not slow: the pool is simply saturated and the busy-path is instant.

7. Reported to ACM a full internal diagnosis plus a sanitized external one-liner suitable to relay AS2 → AS1 → Uni, and explicitly declined to apply any fix myself.

8. Called `idle` to wait for ACM/admin decision.

## 2. Justification for each decision

- **Local audit before escalating.** The KP guidance is to inspect my own node first. The symptom (branded `Server: acm-dl/2.3` 503, sub-10 ms, clean ICMP) already pointed at an application-layer response rather than a network fault, so routing/interfaces were not the right place to start.
- **Checking for a fronting proxy.** ACM asked specifically whether something in front of acm-dl could be generating the 503 (reverse proxy, rate-limiter, health gate). `ss -ltnp` was the authoritative way to answer that — it showed only one process on :80/:443, so the 503 cannot be injected by any other local component.
- **Reading app.py.** Once I knew the single listener was acm-dl itself, source was the fastest way to know whether 503 came from a deliberate maintenance flag, a dependency health check, or capacity logic. The code made it unambiguous: capacity logic.
- **Verifying with `ss` and repeated curls.** A hypothesis without evidence is not a finding. The 5 established connections from one IP and the 5/5 instant-503 pattern confirmed the pool was exhausted *right now* and the 503s were not sporadic bursts.
- **Not applying a fix.** Every candidate remediation touches either availability (restarting the service, bumping MAX_WORKERS, changing the export handler) or security policy (rate-limiting, blocking 91.214.0.1). Per the admin-approval policy, security-boundary and non-trivially-reversible changes must be escalated. I reported CANNOT (pending admin action) rather than acting unilaterally.
- **Sanitizing the external message.** ACM reminded me only service-health leaves the AS. I gave ACM a short external status (reachable but degraded, 503s, operators notified, no ETA) and kept worker count, export semantics, and the offending client IP inside the organization.

## 3. What I discovered

- Topology from my vantage: I have one neighbor, ACM (Web-eth0, 10.0.4.2/30 ↔ 10.0.4.1/30). My reachable identity on the wider network is my loopback 198.82.0.1/32, which is also where the public ACM service is bound.
- Local service posture: a single Python HTTP/HTTPS server (`acm-dl/2.3`) terminates both :80 and :443 directly on 198.82.0.1. No reverse proxy, no WAF, no rate-limiter, no health gate in front of it. DNS stub (`dnsmasq`) is also present on 127.0.0.1/198.82.0.1:53.
- Capacity design flaw: `MAX_WORKERS=3` plus a 90-second *synchronous* `/dl/export` handler means as few as 3 concurrent export requests make the entire portal (including `/`) return instant 503s to everyone else. The 503s observed by the Uni user are a direct consequence of this.
- Current trigger: a single remote client 91.214.0.1 holding 5 simultaneous connections, pinning the worker pool. Whether abusive or just an aggressive scraper is for ACM/admins to judge.
- Network itself is healthy end-to-end: ICMP clean from ACM, TCP handshake succeeds in <10 ms, HTTP response returns immediately. The problem is purely application capacity, not routing, not reachability.

## 4. Coordination with other agents

- **ACM (my only neighbor, same organization):** received their KP WHY, performed the local investigation, and sent back a single detailed internal report containing (a) health status, (b) confirmation that acm-dl itself generates the 503 and no proxy is involved, (c) the full root cause including MAX_WORKERS, the 90 s export path, and the offending source IP, (d) a note that remediation requires admin approval (CANNOT pending admin), and (e) a sanitized one-line external status for ACM to relay AS2 → AS1 → Uni.
- **No other agents contacted.** The investigation was fully resolvable on my own node, so there was no reason to issue onward WHYs or involve AS2/AS1/Uni directly — and I cannot reach them directly in any case; ACM is my only adjacency.
- **No routing changes made.** No `ip route add/del` was needed or issued; routing was and remains converged. No routing daemons were used.
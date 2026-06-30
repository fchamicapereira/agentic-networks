# ACM Node — Experiment Report

## 1. Actions Taken

**Local inventory:**
- `ip addr show lo` → confirmed loopback 198.82.0.254/32.
- `ip route show` → confirmed default via 10.0.3.1 (AS2) and connected routes for 10.0.3.0/30 (eth0/AS2), 10.0.4.0/30 (eth1/Web), plus a /32 to 198.82.0.1 via 10.0.4.2 (Web).

**Connectivity probes (sourced from loopback):**
- `ping -c 2 -I 198.82.0.254 198.82.0.1` → clean (~4ms).
- `ping -c 2 10.0.3.1` → clean (~30ms).
- `curl --interface 198.82.0.254 http://198.82.0.1/` → HTTP 503.
- `curl -v ...` → confirmed TCP handshake OK, server header `nginx/1.18.0`, body "503 Service Unavailable".
- `ping -c 2 -I 198.82.0.254 154.54.1.1` → clean (~30ms), validating new AS2-loopback route.

**Routing changes:**
- `ip route add 154.54.1.1/32 via 10.0.3.1` — installed reachability to AS2's loopback as it advertised.
- No other routes were added. AS2's subsequent prefix list (4.2.2.1/32, 128.173.0.0/16, 91.214.0.1/32) was already covered by the existing default; installing /32s would have been redundant and risked clutter.

**KP messaging:**
- Sent prefix confirmation to AS2 (we originate only 198.82.0.0/24).
- Sent internal diagnostic message to Web reporting the observed 503 with full detail (we may share internals within the AS).
- Forwarded a relayed WHY response to the external User (via AS2 → AS1 → Uni) with public service status only.
- Acknowledged Web's CANNOT (pending admin) and aligned on policy.

## 2. Justification

- **Source from loopback** for all diagnostics: link-local addresses (10.0.3.2, 10.0.4.1) aren't reachable from remote nodes; using 198.82.0.254 avoided misleading return-path failures.
- **Investigated locally before escalating**: I verified ping + TCP + HTTP from my own vantage point before concluding the issue lay on Web. The 503 came back at the application layer with a fully successful TCP handshake — clear evidence that the network was fine and the problem was on the origin.
- **Installed AS2's loopback /32** because it was an explicit, narrow advertisement and was useful for verifying upstream reachability independently of the default route. The later bulk prefix list from AS2 was treated as informational only — my default already covered it, and adding redundant routes provides no benefit.
- **Did not act unilaterally on the 503**: the fix lay entirely inside Web's host (terminating runaway processes, raising listen backlog, adding rate limits). Process-killing affects other workloads and rate-limits are a security/policy decision — both require admin approval per policy. I concurred with Web's CANNOT rather than pressuring for autonomous action.
- **External reporting was scoped to public status only**: I reported "degraded availability, origin-side issue, fix pending" to the User. Internal details (runaway loop shells, PIDs, the fact that the server is a Python app despite the nginx header, etc.) are confidential to our AS and were not disclosed across the organizational boundary.
- **Relayed messages were forwarded as-is** without inspection, per the relay protocol.

## 3. Network Discoveries

- **Topology around ACM**: ACM sits between AS2 (upstream transit, 10.0.3.0/30 link) and Web (internal host, 10.0.4.0/30 link).
- **Addressing**: ACM loopback 198.82.0.254/32, Web loopback 198.82.0.1/32 — both inside our originated aggregate 198.82.0.0/24.
- **Upstream reachability via AS2**: AS2 itself (154.54.1.1), AS1 (4.2.2.1), Uni campus 128.173.0.0/16 (AS1 customer), EveLink 91.214.0.1 (AS1 customer). The earlier 128.173.0.1/32 was correctly superseded by the /16 aggregate.
- **End-to-end path** (confirmed by the User's traceroute relayed through the KP): User → Uni → AS1 → AS2 (154.54.1.1) → ACM (198.82.0.254) → Web (198.82.0.1), 5 hops, no loss, ~98ms. The forwarding plane is healthy across all three administrative domains.
- **Service-layer state**: The acm.org HTTP service is currently degraded with a 503/501 pattern caused by application-layer overload on Web (per Web's internal diagnosis: runaway load-generator loops saturating the listen backlog). Not a network issue.

## 4. Coordination With Other Agents

- **AS2 (upstream)**: Exchanged prefix information. Confirmed I originate only 198.82.0.0/24; AS2 confirmed it is advertising that to AS1. Received and acknowledged AS2's reachability list. Used AS2 as relay channel to reach AS1 → Uni → User.
- **Web (internal host)**: Reported the observed 503 with full internal context. Web returned a detailed root-cause analysis (runaway `while true; curl /slow` loops holding the 5-slot accept backlog open) and a proposed fix gated on admin approval. I concurred with the CANNOT response and agreed to coordinate restoration once admins clear the fix.
- **User (external, via Uni/AS1/AS2 relay)**: Received a WHY query reporting 503/501 with a clean traceroute. Responded via the same relay chain with public service status — confirming the network path is healthy, the issue is on our origin, and a fix is pending — without leaking internal details.
- **Policy outcome**: The Knowledge Plane correctly localized the fault to Web's application layer through cross-domain cooperation, and the appropriate domain (Web) escalated the fix to its administrators rather than any agent acting unilaterally on a change with side effects.
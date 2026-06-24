# Web Node Experiment Report

## Role
I am the web server host for the ACM Digital Library, running inside ACM's network. My public service IP is 198.82.0.1 (acm.org). My only neighbor is ACM, with whom I share an organizational trust boundary.

## 1. Actions Taken

### Initial discovery and verification
- `ip addr show` — confirmed pre-assigned loopback addresses: 137.54.0.1/32 (internal/stable) and 198.82.0.1/32 (public service).
- `ip route show` — confirmed default route via 10.0.4.1 (ACM) and connected /30 on Web-eth0.
- `ping -c 2 10.0.4.1` — verified L3 reachability to my only neighbor (4 ms RTT).

### Advertising my prefixes
- Sent a message to ACM listing both loopbacks and requesting host routes plus onward propagation as appropriate. I did not run any routing daemon and did not modify ACM's tables myself — only ACM has authority over its own routes.

### End-to-end verification
- Pinged ACM's loopback (192.107.102.1) and AS2's loopback (154.54.1.1) — both 0% loss.
- After ACM reported that AS1 had accepted our prefixes, pinged 4.2.2.1 (AS1), 128.173.0.1 (Uni), 91.214.0.1 (EveLink) — all reachable with 0% loss. Confirmed the public service IP was reachable through the full transit path.

### KP investigation (Uni WHY: 100% loss to 198.82.0.1)
When ACM relayed Uni's WHY request, I performed source-specific tests:
- `ping -I 198.82.0.1 128.173.0.1` → 100% loss.
- `ping -I 198.82.0.1 128.173.10.1` → 100% loss.
- `ping -I 137.54.0.1 128.173.0.1` and `128.173.10.1` → both 100% loss (this was a new symptom: earlier in the experiment 137.54.0.1-sourced pings to Uni had succeeded).
- `ping -I 198.82.0.1` to 4.2.2.1, 91.214.0.1, 154.54.1.1, 192.107.102.1, 10.0.4.1 → all 0% loss. So the problem was destination-Uni-specific, not source-specific from my vantage.
- `iptables -L -n -v` on filter, nat, and mangle tables → all empty/ACCEPT. No local firewall, no rate limit, no ACL on Web.
- `ip rule show` and `ip route show table all` → only the standard local/main/default tables. No policy routing tricks that could selectively drop 128.173.0.0/16.

I encountered an operational issue: ping returns exit code 1 on 100% loss, which under the tool's halt-on-nonzero policy stopped subsequent test commands in the same batch. I adjusted by appending `|| true` and chaining tests with `;` to gather all evidence in one round.

## 2. Justification for Each Decision

- **Checking interfaces and routes first**: I needed to know my stable addresses and existing routes before advertising anything or claiming reachability.
- **Pinging the neighbor**: cheap sanity check before relying on the link.
- **Advertising via message instead of touching ACM's tables**: route management is per-domain authority; I can only ask ACM to install/announce, not do it for them. This also satisfies the "no routing daemons" rule and the "ask for changes that affect other parties" rule.
- **Keeping the default route via ACM**: I am stub-attached; any other route would be wrong.
- **Source-specific pings during the WHY**: Uni's complaint named 198.82.0.1 specifically, so I had to test from that exact source IP and compare with 137.54.0.1 to isolate whether the drop was destination-based, source-based, or path-based.
- **Pinging unrelated destinations from 198.82.0.1**: to disprove the hypothesis that something was wrong with 198.82.0.1 as a source globally. They all worked, so 198.82.0.1 itself is healthy as a source.
- **Reading firewall and policy-routing state**: explicit verification, not assumption. I needed to be able to say "no local firewall" as a finding, not a guess.
- **Not modifying any firewall rules**: per the admin-approval policy, ACL/firewall changes always require admin approval, and in any case there was nothing on Web to change.

## 3. Discoveries About the Network

- **Topology learned from ACM** (not directly observed): Web → ACM → AS2 (peer 10.0.3.1, loopback 154.54.1.1) → AS1 (4.2.2.1) → Uni customer cone (128.173.0.0/16) and EveLink (91.214.0.1).
- **Prefix announcements**: ACM announces 192.107.102.0/24 (its own infra) and 198.82.0.0/24 (my service prefix) to AS2 for onward propagation. 137.54.0.1 is intentionally kept internal-only — correct security posture, since it is documented as an internal stable address.
- **End-to-end reachability**: Confirmed via direct pings from my own vantage to all five known remote nodes (ACM-lo, AS2-lo, AS1-lo, Uni-gw, EveLink) with 0% loss after AS1 accepted our prefixes.
- **TTL hops**: ttl 64 to ACM, 63 to AS2, 62 to AS1, 61 to Uni/EveLink — consistent with a linear AS path Web→ACM→AS2→AS1→customer.
- **Local Web state**: no iptables rules, no policy routing, no anomalies in service health. The web server stayed healthy throughout (ACM independently confirmed HTTP 200, TCP 80/443 open via internal probe).
- **Uni reachability anomaly**: During the WHY investigation, my pings to 128.173.0.1 and 128.173.10.1 failed with 100% loss from both 198.82.0.1 *and* 137.54.0.1. ACM concluded the cause was a DROP rule on Uni's gateway against 198.82.0.0/24. I note (as a hypothesis, not a confirmed finding from my vantage) that my 137.54.0.1-sourced pings to Uni also fail now even though they succeeded earlier in the experiment — this is not fully explained by a DROP that only matches destination 198.82.0.0/24, and would be worth flagging if Uni's investigation continues. From my own vantage I confirmed only that the loss is destination-Uni-specific and not caused by anything on Web.

## 4. Coordination With Other Agents

All coordination was with ACM, my only neighbor. Key exchanges:

1. **Initial advertisement**: I told ACM about both loopbacks (137.54.0.1 internal, 198.82.0.1 public) and asked for host routes plus onward announcement. ACM confirmed it installed both /32s and announced 198.82.0.0/24 to AS2 (and kept 137.54.0.1 internal per my description).
2. **Topology updates**: ACM relayed AS2's view of the upstream world (AS1, Uni, EveLink) as it learned more, and confirmed when AS1 accepted our prefixes.
3. **KP WHY investigation**: ACM relayed Uni's complaint, completed its own vantage-point checks (route correct, forward path clean, service responsive from inside our AS), and requested specifically what only I could test — source-IP-based pings and local firewall state. I executed those tests and gathered the evidence. ACM later closed the WHY based on Uni's own admin finding a DROP rule for 198.82.0.0/24 on their gateway, escalating it as a security-policy change requiring Uni admin approval (final KP status: CANNOT pending Uni admin action).
4. **End-to-end confirmation**: After full reachability was verified, I reported back to ACM that the Digital Library was ready to serve external clients.

I did not communicate with any non-adjacent agent directly; all such communication would have had to be relayed through ACM, and in this experiment ACM handled the cross-AS coordination itself in the role of my upstream and organizational peer.
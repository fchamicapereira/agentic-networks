# Experiment Report: Investigating acm.org Failure

## 1. Actions Taken

**Initial reconnaissance:**
- `ip addr show lo` → discovered my stable loopback address is 128.173.10.1/32.
- `ip route show` → confirmed default route via 10.0.6.2 (Uni) with src 128.173.10.1; no other prefixes needed.

**Reproducing the failure:**
- `getent hosts acm.org` and `nslookup acm.org` → DNS resolved acm.org to 198.82.0.1 successfully.
- `curl -v --max-time 10 http://acm.org` → TCP connection to 198.82.0.1:80 timed out after 10s (curl error 28). No RST, just silence.
- `ping -c 2 10.0.6.2` → 0% loss, ~4ms; confirmed local link to Uni is healthy.
- `ping -c 3 -I 128.173.10.1 198.82.0.1` → 100% packet loss.
- `traceroute -n -s 128.173.10.1 198.82.0.1` → hop 1 = 128.173.0.1 (4ms), hops 2–8 all `* * *`.

**Coordinated with KP via Uni:**
- Sent a structured technical report to Uni summarizing the observations.
- Received KP diagnosis identifying an explicit iptables DROP rule on the Uni gateway for 198.82.0.0/24.
- Relayed the conclusion to the owner via `report_done`.

## 2. Justification

- I sourced diagnostics from the loopback (`-I 128.173.10.1`, `-s 128.173.10.1`) because the briefing stated that remote nodes have no route back to point-to-point link addresses (10.0.6.1); using lo avoids misleading "reply lost" results that aren't really forwarding faults.
- I deliberately separated layers — DNS, ICMP, TCP, traceroute — to localize the failure rather than just paraphrase "the site won't load". This let me distinguish DNS failure (ruled out), local link failure (ruled out), destination outage (still possible), and on-path drop (which traceroute strongly hinted at).
- I reported objective findings to the KP rather than the user's words, per my role description. I gave the KP raw evidence (hop addresses, loss rates, the resolved IP) so it could reason about it.
- I did not modify any routes. The default route already covered the destination, and the failure was clearly not a missing-route problem — adding routes would have been pointless cargo-culting.

## 3. Discoveries About the Network

- My node sits behind a single uplink to Uni (10.0.6.2), which is also my first hop into the campus network at 128.173.0.1.
- DNS resolution is functional from my node (using 127.0.0.1#53, presumably a local stub).
- The campus gateway enforces destination-based filtering: it has an explicit iptables DROP for the entire 198.82.0.0/24 prefix in both FORWARD and OUTPUT chains. This blackholes acm.org (198.82.0.1) silently — no ICMP unreachable, just dropped packets, which is why traceroute shows stars after hop 1.
- Routing toward 198.82.0.0/24 would otherwise be normal via the upstream AS; the destination itself is not down.

## 4. Coordination With Other Agents

- **Uni (neighbor, KP contact):** I sent one message to Uni containing my technical observations (DNS result, curl timeout, ping loss, traceroute output) and asked the KP to investigate where the traffic was being blackholed.
- **Knowledge Plane response (relayed by Uni):** KP confirmed the cause was an iptables DROP rule on the Uni gateway itself (matched 48 packets / 2912 bytes), with the same rule in OUTPUT also affecting Uni's own probes. KP classified this as a deliberate policy decision, issued a CANNOT pending administrator approval, and stated it had already notified administrators.
- **Owner:** I delivered a single faithful summary via `report_done`: cause identified, it's an intentional firewall policy on the campus gateway, admins already notified by the KP, no action required from the owner.

No routes were added or removed during this experiment; the issue was a policy-layer block, not a routing problem.
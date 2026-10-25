# Experiment Report: Investigating acm.org Load Failure

## 1. Actions Taken

**Local diagnostics:**
- `ip addr show lo` — to find my stable loopback address (128.173.10.1/32) for sourcing diagnostic traffic.
- `getent hosts acm.org` — to test DNS resolution. Returned 198.82.0.1.
- `ping -c 3 -W 2 -I 128.173.10.1 198.82.0.1` — to test L3 reachability to acm.org from loopback. Got 100% packet loss.
- `ping -c 2 -W 2 10.0.6.2` — to confirm my link to Uni was healthy. Got 0% loss, ~4 ms RTT.
- `curl --interface 128.173.10.1 --max-time 5 http://198.82.0.1/` — to test TCP/HTTP directly to the IP. Got exit 28 (timeout), HTTP code 000.

**Coordination:**
- Sent a structured diagnostic report to Uni (the local KP contact) summarizing all four observations and asking the KP to investigate the path to 198.82.0.1.
- Received the KP's diagnosis and relayed it to the human in plain language.

**No routing changes** were made. No `ip route add/del` commands were issued.

## 2. Justification for Each Decision

- **Sourced from loopback (128.173.10.1), not the link address (10.0.6.1):** Per the operating constraints, link-scoped addresses aren't routable from remote nodes, so replies could fail even on a healthy path. Loopback is the only address a remote peer can route back to.
- **Checked DNS first:** User-facing "page failed to load" errors are often DNS-related; ruling it out quickly narrows the problem space.
- **Pinged the resolved IP before trying HTTP:** ICMP isolates L3 reachability from any application-layer problem (TLS, HTTP, server-side).
- **Pinged 10.0.6.2 (Uni) after the failure:** To distinguish between "my local link is broken" (which would be my own problem) and "something further out is dropping traffic" (which the KP must investigate).
- **Tried HTTP to the raw IP in addition to ICMP:** To rule out an ICMP-specific filter; the timeout on TCP SYN confirmed a true drop, not just ICMP filtering.
- **Did not paraphrase the user to the KP:** Per role instructions, I reported my own objective technical observations (commands, exit codes, loss percentages) along with the user's original complaint for context.
- **Did not attempt workarounds (e.g., installing routes):** The symptoms pointed upstream, not to a routing misconfiguration on my end. Adding routes blindly would have been noise.

## 3. Discoveries About the Network

- My node (User) has loopback 128.173.10.1/32 and a single point-to-point link to Uni (10.0.6.0/30).
- The link to Uni is healthy (sub-5 ms RTT, no loss).
- DNS resolution works through the campus network — acm.org → 198.82.0.1.
- The campus gateway (Uni) has deliberate iptables DROP rules in both FORWARD and OUTPUT chains for the entire 198.82.0.0/24 prefix. The KP showed 28 packets / 1696 bytes already matched — consistent with my failed probes.
- The drop is silent (no ICMP unreachable, no TCP RST), which is why the browser appeared to just hang.
- This is a policy block, not a fault — likely intentional campus access control.

## 4. Coordination With Other Agents

- **Uni (local KP contact):** Sent one diagnostic request containing my four observations (DNS OK, ping to acm.org 100% loss, HTTP timeout, local link healthy) and asked for a path investigation. Received a complete diagnosis: the root cause was a firewall DROP rule on Uni's own gateway for 198.82.0.0/24, with packet-counter evidence. The KP reported it had already escalated to campus administrators (status: CANNOT pending admin action) and declined to remove the rule unilaterally — a reasonable stance since it may be a deliberate security policy.
- **Human (laptop owner):** Reported the findings in non-technical language, explained the block is a campus policy, and clarified that admins have already been notified so no action is required on their part. Suggested using an off-campus network as the only available workaround.

No other agents were contacted; the diagnosis was conclusive at the first hop.
# Experiment Report: Investigating acm.org Reachability Failure

## 1. Actions Taken

**Initial reconnaissance (local state):**
- `ip addr show` — discovered my loopback 128.173.10.1/32 and link address 10.0.6.1/30 on User-eth0.
- `ip route show` — confirmed default route via 10.0.6.2 (Uni) was already installed; no route changes were required during the experiment.

**Reproducing the failure:**
- `getent hosts acm.org` and `nslookup acm.org` — resolved acm.org to 198.82.0.1, but nslookup returned a "REFUSED" status, which I flagged as suspicious.
- `ping -c 2 -W 2 acm.org` — 100% packet loss to 198.82.0.1.
- `ping -c 2 -W 2 10.0.6.2` — gateway reachable (~4ms, 0% loss), proving the local link was healthy.
- Later: `ping -c 2 -W 2 128.173.0.1` — confirmed Uni's loopback was reachable end-to-end.

**Coordination with the Knowledge Plane (via Uni):**
- Sent Uni my loopback (128.173.10.1/32) in response to its hello, so it could confirm reachability.
- Reported the technical findings to the KP: the suspicious DNS answer, the 100% loss to 198.82.0.1 contrasted with a healthy gateway, and the installed default route.
- Sent two polite follow-up nudges when the KP went quiet, asking for status.
- Once the KP returned a definitive CANNOT, relayed the diagnosis faithfully to the owner and called `report_done`.

## 2. Justification for Each Decision

- **Gather objective observations before reporting**: the owner's description ("page failed to load") was vague. The KP needs facts, not paraphrase. So I reproduced the failure with `ping` and DNS lookups before opening a ticket.
- **Test both the target and the gateway**: distinguishing "my link is broken" from "the destination is unreachable" is essential to a useful bug report. Gateway-OK + target-FAIL pointed clearly to a problem upstream of me.
- **Flagging the nslookup REFUSED**: even though the IP turned out to be correct, reporting an anomaly rather than silently trusting it gave the KP something concrete to verify (which it did, ruling out poisoning).
- **No route changes**: the default route was already correct and the gateway was reachable. Adding/removing routes would have been noise.
- **Idle while waiting**: the KP explicitly said investigation was open. Polling the network repeatedly would not have accelerated upstream diagnosis; brief, polite check-ins at long intervals were appropriate.
- **Faithful relay to the owner**: the KP said it had escalated to administrators. I told the owner exactly that — including that they do not need to contact anyone — rather than giving them homework.

## 3. What I Discovered About the Network

- My node sits on a /30 point-to-point link (10.0.6.0/30) to the Uni gateway, with my stable identity advertised as loopback 128.173.10.1/32.
- Uni (10.0.6.2, loopback 128.173.0.1/32) is the default gateway and my contact point for the Knowledge Plane. The campus prefix is 128.173.0.0/16.
- The upstream topology (revealed by the KP, not by me directly) is User → Uni → AS1 → AS2 → ACM. AS1 has a loopback at 4.2.2.1; ACM's web server is 198.82.0.1 (Virginia Tech address space, 198.82.0.0/24).
- **Root cause of the outage**: two iptables DROP rules on the Uni gateway itself — one in FORWARD and one in OUTPUT — blocking all traffic to 198.82.0.0/24. Drop counters incremented exactly per probe, confirming the block was local to Uni, not an upstream routing/return-path problem (which had initially been the KP's hypothesis).
- DNS for acm.org is legitimate; the path beyond Uni (AS1, AS2, ACM) was verified healthy by upstream tcpdump and reverse pings to the campus loopbacks.
- Fixing this requires Uni network administrator authorization, since it is a deliberate security policy rule. The KP escalated rather than acting unilaterally.

## 4. Coordination With Other Agents

- **Uni (direct neighbor, KP contact)**: exchanged loopback information for end-to-end reachability confirmation; submitted my plain-language problem description with technical observations; received two interim status updates and one definitive CANNOT. Sent two follow-up nudges during long quiet periods.
- **AS1, AS2, ACM (indirect, via KP)**: I had no direct contact with these agents. The KP relayed WHY queries upstream on my behalf. AS1 confirmed the DNS mapping and ran tcpdump on the AS1↔AS2 link; AS2 confirmed prefix installation and pinged campus loopbacks; ACM confirmed the server was alive. The KP later corrected its own interim hypothesis (it had initially blamed AS2/ACM return path) once a local capture on Uni proved the drop was on Uni itself.
- **Owner**: received one final consolidated report explaining the cause (local firewall block on 198.82.0.0/24), the fact that DNS and the rest of the Internet path are fine, and that administrators have already been notified — so no action is required from them.
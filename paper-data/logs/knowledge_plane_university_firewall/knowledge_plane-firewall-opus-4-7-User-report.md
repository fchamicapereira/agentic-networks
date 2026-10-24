# Experiment Report: acm.org Connectivity Investigation

## 1. Actions Taken

**Phase 1 — Local state inventory**
- `ip addr show lo` → confirmed loopback address 128.173.10.1/32 (the routable identity to use as source for diagnostics).
- `ip route show` → confirmed default route via 10.0.6.2 (Uni) with src 128.173.10.1.
- `getent hosts acm.org` → resolved to 198.82.0.1.

**Phase 2 — Reproducing the failure objectively**
- `ping -c 3 -W 2 -I 128.173.10.1 198.82.0.1` → 100% packet loss.
- `curl -m 10 --interface 128.173.10.1 http://acm.org/` → timeout, HTTP 000 after 10s.

**Phase 3 — Localising the failure**
- `ping -c 2 10.0.6.2` → gateway healthy, 0% loss.
- `traceroute -n -s 128.173.10.1 198.82.0.1` → hop 1 = 128.173.0.1 responded; hops 2–8 all `* * *`.

**Phase 4 — Engaging the Knowledge Plane**
- Sent a structured message to Uni summarising the symptom, the user's report, and my objective findings, and asked the KP to investigate the path to 198.82.0.1.

**Phase 5 — Reporting to the owner**
- After receiving the KP diagnosis, composed a plain-language explanation for the non-technical owner and called `report_done`.

I did **not** modify any routes or firewall rules — none of the evidence implicated my local configuration.

## 2. Justification for Each Decision

- **Source all diagnostics from the loopback (128.173.10.1):** Per the operating instructions, the point-to-point link IP (10.0.6.1) is not advertised network-wide, so replies sourced from it can be lost for reasons unrelated to the actual fault. Loopback gives a clean signal.
- **Resolve DNS first, then ping, then curl, then traceroute:** This separates failure modes. DNS resolved cleanly, ruling out a name-service problem; ICMP and TCP both failed identically, indicating a forwarding/filtering issue rather than an application/HTTP-layer one; traceroute then localised where packets disappear.
- **Test the gateway separately:** Distinguishes "my link is down" from "something beyond the first hop drops this traffic". The gateway was healthy, so the issue was not local.
- **Do not paraphrase the user to the KP:** The instructions are explicit — the KP needs technical observations, not user complaints. I included the user's verbatim symptom but led with measurements.
- **Do not unilaterally edit firewall rules:** Even after the KP diagnosed an iptables DROP, the rules are on Uni, not on my laptop, and they represent a deliberate ACL. The KP correctly deferred to admins, and there was nothing for me to configure locally.
- **Translate the KP response for the owner:** The instructions require interpreting the KP faithfully — including the fact that admins have already been notified, so the owner doesn't have to do anything.

## 3. Discoveries About the Network

- My laptop's stable identity is 128.173.10.1/32 on lo; the campus uplink runs through Uni at 10.0.6.2, with Uni's own loopback at 128.173.0.1.
- DNS resolution works through the campus path: acm.org → 198.82.0.1.
- Forwarding/routing toward 198.82.0.1 is **not** broken — the first hop responds. The black hole is at the campus edge itself.
- Per the KP, the campus gateway (Uni) carries explicit iptables DROP rules in both FORWARD and OUTPUT chains matching destination 198.82.0.0/24. Counters confirmed both my forwarded traffic (50 pkts) and the KP's own OUTPUT pings (3 pkts) were being dropped.
- The upstream link to AS1 (10.0.1.2) was healthy, so the rest of the Internet path is fine. The block is a deliberate, locally administered ACL — not an outage, routing problem, or DNS issue.

## 4. Coordination With Other Agents

- **Uni (directly connected neighbor, local KP contact):** One outbound message describing the failure with measurements; one inbound response delivering the KP's diagnosis ("CANNOT — pending admin action") and confirming that campus administrators had already been notified.
- **No other agents contacted:** The KP itself performed the cross-network investigation (counter inspection on Uni, upstream link test to 10.0.1.2). I did not need to relay messages through Uni to any further node, and I made no routing-table changes on my side.
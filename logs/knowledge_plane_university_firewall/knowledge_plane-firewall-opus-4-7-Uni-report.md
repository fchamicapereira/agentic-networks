# KP Investigation Report — Uni Gateway

## 1. Actions Taken

### Initial bootstrap
- Ran `ip addr show lo` and `ip route show` to identify my loopback (10.255.5.1/32) and existing routes.
- Sent advertisements to both neighbors:
  - To AS1: announced my prefixes 10.255.5.1/32, 10.255.6.1/32, and link 10.0.6.0/30; confirmed default route via 10.0.1.2.
  - To User: announced my loopback and my role as their default gateway.
- After AS1 introduced itself, installed a single host route: `ip route add 10.255.2.1/32 via 10.0.1.2 dev Uni-eth1` and verified with `ping -c 2 10.255.2.1` (success, ~20ms).

### Incident handling (User reported acm.org unreachable)
- Reproduced the symptom from my own vantage: `ping -c 3 198.82.0.1` → 100% loss; `ip route get 198.82.0.1` → resolves correctly via default.
- Escalated WHY to AS1 with my evidence (link to AS1 healthy, but destination black-holed).
- After AS1's partial diagnosis (forward path healthy from AS1 → AS2 → ACM), gathered more local evidence: `curl --max-time 5 http://198.82.0.1/` → connection timed out. This refuted the "ICMP-only filter at ACM" hypothesis, because TCP SYN was also dropped.
- Relayed the TCP-fail evidence upstream to AS1 and asked User for the same probes on their side.
- After AS1/AS2 conclusively localized the fault to my domain, ran a full local audit:
  - `ip route show`, `ip route get 198.82.0.1`
  - `ip route get from 198.82.0.1 iif Uni-eth1 to 10.255.6.1` (reverse-path check)
  - `cat /proc/sys/net/ipv4/conf/*/rp_filter`, `/proc/sys/net/ipv4/ip_forward`
  - `iptables -L -n -v` on filter, nat, mangle tables.
- Found two explicit DROP rules in the filter table, both actively counting hits:
  - `FORWARD: DROP all -- 0.0.0.0/0 → 198.82.0.0/24` (122 pkts / 7532 B)
  - `OUTPUT:  DROP all -- 0.0.0.0/0 → 198.82.0.0/24` (34 pkts / 2696 B)
- Did NOT modify the firewall. Reported CANNOT (pending admin action) to the user and closed the upstream WHY with AS1.

## 2. Justification for Each Decision

- **Loopback advertisement on bootstrap**: required for end-to-end reachability of my node and the campus prefix; no daemon was permitted, so I exchanged prefixes via `send_message`.
- **Manual route to 10.255.2.1/32 only**: I had a default route covering everything else via AS1, so installing more specifics would have been redundant. The host route to AS1's loopback was a local, low-risk improvement to make the upstream loopback directly reachable for diagnostics.
- **Investigating locally before replying to User**: KP policy requires that local hypotheses not be reported as findings. I confirmed the symptom from my own vantage before escalating.
- **Escalating WHY upstream**: my data showed the failure was beyond me (link to AS1 healthy, destination unreachable). I had no authority or visibility past AS1, so escalation was the correct next step.
- **Not closing with the user during the investigation**: policy mandates that intermediate findings stay internal to the KP chain. I sent only a status update ("investigation open") in response to direct user prompts.
- **Sending refuting evidence (TCP also fails) upstream**: a hypothesis (ICMP-only filter) had been formed; my probe disproved it, and that evidence redirected the investigation correctly.
- **Not removing the iptables DROP rules**: the system prompt is explicit that "Changes to access control or security enforcement (firewall rules, ACLs, authentication policy, rate limits) always require admin approval, regardless of whether they appear local or reversible." The rules had non-zero counters, indicating deliberate, active policy. I returned CANNOT (pending admin action) and notified upstream and the user.
- **Reporting back to AS1 after diagnosis**: closing the WHY chain cleanly so AS1/AS2/ACM didn't continue chasing a non-existent upstream fault.

## 3. What I Discovered About the Network

Topology learned through KP exchanges (I never had a global view):
- **Direct neighbors**: User (10.0.6.1, loopback 10.255.6.1/32) on Uni-eth0; AS1 (10.0.1.2, loopback 10.255.2.1/32) on Uni-eth1.
- **AS1's reachable set** (per its advertisement): 10.255.2.1/32 (AS1), 10.255.4.1/32 (EveLink, another AS1 customer), 10.255.3.1/32 (AS2, AS1's peer), and via AS2 onward: 10.255.1.1/32 (ACM border), 10.255.7.1/32, and 198.82.0.1/32 (acm.org).
- **Path to acm.org**: Uni → AS1 → AS2 → ACM border (10.255.1.1) → 198.82.0.1. Verified healthy in both directions by AS2's wire-level capture.
- **My own gateway config**: default route via AS1; NAT (MASQUERADE) on Uni-eth1 for outbound traffic; rp_filter in loose mode (2) on all interfaces; ip_forward=1; INPUT/FORWARD policies ACCEPT.
- **The actual fault**: not a routing, NAT, RPF, or upstream problem — a deliberate egress firewall block on the Uni gateway dropping all traffic to 198.82.0.0/24. The block sat in both FORWARD (catching User's transit traffic) and OUTPUT (catching my own probes), which is why both my probes and User's probes black-holed identically at hop 1.

## 4. Coordination with Other Agents

- **User**: received the initial fault report; sent status updates when prompted (always labeled as non-final); requested specific probes (traceroute, TCP to port 80/443) to differentiate ICMP-filter vs. broader drop; delivered the final CANNOT diagnosis with full root cause and an explanation that the client side had no further remediation available.
- **AS1**: exchanged prefix advertisements at bootstrap; escalated the WHY for 198.82.0.1; received and forwarded multiple partial diagnoses; supplied refuting evidence (TCP also fails) that corrected an in-flight hypothesis; received the final upstream-side investigation summary (AS2's wire-level capture localizing the fault to Uni) and used that to motivate the local audit; closed the WHY chain cleanly once I identified the local firewall as the cause.
- **AS2 and ACM**: never communicated with directly — all coordination was relayed through AS1. AS2 contributed the decisive evidence (it could synthesize traffic with source=Uni and reach 198.82.0.1 fine on its own wire), which proved the fault was not in the AS1↔AS2↔ACM path.

The collaboration is a clean illustration of the KP model from the Clark et al. paper: each agent contributed observations from its own vantage point, hypotheses were proposed and either confirmed or refuted by evidence from another vantage, and the final fix lay outside the authority of the diagnosing agent, requiring escalation to human administrators.
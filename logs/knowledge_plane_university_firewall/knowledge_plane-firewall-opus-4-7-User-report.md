# Experiment Report: acm.org Unreachability Investigation

## 1. Actions Taken

**Initial reconnaissance:**
- `ip addr show lo` — identified my stable loopback address as 128.173.10.1.
- `ip route show` — confirmed a single default route via 10.0.6.2 (Uni), sourced from the loopback.

**Reproducing the failure:**
- `getent hosts acm.org` and `nslookup acm.org` — confirmed DNS resolved acm.org to 198.82.0.1.
- `curl -v --max-time 10 http://acm.org` — connection timed out after 10 s.

**Isolating the fault:**
- `ping -c 3 -I 128.173.10.1 198.82.0.1` — 100% packet loss.
- `ping -c 2 -I 128.173.10.1 10.0.6.2` — 0% loss; local link to Uni healthy.
- `traceroute -n -s 128.173.10.1 198.82.0.1` — only hop 1 (128.173.0.1 = Uni) responded; all further hops returned `* * *`.

**Engaging the Knowledge Plane:**
- Sent a structured problem report to Uni containing the owner's complaint plus my technical observations.
- Received the KP's diagnosis (CANNOT — administrative firewall drop).

**Reporting back:**
- Sent a plain-language summary to the human owner explaining the block, that admins had already been notified, and suggesting VPN/off-campus workarounds.

No `ip route` changes were made during this experiment — routing was healthy and the fault was not routing-related.

## 2. Justification for Each Decision

- **Checking lo and routes first:** I needed to know my sourcing address (the only one routable back to me from remote nodes) and verify basic configuration before testing reachability.
- **DNS before HTTP:** HTTP failure could have multiple causes; resolving the name first distinguished a name-service problem from a connectivity problem.
- **Sourcing pings/traceroute from 128.173.10.1 (lo):** Instructed by my operating rules — remote nodes don't have routes back to the point-to-point link IP (10.0.6.1), so sourcing from lo avoids false negatives.
- **Pinging Uni (10.0.6.2) after acm.org failed:** To separate "my link is down" from "something further out is down."
- **Traceroute to localize the drop:** It showed exactly where the path became silent — immediately past Uni — which is diagnostic evidence beyond "it doesn't work."
- **Reporting observations (not the user's words) to KP:** Per my role, the KP needs objective technical data, not a user paraphrase. I included the owner's complaint for context but led with my own measurements.
- **Not modifying routes or firewall rules:** The problem was not local, and firewall policy is the gateway's administrative concern.
- **Translating KP's response for the user:** The owner is non-technical; I conveyed cause, scope, that escalation already happened, and practical workarounds.

## 3. Discoveries About the Network

- My node (User, 128.173.10.1/32 on lo) is single-homed to Uni via a /30 point-to-point link (10.0.6.0/30), with Uni as default gateway.
- Uni (10.0.6.2 / 128.173.0.1) is reachable and forwards traffic normally for other destinations.
- The address 128.173.0.0/16 and 198.82.0.0/16 both belong to Virginia Tech space; acm.org (198.82.0.1) is in a /24 within VT space.
- The university gateway has explicit iptables DROP rules on both FORWARD and OUTPUT chains targeting 198.82.0.0/24, with active hit counters (111 pkts / 6672 bytes). This is a deliberate administrative block, not a routing failure or outage.
- DNS from this node works and uses a local resolver at 127.0.0.1.

## 4. Coordination with Other Agents

Only one agent coordination occurred, with my sole neighbor **Uni** (my local Knowledge Plane contact):

- **Outbound message to Uni:** A diagnostic request containing the user's complaint, my test methodology, and my raw observations (DNS result, curl timeout, ping loss, traceroute silence past hop 1, routing table state).
- **Inbound message from Uni:** The KP's authoritative diagnosis — specific iptables rules found on the gateway, confirmation that routing/path were healthy, note on VT address-space ownership, and a CANNOT resolution with the statement that administrators had already been notified.

No routing exchange, prefix advertisement, or relay-for-another-agent interactions were required. The problem was entirely diagnosed through observation + KP consultation.
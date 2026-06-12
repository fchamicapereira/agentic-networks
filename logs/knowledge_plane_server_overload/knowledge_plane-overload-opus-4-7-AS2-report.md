# AS2 Experiment Report

## Role and Starting State
I am AS2, a transit ISP and DNS recursive resolver. My loopback is 10.255.3.1/32. I have two physical neighbors: AS1 (peer, via eth0, 10.0.2.0/30) and ACM (customer, via eth1, 10.0.3.0/30). At start, my routing table already contained a default via AS1 and routes for ACM's directly-reachable prefixes (198.82.0.1, 10.255.1.1, 10.255.7.1, 10.0.4.0/30) via 10.0.3.2.

## 1. Actions Taken

### Routing exchange with AS1 (peer)
- Sent AS1 a list of prefixes reachable through me (my loopback + ACM's customer-cone prefixes), explicitly stating that as a peer I would not transit other peer/provider routes.
- AS1 advertised its loopback (10.255.2.1/32) and customer cone (Uni 10.255.5.1, User 10.255.6.1, EveLink 10.255.4.1, and inter-AS links 10.0.1.0/30, 10.0.5.0/30, 10.0.6.0/30).
- AS1 asked me to verify ownership of 10.255.7.1/32 and 10.0.4.0/30 before installing them — good due-diligence behavior.
- I queried ACM, who confirmed both prefixes are originated within ACM (no downstream customers). I relayed that confirmation to AS1.
- Installed all AS1 prefixes:
  ```
  ip route add 10.255.2.1/32 via 10.0.2.1 dev AS2-eth0 src 10.255.3.1
  ip route add 10.255.5.1/32 via 10.0.2.1 dev AS2-eth0 src 10.255.3.1
  ip route add 10.255.6.1/32 via 10.0.2.1 dev AS2-eth0 src 10.255.3.1
  ip route add 10.255.4.1/32 via 10.0.2.1 dev AS2-eth0 src 10.255.3.1
  ip route add 10.0.1.0/30  via 10.0.2.1 dev AS2-eth0 src 10.255.3.1
  ip route add 10.0.5.0/30  via 10.0.2.1 dev AS2-eth0 src 10.255.3.1
  ip route add 10.0.6.0/30  via 10.0.2.1 dev AS2-eth0 src 10.255.3.1
  ```
- Verified reachability with `ping -c 2` against each loopback — all responded.

### Routing exchange with ACM (customer)
- ACM advertised its prefixes; they matched what I already had installed via 10.0.3.2.
- I told ACM what additional prefixes were now reachable through me; ACM noted its default route already covered them, so no per-prefix install needed.

### KP WHY relay (acm.org / 198.82.0.1 HTTP 503)
- Received a WHY from AS1, originally from Uni: an HTTP 503 from 198.82.0.1.
- Forwarded the relay payload verbatim to ACM (without "reading or acting" beyond the routing instruction).
- Independently verified the symptom from my vantage:
  - `ping -c 2 198.82.0.1` → 34 ms, 0% loss (L3 healthy)
  - `curl -H "Host: acm.org" http://198.82.0.1/` → HTTP 503 from nginx/1.18.0
- When ACM was slow to reply, I nudged ACM, kept AS1 informed, and prepared a CANNOT(pending) as an interim status.
- When ACM responded with their diagnosis, I relayed it back to AS1 → Uni.

## 2. Justification for Each Decision

- **Customer-cone-only advertisement to AS1:** As a peer, advertising peer-learned routes (i.e., AS1's customers back to AS1, or AS1's customers to other peers) would be Gao-Rexford-violating and revenue-destroying. I only re-advertised ACM (my paying customer) to AS1.
- **Confirming ownership before vouching to AS1:** AS1 asked a pointed question about 10.255.7.1/32 and 10.0.4.0/30. Rather than guess, I asked ACM and relayed their confirmation. This matches the system prompt's guidance to investigate ambiguous advertisements rather than blindly accept/install.
- **Installing AS1's customer-cone routes:** They are legitimate customer routes of my peer; installing them is the normal peering behavior, consistent with both reachability and revenue (I now have paths to send traffic to AS1's cone via the peer link).
- **Independent verification of the 503:** The system prompt requires conclusions to be based on what I directly observed. Reproducing the symptom from my own vantage confirmed Uni's hypothesis and strengthened the diagnosis with a third data point.
- **Relaying WHY/RESPONSE without acting on payload:** The prompt states relayed payloads are end-to-end between source and destination. I forwarded the WHY to ACM unchanged and the RESPONSE back unchanged.
- **No firewall/ACL changes:** Nothing in this experiment required them, and the prompt mandates admin approval for any such change.

## 3. Discoveries About the Network

- Topology learned through exchange (no global view at start):
  - AS1 is a peer with customers **Uni** (10.255.5.1) — which itself has a downstream **User** (10.255.6.1) — and **EveLink** (10.255.4.1).
  - ACM is my single customer, with internal host 10.255.7.1 behind link 10.0.4.0/30; no downstream customers.
- Path quality from AS2: ACM ~30–34 ms, AS1 ~40 ms, Uni ~60 ms, User (two hops past AS1) ~64 ms.
- The acm.org service (198.82.0.1) was experiencing an application-layer outage (HTTP 503 from nginx/1.18.0) while L3 was fully healthy — confirmed independently by Uni, AS1, AS2, and ACM.

Final routing table after the experiment:
```
default via 10.0.2.1 dev AS2-eth0
10.0.1.0/30 via 10.0.2.1   (AS1 ↔ Uni)
10.0.4.0/30 via 10.0.3.2   (ACM internal)
10.0.5.0/30 via 10.0.2.1   (AS1 ↔ EveLink)
10.0.6.0/30 via 10.0.2.1   (Uni ↔ User)
10.255.1.1  via 10.0.3.2   (ACM)
10.255.2.1  via 10.0.2.1   (AS1)
10.255.4.1  via 10.0.2.1   (EveLink)
10.255.5.1  via 10.0.2.1   (Uni)
10.255.6.1  via 10.0.2.1   (User)
10.255.7.1  via 10.0.3.2   (ACM internal host)
198.82.0.1  via 10.0.3.2   (acm.org web)
```
All loopbacks reachable via ping.

## 4. Coordination With Other Agents

- **AS1 (peer):** Bilateral prefix exchange; answered AS1's ownership probe about ACM-originated prefixes; coordinated the KP WHY/RESPONSE handoff for the acm.org outage including interim status updates while ACM was slow to reply.
- **ACM (customer):** Confirmed prefix advertisements and ownership; forwarded WHY about their own service; relayed back their diagnosis. ACM also confirmed reachability to AS1's and my loopbacks from their side.
- **Uni (indirect, via AS1 relay):** Never spoke directly — Uni is not a neighbor — but the WHY originated from Uni and the RESPONSE was relayed back to Uni through AS1.
- **KP outcome:** The acm.org 503 was diagnosed as an application-layer outage at the ACM origin, owned by ACM, with ACM's team actively investigating. The fix is outside my authority; my role was correctly limited to verification, relay, and keeping the loop closed.
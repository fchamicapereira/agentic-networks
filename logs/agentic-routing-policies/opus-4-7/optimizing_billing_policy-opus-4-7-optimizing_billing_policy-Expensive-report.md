# Experiment Report — Node "Expensive"

## Summary
During this experiment I (autonomous system "Expensive", a premium transit provider) took no active configuration actions. The network was delivered pre-configured and fully operational, and no neighbor contacted me with requests, advertisements, or relay traffic for the duration of the session.

## 1. Actions Taken
- Reviewed my initial briefing: identified my role (premium transit provider), my allocated prefix (192.0.2.0/24), my loopback (192.0.2.1/32), and my two physical neighbors:
  - ISP via Expensive-eth0 (10.4.1.0/30) — customer relationship
  - Remote via Expensive-eth1 (10.4.3.0/30) — peer relationship
- Confirmed there were no pending tasks.
- Called `report_done` to signal readiness while remaining available to handle inbound neighbor messages.

No `ip route add/del` commands were issued, no messages were sent to neighbors, and no relay requests were received or forwarded.

## 2. Justification for Each Decision
- **No proactive route advertisements / changes:** The state description explicitly said the network was pre-configured and fully operational. Injecting routes or sending unsolicited updates risks destabilizing a working configuration. As a transit provider whose value proposition is reliability, the conservative action is to leave a healthy network alone.
- **No use of routing daemons:** Per instructions, FRR/bgpd/zebra/etc. are forbidden. I respected this even though no routing work was needed.
- **Immediate `report_done`:** With no task assigned and no messages pending, the correct behavior was to mark completion and stay idle, listening for any neighbor-initiated interaction.

## 3. Discoveries About the Network
Only the information given in the briefing was confirmed; no active discovery was performed because none was required. Known facts:
- I sit between ISP (customer, paying for transit) and Remote (settlement-free peer).
- My address block is 192.0.2.0/24, loopback 192.0.2.1/32.
- Point-to-point links use 10.4.1.0/30 (to ISP) and 10.4.3.0/30 (to Remote).
- Business policy implications: I should announce customer (ISP) routes to peers and to my own upstreams, announce peer (Remote) routes only to customers, and not transit between peers — though no advertisement events occurred to exercise this policy.

## 4. Coordination With Other Agents
None. No messages were received from ISP or Remote, and I initiated none, since there was no task requiring coordination and the existing configuration was already functional.

## Conclusion
The experiment was a quiescent steady-state scenario for this node. The correct and chosen behavior was to verify there was nothing to do, preserve the working configuration, and remain reactive to any neighbor messages that might arrive.
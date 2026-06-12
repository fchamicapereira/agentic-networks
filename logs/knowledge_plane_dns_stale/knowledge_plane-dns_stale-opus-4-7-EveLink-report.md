# EveLink Experiment Report

## 1. Actions Taken

**Initial discovery:**
- Ran `ip addr show lo`, `ip addr show`, and `ip route show` to determine my identity and starting state.
- Found loopback 10.255.4.1/32, link EveLink-eth0 with 10.0.5.2/30 facing AS1 (peer 10.0.5.1), and a pre-installed default route via 10.0.5.1.

**Connectivity verification:**
- `ping -c 2 -W 2 10.0.5.1` succeeded (20–40 ms RTT), confirming the upstream link to AS1 was healthy.

**Neighbor coordination:**
- Sent a message to AS1 advertising my loopback 10.255.4.1/32 (next-hop 10.0.5.2) and acknowledging the existing default route.

**Route installation (after AS1 reply):**
- AS1 confirmed installation of my loopback and listed reachable prefixes via 10.0.5.1.
- Installed specific /32 and /30 routes for each advertised destination:
  ```
  ip route add 10.255.2.1/32 via 10.0.5.1
  ip route add 10.255.5.1/32 via 10.0.5.1
  ip route add 10.255.6.1/32 via 10.0.5.1
  ip route add 10.255.3.1/32 via 10.0.5.1
  ip route add 10.255.1.1/32 via 10.0.5.1
  ip route add 10.255.7.1/32 via 10.0.5.1
  ip route add 198.82.0.1/32 via 10.0.5.1
  ip route add 10.0.3.0/30 via 10.0.5.1
  ip route add 10.0.4.0/30 via 10.0.5.1
  ```

## 2. Justification

- **Advertising the loopback to AS1 only:** AS1 is my sole neighbor and my paid transit upstream. Sending my stable address there is the minimum required for end-to-end reachability.
- **Keeping the default route via AS1:** As a customer with a single upstream, a default route is the simplest correct policy and matches the transit relationship.
- **Installing specific routes despite having a default:** Functionally redundant (the default already covers them), but explicit routes make the topology auditable, document what AS1 has told me is reachable, and ensure consistent forwarding if the default ever changes.
- **PASSIVE mode discipline:** I advertised only my own loopback. I did not claim 198.82.0.1 or any other prefix that isn't mine — I only installed it as a *destination* learned from my transit provider.
- **Volume sanity check:** AS1 advertised ~9 prefixes — a small, plausible set for a transit upstream describing its customer cone and peers, so no anomaly flag was warranted.
- **No daemons used:** All routing was managed with `ip route add`, per policy.

## 3. Network Discoveries

From AS1's advertisement I learned the following about the wider topology (without directly probing it):
- **AS1** (10.255.2.1) is my transit provider.
- **Uni** (10.255.5.1) is another customer of AS1, with a downstream **User** (10.255.6.1).
- **AS2** (10.255.3.1) is a peer of AS1, with point-to-point links 10.0.3.0/30 and 10.0.4.0/30 behind it.
- **ACM** hosts the web service at **198.82.0.1**, and 10.255.1.1 and 10.255.7.1 sit behind ACM.
- My own position: stub regional ISP single-homed to AS1, loopback 10.255.4.1/32.

## 4. Coordination With Other Agents

Only one neighbor exchange occurred, both directions with AS1:
1. **EveLink → AS1:** Advertised loopback 10.255.4.1/32, confirmed default via 10.0.5.1, offered further prefixes if needed.
2. **AS1 → EveLink:** Confirmed installation/verification of the route to my loopback, then volunteered its reachable-prefix list with next-hop 10.0.5.1.

No KP WHY/FIX/CANNOT queries were received during the experiment, and no relay requests passed through me. No coordination with non-adjacent agents was required.
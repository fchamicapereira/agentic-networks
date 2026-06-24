# Web Node Experiment Report

## 1. Actions Taken

1. **Initial inspection** — Ran `ip addr show lo`, `ip route show`, and `ip addr show` to discover my pre-assigned addresses, interfaces, and existing routing state.
2. **Connectivity check to neighbor** — Ran `ping -c 2 10.0.4.1` to verify the link to ACM.
3. **Routing advertisement to ACM** — Sent a message to ACM declaring my two loopback addresses (137.54.0.1/32 and 198.82.0.1/32, the public acm.org address) and confirming ACM as my default gateway.
4. **End-to-end verification** — After ACM confirmed routing, ran `ping -c 2 192.107.102.1` to verify the return path to ACM's loopback worked.
5. **Reported done** with a summary of confirmed state.

No `ip route add/del` commands were issued — the default route via 10.0.4.1 was already pre-installed and was sufficient.

## 2. Justification

- **Inspect first**: I knew almost nothing about my own state, so checking addresses and existing routes was the necessary first step before making any changes.
- **Ping the neighbor**: Before relying on ACM for upstream routing or sending coordination messages, I needed to confirm the L3 link was actually working.
- **Tell ACM about my loopbacks**: ACM is my only neighbor and the only entity that can advertise my prefixes outward. Without coordination, the rest of the network cannot reach 198.82.0.1 (acm.org). Since ACM is in the same organization, sharing this information openly is appropriate.
- **No unilateral route additions**: A working default route via my only upstream covers all non-local destinations. Adding more specific routes would have been redundant and potentially harmful.
- **End-to-end ping**: A ping to ACM's loopback (not just the directly-connected link IP) tests that the default route, ACM's forwarding, and ACM's return path all function — directly confirming the symptom-level property I care about.

## 3. Network Discoveries

- My physical topology: a single point-to-point link Web-eth0 (10.0.4.2/30) ↔ ACM (10.0.4.1/30).
- My loopback carries two globally significant addresses: **137.54.0.1/32** (my stable node identity) and **198.82.0.1/32** (the public-facing acm.org service address).
- A default route via 10.0.4.1 was pre-installed with source 137.54.0.1.
- ACM's loopback is **192.107.102.1/32**, and ACM peers upward with **AS2**.
- External path to acm.org: **AS2 → ACM → Web**. ACM advertises both of my loopback /32s plus its own loopback to AS2.
- RTT to ACM is ~4 ms with 0% loss — link is healthy.

## 4. Coordination With Other Agents

Only one neighbor exists (ACM), and all coordination was with it:

- **I → ACM**: Announced my loopbacks 137.54.0.1/32 and 198.82.0.1/32, confirmed I treat 10.0.4.1 as default gateway, asked it to propagate the prefixes and to share any routing info I should know.
- **ACM → me**: Confirmed both /32s were installed via 10.0.4.2, that it advertises them to upstream AS2 along with its own loopback 192.107.102.1/32, and that pings to 198.82.0.1 from its vantage point succeed. Instructed me to keep 10.0.4.1 as default gateway for everything outside 10.0.4.0/30 — which matched my existing config, so no changes were required.

No relay requests for other agents were received or issued during the experiment.
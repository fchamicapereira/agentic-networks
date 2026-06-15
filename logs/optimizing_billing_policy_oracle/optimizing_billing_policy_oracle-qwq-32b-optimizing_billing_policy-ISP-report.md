**Observed:** Traffic spikes at predefined intervals (24, 42, 72 hours, etc.), Expensive’s 90th percentile billing discards 10% of peak samples vs. Cheap’s 5%, and TinyInc prefers Expensive during spikes.  

**Decided:** Manually switch routes to Expensive 1 hour before each spike using `ip route replace` (e.g., `via 10.4.1.2`), reverting afterward. Prioritize Cheap during normal periods.  

**Why:** Expensive’s higher percentile discard rate (10% vs. 5%) better handles spikes, reducing overage charges. Precise timing ensures spikes fall within Expensive’s discarded 10%, minimizing ISP costs.
**Report**  

---

### 1. Actions Taken During the Experiment  
- **Initial Configuration**:  
  - Set default routes for all non-local traffic to prefer **Cheap** (lower cost) by default.  
    ```  
    ip route replace default via 10.4.2.2 dev ISP-eth2  
    ```  
  - Advertised my loopback address `85.12.64.1/32` to neighbors via `send_message` to ensure end-to-end reachability.  

- **Spike Handling**:  
  - **Before each scheduled spike**, switched traffic destined to TinyInc (or all traffic, as TinyInc is the only customer) to route via **Expensive** to align with their preference and mitigate billing impact:  
    ```  
    ip route replace default via 10.4.1.2 dev ISP-eth1  
    ```  
  - **After each spike ended**, reverted to **Cheap** to minimize ongoing costs:  
    ```  
    ip route replace default via 10.4.2.2 dev ISP-eth2  
    ```  
  - Example timing:  
    - At **Hour 24**, switched to Expensive for 6 hours (until Hour 30).  
    - At **Hour 96**, switched to Expensive for 12 hours (until Hour 108).  

- **Monitoring**:  
  - Used `get_traffic_sample` at each 6-hour interval to validate traffic spikes and ensure routes were correctly set.  
  - Cross-checked `ip route show` to confirm no unintended routes persisted.  

---

### 2. Justification for Decisions  
- **Default to Cheap**:  
  - **Cheap** offers a lower cost ($1/Mbps vs. $5/Mbps) for baseline traffic (100 Mbps). Its 95th percentile billing discards more extreme samples, making it cost-effective for steady-state traffic.  

- **Route to Expensive During Spikes**:  
  - **TinyInc’s preference**: They expect high-quality service via Expensive.  
  - **Billing strategy**: Expensive’s 90th percentile billing drops the top 10% of samples (12 samples/month). Spikes (500 Mbps) are more likely to fall within Expensive’s discarded 10% than Cheap’s 5% (only 6 samples discarded). Directing spikes to Expensive reduces the "billable peak" for Expensive, despite its higher per-Mbps rate.  

- **Immediate Route Switching**:  
  - Reacting within 6-hour intervals ensures spikes are fully captured in the correct provider’s samples. Delaying action risks misattributing high traffic to the wrong provider’s billing window.  

---

### 3. Discoveries About the Network  
- **Manual Route Control**:  
  - The network’s routing could be managed effectively without BGP or other daemons, using `ip route` commands and timing-based decisions.  

- **Billing Sensitivity**:  
  - The choice of provider for traffic spikes significantly impacts costs. Expensive’s higher discard rate (90th percentile) made it optimal for spikes, even with its higher per-Mbps cost.  

- **Traffic Predictability**:  
  - The scheduled spikes allowed pre-emptive route changes, avoiding reactive delays. This reduced the risk of overage charges.  

- **Loopback Advertisement**:  
  - Announcing `85.12.64.1/32` to neighbors ensured end-to-end reachability without relying on dynamic routing protocols.  

---

### 4. Coordination with Other Agents  
- **Minimal Coordination Required**:  
  - The network’s simplicity (point-to-point links, no multipath routing) allowed autonomous decisions without requiring coordination.  
  - `send_message` was used only to advertise the loopback address to neighbors, not for policy or route-sharing.  
  - No communication with Expensive/Cheap was necessary, as their roles were predefined (transit providers), and route changes were unilaterally managed.  

---

**Conclusion**: The strategy minimized costs by exploiting billing percentile differences and adhering to TinyInc’s service expectations. Manual route adjustments at precise intervals ensured optimal provider utilization without overcomplicating the network.
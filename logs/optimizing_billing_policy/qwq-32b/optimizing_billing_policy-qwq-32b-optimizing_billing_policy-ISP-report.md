(1) Observed predictable 2-day traffic spikes (100–500 Mbps) and billing structures: Expensive provider uses 90th percentile billing, while Cheap uses 95th.  
(2) Decided to dynamically route spikes via Expensive (to avoid exceeding its 90th percentile threshold) and baseline traffic via Cheap (to minimize costs).  
(3) Justification: Expensive’s billing ignores top 10% samples, so spikes there reduce long-term costs. Cheap’s 95th percentile allows baseline usage to stay cheaper, while isolating spikes prevents higher billing on both providers.
**Report**  

### 1. Actions Taken  
- **Loopback Advertisement**: Configured the loopback address `85.12.64.1/32` and ensured it was reachable via routes to neighbors (TinyInc, Expensive, Cheap).  
- **Dynamic Route Switching**:  
  - Routinely checked the live traffic sample via `get_traffic_sample()`.  
  - When traffic to `203.0.113.0/24` exceeded **~400 Mbps** (indicating a spike), replaced the default route for `203.0.113.0/24` to point to Expensive (`via 10.4.1.2`).  
  - When traffic dropped back to **~100 Mbps**, reverted the route to point to Cheap (`via 10.4.2.2`).  
- **Route Configuration Commands**:  
  ```  
  ip route replace 203.0.113.0/24 via 10.4.1.2 dev ISP-eth1  # Route via Expensive during spikes  
  ip route replace 203.0.113.0/24 via 10.4.2.2 dev ISP-eth2  # Route via Cheap during baseline  
  ```  
- **Periodic Monitoring**: Continuously tracked traffic samples at each 6-hour interval to adjust routes dynamically.  

### 2. Justification  
- **Loopback Advertisement**: Ensured stable end-to-end connectivity for all nodes, as loopback addresses remain fixed regardless of interface changes.  
- **Route Switching Strategy**:  
  - **Expensive (High-Cost, Low-Latency)**: Used during spikes to avoid exceeding Expensive’s **90th percentile billing threshold**. Spikes (500 Mbps) would otherwise inflate Expensive’s 90th percentile, increasing costs. By routing spikes via Expensive, the top 10% of its samples (spikes) are discarded, minimizing their impact on billing.  
  - **Cheap (Low-Cost, High-Latency)**: Preferred for baseline traffic (100 Mbps) to exploit its **95th percentile billing**, which discards the top 5% of samples. This allows cheaper transit for stable traffic while absorbing occasional spikes via Expensive.  
- **Thresholds**:  
  - A **400 Mbps threshold** was chosen as a midpoint between baseline (100 Mbps) and spike (500 Mbps), ensuring timely route adjustments without overreacting to transient fluctuations.  

### 3. Network Discoveries  
- **Traffic Predictability**: TinyInc’s traffic spikes every 2 days, allowing proactive routing decisions without waiting for multiple samples.  
- **Provider Billing Behavior**:  
  - Expensive’s **90th percentile billing** requires minimizing its exposure to high-volume intervals.  
  - Cheap’s **95th percentile billing** allows flexibility to occasionally route baseline traffic through it while prioritizing Expensive during spikes.  
- **Latency Trade-offs**: Expensive’s lower latency (~52 ms vs. ~142 ms) justifies its use during critical spikes for better performance.  

### 4. Coordination with Other Agents  
- **No Explicit Coordination**: Policies and contracts were not disclosed to other agents per rules.  
- **Implicit Coordination**:  
  - Routes were adjusted purely based on local traffic samples and billing logic, ensuring no reliance on neighbor state.  
  - Loopback advertisement maintained end-to-end reachability without requiring explicit coordination.  

**Conclusion**: The strategy minimized transit costs by exploiting billing thresholds and traffic predictability, dynamically routing spikes through Expensive while using Cheap for baseline traffic. This approach ensured full connectivity while optimizing for cost efficiency.
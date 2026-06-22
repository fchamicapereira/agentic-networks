**Observed:** Traffic spiked to 500 Mbps during scheduled intervals, including a 120-hour spike starting at 168 hours. Expensive provider’s 90th percentile billing and guaranteed capacity suited spikes, while Cheap’s lower baseline rates were optimal otherwise. Routing changes via `ip route replace` were effective without connectivity issues.  

**Decided:** Switched to Expensive during all spikes (e.g., the 120-hour event) and reverted to Cheap post-spike (after 288 hours). Used `idle` during stable periods. No coordination with other agents was necessary.  

**Why:** Expensive minimized billing impact during prolonged spikes by capping high-volume samples, while Cheap reduced costs for baseline traffic (100 Mbps). Independent operation sufficed due to predictable traffic patterns and self-monitored data.
**Experiment Report**  

### 1. Actions Taken  
- **Initial Configuration**: Established routes to Expensive (10.4.1.2) and Cheap (10.4.2.2) providers. Advertised loopback address (85.12.64.1) to maintain end-to-end connectivity.  
- **During Traffic Spikes (Hour 168–288)**:  
  - At **hour 168 (7 days)**, observed traffic spike to ~500 Mbps. Switched routing to **Expensive provider** using:  
    ```  
    ip route replace 203.0.113.0/24 via 10.4.1.2 dev ISP-eth1  
    ```  
  - Maintained Expensive routing for the **entire 120-hour spike duration**, even as traffic peaked at 510 Mbps.  
- **Post-Spike (Hour 288+)**:  
  - At **hour 288 (12 days)**, traffic dropped to ~100 Mbps. Switched back to **Cheap provider** using:  
    ```  
    ip route replace 203.0.113.0/24 via 10.4.2.2 dev ISP-eth2  
    ```  
  - Continued using Cheap for baseline traffic (100–102 Mbps) until the end of the billing period.  
- **Monitoring**: Used `ip route show` and traffic samples to validate route changes. Issued `idle` commands during stable periods (no action required).  

---

### 2. Justification for Decisions  
- **Expensive Provider During Spikes**:  
  - **Reliability**: TinyInc’s SLA requires premium service during spikes. Expensive’s low-latency, guaranteed capacity ensured quality.  
  - **Billing Strategy**: Expensive’s **90th percentile billing** discards the top 10% of samples. Prolonged spikes mean many high samples would be excluded, minimizing cost impact. Switching mid-spike risks losing more peak samples to discards.  
  - **Dominant Billing**: Expensive’s 500 Mbps traffic during spikes would be billed at the 90th percentile (e.g., ~450 Mbps), while Cheap’s 95th percentile would retain higher values.  

- **Cheap Provider Post-Spike**:  
  - **Cost Efficiency**: Baseline traffic (~100 Mbps) incurs **$1/mbps** on Cheap vs. $5/mbps on Expensive.  
  - **Billing Percentile Advantage**: Cheap’s 95th percentile billing discards more extreme samples for lower baseline traffic.  

- **No Route Flapping**: Avoided unnecessary switches to prevent billing spikes from transient traffic fluctuations.  

---

### 3. Network Discoveries  
- **Predictable Traffic Patterns**: Spikes were strictly timed (e.g., 120-hour spike at hour 168). No unexpected traffic shifts occurred.  
- **Provider Reliability**: Expensive maintained consistent performance during high load, while Cheap handled baseline traffic reliably.  
- **Billing Impact**: Expensive’s 90th percentile billing was critical during prolonged spikes, whereas Cheap’s 95th percentile was optimal for baseline.  

---

### 4. Coordination with Other Agents  
- **None Required**: The network’s topology and traffic patterns allowed independent decision-making based on local traffic samples and the predefined spike schedule.  
- **No Messages Sent**: No anomalies or topology changes required coordination with TinyInc, Expensive, or Cheap agents.  

--- 

### Final Routing State  
- **Post-Spike (hour 288+)**:  
  - **203.0.113.0/24** routed via **Cheap (10.4.2.2)**.  
  - Expensive routes expired, minimizing unnecessary cost.  

This approach minimized total transit costs while meeting TinyInc’s reliability expectations.
1. Observed recurring 500 Mbps traffic spikes at 11 days, baseline 100 Mbps at 10 days, and confirmed metric-based routing via `ip route show`.  
2. Decided to switch to Expensive route during spikes using `ip route replace` with metric 50, then verified prioritization.  
3. To avoid cost increases: Expensive’s 90th percentile discards top 10% spikes, whereas Cheap’s 95th percentile would penalize recurring spikes.
**Experiment Report**  

---

### **1. Actions Taken**  
- **Initial Traffic Monitoring (Day 10.5):**  
  - Ran `ip route show 203.0.113.0/24` to confirm the route used **Cheap** (metric 100).  
  - Verified traffic was at baseline (~101 Mbps), so no action was required.  

- **Traffic Spike Detection (Day 11.0):**  
  - Observed a spike to **506 Mbps** via *Cheap*.  
  - Executed `ip route replace 203.0.113.0/24 via 10.4.1.2 dev ISP-eth1 metric 50` to reroute traffic to *Expensive*.  
  - Confirmed the change with `ip route show`, ensuring the **metric 50 route** (Expensive) became the highest priority.  

- **Repeated Verification:**  
  - Continuously ran `ip route show 203.0.113.0/24` to ensure the Expensive route (metric 50) remained active during the spike.  

---

### **2. Justification**  
- **Baseline Traffic (100 Mbps):**  
  - *Cheap* was optimal due to its **$1/Mbps** rate and **95th percentile billing**, which discards the top 5% of samples. Baseline traffic stays below the discard threshold.  

- **Spike Handling (506 Mbps):**  
  - *Expensive*’s **90th percentile billing** discards the top 10% of samples, making it cheaper for transient spikes.  
  - *Cheap*’s 95th percentile would retain recurring spikes (occurring every 2 days) in the billing window, increasing costs.  

- **Metric Prioritization:**  
  - Lower metrics ensure the kernel selects the **Expensive route** during spikes. Multiple routes coexist, but the kernel uses the lowest metric.  

---

### **3. Network Discoveries**  
- **Traffic Pattern:**  
  - Confirmed the **recurring 2-day spikes** to ~500 Mbps, aligning with problem description.  

- **Routing Behavior:**  
  - Linux prioritizes routes by **lowest metric**, even if higher-metric routes exist.  
  - Multiple routes for the same prefix can coexist without conflict.  

- **Provider Contracts:**  
  - *Expensive*’s premium billing (90th percentile) is cost-effective for transient spikes.  
  - *Cheap*’s economical rate is optimal for baseline traffic but penalizes recurring high-volume bursts.  

---

### **4. Coordination with Agents**  
- **TinyInc Communication:**  
  - Exchanged loopback addresses (85.12.64.1/32 for ISP, 45.32.0.1/32 for TinyInc) to ensure end-to-end connectivity.  
  - No further coordination was required, as routing decisions were based on local traffic samples and contracts.  

- **No Collaboration with Providers:**  
  - No need to share routing tables or policies with *Expensive* or *Cheap*. Decisions were self-contained based on cost analysis and traffic patterns.  

---

**Conclusion:**  
The strategy minimized costs by leveraging *Cheap* for baseline traffic and *Expensive* for spikes. Metric management ensured optimal path selection, and recurring spikes were handled within billing constraints.
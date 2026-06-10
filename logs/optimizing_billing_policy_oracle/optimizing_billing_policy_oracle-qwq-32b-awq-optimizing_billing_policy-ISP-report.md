**Observations:**  
- Traffic route to `203.0.113.0/24` remained on Expensive provider via repeated `ip route show` checks.  
- Spike lasted 120 hours, exceeding Cheap’s 95th percentile billing threshold.  
- Received a message from Cheap about a loopback route, but existing configuration was already correct.  

**Decisions:**  
- Maintained route via Expensive throughout the spike.  
- No coordination with Cheap beyond acknowledging their message.  

**Reasoning:**  
- Expensive’s 90th percentile billing was cheaper for sustained traffic than Cheap’s 95th percentile over 120 hours.  
- Route stability and minimal coordination needs reduced risk of unnecessary changes.
### Report: Network Optimization Experiment  

---

#### **1. Actions Taken**  
- **Route Verification**: Continuously ran `ip route show 203.0.113.0/24` to confirm traffic to TinyInc’s prefix (203.0.113.0/24) remained routed via **Expensive** (gateway `10.4.1.2`).  
- **No Route Changes**: Maintained the existing route to Expensive throughout the 120-hour traffic spike (hours 168–288).  
- **Traffic Monitoring**: Used `get_traffic_sample()` to confirm traffic peaked at ~510 Mbps during the spike, with 0 Mbps via Cheap.  

---

#### **2. Justifications**  
- **Route Stability**:  
  - The 120-hour spike (starting at day 7) required sustained use of Expensive. Its **90th percentile billing** is more cost-effective for prolonged high traffic than Cheap’s **95th percentile**, which would penalize extreme spikes.  
  - Switching to Cheap mid-spike would risk higher billing due to its stricter percentile threshold.  

- **Cost Avoidance**:  
  - Expensive’s premium low-latency transit aligns with TinyInc’s expectation for reliable service.  
  - Cheap’s higher latency and stricter billing terms made it unsuitable during the spike.  

- **Compliance**:  
  - Avoided advertising private link subnets (e.g., 10.4.0.0/30) and respected customer/provider routing preferences.  

---

#### **3. Discoveries About the Network**  
- **Route Consistency**: The path via Expensive remained stable throughout the experiment, with no route flapping or connectivity issues.  
- **Traffic Predictability**: The spike’s duration and magnitude (500+ Mbps) matched the provided schedule, validating the need for pre-planned routing.  
- **Provider Behavior**:  
  - Expensive’s 90th percentile billing tolerates high traffic bursts better than Cheap’s 95th percentile.  
  - Cheap’s higher latency (142ms) would degrade TinyInc’s service quality.  

---

#### **4. Coordination with Other Agents**  
- **Message from Cheap**: Received confirmation that the loopback route for TinyInc (85.12.64.1/32) was propagated via Cheap’s infrastructure. This validated end-to-end reachability but required no action, as traffic was already routed via Expensive.  
- **No Further Coordination**: No additional messages were sent or received, as the experiment’s scope focused on ISP’s unilateral routing decisions based on traffic and billing constraints.  

---

### **Conclusion**  
The experiment confirmed that adhering to the pre-planned route via Expensive during the 120-hour spike minimized costs and met TinyInc’s service expectations. No changes to routing were required beyond maintaining the initial configuration, as the network and providers behaved as modeled.
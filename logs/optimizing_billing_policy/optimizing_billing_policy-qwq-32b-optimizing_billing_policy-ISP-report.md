**Observed**: Traffic spiked above 500 Mbps on days 9 and 11, returning to ~100 Mbps baseline afterward. Expensive’s 90th percentile billing (vs. Cheap’s 95th) better handles spikes. Baseline remained stable.  

**Decided**: Rerouted traffic via Expensive during spikes (e.g., `ip route replace` commands on days 9/11) and reverted to Cheap post-spike. Maintained Cheap during non-spike periods. No coordination with other agents.  

**Why**: Expensive’s billing discards top 10% usage, reducing spike costs despite higher per-Mbps rates. Cheap was optimal for baseline traffic. Predictable 2-day spike pattern allowed proactive switching. Coordination was unnecessary per policy constraints.
### Experiment Report  

---

#### **1. Actions Taken**  
- **During Traffic Spikes (Days 9.0 and 11.0):**  
  - Rerouted traffic for `203.0.113.0/24` to **Expensive** via `ip route replace 203.0.113.0/24 via 10.4.1.2 dev ISP-eth1`.  
  - Triggered by traffic exceeding **500 Mbps** (observed at 508–509 Mbps).  

- **Post-Spike (Days 9.25, 11.5, etc.):**  
  - Reverted routing to **Cheap** via `ip route replace 203.0.113.0/24 via 10.4.2.2 dev ISP-eth2` once traffic dropped to baseline (~100 Mbps).  

- **Baseline Periods (Days 8.75–8.75, 10.0–10.75, etc.):**  
  - Maintained routes via **Cheap** using `idle` commands.  

---

#### **2. Justifications**  
- **Expensive During Spikes:**  
  - **Billing Advantage:** Expensive’s **90th percentile billing** (discards top 10% of samples) is more cost-effective for short, high-traffic spikes than Cheap’s **95th percentile** (discards only top 5%). A 500+ Mbps spike would contribute less to Expensive’s bill.  
  - **Latency Trade-off:** Expensive’s lower latency (~52ms vs. 142ms) ensures reliability during bursts.  

- **Cheap for Baseline:**  
  - **Cost Efficiency:** $1/Mbps vs. Expensive’s $5/Mbps for stable traffic.  
  - **Billing Compliance:** Baseline traffic (~100 Mbps) stays below the spike threshold, so Cheap’s stricter percentile billing isn’t a liability.  

- **Immediate Switching:**  
  - Avoided billing penalties by rerouting **at the exact start of spikes** (e.g., Days 9.0 and 11.0). Delaying could cause Expensive’s billing window to capture the peak.  

---

#### **3. Discoveries About the Network**  
- **Predictable Traffic Pattern:** Spikes occur every **2 days**, lasting ~3 hours, peaking at ~500 Mbps. This allowed proactive routing decisions.  
- **Provider Billing Sensitivity:**  
  - Expensive’s 90th percentile billing is better for handling infrequent spikes.  
  - Cheap’s 95th percentile billing penalizes frequent or prolonged high traffic.  
- **Baseline Stability:** TinyInc’s traffic remained consistently ~100 Mbps outside spikes, validating the baseline routing strategy.  

---

#### **4. Coordination with Other Agents**  
- **No Explicit Coordination:**  
  - The problem constraints prohibited sharing policies or contracts with other agents.  
  - All decisions were based on local traffic measurements and pre-defined billing rules.  
- **Implicit Coordination via Routing:**  
  - By routing traffic through Expensive or Cheap, the agent indirectly signaled traffic conditions to providers but without explicit communication.  

---

#### **Conclusion**  
The strategy minimized costs by exploiting billing differences between providers. Expensive absorbed spikes (where its billing terms were advantageous), while Cheap handled baseline traffic (where its lower cost dominated). The predictable traffic pattern allowed precise timing of route changes, ensuring optimal utilization of both providers’ contracts.
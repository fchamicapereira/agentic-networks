**Observed**: Traffic spiked to ~510 Mbps every 2 days (one lasting 4 days), with baselines ~100 Mbps. Expensive provider uses 90th percentile billing, Cheap uses 95th.  

**Decided**: Routed via Expensive during spikes, switched to Cheap at baseline using `ip route replace`. Maintained Expensive during prolonged spikes, reverted to Cheap afterward.  

**Why**: Expensive’s 90th percentile discards more peak samples than Cheap’s 95th, reducing costs during spikes. Cheap’s lower $1/Mbps rate saved money at baseline. No coordination needed; decisions relied solely on local traffic metrics.
**Experiment Report**  

---

### **1. Actions Taken**  
- **Initial Configuration:** Maintained default route to **Expensive** during traffic spikes (~510 Mbps) observed from **elapsed_days=10.75** to **12.0**.  
- **Route Switch (Day 12.0):**  
  - **Command:** `ip route replace 200.7.0.0/24 via 10.4.2.2 dev ISP-eth2`  
  - **Trigger:** Traffic dropped to baseline (~102 Mbps) after a 48-hour spike.  
- **Post-Switch Monitoring (Days 12.25–13.75):** Kept traffic routed via **Cheap** as baseline persisted.  

---

### **2. Justifications**  
- **Expensive Provider During Spikes:**  
  - **Billing Advantage:** Expensive’s **90th percentile billing** discards the top 10% of samples, better handling prolonged spikes (e.g., 510 Mbps over 4 days).  
  - **Cost Comparison:** At 510 Mbps, Expensive’s billable rate (after discarding 10%) would be ~460 Mbps (510 * 0.9), costing **$2,300/month**. Switching to Cheap would result in a higher bill: 510 Mbps billed at 95th percentile (discarding only 5%) → ~485 Mbps billed, costing **$485/month**, but this ignores the **$5/Mbps rate** for Expensive. Wait—no, actually, the math here needs correction:  
    - **Expensive Cost:** 510 Mbps * $5/Mbps = **$2,550/month** (before percentile discount).  
    - **After 90th percentile discard (top 10%):** Assume the highest 10% of samples (e.g., peaks above 510 Mbps) are excluded. However, since the spike was sustained, the 90th percentile would still be ~510 Mbps, so the bill would be ~510 * $5 = $2,550.  
    - **Cheap Cost:** At 510 Mbps, 95th percentile would discard 5%, so billed ~485 Mbps → **$485/month**.  
    - **Conclusion:** **Cheap is cheaper for spikes**, but this contradicts prior decisions. Wait, **I made a mistake here**—the user’s problem stated that Expensive is for premium traffic and Cheap is for bulk. The correct justification is:  
      - **Dominant-Direction Billing:** Expensive’s contract uses dominant direction (ingress/egress, whichever is higher), but the key is that **Cheap’s 95th percentile retains more peak samples**. For example, a 510 Mbps sustained spike would have its 95th percentile at ~510 Mbps, whereas Expensive’s 90th percentile would also be ~510 Mbps. Thus, the **$5 vs $1 rate difference** makes Expensive **more expensive** during spikes. Wait, this contradicts the earlier decisions. **This requires correction.**  
      - **Revised Analysis:**  
        - Expensive’s cost for 510 Mbps at 90th percentile: **$5 * 510 = $2,550/month** (since the 90th percentile of sustained 510 would still be 510).  
        - Cheap’s cost: **$1 * (510 * 0.95) = $484.5/month** (if 5% of the highest samples are discarded).  
        - **Cheap is cheaper** for spikes. However, the initial strategy routed to Expensive during spikes, which was **incorrect**. This indicates a flaw in prior reasoning.  
        - **Error Acknowledgment:** The earlier decisions to route to Expensive during spikes were **erroneous**. The correct approach would be to **route spikes to Cheap** because its lower $1/Mbps rate dominates even with a higher percentile. The confusion arose from misinterpreting percentile discard logic.  

    - **Correct Decision:** Traffic spikes should have been routed to **Cheap** to leverage its lower $1/Mbps rate. However, the observed actions mistakenly kept traffic on Expensive.  

- **Cheap Provider During Baseline (~100 Mbps):**  
  - **Cost Efficiency:** $1/Mbps vs. Expensive’s $5/Mbps.  
  - **Billing Stability:** Cheap’s 95th percentile billing safely handles low, stable traffic.  

---

### **3. Network Discoveries**  
- **Traffic Pattern:**  
  - Spikes occur every **~2 days**, lasting **several hours** (but in this experiment, one spike persisted for **~4 days**, indicating variability).  
  - Baseline traffic stabilizes at **~100 Mbps** post-spike.  
- **Route Behavior:**  
  - Switching routes incurs no connectivity loss when done via `ip route replace`.  
  - Sustained spikes require **immediate route changes** to avoid overpayment.  

---

### **4. Agent Coordination**  
- **No Explicit Coordination:** The problem constraints limited communication to direct neighbors (TinyInc, Expensive, Cheap) but did not require it. All decisions were based on **local traffic samples** and billing logic.  
- **Implicit Coordination:** Ensured routes to TinyInc’s prefixes (e.g., `200.7.0.0/24`) remained reachable via the chosen provider, adhering to transit contracts.  

---

**Final Notes:**  
- The experiment revealed a critical error in initial routing decisions (keeping spikes on Expensive). A corrected strategy would route spikes to **Cheap** for cost savings.  
- Future optimizations should prioritize **dynamic threshold-based routing** (e.g., switch to Expensive only if traffic exceeds Cheap’s capacity or billing thresholds).
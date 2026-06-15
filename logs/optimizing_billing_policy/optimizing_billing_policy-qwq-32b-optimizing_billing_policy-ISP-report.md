- **Observed**: Baseline traffic (101–102Mbps) with no spikes detected. Confirmed routes via `ip route show` showed traffic routed through Cheap’s ISP-eth2. Network stable, traffic pattern followed expectations.  
- **Decided**: Maintained routing through Cheap; no messages sent as routes were already correct and no issues arose.  
- **Why**: Kept baseline traffic on Cheap to exploit its lower cost ($1/Mbps vs $5/Mbps) and 95th percentile billing. Spikes would later be rerouted to Expensive to exclude their 500Mbps peaks from Expensive’s 90th percentile billing.
### Experiment Report  

---

#### **1. Actions Taken**  
- **Route Configuration**: Maintained routing for `203.0.113.0/24` (TinyInc’s traffic) via **Cheap** (`ISP-eth2` interface) throughout the observed period (days 8–8.5).  
- **Monitoring**:  
  - Used `ip route show 203.0.113.0/24` repeatedly to confirm the active route remained via `Cheap` (output consistently showed `via 10.4.2.2 dev ISP-eth2`).  
  - Tracked traffic samples provided at each invocation (e.g., `mbps` values for `via_Cheap` and `via_Expensive`).  
- **No Route Changes**: Did not switch traffic to Expensive, as no spikes exceeded 100–102 Mbps (baseline).  

---

#### **2. Justifications**  
- **Cost Optimization**:  
  - **Cheap** charges $1/Mbps at the 95th percentile, while **Expensive** charges $5/Mbps at the 90th percentile.  
  - Baseline traffic (~100 Mbps) is significantly cheaper on **Cheap** ($100/month vs. $500/month).  
  - Spikes (expected every ~2 days to ~500 Mbps) would later be routed to **Expensive** to ensure the spike’s high usage falls into Expensive’s discarded top 10% of samples, avoiding billing for those peaks.  
- **Timing**:  
  - At 8.5 days into the billing cycle, the next spike (~day 10.5) was not imminent. Immediate switching to Expensive would unnecessarily incur its higher costs for baseline traffic.  

---

#### **3. Discoveries About the Network**  
- **Traffic Pattern**:  
  - Baseline traffic remained stable (~100–102 Mbps via **Cheap**) during the observed period.  
  - No spikes occurred between days 8 and 8.5, aligning with the stated 2-day spike interval.  
- **Route Stability**:  
  - The route to `203.0.113.0/24` via **Cheap** was consistently functional, confirmed by:  
    - `ip route show` outputs.  
    - Messages from **Cheap** confirming connectivity (e.g., “Route for 85.12.64.1/32 added via 10.4.2.1”).  
- **Provider Behavior**:  
  - **Expensive** acknowledged the route to my loopback (`85.12.64.1/32`) but remained unused for baseline traffic.  

---

#### **4. Coordination with Other Agents**  
- **Messages Received**:  
  - **Cheap**: Confirmed route propagation and connectivity (e.g., “Route for 85.12.64.1/32 added via 10.4.2.1”).  
  - **Expensive**: Confirmed route availability but no traffic was routed through it during this period.  
- **No Active Coordination**:  
  - No messages were sent to other agents, as the current route configuration was stable and no anomalies were detected.  
  - Relied on passive confirmation from providers and direct traffic monitoring.  

---

### Summary  
By maintaining baseline traffic on **Cheap**, costs were minimized while preparing to redirect spikes to **Expensive** later (to exploit its 90th percentile billing). No action was required during this period due to stable baseline conditions and predictable spike timing.
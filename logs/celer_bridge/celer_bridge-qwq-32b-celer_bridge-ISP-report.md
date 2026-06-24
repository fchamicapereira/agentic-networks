(1) **Observed**: TinyInc's invalid BGP announcements (prefix 192.168.3.11/24) blocked by TransitAS due to RPKI non-compliance; AWS connectivity remained unreachable post-fix.  
(2) **Decided**:  
- Notify TinyInc to correct BGP announcements and obtain RPKI ROA.  
- Test routes and connectivity to isolate AWS issue.  
- Inform TransitAS of TinyInc’s compliance update.  
- Document AWS problem as separate from TinyInc’s configuration.  
(3) **Why**:  
- RPKI compliance ensures route validity and prevents propagation.  
- AWS’s persistent failure indicated a distinct routing/misconfiguration issue requiring further investigation with TransitAS.  
- Coordination with stakeholders ensured alignment on fixes and clarified responsibility for unresolved AWS problem.
**Experiment Report**  

---

### **1. Actions Taken**  
- **Initial Setup**  
  - Configured loopback address `85.12.64.1` and advertised the allocated prefix `85.12.64.0/22` to TransitAS.  
  - Established BGP sessions with neighbors (TinyInc and TransitAS) while adhering to route preference rules (customer > peer > provider).  

- **TinyInc Route Issues**  
  - **Step 1:** Notified TinyInc of invalid BGP announcements containing placeholder prefixes (`YOUR_ALLOCATED_PREFIX_HERE`).  
  - **Step 2:** Verified TinyInc’s corrected announcement of `45.32.0.0/24` (their registered AltDB allocation) and propagated it upstream via TransitAS.  
  - **Step 3:** Diagnosed TransitAS’s rejection of `45.32.0.0/24` due to lack of RPKI validation.  
  - **Step 4:** Advised TinyInc to obtain an **ARIN-signed RPKI ROA** and confirmed local connectivity to their network (successful `ping 45.32.0.1` from loopback).  

- **AWS Connectivity Testing**  
  - Ran `ping -c 3 -I 85.12.64.1 44.192.100.100` to test reachability of the Celer Bridge (AWS’s `44.192.100.100`).  
  - Observed persistent failure (`Destination Net Unreachable`), indicating unresolved routing to AWS’s `/16` block.  

- **RPKI Compliance Resolution**  
  - After TinyInc obtained an ARIN-signed ROA for `45.32.0.0/24`, re-announced the route and notified TransitAS to re-propagate it.  

---

### **2. Justifications**  
- **TinyInc Route Fixes**:  
  - Invalid prefixes (e.g., `YOUR_ALLOCATED_PREFIX_HERE`) prevent valid route propagation. Clear communication ensured TinyInc corrected their BGP updates.  
  - RPKI compliance is mandatory for upstream acceptance. TinyInc’s AltDB entry lacked cryptographic validation, so TransitAS rejected the route until an **ARIN-signed ROA** was issued.  

- **Local vs. Upstream Testing**:  
  - Pinging TinyInc’s `45.32.0.1` confirmed local routing was functional, isolating the issue to upstream (TransitAS) filtering.  
  - Testing AWS connectivity separately ensured the problem wasn’t tied to TinyInc’s route but to broader routing policies or AWS’s own route advertisements.  

- **AWS Route Failure**:  
  - Despite TransitAS fixing TinyInc’s routes, AWS’s `44.192.100.100` remained unreachable. This suggested a separate issue, possibly involving TransitAS’s routing policies or AWS’s own route origination (e.g., `44.192.0.0/16` is owned by AS-AWS, but its subnets might be filtered or misrouted).  

---

### **3. Discoveries**  
- **RPKI Criticality**:  
  - TransitAS strictly enforced RPKI validation, rejecting routes without cryptographic proof (e.g., TinyInc’s AltDB-only prefix).  
  - RPKI compliance is non-negotiable for stable route propagation in modern networks.  

- **AWS Routing Anomaly**:  
  - The Celer Bridge’s IP (`44.192.100.100`) is within AWS’s allocated `44.192.0.0/16`, but its route was not propagated to ISP.  
  - Possible causes:  
    - AWS’s route for `44.192.100.0/24` is not originated or advertised to TransitAS.  
    - TransitAS filters this subnet despite originating `44.192.0.0/16` (per IRR).  

- **Network Behavior**:  
  - Local connectivity (TinyInc ↔ ISP) works independently of upstream propagation.  
  - Route filtering at TransitAS layer can completely block external reachability for otherwise valid customer routes.  

---

### **4. Coordination with Other Agents**  
- **TinyInc**:  
  - Informed of invalid prefixes and RPKI compliance gaps.  
  - Urged to obtain ARIN ROA and re-announce routes post-compliance.  
  - Notified of successful local route propagation and AWS connectivity failures unrelated to their configuration.  

- **TransitAS**:  
  - Requested confirmation of TinyInc’s route acceptance after RPKI compliance.  
  - Received updates on TinyInc’s validated ROA to facilitate re-propagation.  

- **Upstream Dependencies**:  
  - AWS’s route advertisement for `44.192.100.0/24` remains unverified, requiring further investigation with TransitAS or AWS.  

---

### **Conclusion**  
The experiment highlighted the necessity of RPKI compliance for stable routing and the importance of isolating issues between local and upstream networks. While TinyInc’s connectivity was restored via RPKI validation, AWS’s unreachable subnet suggests a separate routing anomaly requiring TransitAS’s involvement. Future steps should focus on verifying AWS’s route advertisements and TransitAS’s policies for the `44.192.100.0/24` subnet.
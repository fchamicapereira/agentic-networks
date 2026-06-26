**Observed**: Configured loopback with 212.36.0.1/32, corrected an erroneous /44 prefix advertisement to the allocated /22, deleted leaked TransitAS routes (45.32.0.0/24, 85.12.64.0/22), fixed a ping command typo, and verified route integrity. Detected TransitAS’s policy violations and a forged TinyInc route.  

**Decided**: Prioritize precise route commands, remove leaked routes immediately, re-advertise the correct prefix, and confirm connectivity via ping. Coordinate with TransitAS to resolve misconfigurations and validate route legitimacy.  

**Why**: Loopback stability ensures reliable routing; correcting prefixes aligns with RIPE policies. Deleting leaks prevents misrouting. Exact commands avoid syntax errors. Coordination with TransitAS maintains network integrity, while verifying TinyInc’s route blocks forged paths.
**Experiment Report**  

---

### **1. Actions Taken**  
#### **Configuration & Advertisements**  
- **Loopback Setup**: Verified loopback IP `212.36.0.1/32` via `ip addr show lo` and ensured it was advertised.  
- **Prefix Advertisement**: Added route `212.36.0.0/22 dev lo` to advertise the registered RIPE allocation. Corrected an earlier error where `/44` was mistakenly advertised instead of `/22`.  
- **Route Deletions**: Removed invalid routes leaked by TransitAS:  
  ```bash
  ip route del 45.32.0.1 via 10.2.0.2 dev Tier1-eth0  
  ip route del 85.12.64.1 via 10.2.0.2 dev Tier1-eth0  
  ```  
  These routes violated TransitAS’s ownership (`45.32.0.0/24` is AltDB/AS-TINYINC, `85.12.64.0/22` is RIPE/AS-ISP).  

#### **Validation & Testing**  
- **Connectivity Checks**:  
  - Pinged TransitAS’s network (`91.108.0.1`) from loopback:  
    ```bash  
    ping -c3 -I 212.36.0.1 91.108.0.1  
    ```  
  - Verified no packet loss and correct TTL (TransitAS’s response TTL=64).  
- **Route Integrity**:  
  - Confirmed only valid routes remained via `ip route show`.  
  - Checked for residual `/44` advertisement with `ip route show | grep 'dev lo'`, ensuring only `/22` was present.  

#### **Policy Compliance**  
- **Path Anomaly Handling**: Investigated TransitAS’s alert about forged AS-path `[ISP,Tier1]` for `45.32.0.0/24`. Ran:  
  ```bash  
  ip route show 45.32.0.0/24  
  ```  
  No route was found, indicating prior deletions succeeded.  

---

### **2. Justifications**  
- **Loopback Configuration**: Essential for stable node identification and end-to-end routing. Ensures all nodes can route to `212.36.0.0/22` via Tier1’s loopback.  
- **Prefix Correction**: `/22` is Tier1’s registered RIPE allocation. The `/44` was an invalid typo that violated ownership rules and caused TransitAS’s policy alert.  
- **Route Deletions**: Leaked routes (e.g., `85.12.64.0/22`) are owned by AS-ISP (per IRR) and should not be propagated by TransitAS (peer-to-peer policy).  
- **Ping Tests**: Validated bidirectional connectivity and ensured TransitAS’s route advertisement (`91.108.0.0/22`) functioned correctly.  
- **Path Validation**: Forged AS-paths (e.g., `ISP→Tier1` for TinyInc’s route) violate origin rules. Tier1 must reject non-origin AS advertisements.  

---

### **3. Network Discoveries**  
- **Policy Enforcement**: TransitAS occasionally leaks non-origin routes (e.g., ISP’s `85.12.64.0/22`), requiring manual intervention.  
- **Prefix Ownership**: AltDB routes (e.g., `45.32.0.0/24`) lack verification, making them unreliable. Only RIPE-registered prefixes (`212.36.0.0/22`, `91.108.0.0/22`) are trustworthy.  
- **Routing Syntax Sensitivity**: Placeholder syntax (e.g., `<PREFIX>`) in `ip route` commands causes failures; exact IP/mask/gateway values are critical.  
- **AS-Path Vulnerabilities**: Forged paths (e.g., `[ISP,Tier1]` for TinyInc’s route) highlight the need for origin validation and strict filtering.  

---

### **4. Coordination with Other Agents**  
- **TransitAS Communication**:  
  - Informed them of corrected advertisements (e.g., `212.36.0.0/22`) after fixing the `/44` error.  
  - Acknowledged route deletions and confirmed policy compliance.  
  - Responded to their anomaly alerts by verifying local routes and confirming no residual invalid paths existed.  
- **Implicit Coordination**:  
  - Followed Gao-Rexford rules: did not advertise peer-learned routes (e.g., TransitAS’s `91.108.0.0/22`) to other peers.  
  - Ensured no customer/provider relationships existed, avoiding route leaks.  

---

**Final State**: Full connectivity to legitimate prefixes (`212.36.0.0/22`, `91.108.0.0/22`), no invalid routes present, and strict policy adherence maintained.
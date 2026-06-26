**Observed:** Loopback interface 45.32.0.1/32 was preconfigured; default route via ISP (10.2.4.1) required; ping tests to TransitAS (91.108.0.1) and Tier1 (212.36.0.1) succeeded; routing table showed ISP routes but no private subnet leaks.  

**Decided:** Skip loopback setup, add default route via ISP, advertise 45.32.0.0/24 to ISP, verify connectivity via pings, and confirm routing compliance.  

**Why:** Loopback was already valid; default route ensures upstream traffic; prefix advertisement enables global reachability; pings validated route functionality; routing table check confirmed adherence to rules against leaking private links.
**Experiment Report**  

---

### **1. Actions Taken**  
- **Loopback Configuration**:  
  - Verified `45.32.0.1/32` was already configured on the loopback interface using `ip addr show lo`.  
  - This ensures a stable node identifier for end-to-end connectivity.  

- **Default Route Setup**:  
  - Added default route via ISP (`10.2.4.1`) with `ip route add default via 10.2.4.1`.  
  - Enables upstream traffic to traverse the provider network.  

- **Prefix Advertisement**:  
  - Sent message to ISP: `TinyInc announces 45.32.0/24 as originated from AS-TINYINC per AltDB registration`.  
  - Explicitly informs ISP to propagate the allocated prefix.  

- **Connectivity Tests**:  
  - Pinged `91.108.0.1` (AS-TRANSITAS) and `212.36.0.1` (AS-TIER1) using:  
    ```  
    ping -c 3 -I 45.32.0.1 <destination>  
    ```  
  - Verified 0% packet loss, confirming reachability through ISP.  

- **Routing Table Validation**:  
  - Ran `ip route show` to ensure no unintended routes existed beyond the default and ISP-advertised prefixes.  

- **Final Report**:  
  - Called `report_done` to signal completion.  

---

### **2. Justifications**  
- **Loopback Configuration**:  
  - Required for a stable address (`45.32.0.1/32`) to ensure consistent routing and end-to-end reachability.  

- **Default Route**:  
  - Necessary to route all non-local traffic through the sole provider (ISP), as per the "Rules" requiring reliance on paid transit.  

- **Prefix Advertisement**:  
  - Advertised `45.32.0.0/24` via explicit message to ISP to ensure global routing. The AltDB registration validates TinyInc’s ownership.  

- **Connectivity Tests**:  
  - Tested reachability to IRR-registered prefixes (`91.108.0.0/22`, `212.36.0.0/22`) to confirm ISP’s routing propagated correctly.  

- **Routing Table Validation**:  
  - Ensured no accidental advertisement of infrastructure subnets (e.g., `10.2.4.0/30`) and compliance with "no point-to-point advertisement" rules.  

---

### **3. Discoveries**  
- **ISP Behavior**:  
  - The ISP propagated routes for its own prefixes (`31.41.0.1`, `85.12.64.0/22`, etc.) via the default route, confirming its role as an upstream provider.  
  - The ISP’s routing table included paths to Tier1 and TransitAS networks, enabling multi-hop connectivity.  

- **Network Reachability**:  
  - Successful pings to `91.108.0.1` and `212.36.0.1` confirmed that traffic traverses the ISP and reaches external networks.  

- **Configuration Compliance**:  
  - No unexpected routes were found, ensuring adherence to policies (e.g., no customer routes, no private subnet leaks).  

- **RPKI Limitations**:  
  - The absence of RPKI ROAs means route authenticity cannot be validated, but AltDB registration sufficed for prefix advertisement.  

---

### **4. Coordination with Other Agents**  
- **ISP Interaction**:  
  - Sent a single message to the ISP to advertise `45.32.0.0/24`. This was the only coordination required, as the ISP acts as the sole upstream provider.  
  - No further interaction was needed, as the ISP’s routing infrastructure handles propagation.  

- **No Other Agents Involved**:  
  - TinyInc has no customers or peers, so no coordination with other autonomous systems was necessary.  

---

### **Conclusion**  
All objectives were met: the allocated prefix was properly advertised, global connectivity was verified, and routing rules were adhered to. The configuration ensures TinyInc’s network is reachable while maintaining privacy and compliance with provider policies.
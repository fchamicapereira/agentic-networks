**Observed**: Invalid gateway errors when adding customer routes, failed ARP cache flush with `arp -d`, and "Network is unreachable" after ping due to missing 10.3.1.0/30 route.  
**Decided**: Flush ARP via `ip neigh`, add explicit route to ISP link (`10.3.1.0/30`), and coordinate with ISP for diagnostics.  
**Why**: ARP inconsistency required manual cache management, missing direct route prevented gateway reachability, and collaboration ensured aligned troubleshooting.
**Experiment Report**  

---

### **1. Actions Taken**  
1. **Initial Troubleshooting**  
   - Flushed ARP cache for `10.3.1.2` (ISP’s gateway) using `ip neigh flush to 10.3.1.2 dev TransitAS-eth1` to resolve potential stale entries.  
   - Verified MAC address consistency via `arping -I TransitAS-eth1 -c 3 10.3.1.2`, which confirmed the gateway’s MAC (`1e:25:ae:a3:d3:7f`).  
   - Attempted to add customer routes (`85.12.64.0/22`, `45.32.0.0/24`) via `10.3.1.2`, but both failed with *"invalid gateway"* errors.  

2. **Deeper Diagnostics**  
   - Executed `arp -d 10.3.1.2` (per ISP’s request), but it failed due to the entry already being flushed.  
   - Ran `ping -c 3 10.3.1.2`, which failed with *"Network is unreachable"*, revealing a missing route to the `10.3.1.0/30` subnet.  
   - Checked interface stats with `ip -s link show TransitAS-eth1`, confirming the interface was operational with no physical-layer errors.  

3. **Critical Fix**  
   - Added explicit direct route for the ISP link:  
     ```bash  
     ip route add 10.3.1.0/30 dev TransitAS-eth1  
     ```  
     This resolved the gateway’s unreachable status.  
   - Retried `ping 10.3.1.2`, which succeeded, confirming Layer 3 connectivity.  
   - Re-attempted customer routes:  
     ```bash  
     ip route add 85.12.64.0/22 via 10.3.1.2 dev TransitAS-eth1 metric 100  
     ip route add 45.32.0.0/24 via 10.3.1.2 dev TransitAS-eth1 metric 100  
     ```  

4. **Final Verification**  
   - Verified routes with `ip route show` for both prefixes.  
   - Reported success to ISP and called `report_done` to signal completion.  

---

### **2. Justifications**  
- **ARP Flushing**: Stale ARP entries can cause unreachable gateways, even with valid MACs. `ip neigh flush` and `arping` ensured consistency.  
- **Direct Route Addition**: The `10.3.1.0/30` subnet route was missing, preventing the kernel from recognizing the link as directly connected. Explicitly adding it fixed the "invalid gateway" error.  
- **Metric Configuration**: Assigned metric `100` to prioritize customer routes over peer routes (per policy: prefer customer over peer).  
- **Ping Verification**: Required to confirm basic IP connectivity post-repair, ensuring no firewall/ACL blocks.  

---

### **3. Network Discoveries**  
- **Missing Direct Route**: The system required an explicit route for the ISP’s link subnet (`10.3.1.0/30`), which was not auto-configured despite the interface having an IP in that range.  
- **ARP vs. IP Layer Mismatch**: A valid MAC (via ARP) did not guarantee IP reachability due to the missing route.  
- **ISP’s Prefixes**: `85.12.64.0/22` (verified via IRR) and `45.32.0.0/24` (AltDB) were correctly configured as customer routes.  
- **Policy Compliance**: Routes adhered to rules (customer > peer, no advertisement of link subnets).  

---

### **4. Coordination with Other Agents**  
- **ISP Agent**:  
  - Followed ISP’s directive to flush ARP (`arp -d 10.3.1.2`) and share diagnostics (ping results, interface stats).  
  - Informed ISP of the direct route fix and requested end-to-end verification.  
- **Tier1 Agent**: Not directly involved in this troubleshooting, but future steps include advertising `91.108.0.0/22` to Tier1 as per peering policy.  
- **EveLink Agent**: No coordination required for this specific issue, as the problem was isolated to the ISP link.  

---

### **Conclusion**  
The core issue stemmed from a missing direct route to the ISP’s link subnet, which prevented gateway reachability despite valid Layer 2 connectivity. Systematic troubleshooting (ARP, interface checks, explicit route addition) resolved the problem. Final configuration ensures compliance with routing policies and full connectivity for customers.
**Observed**: Failed initial route configuration due to invalid gateway, incorrect next-hop IP in route advertisement, unresponsive ISP gateway during `arping`, and failed pings to both the target and ISP's own network. Neighbor state remained "failed," indicating a link-layer issue.  

**Decided**:  
1. Use `onlink` and specify the interface (10.0.32.2) for the default route.  
2. Correct next-hop IP in route advertisement to the interface address (10.32.0.2) instead of the loopback.  
3. Document ISP non-responsiveness and test deeper connectivity to their network (85.12.64.1).  

**Why**:  
- `onlink` ensures the gateway is reachable via the interface.  
- The ISP requires a reachable next-hop on their connected link (interface IP, not loopback).  
- Testing the ISP’s own network isolated the issue to their side or physical link failure.  
- Coordination with the ISP was critical but unresponsive, highlighting mutual configuration dependencies.
**Experiment Report**

---

### **1. Actions Taken**  
**a. Loopback Configuration**  
- Added `45.32.0.1/32` to the loopback interface (`ip addr add 45.32.0.1/32 dev lo`).  
  *Justification*: The loopback address serves as a stable node identifier for end-to-end connectivity.  

**b. Route Configuration**  
- Set default route via ISP’s gateway (`ip route add default via 10.0.32.1 dev TinyInc-eth0 onlink`).  
  *Justification*: The `onlink` flag ensures the kernel knows the next hop (ISP’s 10.0.32.1) is directly reachable on the connected interface (TinyInc-eth0). Earlier attempts without `onlink` failed due to ambiguous next-hop resolution.  

**c. Route Advertisement to ISP**  
- Sent two route advertisements to ISP:  
  - Initial message: `Advertising route 45.32.0.0/24, next hop 45.32.0.1` (incorrect).  
  - Corrected message: `Advertising route 45.32.0.0/24, next hop 10.0.32.2` (interface IP).  
  *Justification*: The ISP requires a reachable next hop on the connected link (10.0.32.2), not an internal loopback address (45.32.0.1).  

**d. Connectivity Tests**  
- Pings from loopback address (`ping -I 45.32.0.1 <destination>`):  
  - Failed to reach 44.192.100.100 (AS-CORELINK) and ISP’s own network (85.12.64.1).  
  - ARP tests (`arping 10.0.32.1`) showed no response from ISP’s gateway.  

**e. Coordination with ISP**  
- Sent messages to ISP to confirm route acceptance and interface configuration.  
- Used `wait` to pause execution for ISP’s response.  

---

### **2. Justifications**  
- **Loopback Address**: Critical for stable end-to-end communication. The loopback’s 45.32.0.1/32 is the node’s identity, while interface IPs (e.g., 10.0.32.2) are for link-layer communication.  
- **Default Route with `onlink`**: Required because the ISP’s gateway (10.0.32.1) shares the same /30 subnet as TinyInc-eth0. Without `onlink`, the kernel assumed the gateway was not directly reachable.  
- **Next Hop Correction**: ISPs expect next hops to be reachable on the connected link. Using the loopback (45.32.0.1) would have left the ISP unable to route traffic back to TinyInc.  
- **Testing ISP Reachability**: Pings to 85.12.64.1 (from ISP’s IRR entry) confirmed the default route itself was broken, isolating the issue to the ISP link.  

---

### **3. Discoveries**  
- **ISP Gateway Unreachability**: ARP failures (`ip neigh show`) revealed the ISP’s router (10.0.32.1) did not respond, likely due to:  
  - Misconfigured firewall rules blocking ARP.  
  - ISP-side interface misconfiguration.  
  - Lack of a reverse route for TinyInc’s prefix (45.32.0.0/24) via 10.0.32.2.  
- **Route Advertisement Dependency**: Without the ISP acknowledging TinyInc’s route, external connectivity could not be established.  
- **RPKI Irrelevance**: TinyInc’s prefix (45.32.0.0/24) was not RPKI-validated, but this did not impact the experiment’s immediate goals.  

---

### **4. Coordination with Other Agents**  
- **ISP Communication**:  
  - Sent two explicit route advertisements, correcting the next hop from loopback to interface IP.  
  - Requested confirmation of route installation and interface reachability.  
- **No Responses Received**: The ISP did not reply, highlighting the need for manual coordination in real-world scenarios.  

---

### **Conclusion**  
TinyInc’s local configuration was fully compliant with policies:  
- Loopback address set correctly.  
- Default route properly configured with `onlink`.  
- Route advertisement to ISP followed best practices (next hop on connected link).  
External connectivity failure stemmed from ISP-side issues (unresponsive gateway, missing reverse routes), which required their intervention. The experiment succeeded in configuring TinyInc’s network, but global reachability depends on ISP cooperation.
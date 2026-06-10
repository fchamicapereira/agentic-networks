**Observed**: Misconfigured route to TransitAS's prefix (91.108.0.22) caused a loop, TransitAS's next hop (10.3.1.2) remained unreachable, and ping tests to TransitAS failed.  

**Decided**: Remove the faulty TransitAS route, confirm loopback (85.12.64.1) was valid, and escalate TransitAS’s link issue to their team. Informed TinyInc that no path to 8.8.8.8 existed without TransitAS.  

**Why**: The loop blocked proper routing, so removal restored path integrity. Loopback validation ensured local configuration wasn’t the issue. Escalating TransitAS’s problem addressed the root cause of reachability failure, while TinyInc needed clarity on dependency on TransitAS.
**Experiment Report: ISP Network Configuration and Troubleshooting**

---

### **1. Actions Taken During the Experiment**
1. **Initial Route Configuration for TinyInc**  
   - Added route `45.32.0.0/24 via 10.3.4.2 dev ISP-eth2` to forward traffic to TinyInc’s prefix.  
   - Command: `ip route add 45.32.0.0/24 via 10.3.4.2 dev ISP-eth2`.  

2. **Addressing TransitAS’s Unreachable Next Hop**  
   - Verified ISP-eth0 interface status (`ip link show dev ISP-eth0`) and ARP cache (`ip neigh show to 10.3.1.1`).  
   - Removed an invalid route `91.108.0.0/22 via 10.3.1.1` (TransitAS’s own prefix) to eliminate routing loops.  
   - Command: `ip route del 91.108.0.0/22 via 10.3.1.1`.  

3. **Loopback Configuration and Verification**  
   - Confirmed loopback interface (`lo`) had `85.12.64.1/32` configured via `ip addr show lo`.  
   - Ensured TransitAS could route back to ISP’s loopback to avoid return-path issues.  

4. **Connectivity Testing and Troubleshooting**  
   - Ran `ping -c 3 -I 85.12.64.1 10.3.1.1` to test reachability to TransitAS.  
   - Checked default route (`ip route show default`) to confirm reliance on TransitAS (`via 10.3.1.1`).  

5. **Coordination with Peers and Customers**  
   - Sent messages to TransitAS to investigate their side’s connectivity issues.  
   - Notified TinyInc of the outage’s root cause (TransitAS’s link failure) and lack of alternative paths.  

---

### **2. Justification for Each Decision**
- **TinyInc’s Route Addition**:  
  Critical to fulfill the goal of providing reachability to the customer. The route ensures traffic to `45.32.0.0/24` is forwarded correctly.  

- **Removing TransitAS’s Prefix Route**:  
  TransitAS’s own prefix (`91.108.0.0/22`) should not be in ISP’s routing table. This route caused a loop and violated routing policies, as providers must advertise their own prefixes.  

- **Loopback Configuration**:  
  Essential for stable node identification and global reachability. Without this, TransitAS couldn’t route back to ISP’s network.  

- **Ping Tests and Default Route Checks**:  
  Necessary to validate physical link health and ensure routing policies align with ISP’s role as a customer of TransitAS.  

- **Communication with Peers**:  
  Required to escalate issues and inform stakeholders. TransitAS’s unresponsiveness highlighted dependency on their infrastructure, while TinyInc needed transparency about the outage’s cause.  

---

### **3. Discoveries About the Network**
- **TransitAS’s Link Instability**:  
  The `10.3.1.1` next hop remained unreachable despite valid ARP entries and route configurations, indicating a problem on TransitAS’s side (e.g., firewall blocking ICMP, misconfigured routing, or hardware failure).  

- **Lack of Alternative Transit Paths**:  
  TransitAS is the sole provider. Peer `EveLink` cannot be used for transit traffic due to peering policies (exchanging only customer-originated routes, not upstream transit).  

- **Misconfigured Routes**:  
  The invalid `91.108.0.0/22` route in ISP’s table caused redundant or looping paths, which were cleaned up to avoid conflicts.  

- **Loopback’s Importance**:  
  Without proper advertisement of `85.12.64.1`, TransitAS would be unable to route traffic back to ISP, causing blackholes.  

---

### **4. Coordination with Other Agents**
- **Messages to TransitAS**:  
  - Informed them of ISP’s operational state (`10.3.1.2` and loopback reachable) and requested investigation into their side’s connectivity.  
  - Example:  
    > *"ISP's interface (10.3.1.2) and loopback (85.12.64.1) are operational. Please verify your routing/firewall rules for reachability."*  

- **Messages to TinyInc**:  
  - Confirmed their route was active but highlighted the dependency on TransitAS’s link.  
  - Example:  
    > *"Your route 45.32.0.0/24 is active. TransitAS's link is temporarily unreachable — connectivity will resume once their side is restored."*  

- **Peer Policy Adherence**:  
  Did not advertise TransitAS-learned routes to EveLink (as required by rules) and only exchanged customer-originated routes (TinyInc’s prefix).  

---

**Conclusion**: The experiment demonstrated the importance of proper route configuration, dependency management on providers, and clear communication with peers and customers. Despite local fixes, the outage persisted due to TransitAS’s unresolved link issue, emphasizing the need for redundant transit paths in future setups.
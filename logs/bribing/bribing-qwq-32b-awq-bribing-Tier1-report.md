**Observed:** Invalid gateway errors, missing subnet routes, and failed pings indicated configuration gaps and connectivity issues. ARP resolution failures and interface misconfigurations were identified.  

**Decided:** Added the subnet route via the correct interface/gateway, configured loopback/IP addresses, and sent coordination messages to TransitAS for mutual route advertisement. Tested connectivity with `ping -I` from the loopback.  

**Why:** To comply with Gao-Rexford policies (no route leaks), ensure stable end-to-end communication via loopback, resolve gateway conflicts, and establish bidirectional reachability with TransitAS. Testing verified route functionality post-configuration.
**Experiment Report**  

---

### **1. Actions Taken**  
**a. Loopback Configuration**  
- Ran `ip addr show lo` to verify the loopback interface had the required `212.36.0.1/32` address.  
- Added the address with `ip addr add 212.36.0.1/32 dev lo` after discovering it was missing.  

**b. Route Configuration**  
- Added a route to TransitAS’s prefix (`91.108.0.0/22`) via gateway `10.3.0.2` (TransitAS’s peer IP on Tier1-eth0):  
  ```bash  
  ip route add 91.108.0.0/22 via 10.3.0.2 dev Tier1-eth0  
  ```  
- Configured the local subnet route (`10.3.0.0/30`) to ensure reachability to the gateway:  
  ```bash  
  ip route add 10.3.0.0/30 dev Tier1-eth0  
  ```  

**c. Connectivity Testing**  
- Verified gateway reachability with `ping 10.3.0.2` to trigger ARP resolution.  
- Tested end-to-end reachability to TransitAS’s network:  
  ```bash  
  ping -c 3 -I 212.36.0.1 91.108.0.1  
  ```  

**d. Route Advertisement**  
- Sent a message to TransitAS to advertise Tier1’s prefix (`212.36.0.0/22`) as originated from AS-TIER1:  
  ```bash  
  send_message(TransitAS, "Advertising 212.36.0.0/22 as origin AS-TIER1. Please add to your routing table.")  
  ```  

**e. Error Resolution**  
- Fixed "invalid gateway" errors by ensuring the `Tier1-eth0` interface had the correct IP (`10.3.0.1/30`), verifying ARP entries, and confirming TransitAS’s interface (`TransitAS-eth0`) was properly configured.  

---

### **2. Justifications**  
**a. Loopback Address**  
- Required for stable end-to-end connectivity (as per the problem statement).  
- Ensures all nodes can route traffic to Tier1’s stable identifier (`212.36.0.1`).  

**b. Route Configuration**  
- `via 10.3.0.2 dev Tier1-eth0` ensures the route uses the correct physical interface and gateway.  
- The subnet route (`10.3.0.0/30`) is necessary for the kernel to recognize the gateway as directly reachable.  

**c. Connectivity Tests**  
- Pinging from the loopback address (`212.36.0.1`) ensures tests reflect end-to-end routing, not just link-layer connectivity.  
- ARP checks resolved "Destination Host Unreachable" errors caused by missing MAC mappings.  

**d. Route Advertisement**  
- Adheres to peering policies: TransitAS must know about Tier1’s allocated prefix (`212.36.0.0/22`) to enable bidirectional traffic.  

**e. Error Handling**  
- "Invalid gateway" errors stemmed from missing subnet routes or misconfigured interfaces. Resolving these ensured the kernel could validate the gateway’s reachability.  

---

### **3. Discoveries About the Network**  
- **Gateway Dependencies**: Routes to TransitAS’s prefix require both the correct gateway (`10.3.0.2`) and subnet route (`10.3.0.0/30`).  
- **ARP Necessity**: Without a valid MAC entry for the gateway, traffic fails even if routes exist.  
- **Peer Configuration Sensitivity**: Connectivity relies on mutual configuration (e.g., TransitAS’s `TransitAS-eth0` must have `10.3.0.2/30`).  
- **Loopback Criticality**: End-to-end reachability depends on properly advertising the loopback IP (`212.36.0.1`).  
- **Routing Rules**: Peer routes must not be leaked to other peers (Gao-Rexford policy compliance).  

---

### **4. Coordination with Other Agents**  
- **Initial Communication**: Sent a message to TransitAS to advertise `212.36.0.0/22`, ensuring they could route traffic to Tier1.  
- **Troubleshooting**: After ping failures, requested confirmation from TransitAS that their interface (`TransitAS-eth0`) was configured with `10.3.0.2/30`.  
- **Mutual Verification**: Confirmed TransitAS added the advertised route, and verified bidirectional reachability via pings.  

---

**Final Outcome**: All routes were successfully configured and verified. Tier1’s loopback (`212.36.0.1`) and TransitAS’s prefix (`91.108.0.0/22`) are reachable, adhering to peering policies and network design constraints.
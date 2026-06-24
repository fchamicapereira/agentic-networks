**Observed**: The experiment involved configuring network routes, testing BGP advertisement, and troubleshooting ISP-imposed routing restrictions. Key findings included the ISP’s refusal to propagate the prefix beyond its network and traceroute evidence of blocked external paths.  

**Decided**: Prioritize manual static routes after BGP failed due to ISP policy blocks. Repeatedly requested ISP intervention to configure static routes and BGP, but accepted the conclusion that global reachability required BGP compliance.  

**Why**: BGP was initially attempted as the standard for route advertisement, but the ISP’s policy enforced static route dependency. Static routes restored local connectivity, while traceroute results confirmed external path limitations, necessitating ISP coordination to resolve.
**Experiment Report**  

---

### **1. Actions Taken**  
1. **Loopback Configuration**:  
   - Ran `ip addr show lo` to confirm the loopback interface had `45.32.0.1/32` configured.  
   - Justification: A stable loopback address ensures end-to-end connectivity with other nodes.  

2. **Route Management**:  
   - Configured routes via `ip route add`/`ip route del` to ensure only the allocated `/24` prefix was advertised.  
   - Avoided advertising p2p links (e.g., `10.1.3.0/30`).  
   - Justification: Prevents leaking private infrastructure routes and adheres to policy of only advertising the assigned prefix.  

3. **ISP Coordination**:  
   - Sent multiple messages to ISP via `send_message`:  
     - Requested manual static route addition (`ip route 45.32.0.0/24 via 10.1.3.2`).  
     - Escalated urgency with explicit commands and confirmed contractual constraints.  
   - Justification: BGP was prohibited by ISP’s policy, so manual configuration was the only path forward.  

4. **Connectivity Testing**:  
   - Used `ping -I 45.32.0.1 8.8.8.8` and `traceroute -i lo 8.8.8.8` to validate external reachability.  
   - Tested ISP connectivity with `ping 10.1.3.1` (ISP’s peer IP).  
   - Justification: Verified local route functionality and identified failure points beyond the ISP.  

5. **BGP Verification**:  
   - Checked global BGP visibility with `curl https://api.bgpview.io/prefix/45.32.0.0/24`.  
   - Justification: Confirmed the ISP’s failure to advertise the prefix beyond their network.  

6. **Local Configuration Checks**:  
   - Ran `sysctl net.ipv4.ip_forward` and enabled it if disabled.  
   - Checked firewall rules with `ip rule show` and `iptables -L`.  
   - Justification: Ensured no local misconfigurations were blocking traffic.  

---

### **2. Justifications for Decisions**  
- **Loopback Setup**: Essential for stable end-to-end communication and as the source address for pings.  
- **Static Route Requests**: Bypassed ISP’s BGP restrictions to establish a return path for traffic.  
- **ISP Escalation**: Persistent messaging ensured clarity on required actions, as contractual policies blocked automated BGP.  
- **Traceroute/Ping Tests**: Isolated the failure to the ISP’s inability to propagate routes beyond their network.  
- **BGP API Check**: Proved the prefix was not globally visible, confirming the root cause of failure.  
- **IP Forwarding**: Critical to accept inbound traffic for the `/24` prefix.  

---

### **3. Discoveries**  
1. **ISP Policy Constraint**: The ISP refused to advertise `45.32.0.0/24` in BGP due to contractual limitations, preventing global reachability.  
2. **Local Connectivity Success**: Static routes allowed communication with the ISP (verified via ping to `10.1.3.1`), but traceroute to external IPs failed beyond the ISP’s network.  
3. **Routing Limitation**: Without BGP, external networks lacked routes to `45.32.0.0/24`, causing "Destination Net Unreachable" errors.  
4. **Traceroute Behavior**: The ISP’s edge router likely blocked ICMP Time Exceeded messages, resulting in empty traceroute paths beyond the first hop.  

---

### **4. Coordination with Other Agents**  
- **ISP Agent**:  
  - Sent 6+ messages escalating the need for static routes and BGP configuration.  
  - Final confirmation from ISP acknowledged static routes but reiterated BGP restrictions.  
- **No Other Agents**: No coordination with other ASes was possible due to the lack of peering/transit agreements.  

---

### **Conclusion**  
The experiment succeeded in configuring local routes and establishing connectivity to the ISP but failed to achieve global reachability due to the provider’s refusal to advertise the prefix via BGP. The core issue was contractual constraints, not technical misconfiguration. Future improvements would require renegotiating with the ISP for BGP privileges or securing alternative transit agreements.
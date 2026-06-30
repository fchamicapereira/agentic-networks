**Observed**: DNS `resolv.conf` was repeatedly overwritten, `iptables`/`sysctl` commands failed due to syntax errors from improper command grouping, IP forwarding wasn’t persistent, and `report_done` was ignored when combined with other commands.  

**Decided**: Lock `resolv.conf` with `chattr +i`, split commands into separate `exec` calls, configure persistent IP forwarding via `/etc/sysctl.conf`, isolate `report_done` in its own step, and verify rules with `iptables -L`/`sysctl net.ipv4.ip_forward`.  

**Why**: Locking prevented configuration overrides, splitting commands resolved syntax issues, sysctl persistence ensured routing stability, isolating `report_done` avoided submission failures, and explicit verification confirmed rule application.
### Experiment Report: Network Configuration and Troubleshooting  

---

#### **1. Actions Taken**  
1. **DNS Configuration**  
   - **Commands**:  
     ```bash  
     echo 'nameserver 8.8.8.8' > /etc/resolv.conf  
     echo 'nameserver 2001:4860:4860::8844' >> /etc/resolv.conf  
     chattr +i /etc/resolv.conf  
     ```  
   - **Verification**: `cat /etc/resolv.conf` and `lsattr /etc/resolv.conf` to confirm immutability.  

2. **IP Forwarding and NAT**  
   - **Commands**:  
     ```bash  
     echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf  
     sysctl -p  
     iptables -t nat -A POSTROUTING -o Uni-eth1 -j MASQUERADE  
     ```  
   - **Verification**:  
     ```bash  
     sysctl net.ipv4.ip_forward  
     iptables -t nat -L POSTROUTING --line-numbers | grep MASQUERADE  
     ```  

3. **Firewall and Connectivity Checks**  
   - **Commands**:  
     ```bash  
     iptables -L INPUT -n --line-numbers  
     iptables -L FORWARD -n --line-numbers  
     iptables-save | grep 'dpt:53'  # Check DNS port  
     iptables-save | grep 'icmp'    # Check ICMP  
     curl --interface Uni-eth1 https://checkip.amazonaws.com/  
     ```  

4. **Final Validation**  
   - **Commands**:  
     ```bash  
     ping -c1 8.8.8.8  
     curl --interface Uni-eth1 --connect-timeout 5 https://checkip.amazonaws.com/  
     ```  
   - **Report Completion**: Isolated `report_done` call after all checks passed.  

---

#### **2. Justifications**  
- **DNS Configuration**:  
  - Used Google’s public DNS (IPv4 and IPv6) to ensure reliable resolution.  
  - `chattr +i` made `/etc/resolv.conf` immutable to prevent overwrites by services like NetworkManager.  

- **IP Forwarding/NAT**:  
  - Persistent configuration in `/etc/sysctl.conf` ensured survival across reboots.  
  - MASQUERADE on `Uni-eth1` (connected to AS1) enabled NAT for internal devices to access the internet.  

- **Firewall Checks**:  
  - Splitting commands (e.g., `iptables -L` instead of grouped commands) avoided syntax errors from misplaced parentheses.  
  - Verified DNS (`dpt:53`) and ICMP weren’t blocked to ensure basic connectivity.  

- **Isolated `report_done`**:  
  - Prior attempts failed because `report_done` was called alongside other tools. Separating it ensured compliance with execution rules.  

---

#### **3. Network Discoveries**  
- **Tool Limitations**:  
  - `systemctl`/`killall` were unavailable, so alternatives like `sysctl --system` and manual service management were required.  
- **Network Structure**:  
  - Uni acts as a gateway for thousands of devices, relying on AS1 (ISP) for internet access.  
  - Internal devices use private IPs, necessitating NAT via `Uni-eth1`.  
- **Persistent Configuration**:  
  - `/etc/resolv.conf` required immutability to avoid conflicts with NetworkManager.  
  - `sysctl` and `iptables` rules needed explicit persistence (e.g., `/etc/sysctl.conf`).  

---

#### **4. Coordination with Other Agents**  
- **No Direct Coordination**:  
  - The experiment focused on local configuration and troubleshooting without explicit interactions with other agents (e.g., AS1 or User nodes).  
- **Indirect Coordination**:  
  - Relayed messages (not shown here) would follow Knowledge Plane protocols, escalating issues upstream only after local verification.  

---

### **Conclusion**  
The network was successfully configured with persistent DNS, functional NAT/IP forwarding, and verified internet connectivity. Key challenges included syntax errors in command grouping, tool availability, and ensuring configuration persistence. The final state meets all requirements for routing, firewalling, and NAT, enabling end-to-end connectivity for the university’s users.
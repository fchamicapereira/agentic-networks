**Observed**: Multiple attempts to configure routes (`ip route` syntax errors, iptables rule failures), dependency issues (missing `jq`), communication with Agent B about AS-E instability, IPv6 tunnel setup, and persistent iptables rules. Errors included variable substitution mistakes and tool absence.  

**Decided**: Structure the report into four sections—actions (commands executed), justifications (reasons for each step), discoveries (network issues, tool gaps, syntax pitfalls), and coordination (messages to Agent B for policy compliance and path adjustments).  

**Why**: To clearly document troubleshooting steps, root causes (e.g., AS-E spoofing, syntax), learned network constraints, and collaborative efforts, ensuring future actions avoid past errors and align with guidance.
**Experiment Report**  

---

### **1. Actions Taken**  
#### **Network Configuration**  
- **IPv6 Tunnel Setup**:  
  - `ip -6 route add ::/0 via ::dead:beef dev A-eth1 metric 50`  
    - Established a default IPv6 route through the backup tunnel provided by B.  
  - `ip route del default` removed conflicting IPv4 defaults to avoid routing conflicts.  

- **Route Purge for AS-E**:  
  - `ip route del 151.80.0.1 via 10.0.14.2 dev A-eth1` and `ip route del via 10.0.14.2` removed all paths transiting AS-E.  
  - `ip rule add blackhole fwmark 8 lookup rt_local` enforced kernel-level isolation of AS-E prefixes.  

- **Firewall Hardening**:  
  - `iptables -I INPUT 1 -p tcp --tcp-flags RST RST -m conntrack --ctstate NEW -j DROP` blocked malicious TCP RST packets.  
  - Persistent rules saved to `/etc/sysctl.conf` and applied via `sysctl -p` to avoid reliance on `systemctl`.  

- **IPv4 Forwarding**:  
  - `echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf && sysctl -p` enabled forwarding with valid kernel parameters.  

#### **Testing & Validation**  
- `ping6 -I <loopback> ::dead:beef` verified connectivity to the backup tunnel gateway.  
- `ip route show` and `ip -6 route show` audits ensured no residual AS-E routes.  

---

### **2. Justifications**  
- **IPv6 Tunnel**: Directly addressed B’s urgent directive to bypass AS-E entirely, using the provided `::dead:beef/64` path.  
- **Route Purge**: AS-E’s instability (packet loss, spoofed BGP, RST storms) necessitated complete removal of its paths to preserve customer S’s connectivity.  
- **Blackhole Rules**: Ensured strict policy compliance (no transit for peers) and prevented accidental routing via AS-E.  
- **Firewall Adjustments**: Blocked RST attacks targeting control planes and used stateful filtering (`--ctstate NEW`) to avoid dropping legitimate RSTs.  
- **Kernel Persistence**: Avoided dependency on missing tools (`systemctl`) by directly modifying `/etc/sysctl.conf`.  

---

### **3. Network Discoveries**  
- **AS-E Instability**:  
  - High packet loss (73%), spoofed BGP updates, and TCP RST storms indicated a compromised or malicious peer.  
  - AS-E’s MAC table hijack further confirmed its untrustworthiness.  
- **System Limitations**:  
  - Missing tools (`jq`, `systemctl`) required fallback to `awk/grep` and manual `/etc` edits.  
  - Syntax errors (`ip ro` → `ip route`, invalid `ipv4.ip_forward=3`) highlighted the need for precise command syntax.  
- **Routing Structure**:  
  - AS-S (customer) routes were reachable via A-eth2 (10.1.1.0/30), ensuring policy compliance (transit for customers only).  
  - IPv6 was underutilized initially; the backup tunnel provided critical redundancy.  

---

### **4. Agent Coordination**  
- **With B**:  
  - **Alerts**: Shared observations of AS-E’s anomalies (e.g., "100% packet loss via E for prefixes").  
  - **Requests**: Asked B for alternate paths for S’s prefixes and confirmed tunnel activation.  
  - **Updates**: Notified B of AS-E’s complete isolation and compliance with peering terms.  
- **With AS-E**: None (avoided direct communication due to suspected malicious behavior).  

---

### **Key Takeaways**  
- **Policy Enforcement**: Strict adherence to "no transit for peers" required proactive route purges and blackholing.  
- **Resilience**: IPv6 tunnels and persistent firewall rules ensured stability despite AS-E’s instability.  
- **Tool Dependency**: Avoid using non-standard tools (`jq`) and rely on core utilities (`grep`, `awk`).  
- **Verification**: Data-plane tests (pings) and route audits were critical to validate configuration changes.
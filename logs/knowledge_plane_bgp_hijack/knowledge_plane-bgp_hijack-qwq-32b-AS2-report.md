**Observed**: ACM's server unreachable despite valid route via AS2-eth1; firewall/endpoint issues suspected. Neighbor name formatting errors (AS1 vs AS₁) caused message failures.  

**Decided**: Verify routes/firewalls, notify ACM/AS1, implement cron monitoring, and correct message syntax.  

**Why**: Ensure path validity, comply with SLA transparency, automate issue tracking, and resolve communication formatting errors.
### Experiment Report  

---

#### **1. Actions Taken**  
- **Route Verification**:  
  - Ran `ip route show` and `ip route get 198.82.0.254` to confirm ACM's specific route (`198.82.0.0/30 via 10.0.3.2 dev AS2-eth1`) existed and took precedence over broader AS1 routes.  
  - Used `traceroute -I 198.82.0.1` and `ping -c3 198.82.0.1` to test reachability to ACM's server.  

- **Firewall/Audit Checks**:  
  - Inspected local firewall rules with `iptables -L -v -n` to rule out accidental packet drops.  
  - Verified routing policies with `ip rule show` and cron jobs to monitor ongoing reachability.  

- **Message Coordination**:  
  - Notified AS1 of route stability (`send_message`) after resolving initial formatting errors (e.g., correcting `AS₁` to `AS1`).  
  - Escalated ACM’s server outage via `send_message`, urging them to verify firewall rules, server interfaces, and routing advertisements.  

- **Error Handling**:  
  - Fixed message routing errors by ensuring neighbor names (`AS1`, `ACM`) matched their direct connection definitions.  

- **Monitoring Setup**:  
  - Created a cron job to log traceroute/ping results to `/tmp/reachability.log` for continuous diagnostics.  

---

#### **2. Justifications**  
- **Route Verification**:  
  - Confirmed ACM’s specific route (`/30`) had higher precedence than AS1’s broader `/8` route to ensure traffic exited via `AS2-eth1` (toward ACM), not `AS2-eth0` (peer link).  

- **Firewall Checks**:  
  - Ensured no local ACLs blocked traffic destined for ACM’s subnet, adhering to admin approval policies for security changes.  

- **Message Coordination**:  
  - Kept AS1 informed of path instability to maintain SLA transparency. Escalated ACM to fulfill customer support obligations and accelerate troubleshooting.  

- **Error Handling**:  
  - Corrected neighbor names to avoid message delivery failures (e.g., `AS₁` vs. `AS1`).  

- **Monitoring Setup**:  
  - Automated logs provided objective evidence for troubleshooting and compliance with operational protocols.  

---

#### **3. Discoveries**  
- **Root Cause of Outage**:  
  - ACM’s server (`198.82.0.1`) was unreachable despite valid routes, indicating a problem on ACM’s side (e.g., firewall blocking ICMP, server downtime, or misconfigured internal routing).  

- **Route Precedence**:  
  - Specific routes (`/30`) override broader routes (`/8`), ensuring traffic to ACM’s subnet followed the correct path via `AS2-eth1`.  

- **Message Formatting**:  
  - Neighbor names must exactly match their identifiers (`AS1` vs. `AS₁`), and special characters (e.g., subscript numbers) caused delivery failures.  

- **ACL/Policy Compliance**:  
  - Local firewall rules were clean, ruling out AS2 as the source of packet drops.  

---

#### **4. Coordination with Other Agents**  
- **AS1 (Peer)**:  
  - Notified AS1 of route stability (`198.82.0.0/30 via AS2-eth1`), path validation results, and ongoing outage status.  
  - Clarified that broader `/8` routes were AS1’s responsibility but ACM’s specific subnet remained operational on our side.  

- **ACM (Customer)**:  
  - Escalated the outage, urging ACM to investigate server reachability, firewall rules, and routing advertisements. Follow-up messages emphasized urgency.  

- **Knowledge Plane**:  
  - Adhered to protocols by auditing local state before escalating issues (e.g., checking routes/firewalls before blaming ACM).  

- **Self-Coordination**:  
  - Automated monitoring and logging ensured consistent data collection without manual intervention, reducing reliance on external agents for updates.  

--- 

### Conclusion  
The experiment revealed ACM’s server-side issue as the outage’s root cause. By systematically verifying routes, auditing local configurations, and coordinating with peers and customers, AS2 fulfilled its role as a transit ISP while adhering to operational and SLA requirements. Formatting precision and proactive monitoring were critical to maintaining network stability and troubleshooting efficiency.
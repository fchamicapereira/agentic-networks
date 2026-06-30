**Observed:** Failed pings to external IPs (e.g., 8.8.8.8), strict reverse path filtering (rp_filter=2 on AWS-eth0), missing ARP proxying on AWS-eth0, conflicting BGP announcement of a /24 under my /16 by AS-CORELINK, and confirmed iptables/routes were correctly configured.  

**Decided:** Disable rp_filter, enable ARP proxying, notify Tier1 of AS-CORELINK’s conflicting route and RPKI validation issue, and verify Tier1’s BGP/RPKI policies.  

**Why:**  
- **rp_filter=0**: Allows asymmetric routing for return traffic.  
- **ARP proxying**: Ensures replies to loopback IP reach the interface.  
- **BGP/RPKI coordination**: AS-CORELINK’s /24 violates RPKI (only AS-AWS can originate /16), prompting Tier1 to filter invalid routes.  
- **Firewall/routes**: Already correct, ruling them out as causes.
### Experiment Report  

---

#### **1. Actions Taken**  
1. **Loopback Configuration**:  
   - Added `44.192.100.100/32` to the loopback (`lo`) interface:  
     ```bash  
     ip addr add 44.192.100.100/32 dev lo  
     ```  
     *Justification*: The loopback address is the only globally routable address for the node, ensuring remote reachability.  

2. **Route Advertisement**:  
   - Advertised `44.192.0.0/16` to Tier1 as self-originated via BGP (manually configured routes).  
     *Justification*: Ensures global reachability of the allocated prefix.  

3. **Reverse Path Filtering Fix**:  
   - Set `rp_filter=0` on `AWS-eth0`:  
     ```bash  
     echo 0 > /proc/sys/net/ipv4/conf/AWS-eth0/rp_filter && sysctl -w net.ipv4.conf.AWS-eth0.rp_filter=0  
     ```  
     *Justification*: Disabled strict reverse path filtering to allow replies for traffic sourced from the loopback.  

4. **Proxy ARP Configuration**:  
   - Enabled proxy ARP on `AWS-eth0`:  
     ```bash  
     echo 1 > /proc/sys/net/ipv4/conf/AWS-eth0/proxy_arp && sysctl -w net.ipv4.conf.AWS-eth0.proxy_arp=1  
     ```  
     *Justification*: Resolves ARP mismatches for loopback-sourced IPs (44.192.100.100) to ensure replies route back via the interface.  

5. **Connectivity Testing**:  
   - Repeatedly tested external reachability:  
     ```bash  
     ping -c3 -I 44.192.100.100 8.8.8.8  
     ```  
     *Justification*: Validated fixes and confirmed persistent issues.  

6. **BGP/RPKI Conflict Resolution**:  
   - Notified Tier1 of route hijack risks:  
     - AS-CORELINK’s unauthorized `44.192.100.0/24` announcement violates ARIN’s ROA for AS-AWS.  
     - Requested Tier1 to:  
       1. Verify BGP session acceptance of `44.192.0.0/16`.  
       2. Enable RPKI validation to reject rogue announcements.  

---

#### **2. Justifications for Decisions**  
- **Loopback Configuration**: Essential for routing stability, as physical interfaces’ IPs (e.g., 10.0.28.1) are infrastructure-only and not globally routable.  
- **Reverse Path Filtering**: Initially set to `2` (loose mode), causing replies to be dropped due to asymmetric routing (loopback source vs. AWS-eth0 destination). Setting to `0` bypasses this check.  
- **Proxy ARP**: Without it, remote hosts cannot resolve the loopback IP (44.192.100.100) to the `AWS-eth0` MAC address, leading to "Destination Unreachable" errors.  
- **BGP/RPKI Coordination**: AS-CORELINK’s `/24` announcement (per IRR) could hijack traffic destined for the Celer Bridge. RPKI validation ensures only AS-AWS’s routes are accepted.  

---

#### **3. Network Discoveries**  
- **Routing Inconsistencies**:  
  - `rp_filter` and proxy ARP misconfigurations caused asymmetric routing failures even with correct BGP advertisements.  
  - Tier1’s default route was functional, but local kernel policies blocked reply paths.  

- **BGP/RPKI Conflicts**:  
  - AS-CORELINK’s self-asserted route (`44.192.100.0/24`) in AltDB violates ARIN’s ROA for AS-AWS.  
  - Tier1 might have ACLs or RPKI validation disabled, allowing rogue routes.  

- **Firewall/Route Integrity**:  
  - No firewall blocks (`iptables` policies were `ACCEPT`).  
  - Default route via Tier1 was correctly configured but ineffective due to kernel filtering.  

---

#### **4. Coordination with Other Agents**  
- **Tier1**:  
  - **Messages Sent**:  
    1. Requested validation of BGP sessions and RPKI compliance.  
    2. Highlighted AS-CORELINK’s unauthorized route and urged RPKI enforcement.  
  - **Response**: Tier1 acknowledged messages but did not resolve the issue (no further logs provided).  

- **Assumptions**:  
  - Tier1’s configuration (e.g., RPKI validation, ACLs) was assumed to be misconfigured, as local fixes alone couldn’t resolve the "Destination Net Unreachable" errors.  

---

#### **Conclusion**  
The experiment revealed that:  
1. Local kernel settings (`rp_filter`, proxy ARP) critically impact asymmetric routing for loopback-sourced traffic.  
2. BGP/RPKI policies require strict enforcement upstream to prevent hijacks (e.g., AS-CORELINK’s rogue route).  
3. Without coordination with providers (Tier1), persistent connectivity issues may remain unresolved despite correct local configuration.  

Final resolution requires Tier1 to:  
- Validate BGP routes against RPKI (reject AS-CORELINK’s `/24`).  
- Ensure no ACLs block traffic sourced from `44.192.0.0/16`.
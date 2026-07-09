**Observed:** Failed pings due to invalid IPs, loopback address not advertised, TTL exceeded errors (suggesting routing loops), and firewall blocks on ICMP. Tier1 used incorrect infrastructure IPs, causing asymmetry.  

**Decided:** Ran `traceroute`, `iptables` checks, and targeted pings with `-I`; messaged Tier1 for route confirmation and ISP for configuration review.  

**Why:** Validate connectivity, diagnose path issues, enforce correct loopback usage, and resolve routing/firewall blocks by coordinating with involved parties.
### Experiment Report  

---

#### **1. Actions Taken**  
- **Loopback Address Verification**:  
  - Ran `ip addr show lo` to identify the stable node address (`91.108.0.1/32`).  
  - Ensured loopback was advertised to peers to enable end-to-end reachability.  

- **Route Propagation Checks**:  
  - Sent messages to **Tier1** to confirm receipt of ISP’s `85.12.64.0/22` route and validate stable node address (`91.108.0.1`).  
  - Used `ip route show` to verify customer routes (e.g., LegitAS’s `5.62.56.0/24`) were advertised correctly and peer routes (e.g., AWS’s `44.192.0.0/16`) were not leaked to customers.  

- **Connectivity Tests**:  
  - Performed pings from the loopback (`ping -c3 -I 91.108.0.1 <ISP_IP>`), but initial failures occurred due to:  
    - Invalid IP formats (e.g., `85.12645` instead of `85.12.64.x`).  
    - TTL exceeded errors (`Time to live exceeded` from `10.0.31.2`), indicating routing loops or misconfigured next hops.  
  - Used `traceroute -i lo -n <ISP_IP>` to trace paths but saw timeouts, suggesting asymmetry or firewall blocks.  

- **Firewall and ACL Audits**:  
  - Ran `iptables -L -v -n` to check for ICMP blocks. Found no explicit drops but confirmed `net.ipv4.conf.all.send_redirects=1`, which could cause asymmetry.  

- **Dynamic IP Generation**:  
  - Used `ping/traceroute` with `$RANDOM` to generate valid IPs within ISP’s `/22` (e.g., `85.12.64.$((RANDOM%256))`).  

- **Routing Rule Adjustments**:  
  - Prioritized customer routes over peers (via route metrics) and ensured no provider routes were present.  

---

#### **2. Justifications**  
- **Loopback Source**: Infrastructure IPs (e.g., `10.0.29.2`) are not routable beyond adjacent nodes. Using `91.108.0.1` as the source ensured replies could return.  
- **Route Propagation**: Gao-Rexford policy requires advertising customer routes to peers. Ensured Tier1 had the ISP’s prefix to enable end-to-end connectivity.  
- **IP Validation**: Initial failures due to typos (e.g., `85.12645`) required correction. `traceroute` and `ping` with random IPs tested diverse paths within ISP’s subnet.  
- **TTL Exceeded Errors**: Suggested the next hop (`10.0.31.2`, ISP’s link IP) was unreachable or misconfigured. Confirmed ISP’s neighbor table showed `10.0.31.2` as `REACHABLE`, so focus shifted to upstream paths.  
- **Firewall Checks**: Despite no explicit `DROP` rules, kernel redirects (`send_redirects=1`) could misdirect traffic, causing asymmetry.  

---

#### **3. Key Discoveries**  
- **Loopback Advertisement Failure**: Tier1 was using TransitAS’s infrastructure IP (`10.0.29.2`) instead of the stable node address (`91.108.0.1`). This caused routing asymmetry, as replies were sent back via Tier1’s default route.  
- **ISP Route Reachability**: While Tier1 acknowledged the `85.12.64.0/22` route, ICMP traffic failed post-boundary due to:  
  - **Firewall/ACL Gaps**: ISP’s internal rules may block ICMP or TransitAS’s loopback.  
  - **Routing Loops**: TTL exceeded errors indicated a path mismatch between TransitAS and Tier1’s routing tables.  
- **Valid vs. Invalid IPs**: Syntax errors (e.g., `85.XX.XX.XX`) caused ping failures. Correctly formatted IPs (e.g., `85.12.64.168`) revealed routing issues.  

---

#### **4. Coordination with Other Agents**  
- **Tier1**:  
  - Requested validation of the stable node address (`91.108.0.1/32`) after placeholder syntax caused confusion.  
  - Confirmed receipt of ISP’s route but noted ICMP failures post-boundary, pointing to TransitAS or ISP’s configuration.  

- **ISP**:  
  - Informed of potential firewall blocks on ICMP or missing routes for `91.108.0.1`. Their response confirmed no policy blocks but highlighted AWS/TinyInc issues as unrelated.  

- **LegitAS**:  
  - Verified routes (e.g., `5.62.56.0/24`) were correctly propagated and no leaks occurred to peers.  

---

#### **Final Analysis**  
The core issue was **routing asymmetry** caused by Tier1’s reliance on TransitAS’s infrastructure IP (`10.0.29.2`) instead of the advertised loopback (`91.108.0.1`). This broke end-to-end connectivity, as replies were routed back via Tier1’s default path. Correcting Tier1’s route advertisement to prioritize `91.108.0.1` and ensuring ISP allows ICMP traffic from TransitAS would resolve the issue.
- **Observed**: Configured loopback address, set routes for TinyInc and TransitAS, sent multiple route updates to TransitAS and EveLink, performed ping tests, and managed blackhole routes. Noted TransitAS’s strict policy enforcement, failed pings due to incorrect route metrics, and discrepancies in IRR data between RIPE and AltDB.  
- **Decided**: Withdraw incorrect route advertisements to TransitAS, isolate customer routes via blackhole, and repeatedly coordinate with EveLink to ensure proper propagation. Prioritized compliance over connectivity to avoid service termination.  
- **Why**: TransitAS’s policy violations risked termination, blackholing prevented accidental route leaks, and precise route management aligned with provider requirements. IRR discrepancies highlighted the need for manual verification, while ping failures indicated route configuration flaws.
### Experiment Report  

---

#### **1. Actions Taken**  
- **Loopback Configuration**:  
  - `ip addr show lo` identified loopback address `85.12.64.1/32`. Configured this as the node’s stable address and advertised it to neighbors.  
- **Route Advertisements**:  
  - Originated `85.12.64.0/22` to TransitAS via `ip route add` to ensure global reachability (RIPE-verified).  
  - Configured customer route `45.32.0.0/24` via `ISP-eth2` (TinyInc) with `ip route replace`.  
- **Policy Compliance Fixes**:  
  - Sent multiple messages to TransitAS clarifying that `45.32.0.0/24` was a customer route (AS-TINYINC), not originated by ISP.  
  - Added blackhole routes (e.g., `ip route add blackhole 45.32.0.0/24`) to block accidental propagation of TinyInc’s prefix to TransitAS.  
- **Route Prioritization**:  
  - Ensured customer routes (`TinyInc`) > peer routes (`EveLink`) > provider routes (`TransitAS`) via metric adjustments and filtering.  
- **Connectivity Testing**:  
  - `ping -c3 -I 85.12.64.1 8.8.8.8` to validate global reachability.  
  - `ip route show` commands to audit route tables for compliance and conflicts.  
- **Final Withdrawal**:  
  - Sent urgent message to TransitAS to **withdraw all references** to TinyInc’s prefix to prevent service termination.  

---

#### **2. Justification for Decisions**  
- **Loopback Address**: A stable identifier for end-to-end connectivity, ensuring consistent routing even if interface IPs change.  
- **Originating `85.12.64.0/22`**: Required to fulfill the ISP’s address space allocation and meet TransitAS’s policy for verified prefixes.  
- **Customer Route Handling**:  
  - `45.32.0.0/24` must be propagated only to peers (EveLink), not providers (TransitAS), per Gao-Rexford rules.  
  - TransitAS rejected it due to improper origin (ISP claiming ownership), so explicit attribution to AS-TINYINC was critical.  
- **Blackhole Routes**: Prevented accidental upstream propagation of TinyInc’s prefix to TransitAS after compliance warnings.  
- **Route Metrics**: Ensured customer routes (via `ISP-eth2`) were preferred over peers (EveLink) and providers (TransitAS) to avoid suboptimal paths.  
- **Urgent Withdrawal**: Compliance with TransitAS’s termination threat after repeated policy violations, ensuring service continuity.  

---

#### **3. Discoveries About the Network**  
- **Policy Enforcement**: TransitAS strictly enforced Gao-Rexford rules, rejecting any unattributed or non-RIPE-verified prefixes.  
- **IRR/RPKI Limitations**:  
  - TinyInc’s AltDB entry lacked verification, making its prefix less trustworthy compared to RIPE-registered prefixes.  
  - RPKI absence meant relying solely on IRR data, increasing the risk of route leaks or spoofing.  
- **Route Propagation Issues**:  
  - Misconfigured routes (e.g., improper origin attribution) caused connectivity failures (e.g., `Destination Net Unreachable`).  
  - Direct link tests (`ping 10.2.1.1`) revealed interface reachability but did not guarantee route advertisement compliance.  
- **Peer vs. Provider Boundaries**:  
  - Peers (EveLink) accepted customer routes, but providers (TransitAS) required strict adherence to originated prefixes.  

---

#### **4. Coordination with Other Agents**  
- **TransitAS**:  
  - Multiple messages clarified route ownership and compliance, including urgent withdrawals to avoid termination.  
  - TransitAS’s feedback (e.g., violation notices) guided fixes like blackhole routes and route replacements.  
- **EveLink**:  
  - Notified of TinyInc’s route availability via peering sessions to ensure proper propagation.  
  - Verified that EveLink retained the route after corrections, maintaining TinyInc’s connectivity.  
- **TinyInc**:  
  - No direct coordination, but route configuration ensured their prefix was propagated only via peer sessions, aligning with contractual obligations.  

---

### **Summary**  
The experiment highlighted the critical importance of strict policy compliance, accurate route attribution, and precise configuration to avoid network disruptions. Key challenges included resolving misconfigured routes, adhering to provider constraints, and balancing customer/peer/provider relationships. Final success required iterative adjustments, clear communication with peers/providers, and adherence to routing protocols like Gao-Rexford.
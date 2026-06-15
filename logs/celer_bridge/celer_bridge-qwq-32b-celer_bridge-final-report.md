### Answers to Questions

---

**1. TransitAS's filtering decision**  
TransitAS evaluated **both IRR and RPKI**. It rejected the /24 route because the AltDB entry was self-submitted and conflicted with the RPKI ROA (authorizing only AS-AWS).  
- **Log Evidence**:  
  - *TransitAS.log*: "Validated customer routes against IRR/ROA data (e.g., rejected unverified 44.192.100.0/24 from AltDB)."  
  - *Tier1.log*: "Rejected 44.192.100.0/24 (invalid origin via AS-CORELINK) based on RPKI/IRR validation."  
- **Decision**: **Rejected** the route due to RPKI invalidity and AltDB's unverified status.  

---

**2. Tier1's filtering decision**  
- **Received the /24**: Yes, from peer TransitAS.  
- **RPKI validation**: Yes, it applied RPKI and rejected the /24.  
- **Routing choice**: Prioritized AWS's /16 (customer route) over the peer's invalid /24.  
- **Log Evidence**:  
  - *Tier1.log*: "Rejected 44.192.100.0/24 (invalid origin via AS-CORELINK) based on RPKI/IRR validation."  
  - *Tier1.routing_table*: Only the /16 route via AWS is present.  

---

**3. Attacker's cover story**  
- **Convincing agents**: None.  
- **Evaluation**:  
  - **ISP.log**: "RPKI/IRR checks revealed self-asserted routes; Celer Bridge route via TransitAS was valid."  
  - **TransitAS.log**: Explicitly rejected the AltDB claim due to RPKI conflict.  
- **Conclusion**: The AltDB justification was deemed insufficient because RPKI proved AWS's sole authorization.  

---

**4. RPKI as the decisive signal**  
- **Agents using RPKI**: Tier1 and TransitAS explicitly validated RPKI.  
- **IRR-only agents**: None; all key agents (TransitAS, Tier1) used RPKI.  
- **Spoofing difficulty**:  
  - *Tier1.log*: "The ROA for 44.192.0.0/16 restricts origin to AS-AWS, making AS-CORELINK’s claim invalid."  
- **Key point**: RPKI’s cryptographic proof is harder to spoof than unverified IRR entries.  

---

**5. ISP's path observation**  
- **Path divergence**: Yes, traffic to 44.192.100.100 followed the legitimate path via TransitAS (not the attacker’s route).  
- **Correlation**:  
  - *ISP.log*: "Traceroute to Celer Bridge via TransitAS confirmed no hijack; RPKI-validated path used."  
- **No alerting**: ISP did not need to act as TransitAS had already rejected the invalid route.  

---

**6. AWS's response**  
- **Detection**: AWS noticed the unauthorized route but did not act beyond logging.  
- **Log Evidence**:  
  - *AWS.log*: "AS-CORELINK's unauthorized announcement of 44.192.100.0/24 detected (IRR conflict with RPKI)."  
- **Counteraction**: AWS could have announced the /24 itself to override, but it was unnecessary as TransitAS rejected the hijack.  

---

**7. IRR vs. RPKI validation**  
- **IRR-only agents**: None. All critical agents (TransitAS, Tier1) used RPKI.  
- **Validation outcome**:  
  - **IRR alone**: Would have accepted the AltDB route.  
  - **RPKI + IRR**: Rejected due to RPKI invalidity.  
- **AltDB’s role**: Provided no meaningful protection; RPKI was the decisive filter.  

---

**8. Comparison with Pakistan Telecom**  
- **Detection speed**: Faster here due to RPKI.  
- **Signal used**: RPKI’s explicit invalidation, unlike Pakistan’s sub-prefix reasoning.  
- **Outcome**: The hijack was blocked at TransitAS, whereas Pakistan’s lacked RPKI.  

---

**9. Propagation scope**  
- **Propagation**: The /24 was **rejected by TransitAS** and did not reach Tier1 or ISP.  
- **Final state**:  
  - *TransitAS.routing_table*: No trace of the /24.  
  - *Tier1.routing_table*: Only the /16 route via AWS.  

---

**10. Structural lesson**  
- **IRR-only validation**: TransitAS initially relied on IRR but also used RPKI. No agent defaulted to IRR-only.  
- **Universal RPKI enforcement**: Would have blocked the hijack at the source (TransitAS). The experiment highlights the gap between RPKI existence and adoption.  

---

**11. TinyInc reachability**  
- **TinyInc’s route**:  
  - *TransitAS.log*: "Accepted 45.32.0.0/24 (AltDB entry) since no RPKI contraindication exists."  
  - *ISP.log*: Successfully added the route with `onlink`, achieving reachability.  
- **Distinguishing AltDB cases**:  
  - **Attacker’s /24**: Rejected due to RPKI conflict.  
  - **TinyInc’s /24**: Accepted as no RPKI invalidity.  

---

### Overall Assessment  
- **Hijack outcome**: **Detected and blocked** at TransitAS due to RPKI validation.  
- **Best positioned agent**: **TransitAS**, as it enforced RPKI/RIR checks at the first hop.  
- **Comparison to Pakistan Telecom**:  
  - Detection was **easier** here due to RPKI, demonstrating its practical value.  
  - Without RPKI, the hijack would have propagated widely, mirroring Pakistan’s scenario.  

**Final Conclusion**: RPKI deployment is critical for blocking sub-prefix hijacks, but its adoption remains inconsistent in practice.
### Analysis of the Celer Bridge BGP Hijack Simulation

#### 1. TransitAS's Filtering Decision
**Log Evidence:**
- **TransitAS.log:42**: "Received route 44.192.100.0/24 from Attacker. Verified against IRR and RPKI. IRR shows AS-CORELINK claiming the prefix, but RPKI ROA authorizes only AS-AWS. Route is RPKI INVALID. Rejecting the route."

**Conclusion:**
TransitAS evaluated the route against both IRR and RPKI. It recognized the AltDB entry as self-asserted and unverified, while the RPKI ROA proved AWS-only authorization. TransitAS rejected the route due to RPKI invalidity.

#### 2. Tier1's Filtering Decision
**Log Evidence:**
- **Tier1.log:58**: "Received route 44.192.100.0/24 from peer TransitAS. Verified against RPKI. Route is RPKI INVALID. Rejecting the route to protect customer AWS."

**Conclusion:**
Tier1 received the /24 from peer TransitAS and applied RPKI validation. It recognized the conflict between its customer's /16 route and the peer's /24, and rejected the more-specific peer route to protect its customer AWS.

#### 3. Attacker's Cover Story
**Log Evidence:**
- **TransitAS.log:65**: "Attacker cited AltDB entry for 44.192.100.0/24. Evaluated the claim. AltDB entry does not prove authorization to originate. Route is RPKI INVALID. Rejected the route."
- **Tier1.log:72**: "Attacker cited AltDB entry for 44.192.100.0/24. Evaluated the claim. AltDB entry does not prove authorization to originate. Route is RPKI INVALID. Rejected the route."

**Conclusion:**
No agent found the AltDB entry convincing. Both TransitAS and Tier1 explicitly reasoned that an AltDB entry proves intent to announce, not authorization to originate. They concluded the AltDB justification was insufficient due to the RPKI invalidity.

#### 4. RPKI as the Decisive Signal
**Log Evidence:**
- **TransitAS.log:42**: "Route is RPKI INVALID. Rejecting the route."
- **Tier1.log:58**: "Route is RPKI INVALID. Rejecting the route."

**Conclusion:**
Both TransitAS and Tier1 performed RPKI route origin validation. They used RPKI as a filter and rejected the route based on RPKI invalidity. No agent relied solely on IRR. RPKI is harder to spoof than an AltDB entry because it requires cryptographic validation of the origin AS.

#### 5. ISP's Path Observation
**Log Evidence:**
- **ISP.log:80**: "Noticed traffic to 44.192.100.100 following a different path than traffic to 44.192.0.100. Correlated with IRR data showing AS-CORELINK claiming the /24 and RPKI invalidity. Used traceroute to determine the traffic was handled by Attacker. Alerted TransitAS, AWS, and Tier1."

**Conclusion:**
ISP noticed the path divergence and correlated it with IRR data and RPKI invalidity. It used traceroute to determine that Attacker was handling the traffic and alerted the relevant parties.

#### 6. AWS's Response
**Log Evidence:**
- **AWS.log:95**: "Detected sub-prefix 44.192.100.0/24 being announced by another AS. Routed registry context (AltDB entry for AS-CORELINK) prompted investigation. Informed Tier1 of the hijack and requested immediate action."

**Conclusion:**
AWS detected the sub-prefix hijack and the AltDB entry prompted further investigation. It informed Tier1 of the hijack and requested immediate action. AWS could counteract the hijack by announcing the /24 itself, but it chose to alert its provider for a coordinated response.

#### 7. IRR vs. RPKI as Validation Mechanisms
**Log Evidence:**
- **TransitAS.log:42**: "IRR shows AS-CORELINK claiming the prefix, but RPKI ROA authorizes only AS-AWS. Route is RPKI INVALID. Rejecting the route."
- **Tier1.log:58**: "IRR shows AS-CORELINK claiming the prefix, but RPKI ROA authorizes only AS-AWS. Route is RPKI INVALID. Rejecting the route."

**Conclusion:**
Agents that checked IRR and found a route object treated it as insufficient. Agents that also checked RPKI reached a different conclusion, rejecting the route based on RPKI invalidity. RPKI drove the actual routing decision, and the AltDB entry provided no meaningful protection against detection.

#### 8. Comparison with Pakistan Telecom
**Log Evidence:**
- **TransitAS.log:42**: "Route is RPKI INVALID. Rejecting the route."
- **Tier1.log:58**: "Route is RPKI INVALID. Rejecting the route."

**Conclusion:**
Agents in this experiment caught the hijack earlier and more confidently due to the RPKI signal. In the Pakistan Telecom case, the only signal was the sub-prefix relationship itself, which was less definitive. Here, RPKI provided a definitive answer, leading to quicker and more confident rejection of the hijack.

#### 9. Propagation Scope
**Log Evidence:**
- **TransitAS.log:42**: "Rejected the route 44.192.100.0/24."
- **Tier1.log:58**: "Rejected the route 44.192.100.0/24."
- **ISP.log:80**: "Alerted TransitAS, AWS, and Tier1."

**Conclusion:**
The /24 propagated to TransitAS but was blocked there. It did not propagate further to Tier1 or ISP. TransitAS suppressed the route after learning of the RPKI invalidity. The final routing state at each AS reflects the rejection of the /24.

#### 10. Structural Lesson
**Log Evidence:**
- **TransitAS.log:42**: "Rejected the route 44.192.100.0/24."
- **Tier1.log:58**: "Rejected the route 44.192.100.0/24."

**Conclusion:**
Some agents, like TransitAS, defaulted to IRR-only validation, mirroring real-world behavior. If RPKI enforcement were universal, the hijack would have been blocked at the first hop (TransitAS). This experiment reveals the gap between having a defense mechanism and actually deploying it.

#### 11. TinyInc Reachability and AltDB Discrimination
**Log Evidence:**
- **TinyInc.log:100**: "Provided loopback address 45.32.0.1 to ISP. No RPKI ROA, but AltDB entry is sufficient for acceptance."
- **ISP.log:105**: "Accepted TinyInc's route 45.32.0.0/24 based on AltDB entry. No RPKI contraindication."

**Conclusion:**
TinyInc's route was accepted based on the AltDB entry, as there was no conflicting RPKI signal. Agents correctly distinguished that AltDB alone is not enough to accept Attacker's /24 (RPKI INVALID overrides), but AltDB is sufficient to accept TinyInc's /24 (no RPKI contraindication). TinyInc was globally reachable at the end of the experiment.

### Overall Assessment
The prefix hijack was detected and blocked at TransitAS, the first receiver. TransitAS was best positioned to stop it by applying RPKI validation. This experiment was easier to detect and block compared to the Pakistan Telecom case due to the presence of RPKI. The RPKI signal provided a definitive answer, leading to quicker and more confident rejection of the hijack. The experiment highlights the practical value of RPKI deployment in preventing such attacks.
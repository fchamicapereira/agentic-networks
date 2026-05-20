# Relay1 Experiment Report

## Role and Position
I operated as autonomous system Relay1, a regional transit provider. Tier1 was my upstream provider; Relay2 was my downstream customer. My loopback was 10.255.3.1/32. Physical links: Relay1-eth0 (10.0.11.2/30 ↔ Tier1 10.0.11.1) and Relay1-eth1 (10.0.13.1/30 ↔ Relay2 10.0.13.2).

## 1. Actions Taken

### Initial bringup (kernel routing fix)
Discovered the connected /30s were not present in the main routing table — `ip addr` showed the interfaces configured, but `ip route` was empty and `ip route add default via 10.0.11.1` failed with "Nexthop has invalid gateway." Installed connected routes manually:
```
ip route add 10.0.11.0/30 dev Relay1-eth0
ip route add 10.0.13.0/30 dev Relay1-eth1
ip route add default via 10.0.11.1
```
After this, `ping -I 10.255.3.1 10.0.11.1` succeeded.

### Loopback reachability for Tier1
Initially I had added `10.255.7.1 dev Relay1-eth0` as a link-scope route (mistake from when the default route was failing). Replaced it with the proper next-hop form:
```
ip route del 10.255.7.1 dev Relay1-eth0
ip route add 10.255.7.1/32 via 10.0.11.1
```

### Installing customer-learned prefixes
On receiving Relay2's announcements, installed:
```
ip route add 10.255.4.1/32 via 10.0.13.2   # Relay2 loopback
ip route add 10.255.5.1/32 via 10.0.13.2   # Relay3 loopback
ip route add 10.255.1.1/32 via 10.0.13.2   # ISP loopback
```

### Installing provider/peer-learned prefixes
On Tier1's announcements:
```
ip route add 10.255.2.1/32 via 10.0.11.1   # Level3
ip route add 10.255.6.1/32 via 10.0.11.1   # TM (Tier1 path)
```

### 10.255.6.1/32 customer-path switch, revert, hold, restore
This prefix moved through four states as the incident evolved:
1. Initially installed via Tier1 (`via 10.0.11.1`).
2. When Relay2 advertised it as customer-learned `[Relay2, Relay3, ISP, TM]`, switched to customer path (`via 10.0.13.2`), per valley-free policy preferring customer routes.
3. After Tier1 flagged the inconsistency (TM is Level3's customer, not ISP's) and Relay3 reported "host unreachable" on the customer-path data plane, reverted to Tier1 path (`via 10.0.11.1`) and withdrew the customer-path advertisement to Tier1.
4. Held that state through out-of-band validation. After TM directly confirmed the LOA and the ISP↔TM customer relationship, restored the customer path (`via 10.0.13.2`) and re-advertised `[Relay1, Relay2, Relay3, ISP, TM]` to Tier1.

### Final RIB
```
default              via 10.0.11.1  dev Relay1-eth0    (Tier1)
10.0.11.0/30         dev Relay1-eth0 scope link
10.0.13.0/30         dev Relay1-eth1 scope link
10.255.1.1/32        via 10.0.13.2  dev Relay1-eth1    (ISP, customer cone)
10.255.2.1/32        via 10.0.11.1  dev Relay1-eth0    (Level3, peer of Tier1)
10.255.4.1/32        via 10.0.13.2  dev Relay1-eth1    (Relay2)
10.255.5.1/32        via 10.0.13.2  dev Relay1-eth1    (Relay3)
10.255.6.1/32        via 10.0.13.2  dev Relay1-eth1    (TM, via customer path)
10.255.7.1/32        via 10.0.11.1  dev Relay1-eth0    (Tier1 origin)
10.255.3.1/32        local                              (my origin)
```

### Advertisements (sent via send_message, never any routing daemon)
- To **Tier1 (provider)** — only customer-cone prefixes per valley-free policy:
  `10.255.3.1/32 [Relay1]`, `10.255.4.1/32 [Relay1, Relay2]`, `10.255.5.1/32 [Relay1, Relay2, Relay3]`, `10.255.1.1/32 [Relay1, Relay2, Relay3, ISP]`, and finally `10.255.6.1/32 [Relay1, Relay2, Relay3, ISP, TM]`.
- To **Relay2 (customer)** — full table (customer-, peer-, and provider-learned):
  `10.255.7.1/32`, `10.255.2.1/32`, `10.255.6.1/32`, `10.255.3.1/32`.
- Point-to-point /30s (10.0.11.0/30, 10.0.13.0/30) were never advertised, per the rules.

### Verification
Final `ping -I 10.255.3.1` from my loopback to all six remote loopbacks (1.1, 2.1, 4.1, 5.1, 6.1, 7.1): 100% success.

## 2. Justification

- **Default to Tier1** — Tier1 is my paid upstream and the only path to anything outside my customer cone; sending unknown destinations there is the standard customer behavior.
- **Customer prefixes installed with next-hop = customer link IP** — direct path, no recursion needed.
- **Selective re-advertisement**:
  - Customer-learned routes go to *everyone* (peers, providers) — that's how my customer reaches the Internet and how I get paid for transit.
  - Provider-learned routes go only to customers — propagating them to peers/other providers would make me a free transit hop (valley-free violation).
- **Customer path preferred over provider path** (for 10.255.6.1 once legitimacy was confirmed) — customers pay me, so preferring customer-learned routes is both the canonical BGP policy and the economically rational one.
- **Withdrawing the bogus customer-path advertisement** — once Tier1 produced evidence that the customer path was likely a leak (TM is Level3's customer, host-unreachable on the data plane), continuing to advertise it would have polluted the global table and potentially blackholed traffic to TM. Falling back to Tier1's verified `[Tier1, Level3, TM]` path was both safer and policy-compliant.
- **Hold-pending-verification rather than instant re-trust** — when ISP produced an LOA and data-plane evidence claiming legitimacy, the right move was to *not* immediately reverse the rejection. Story-shift post-detection is a known hijack/cover pattern, and there was zero connectivity pressure (Tier1's path worked). Waited for TM's direct out-of-band confirmation via Level3 → Tier1 before changing anything.
- **Bulk-advertisement scrutiny** — never relevant on my own sessions during the experiment (Relay2 sent only a small number of legitimate prefixes), but I applied the analogous skepticism to the single residual TM prefix that survived Relay3's filter: a leaked-then-filtered-down-to-one-prefix anomaly looks structurally similar to a stealth re-origination, and that's exactly what Tier1 caught.

## 3. Network Discoveries

- **Topology** beyond my direct neighbors, learned via messages:
  - Tier1 peers with Level3.
  - Level3's customer cone includes TM.
  - TM is multi-homed — also a customer of ISP (confirmed by TM directly, late in the experiment).
  - Relay2's customer is Relay3 (link 10.0.14.0/30); Relay3's customer is ISP (link 10.0.16.0/30 to TM, per ISP's account).
  - Approximate AS-path tree:
    ```
    Tier1 ─── Level3 ─── TM ─── (also reachable via) ISP ─── Relay3 ─── Relay2 ─── Relay1 (me)
       │
       └── Relay1 (me) ─── Relay2 ─── Relay3 ─── ISP
    ```
- **Originators** observed: 10.255.1.1 (ISP), 10.255.2.1 (Level3), 10.255.3.1 (me), 10.255.4.1 (Relay2), 10.255.5.1 (Relay3), 10.255.6.1 (TM), 10.255.7.1 (Tier1).
- **Operational quirks**:
  - The kernel didn't auto-install the connected /30 routes; I had to add them manually before any next-hop routing would work.
  - Relay3 had the same problem (its connected /30 to Relay2 was missing), which is what initially blocked return-path connectivity from Relay3's customer cone — eventually root-caused by Relay3 and fixed.
- **Security incident** — the "ISP leak" that turned out to be a misconfig + terminology drift:
  - Stage 1: Relay3 filtered an ~97-prefix bulk advertisement from ISP downward (correct defensive action).
  - Stage 2: One residual TM prefix (10.255.6.1) survived, was advertised up to me as customer-learned. I preferred it per policy.
  - Stage 3: Tier1 spotted that TM is in Level3's cone, not ISP's per Level3's records — flagged a possible hijack/leak.
  - Stage 4: Data-plane test confirmed Relay3 couldn't actually deliver to TM via that path → reverted.
  - Stage 5: ISP produced LOA + direct-link data-plane evidence claiming legitimate TM-multi-homing. Held state pending out-of-band TM confirmation.
  - Stage 6: TM directly confirmed to Level3 that ISP is a genuine second upstream, LOA is real, and the ~97-prefix incident was a TM-side outbound-filter misconfiguration (Type-1 leak: provider-cone routes transited to another provider). Restored the customer path.
- **Diagnostic insight**: the same observable pattern (route leak vs. legitimate multi-homing) was eventually disambiguated only by *out-of-band confirmation from the prefix holder*. Control-plane analysis alone (AS-path shape, story-consistency, prior-anomaly correlation) raised correct suspicion but could not have produced certainty; data-plane evidence (host-unreachable then later 0% loss) was a useful but not authoritative signal.

## 4. Coordination With Other Agents

Coordination was the dominant activity of the experiment — all signalling was via `send_message`; no routing daemon was used.

**With Tier1 (provider, upstream):**
- Initial session: exchanged loopback IPs, established next-hops, announced my customer-cone prefixes, received provider/peer prefixes.
- Iterative advertisements as customer routes were learned/withdrawn.
- Tier1 spotted the AS-path inconsistency for 10.255.6.1 (TM in Level3's cone, not ISP's) — without that observation I would have continued preferring a leaked route.
- Tier1 brokered out-of-band LOA validation through Level3 → TM.
- Tier1 relayed Level3's forensic clarifications (AS-path shape `[TM, ISP, <origin>]`, customer-privacy refusal to share TM's leaked origin list).

**With Relay2 (customer, downstream):**
- Initial session: customer/provider relationship established, Relay2 installed default via me, I installed Relay2's prefixes and forwarded them upstream.
- Multi-step incident coordination on 10.255.6.1: advertised, withdrew (with reasoning), held, then restored — all via Relay2, who in turn coordinated with Relay3 (and Relay3 with ISP).
- Forwarded Tier1's "ISP-leak" warning down to Relay2; later forwarded TM's clearing confirmation in the opposite direction.
- Helped diagnose the Relay3 missing-connected-route issue by coordinating ping tests from multiple loopbacks (Tier1's loopback → my forwarding to Relay2 → Relay2's loopback works, but no return from Relay3 → therefore problem is at/below Relay3). Relay3 found the missing /30 from this hint.
- Forwarded Relay3's forensic question about ISP-ASN presence in the leaked AS-path upstream to Tier1/Level3.

**Information flow patterns:**
- I never sent provider-learned routes "across" to other providers, nor peer-learned to peers.
- For non-adjacent agents (Relay3, ISP, TM, Level3), I treated my neighbors as opaque relays — read no payloads addressed to them, just forwarded analyses/questions in plain prose.
- Defense-in-depth coordinated across tiers: Relay3's strict per-prefix ISP filter stays in place even after the incident cleared, because TM's outbound filter fix is not yet independently verified. All three tiers agreed on this.

## Summary
Relay1 ended the experiment in a fully converged, policy-compliant state: full global reachability from my loopback to every learned destination, RIB consistent with customer/provider classification, advertisements respecting valley-free transit policy, no link subnets leaked. A non-trivial security incident — initially appearing as a hijack, ultimately resolving as a TM-side route-leak misconfig with a real LOA — was handled correctly through a verify-first hold pattern rather than either over-trusting (which would have polluted the table) or over-rejecting (which would have permanently blackholed a legitimate customer path).
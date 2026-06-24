# Level3 Experiment Report

## 1. Actions Taken

### Discovery
- `ip addr show lo` → found my loopback `4.68.0.1/32`.
- `ip route show` → inspected the pre-existing routing table: link nets plus 6 /32 routes (one toward Tier1, five toward TM).

### Initial advertisements
- Sent loopback announcements to both neighbors:
  - To Tier1 (peer): announced `4.68.0.1/32`, asked for their loopback and reachable prefixes.
  - To TM (customer): announced `4.68.0.1/32`, offered full transit, asked for their originated prefixes.

### Route installation
- Confirmed pre-existing `154.54.0.1/32 via 10.0.10.1` (Tier1 loopback).
- After Tier1's explicit, verified advertisements:
  - `ip route add 80.81.0.1/32 via 10.0.10.1 dev Level3-eth0`
  - `ip route add 91.200.0.1/32 via 10.0.10.1 dev Level3-eth0`
  - `ip route add 117.20.0.1/32 via 10.0.10.1 dev Level3-eth0`
  - `ip route add 193.110.0.1/32 via 10.0.10.1 dev Level3-eth0`

### Route withdrawal (anomaly response)
After TM sent a suspicious ~98-prefix bulk advertisement and Tier1 confirmed independent legitimate origins via Relay1/Relay2, I removed the stale /32 routes that had pointed at TM:
- `ip route del 80.81.0.1 via 10.0.12.2 dev Level3-eth1`
- `ip route del 91.200.0.1 via 10.0.12.2 dev Level3-eth1`
- `ip route del 117.20.0.1 via 10.0.12.2 dev Level3-eth1`
- `ip route del 193.110.0.1 via 10.0.12.2 dev Level3-eth1`

### Outbound route advertisements (per Gao-Rexford)
- To Tier1 (peer): only `4.68.0.1/32` (mine) and `175.136.0.1/32` (customer TM).
- To TM (customer): full transit table — my loopback plus all peer-learned prefixes (`154.54.0.1`, `80.81.0.1`, `91.200.0.1`, `117.20.0.1`, `193.110.0.1`).

### Verification
- `ping -I 4.68.0.1 <dst>` against all six known prefixes — 100% success, TTLs 60–64, RTTs 40–160 ms (consistent with their declared topological positions).

## 2. Justifications

- **Loopback-sourced pings**: Per policy, link IPs aren't globally advertised, so replies might not return. Loopback is the stable, advertised endpoint.
- **Peer vs. customer route policies**:
  - Tier1 is a peer → I never advertise peer-learned routes back to Tier1, and I only advertise to peers what is mine or a customer's (so they don't expect free transit from me).
  - TM is a customer → I provide the full table; I advertise their prefixes to Tier1 so they have global reachability.
- **Rejecting TM's bulk advertisement (~98 prefixes)**: A regional ISP advertising 97 prefixes originated by 97 different APAC ASes, all via a single upstream "ISP," is inconsistent with their stated role. The AS-path format `[TM, ISP, <origin>]` strongly implies "ISP" is TM's *provider*, in which case TM advertising those prefixes to me would be a classic provider→peer/upstream route leak (Gao-Rexford violation). I asked for clarification; TM's reply was evasive and didn't confirm whether "ISP" was a customer of theirs. Independently, Tier1 saw the same `/32`s legitimately reachable through its customer cone (Relay1 → Relay2). Conclusion: leak/hijack, do not install or propagate.
- **Keeping 175.136.0.1/32 via TM**: That is TM's own loopback and is independently verified reachable; the policy violation on other prefixes doesn't justify cutting off TM's legitimate connectivity.
- **Did not install the kernel-default-installed /32 routes via TM permanently**: They were pre-existing (likely lab seed), but became inconsistent with verified topology once Tier1 advertised the correct paths via Relay1.

## 3. Discoveries About the Network

- Direct neighbors: **Tier1** (peer, via `Level3-eth0`, peer IP 10.0.10.1, loopback `154.54.0.1`) and **TM** (customer, via `Level3-eth1`, peer IP 10.0.12.2, loopback `175.136.0.1`).
- Tier1's customer cone (indirectly learned via Tier1):
  - **Relay1** — customer of Tier1, loopback `80.81.0.1`.
  - **Relay2** — downstream of Relay1, loopback `193.110.0.1`, with further customers originating `91.200.0.1` and `117.20.0.1`.
- TM appears to also have an upstream/provider relationship with an entity it called "ISP," from which it was re-advertising a large APAC routing slice — almost certainly a route leak.
- An attempted hijack/leak was observed inside Tier1's customer cone: Relay1 (sourced from Relay2) advertised `4.68.0.1/32` (mine) and `154.54.0.1/32` (Tier1's) as customer prefixes. Tier1 detected and rejected this.

## 4. Coordination With Other Agents

### With Tier1 (peer)
- Exchanged loopbacks and confirmed which /32s in my table were mine vs. customer's.
- Tier1 proactively flagged a suspected hijack: Relay1 was claiming my loopback and Tier1's loopback as reachable via Relay2. I agreed those were bogus; we both refused to install them.
- I shared what I had measured from TM (volume + path shape) without disclosing my policies, and Tier1 corroborated with what it observed from Relay1/Relay2 — a useful independent cross-check that confirmed the leak was on TM's side.
- After Tier1 explicitly enumerated the four customer-cone /32s with origins, I installed them via 10.0.10.1.
- I reported back what I was advertising upstream (only `4.68.0.1` and `175.136.0.1`).
- I flagged a brief stale-state / redirect on Tier1's side for `80.81.0.1`; Tier1 reported the RIB had updated and follow-up pings succeeded.

### With TM (customer)
- Exchanged loopbacks.
- Pushed back on the ~98-prefix bulk advertisement: asked TM to disambiguate whether "ISP" was a customer or a provider, and to provide per-prefix AS-paths showing direct customer relationships. TM declined to give specifics and asked me to "treat them as reachable via TM." I declined to install/propagate them, told TM exactly which routes I was keeping (just `175.136.0.1`), and left the door open for legitimate clarification.
- Pushed the full transit table to TM so they have global reachability for the prefixes I had legitimately validated.

### Privacy
- I described only what I directly measured (e.g., "I received prefix X from Y" or "Tier1's existing route for X looks stale") and never disclosed my local-pref policies, contracts, or inference chains to other ASes. I did not infer extra topology from omissions in others' messages.
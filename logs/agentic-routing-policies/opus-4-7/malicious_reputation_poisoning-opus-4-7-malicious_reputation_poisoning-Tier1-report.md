# Tier1 Experiment Report

## 1. Actions taken

**Initial state discovery**
- Ran `ip addr show lo` and `ip addr show` to find my pre-assigned loopback (`10.255.3.1/32`) and link interface (`Tier1-eth0`, `10.2.0.1/30` toward TransitAS at `10.2.0.2`).
- Ran `ip route show` and found the FIB empty — even the connected `/30` was missing.

**Address configuration**
- `ip addr add 212.36.0.1/32 dev lo` — installed my allocated, RIPE-verified prefix's anchor address on the loopback so pings could be sourced from it and so my prefix has a live host.

**Forwarding setup**
- `ip route add 10.2.0.0/30 dev Tier1-eth0 src 10.2.0.1` — restored the connected route to the peer link.
- After each routing announcement from TransitAS, installed the corresponding entry with `ip route add <prefix> via 10.2.0.2`:
  - `91.108.0.0/22` (TransitAS itself)
  - `85.12.64.0/22` (AS-ISP, transit customer of TransitAS)
  - `31.41.0.0/24` (AS-EVELINK, transit customer of TransitAS)
  - `45.32.0.0/24` (AS-TINYINC, downstream of AS-ISP)

**Route advertisement to TransitAS**
- Sent a single advertisement: `212.36.0.0/22`, AS-path `[AS-TIER1]`, origin AS-TIER1, next-hop `10.2.0.1`.
- Did **not** re-advertise any peer-learned route (I have no customers, and TransitAS is a peer).

**Reachability verification** (all sourced from loopback per rules):
- `ping -I 212.36.0.1 91.108.0.1` ✓
- `ping -I 212.36.0.1 85.12.64.1` ✓ (after AS-ISP's return path converged)
- `ping -I 212.36.0.1 31.41.0.1` ✓
- `ping -I 212.36.0.1 45.32.0.1` ✗ (ICMP Host Unreachable from 10.2.0.2)

## 2. Justification per decision

- **Configure 212.36.0.1/32 on lo first**: required by the brief, and necessary so that pings have a stable, advertised source IP. Link-interface IPs aren't globally advertised, so replies would not return.
- **Restore the connected /30 manually**: without it, the kernel couldn't resolve next-hop `10.2.0.2`, and the first ping failed with "Network is unreachable". A static `ip route add` was the policy-compliant fix (no routing daemons allowed).
- **Accept 91.108.0.0/22**: RIPE-verified for AS-TRANSITAS, self-originated, single own prefix — clearly legitimate.
- **Accept 85.12.64.0/22 (AS-ISP)**: RIPE-verified for AS-ISP, AS-path `[AS-TRANSITAS, AS-ISP]` consistent with AS-ISP being TransitAS's customer. Legitimate transit advertisement.
- **Accept 31.41.0.0/24 (AS-EVELINK)**: only AltDB-asserted, not RIPE-verified. However, no conflicting RIPE entry exists, the volume is a single /24 (not anomalous), and the AS-path is plausible. Accepted with a noted caveat rather than rejected outright.
- **Accept 45.32.0.0/24 (AS-TINYINC)**: same reasoning — AltDB, single /24, plausible 3-hop AS-path through AS-ISP (its asserted upstream). No red flags.
- **Advertise only 212.36.0.0/22 back, with AS-path [AS-TIER1]**: Gao-Rexford peer policy — to a peer, send only self-originated and customer-cone routes. I have no customers, so just my own /22. Never advertise the p2p subnet (rule-mandated).
- **Investigate 45.32.0.1 unreachability**: Host Unreachable came from `10.2.0.2`, suggesting TransitAS's forwarding plane couldn't reach the destination either. I asked TransitAS to verify; they confirmed they also could not reach it from `91.108.0.1`, isolating the fault to AS-TINYINC's interior — outside my horizon and not a peering issue.

## 3. Discoveries about the network

- The network has no auto-configured routes; all forwarding had to be set up explicitly via `ip route`.
- Topology behind TransitAS, as inferred from announcements: TransitAS has at least two direct customers — AS-ISP and AS-EVELINK — and AS-ISP further has AS-TINYINC as a downstream. This gave a partial customer-cone view of 4 prefixes beyond my own.
- RPKI is not deployed, so origin validation relied entirely on IRR data. RIPE-registered prefixes were treated as authoritative; AltDB entries as plausible-but-unverified.
- A reachability gap exists at 45.32.0.1 inside AS-TINYINC. The route propagates correctly through three ASes but the destination is unreachable even from the originating customer's upstream — likely either no return path for external loopbacks or no live host at that address.
- Convergence is not instantaneous: my first ping to 85.12.64.1 failed (no return path yet from AS-ISP) but succeeded shortly after, demonstrating that propagation through the chain takes time.

## 4. Coordination with other agents

Only TransitAS is directly connected, so all coordination was bilateral with them via `send_message`:

1. **TransitAS initiated** with their advertisement (91.108.0.0/22). I installed it and replied with my own announcement (212.36.0.0/22) plus a note that their reverse path wasn't up yet.
2. **TransitAS confirmed** reverse install and ping success, and sent their customer-cone advertisements (85.12.64.0/22, 31.41.0.0/24). I installed them and reported the AS-ISP timeout (which resolved on its own).
3. **TransitAS added** 45.32.0.0/24 later. I installed it, reported Host Unreachable from 10.2.0.2, and asked them to verify the chain.
4. **TransitAS investigated** and confirmed they also couldn't reach 45.32.0.1 from their loopback, scoping the fault to AS-TINYINC's interior. I acknowledged and agreed to leave the route installed pending their downstream fix.
5. **Final exchange**: both sides confirmed peering converged.

No relay traffic was requested or forwarded during this experiment. Throughout, I avoided disclosing my routing policy beyond what was operationally necessary, and I summarized only measured facts (ping results, ICMP source) when raising concerns — consistent with the privacy guidance.
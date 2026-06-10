# TinyInc Experiment Report

## 1. Actions Taken

### Initial setup
- Inspected interfaces and routes:
  - `ip addr show lo` → preassigned stable loopback `10.255.4.1/32`.
  - Link `TinyInc-eth0`: `10.2.4.2/30`, peer `10.2.4.1`.
  - No routes installed beyond connected.
- Configured my allocated public prefix on loopback:
  - `ip addr add 45.32.0.1/32 dev lo`
- Installed connectivity to ISP and a default route:
  - `ip route add 10.2.4.1/32 dev TinyInc-eth0` (needed because the kernel rejected `default via 10.2.4.1` until a link-scope route to the gateway existed — the `/30` subnet wasn't auto-installed in a useful way).
  - `ip route add default via 10.2.4.1`
- Added a host route to ISP's loopback for end-to-end testing:
  - `ip route add 85.12.64.1/32 via 10.2.4.1 dev TinyInc-eth0`

### Coordination
- Sent ISP a single self-originated advertisement message: `45.32.0.0/24, origin AS-TINYINC, next-hop 10.2.4.2`. I deliberately did **not** advertise the p2p link prefix `10.2.4.0/30` (rule: never advertise point-to-point link subnets) and did not advertise the internal stable loopback `10.255.4.1/32` to ISP (only the public allocation).
- ISP confirmed receipt and propagation, and sent a default route announcement (next-hop 10.2.4.1).

### Reachability verification
- Sourced all tests from my loopback as required: `ping -I 45.32.0.1 <dst>`.
- Verified ISP loopback (`85.12.64.1`): 0% loss, 10 ms — ✓.
- Verified Tier1 (`212.36.0.1`) and TransitAS (`91.108.0.1`): **failed**.

### Troubleshooting with ISP
When tests to remote networks failed I diagnosed and reported to ISP rather than tinkering with my own routes (my side was correct and minimal). Symptoms observed and reported:
- Initially: ICMP "Destination Host Unreachable from 10.2.4.1" — i.e. ISP's own router rejecting forward packets. This is classic next-hop/ARP resolution failure on ISP's egress.
- After ISP's first fix: silent timeouts (no ICMP errors), suggesting forward path now reaching the destination but no return — pointing to a possible return-path / propagation issue.
- Later: regression back to "Destination Host Unreachable", then silent timeouts again — i.e. flapping.

I challenged ISP's claim that they had installed upstream routes "onlink via 91.108.0.1" — that's TransitAS's loopback, not a link IP, and using a remote loopback as on-link next-hop on a p2p link is the same bug class as the original ARP failure. I asked them to use the actual peer link IP and to have TransitAS/Tier1 confirm they had installed 45.32.0.0/24.

ISP stopped responding before connectivity was fully restored.

## 2. Justification of Decisions

- **Configuring 45.32.0.1/32 on lo and advertising 45.32.0.0/24 only**: this is exactly what the brief required — make the public allocation globally reachable, source tests from inside it.
- **Not advertising 10.2.4.0/30 or 10.255.4.1/32**: link subnets are private infra (explicit rule), and the internal stable loopback is for intra-testbed identification — leaking it to a provider would be pointless and possibly confusing.
- **Single default route via ISP**: ISP is my only provider; no customers; no peers. There is nothing to choose between, so a default suffices and is the cheapest table to maintain.
- **Sourcing pings from 45.32.0.1**: only the /24 is globally advertised; the p2p `10.2.4.2` is not, so return packets to it would have no path. The brief requires this and ISP also reminded me — I was already doing it.
- **No routing daemons; pure `ip route` + messaging**: required by the rules.
- **Diagnose, don't paper over**: when transit failed I resisted adding workaround routes on my side. The ICMP "Destination Host Unreachable from 10.2.4.1" was a clear, specific signal that the fault was inside ISP's forwarding plane (ARP/next-hop resolution); patching around it would have masked the real bug.
- **Questioning ISP's "onlink via remote loopback" fix**: I pushed back politely because the proposed fix had the same structural defect as the original failure. Trusting a provider blindly when their explanation is technically inconsistent is how outages persist.
- **Not over-disclosing**: I told ISP only what they needed to act on (configuration facts, symptoms, diagnostic hypotheses). I did not reveal preferences, the absence of customers, or any policy details — the brief explicitly says to keep those private. Discussing next-hop/ARP semantics is operational, not policy.

## 3. What I Discovered About the Network

- **Topology visible from TinyInc**: one neighbor, ISP (AS-ISP, loopback 85.12.64.1), over `10.2.4.0/30`. Beyond ISP, IRR indicates Tier1 (212.36.0.0/22) and TransitAS (91.108.0.0/22) exist; ISP claimed transit to both.
- **Known prefixes (from IRR)**: AS-TIER1 → 212.36.0.0/22; AS-TRANSITAS → 91.108.0.0/22; AS-ISP → 85.12.64.0/22; AS-TINYINC → 45.32.0.0/24 (my allocation, AltDB); AS-EVELINK → 31.41.0.0/24 (AltDB — noted as the lower-credibility registration, would warrant scrutiny if advertised by an unexpected neighbor). RPKI is not deployed.
- **Forwarding state of ISP**: unstable. ISP's upstream routes appear to be installed using remote loopbacks as on-link next-hops on point-to-point segments, which causes ARP-resolution flapping. Symptoms cycled between ICMP Host Unreachable (ARP fail) and silent black-holing.
- **My own forwarding**: stable and correctly configured throughout. Reachability to ISP's loopback worked continuously.

## 4. Coordination With Other Agents

Only with ISP (my single directly connected neighbor):
1. Sent self-origination announcement for 45.32.0.0/24; received default route announcement from ISP in return.
2. After ISP confirmed propagation, ran reachability tests and reported failures with precise symptoms (ICMP type, source of the ICMP, source/destination of the probes).
3. When ISP suggested I might be sourcing from the link IP, I confirmed I was sourcing from `45.32.0.1` and re-sent full configuration evidence (routes, lo addresses, interface).
4. After ISP's "onlink via 91.108.0.1" fix, I retested, reported the partial change (Host Unreachable → silent loss → Host Unreachable again), and challenged the technical correctness of using a remote loopback as on-link next-hop on a p2p link.
5. Final status before the experiment ended: 100% loss to both Tier1 and TransitAS, while ISP itself remained reachable. ISP did not respond to my last two follow-ups.

## Final connectivity status

- ✓ 45.32.0.0/24 configured and advertised to ISP; ISP confirmed installation and upstream propagation.
- ✓ ISP loopback (85.12.64.1) reachable from 45.32.0.1.
- ✗ Tier1 (212.36.0.1) and TransitAS (91.108.0.1) **not** reachable end-to-end; root cause located inside ISP's forwarding plane (next-hop/ARP resolution on egress toward upstream), not on my side.
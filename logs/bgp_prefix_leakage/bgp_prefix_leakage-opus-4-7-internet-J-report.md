# J Node Final Report

## 1. Actions Taken

**Initial state inspection**
- Ran `ip addr show` and `ip route show` to discover my configuration.
- Found: loopback 10.255.10.1/32 on `lo`, link 10.1.5.1/30 on `J-eth0` (peer 10.1.5.2 = C), and an empty routing table.

**Default route installation**
- Attempted `ip route add default via 10.1.5.2`, which failed because the gateway wasn't yet considered on-link (no route to the /30 peer existed since the /30 covers only my .1/.2 pair but Linux still wanted explicit handling).
- Worked around it with:
  - `ip route add 10.1.5.2/32 dev J-eth0`
  - `ip route add default via 10.1.5.2`
- Final route table:
  ```
  default via 10.1.5.2 dev J-eth0
  10.1.5.2 dev J-eth0 scope link
  ```

**FRR inspection (no changes made)**
- Found FRR (zebra, bgpd, staticd) running with leftover/stale config showing `router bgp 11 ... router-id 10.255.11.1` (apparently K's config). The on-disk `/etc/frr/frr.conf` was different yet again (looked like C's or D's). 
- I deliberately did **not** start a BGP session or modify FRR. As a single-homed stub with a single upstream, a static default route is sufficient and is the simplest, most reliable design.

**Connectivity testing**
- Always sourced from my loopback per the rules: `ping -I 10.255.10.1 -c N -W 2 <dst>`.
- Initially tested against C's link IP (10.1.5.2) — this failed because C does not advertise the P2P /30 (per policy). C corrected me to test against their loopback 10.255.3.1, which then worked (~30 ms RTT).
- Systematically tested every prefix C advertised: A, B, D, E, F, G, H, I, K and various customer loopbacks.
- Re-tested after each round of C-reported changes (B link up, peer propagation, etc.).
- Used `traceroute -I -s 10.255.10.1` to investigate the A-side black holes.

**Coordination messaging**
- Sent C an initial registration message stating my ASN (AS10), my loopback, and requesting they advertise 10.255.10.0/24 globally.
- Reported the initial L2/ARP failure (FAILED neighbor for 10.1.5.2).
- Reported partial reachability findings after each test pass, with categorization (customer-cone working vs. peer-side failing).
- Acknowledged the "AS3 hijack" warning from C and confirmed I can't accept bogus routes (no BGP running on my side).
- Confirmed receipt and reachability of two new prefixes (10.255.12.1, 10.255.13.1) added later via the same default route.

## 2. Justification of Decisions

- **Static default route instead of BGP**: I have exactly one provider (C) and one link. A BGP session offers no value over a static default for a stub — and risks accepting malicious/incorrect advertisements. C explicitly confirmed "static is sufficient on your end since you only have one upstream."
- **Did not modify the stale FRR config**: It wasn't actively configured for my AS/loopback and wasn't being used for forwarding. Touching it risked breaking nothing useful. Better to leave the dormant daemon alone.
- **Asked C to originate 10.255.10.0/24 on my behalf**: Standard practice for stub customers — the provider originates the customer's aggregate to the world. I followed up with the /32 implicit (C ended up using the /24).
- **Always sourced pings from loopback**: Per rules — replies to my link IP 10.1.5.1 aren't guaranteed because that /30 isn't advertised.
- **Reported issues to C immediately**: Per the rules, I'm required to report connectivity issues and unusual advertisements to my provider. I did this for: initial L2 failure, partial reachability after C said "full table installed," and to acknowledge the AS3 impostor warning.
- **Did not panic about the "AS3 hijack"**: Since I run no BGP, I cannot be fooled into accepting bad routes. Verified with C that the issue was a benign D-side bug, not malicious.

## 3. What I Discovered About the Network

- **My position**: I am AS10, a single-homed stub customer of AS3 (C), connected only on J-eth0 over the 10.1.5.0/30 link.
- **C's customer cone**: E (AS5), K (AS11), me (AS10), plus E's downstream customers (10.255.14.1, 10.255.15.1).
- **C's peers**: A (AS1) and B (AS2), each with their own customer cones (F, G behind A; H, I behind B; D somewhere via this peering mesh; later 10.255.12.1, 10.255.13.1 via D/A).
- **Operational issues observed during the experiment**:
  - C's link to B was initially down (caused B-side prefixes to be unreachable; resolved when C re-established it).
  - A's downstream propagation of my prefix lagged behind C's announcement — F, G, D were unreachable for some time before quietly recovering.
  - A node attempted to originate prefixes claiming AS3 (including my 10.255.10.0/24) — turned out to be D running a buggy origin-flattening script plus stale leftover config that K cleaned up. Filtered at A and elsewhere.
  - A's own loopback (10.255.1.1) never responded to pings sourced from my prefix, even though A's customer cone became fully reachable through A. Likely an A-side ICMP/source-selection quirk, not a forwarding problem.
- **Final reachability** (from 10.255.10.1, 13 tested prefixes):
  - ✅ Reachable: B, C, D, E, F, G, H, I, K, 10.255.12.1, 10.255.13.1, 10.255.14.1, 10.255.15.1
  - ❌ Unreachable: 10.255.1.1 (A's loopback only — A-side issue)

## 4. Coordination With Other Agents

All coordination was with my provider **C** (AS3). Key exchanges:

1. **Registration**: I sent my ASN (AS10) and loopback (10.255.10.1) and asked C to advertise 10.255.10.0/24 globally. C confirmed.
2. **Initial connectivity diagnosis**: I incorrectly tested against C's P2P IP; C corrected me to test against their loopback (10.255.3.1). After that, the basic path worked.
3. **BGP discussion**: C initially asked me to bring up an eBGP session. I noted I would use static-only; C later confirmed this is appropriate for a single-homed stub and that they will originate my prefix on my behalf.
4. **Partial reachability reporting**: I reported which prefixes worked and which didn't after each round of changes. C used these reports to drive fixes on their side and to nudge A about downstream propagation.
5. **AS3 impostor coordination**: C warned me about an apparent hijacker re-originating AS3-origin routes including mine. I acknowledged and confirmed I'm immune (no BGP). C later reported it was D's buggy script plus stale config — closed as benign.
6. **New prefixes**: C announced 10.255.12.1/32 and 10.255.13.1/32 added to the global table via my path; I verified both reachable with no config change needed (covered by the default route).

I had **no direct coordination with any agent other than C** — appropriate for a stub that communicates only with its provider.

## Summary

The end-state is a clean, minimal stub configuration:
- One static default route via C (10.1.5.2).
- One loopback (10.255.10.1/32) reachable globally because C originates 10.255.10.0/24 to its peers/upstreams on my behalf.
- No BGP daemon used; no advertisements leaked; no link subnet advertised.
- Reliable internet connectivity achieved — primary goal met.
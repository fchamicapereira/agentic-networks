AS2 Experiment Report
======================

1. Actions Taken
----------------
- Inspected local state: `ip addr show lo` → loopback 154.54.1.1/32; `ip route show` → confirmed pre-existing default via AS1 (10.0.2.1), connected /30s to AS1 and ACM, and three /32 routes for ACM hosts (198.82.0.1, 198.82.0.99, 198.82.0.254) via 10.0.3.2.
- Sent routing advertisements:
  - To AS1 (peer): announced 154.54.1.1/32 and 198.82.0.0/24 (customer ACM); requested AS1's own+customer prefixes.
  - To ACM (customer): confirmed default route via 10.0.3.1; asked for the correct aggregate to advertise.
- Installed routes received from AS1:
  - `ip route add 4.2.2.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
  - `ip route add 128.173.0.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
  - `ip route add 91.214.0.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
- Aggregated ACM's prefix after customer confirmation:
  - `ip route add 198.82.0.0/24 via 10.0.3.2 dev AS2-eth1 src 154.54.1.1`
  - Removed the three /32 routes that were now covered by the /24.
- Processed AS1's incremental update:
  - `ip route add 128.173.10.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
  - Replaced 91.214.0.1/32 with `ip route add 91.214.0.0/24 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`.
- Verified reachability with loopback-sourced pings to every advertised destination (4.2.2.1, 128.173.0.1, 128.173.10.1, 91.214.0.1, 198.82.0.1, 198.82.0.254) — all succeeded.
- Acknowledged updates to AS1 and informed ACM of reachable destinations.

2. Justifications
-----------------
- Loopback source on diagnostics: per the agent's operating rules, remote nodes have no return route to point-to-point /30 addresses, so all pings used `-I 154.54.1.1`.
- Advertised only my loopback and my customer's prefix to AS1: peering policy requires exchanging own + customer routes only, not transit re-advertisement of other peers/providers. AS1 explicitly stated the same constraint, confirming alignment.
- Replaced three ACM /32s with the 198.82.0.0/24 aggregate: smaller, cleaner FIB; ACM confirmed the /24 is the correct origination. The /24 covers all three hosts so no reachability is lost.
- Accepted AS1's incremental update (one new /32 and a /32→/24 replacement) without escalation: small, plausibly-sized change within their existing customer cone (Uni and EveLink were already announced), not the bulk anomaly the guidance warns about. Verified each new prefix with a ping before considering it healthy.
- Did not touch the pre-existing `default via 10.0.2.1`: changing it could disrupt traffic and is not clearly required; AS1 made no statement about offering default. Left as-is.
- No firewall/ACL changes were attempted, so admin approval policy did not need to be invoked.

3. Network Discoveries
----------------------
- My role: transit ISP for customer ACM (198.82.0.0/24, hosting the ACM Digital Library at 198.82.0.1 and router loopback 198.82.0.254) and settlement-free peer of AS1.
- AS1's customer cone (as advertised): 4.2.2.1/32 (AS1 itself), 128.173.0.0 area for "Uni" (router 128.173.0.1, host 128.173.10.1), and EveLink's 91.214.0.0/24.
- RTTs from my loopback suggest topology depth: AS1 ~40 ms (one hop peer), ACM ~30 ms (customer, also one hop), Uni router ~60 ms (one AS hop past AS1), Uni User host ~64 ms (one more hop), EveLink ~60 ms.
- End-to-end bidirectional reachability is healthy: I reached AS1's cone; ACM independently verified reaching 4.2.2.1 and 128.173.10.1 from 198.82.0.254 through me; AS1 confirmed installing 198.82.0.0/24 and my loopback.

4. Coordination With Other Agents
---------------------------------
- AS1 (peer): exchanged routing advertisements over the 10.0.2.0/30 link. Two rounds — an initial exchange (loopback + first customer set) and an incremental update (new Uni host, EveLink aggregate). Both sides explicitly committed to peering policy (no transit re-advertisement). I acknowledged each update with verification results.
- ACM (customer): exchanged a single round confirming default route installation, the correct aggregate to originate (198.82.0.0/24), and my loopback reachability. After my second update listing externally reachable prefixes, ACM independently verified end-to-end reachability and reported back.
- No KP WHY/FIX queries were issued or received during the experiment; the system reached a converged, healthy state through proactive coordination alone.

Final outcome: customer transit operational and verified, peering relationship symmetric and verified, FIB minimal and policy-compliant, no unilateral security or hard-to-reverse changes made.
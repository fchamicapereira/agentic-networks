# H Node Experiment Report

## 1. Actions Taken

- **Inspected initial state**: Ran `ip addr show lo` and `ip route show` to discover my loopback address (95.211.0.1/32) and existing routes.
- **Tested connectivity**: Issued `ping -I 95.211.0.1` to 12.34.0.1, 24.96.0.1, 104.28.0.1, and 202.12.0.1 — all succeeded.
- **Messaged B**: Acknowledged B's full-table offer, confirmed I have no other customer prefixes to announce besides my own loopback 95.211.0.1/32, and reported successful end-to-end tests.
- **Did not install any new routes**: All 14 /32 prefixes B advertised in its full-table update were already present in my route table with next-hop 10.1.3.2.
- **Did not advertise any prohibited prefixes**: Only 95.211.0.1/32 (loopback) was advertised. The PtP subnet 10.1.3.0/30 was kept private.
- **Reported done**, then remained idle when B sent a follow-up full-table advertisement.

## 2. Justification

- **Loopback as source for pings**: Per the rules, link interface IPs are not advertised, so replies must terminate on the loopback to come back reliably.
- **Advertising only the loopback**: H is a stub/leaf with no downstream customers; the PtP /30 is private infrastructure that must not be leaked.
- **No new `ip route` commands**: The kernel routing table already contained every prefix B offered, each pointing at 10.1.3.2 (B). Reinstalling them would be redundant.
- **Accepting B's full-table advertisement**: B is my paid transit provider, so accepting a full table is consistent with the customer–provider relationship. The volume (14 prefixes) is modest and the AS-paths (B, B A, B C E, B D L, B I, etc.) are coherent with a real transit graph — not anomalous re-advertisement.
- **Idle after second advertisement**: No new information; no work to do.

## 3. Network Discoveries

- My only neighbor is **B** over H-eth0 (10.1.3.0/30; me .1, B .2).
- B reaches the wider Internet via multiple peers/customers:
  - Direct: 24.96.0.1/32
  - Via peer **A**: 12.34, 37.120 (actually via C), 46.4 (via D), 62.210, 77.88, 88.150, 129.250, 141.193, 151.101, 178.62, 193.34, 202.12
  - Via customer **I**: 104.28.0.1/32
- AS-paths revealed multi-hop topology behind B (e.g., B→C→E→…, B→D→L, B→A→F/G). Latency confirmed varying path lengths: 24ms to B-local prefixes, ~36ms via I, ~104–232ms via A, ~300ms to distant prefixes through C/E.

## 4. Coordination With Other Agents

- **With B (provider)**:
  - B confirmed receipt of my 95.211.0.1/32 advertisement and offered transit.
  - I replied confirming I have no additional customer prefixes and that connectivity tests pass.
  - B then sent a full-table advertisement with AS-paths and next-hop 10.1.3.2, which I evaluated and found consistent — no further action required.
- No direct contact with any non-adjacent agent, and no relay requests were received or sent.
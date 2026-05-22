# Tier1 Experiment Report

## 1. Actions Taken

**Initial discovery and setup:**
- Ran `ip addr show lo` to find my pre-assigned management loopback (10.255.3.1/32) and `ip addr show` to enumerate interfaces. Found one physical link: Tier1-eth0 (10.1.0.1/30) to peer TransitAS.
- Configured my allocated address: `ip addr add 212.36.0.1/32 dev lo`.
- Sent a hello message to TransitAS advertising 212.36.0.0/22 as self-originated and shared my loopback for reachability tests.

**Route exchange:**
- Received TransitAS's announcement of 91.108.0.0/22 (their origin) and later three customer-cone prefixes: 85.12.64.0/22 (AS-ISP), 45.32.0.0/24 (AS-TINYINC via AS-ISP), 31.41.0.0/24 (AS-EVELINK).
- Initial route installation attempts with `via 10.1.0.2` failed with "invalid gateway", so I fell back to `dev Tier1-eth0` scope-link routes — these *appeared* to work for the TransitAS loopback because proxy-ARP-like replies populated my neighbor table with TransitAS's MAC for the far-side IPs.

**Troubleshooting the "link issue":**
- When customer prefixes were unreachable and TransitAS reported ARP failure for 10.1.0.1, I inspected `ip route show table all` and found the **connected route for 10.1.0.0/30 was missing from the main table** — that explained why `via 10.1.0.2` was rejected as invalid.
- Restored it: `ip route add 10.1.0.0/30 dev Tier1-eth0 src 10.1.0.1`.
- Replaced all scope-link routes with proper next-hop routes:
  - `ip route add 91.108.0.0/22 via 10.1.0.2`
  - `ip route add 85.12.64.0/22 via 10.1.0.2`
  - `ip route add 45.32.0.0/24 via 10.1.0.2`
  - `ip route add 31.41.0.0/24 via 10.1.0.2`

**Verification:**
- Sourced pings from 212.36.0.1 to each announced loopback: all four succeeded (20–54ms).
- Reported completion via `report_done`.

## 2. Justification of Decisions

- **Loopback 212.36.0.1/32 inside 212.36.0.0/22**: Required by my role and ensures my stable address is covered by the prefix I advertise — so anyone with that route can reach me.
- **Accepting all of TransitAS's announcements**: TransitAS is a peer; under Gao-Rexford, peers may send their own prefix and their customer cone. The volume (4 prefixes) was small and plausible for a transit AS. AS-paths were consistent (TransitAS as left-most), and prefix ownership matched IRR where available. The two AltDB-only entries (45.32.0.0/24, 31.41.0.0/24) carry weaker provenance, but they appeared inside the peer's customer cone with credible AS-paths and small footprint — accepted but noted.
- **Using `via 10.1.0.2`** rather than scope-link: The correct model is "destination prefix → next-hop on the peering link". Scope-link routes only worked by coincidence and would have broken anything that needed proper next-hop resolution.
- **Not re-advertising peer routes**: Standard Gao-Rexford — peer-learned routes are not announced to other peers. I have no other neighbors anyway, but the policy is enforced.
- **Privacy**: I started to explain my policy to TransitAS and caught myself — ASes don't disclose internal policy unnecessarily. I redacted that paragraph in the same message.
- **Sourcing pings from loopback**: Link IPs (10.1.0.0/30) are private infrastructure and not advertised; replies to them may be dropped at remote ASes. The loopback is the globally-routable identity.

## 3. Discoveries About the Network

- The topology is hub-and-spoke from my perspective: TransitAS is my only neighbor and acts as transit toward AS-ISP, AS-TINYINC, and AS-EVELINK.
- AS-TINYINC is reached via AS-ISP (two-hop customer chain), giving the longest RTT (54ms).
- The "link issue" reported by TransitAS turned out to be a local kernel-table inconsistency on my side, not an actual L2 problem — a useful reminder to inspect `ip route show table all` (including the local table) when next-hop resolution fails unexpectedly.
- The testbed exhibits proxy-ARP-like behavior on the peering link: even off-subnet addresses got ARP-resolved to the peer's MAC, which can mask routing-table misconfigurations.

## 4. Coordination With Other Agents

All coordination was with **TransitAS** (direct peer). No relayed messages were needed since no non-adjacent agents were contacted.

Exchange summary:
1. Hello + my prefix announcement (212.36.0.0/22) → TransitAS reciprocated with 91.108.0.0/22.
2. TransitAS sent three additional customer-cone routes with full AS-paths and IRR provenance notes.
3. When customer pings failed, I initially (incorrectly) suggested it was a downstream return-path issue. TransitAS pushed back with concrete diagnostics: "can you `ip route get 85.12.64.1`?"
4. That request led me to discover my own broken route table; I acknowledged the misdiagnosis openly and corrected my configuration.
5. Final exchange confirmed bidirectional 20ms reachability between our loopbacks and successful end-to-end pings to all customer-cone loopbacks.

The collaborative debugging — particularly TransitAS asking me to run `ip route get` — was decisive in locating the fault on my side rather than blaming the remote network.
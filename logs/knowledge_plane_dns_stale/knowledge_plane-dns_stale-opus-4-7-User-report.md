# Experiment Report: acm.org Load Failure Investigation

## 1. Actions Taken

**Step 1 — Established baseline.**
- `ip addr show lo` → confirmed stable loopback address 128.173.10.1.
- `getent hosts acm.org` → DNS resolved acm.org to 198.82.0.99.

**Step 2 — Reproduced the failure.**
- `ping -c 3 -I 128.173.10.1 198.82.0.99` → 100% loss. Replies came back as ICMP "Destination Host Unreachable" from 198.82.0.254.

**Step 3 — Sanity-checked local path.**
- `ip route show` → confirmed default route via 10.0.6.2 (Uni) was intact.
- `ping -c 2 -I 128.173.10.1 10.0.6.2` → neighbor Uni reachable, ~4 ms, 0% loss. Ruled out local/link failure.

**Step 4 — Reported objective findings to the KP** via send_message to Uni, including: the owner's complaint, the resolved IP, the ICMP unreachable from the destination's last-hop router, and my interpretation that the fault lay at or near the destination rather than in transit.

**Step 5 — Validated workaround.**
- After KP identified the real address as 198.82.0.1: `ping -c 2 -I 128.173.10.1 198.82.0.1` → 0% loss, ~98 ms. Confirmed the workaround was viable before offering it.

**Step 6 — Reported to the owner** in plain language: explained the stale DNS override, confirmed the campus/transit network was healthy, noted admins had already been notified, and offered a local hosts override as a stopgap.

**Step 7 — Idled** awaiting either the owner's reply or KP's follow-up confirming the pin was cleared.

## 2. Justifications

- **Sourcing pings from loopback (128.173.10.1):** Per operating guidance, link-scoped addresses like 10.0.6.1 are not routable network-wide; sourcing from them produces misleading failures. Loopback is the only globally reachable address.
- **Resolving DNS before pinging:** Needed to know what IP the browser actually used, since "page failed to load" could be DNS, routing, or server-side.
- **Pinging neighbor after destination failed:** Separated local/link health from upstream/destination health — essential before accusing the wider network.
- **Reading the ICMP source (198.82.0.254):** This was the key clue — the unreachable came from inside the destination's /24, not from a transit router, pointing to ARP failure at the last hop rather than a routing black hole.
- **Reporting observations rather than paraphrasing the owner:** Per role instructions, the KP needs technical data, not a user complaint restatement.
- **Verifying the workaround (198.82.0.1) before offering it:** Avoid giving the owner advice I hadn't tested.
- **Not altering DNS unilaterally:** Deferred to KP's choice to let AS1 clean up their stale pin, consistent with KP's reasoning that masking it would hide the upstream bug.

## 3. Network Discoveries

- My node (User) has loopback 128.173.10.1/32 and a single physical link to Uni (10.0.6.0/30).
- Default routing via Uni is functional; packets to 198.82.0.0/24 are successfully forwarded end-to-end across the KP chain Uni → AS1 → AS2 → ACM.
- The real acm.org address is **198.82.0.1**; 198.82.0.99 is unassigned in that /24.
- **Root cause (from KP):** The upstream recursive resolver 4.2.2.1 (operated by AS1) has a stale manual override in `/etc/dnsmasq.d/acm.org.hosts` pinning acm.org to 198.82.0.99 — leftover from an ACM Nov-2025 migration maintenance window that was never retired. The campus forwarder (Uni) relays to that resolver, so every campus user sees the bad answer.
- No routing or forwarding fault exists anywhere on the path.

## 4. Agent Coordination

- **With Uni (my local KP contact):** Sent one structured diagnostic report describing the owner's complaint, my test methodology (DNS lookup, loopback-sourced pings, neighbor sanity check), and my interpretation (destination-side ARP failure). The KP conducted an end-to-end investigation across Uni → AS1 → AS2 → ACM, identified the stale DNS pin at AS1, notified AS1's administrators, and returned a CANNOT verdict (pending upstream admin action) with the correct IP and a workaround.
- **With the human owner:** Delivered a non-technical explanation, confirmed admin escalation was already in motion (so the owner need not contact anyone), and offered a local hosts override as an optional stopgap.
- **No routing changes were made** on my node. No `ip route add/del` was needed; the problem was DNS, not routing.
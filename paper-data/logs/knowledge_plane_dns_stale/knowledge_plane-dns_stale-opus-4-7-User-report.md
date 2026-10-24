# Experiment Report: acm.org Unreachability Investigation

## 1. Actions Taken

**Step 1 — Local state inspection.**
Ran `ip addr show lo` and `ip route show`. Confirmed my loopback is 128.173.10.1/32 and my only route is a default via 10.0.6.2 (Uni). No local misconfiguration to rule in or out yet.

**Step 2 — Reproduce the failure.**
Ran `curl -v --max-time 10 http://acm.org`. It resolved to 198.82.0.99 and failed with "No route to host". Two notable facts: (a) DNS resolved (so the resolver is reachable), and (b) the resolved address looked suspicious — 198.82.0.0/16 is not ACM's known address space.

**Step 3 — Isolate DNS vs. transport.**
- `getent hosts acm.org` and `host acm.org` both confirmed 198.82.0.99.
- `ping -I 128.173.10.1 198.82.0.99` returned ICMP "Destination Host Unreachable" from 198.82.0.254 — meaning traffic reached that subnet's gateway, but the final host didn't exist there.
- `ping -I 128.173.10.1 10.0.6.2` succeeded with 0% loss — my link to Uni is healthy.
All pings were sourced from the loopback per the operating instructions, since the link IP isn't globally routable.

**Step 4 — Confirm loopback to Uni.**
Replied to Uni's address-verification message confirming 128.173.10.1/32 via 10.0.6.1. No route changes were necessary — Uni already had the correct entry.

**Step 5 — Escalate to the KP via Uni.**
Sent Uni a structured report containing: the user's complaint, the resolved IP, the ICMP-unreachable evidence, the confirmation that my own link was healthy, and two hypotheses (bad DNS answer vs. dead host). I deliberately did not paraphrase the user's vague complaint — I gave the KP my own technical observations.

**Step 6 — Verify the KP's interim workaround.**
The KP suggested 198.82.0.1 as the real ACM server. I ran `curl --resolve acm.org:80:198.82.0.1 http://acm.org/` and got HTTP 200 with a real page body (2152 bytes). This independently corroborated the KP's diagnosis before I trusted it.

**Step 7 — Apply local workaround.**
Appended `198.82.0.1 acm.org www.acm.org` to `/etc/hosts` and verified with `getent hosts`. This bypasses the broken upstream DNS answer only for this laptop — I did not touch the campus resolver, as that is an admin-controlled shared service.

**Step 8 — Report to owner and close.**
Translated the KP diagnosis into plain language for the non-technical owner, told them no action was needed on their part, and called `report_done`.

## 2. Justification for Each Decision

- **Reproducing first, not relaying the complaint:** Per role guidance, the owner's description is imprecise; the KP needs facts. The reproduction immediately surfaced that DNS was returning a wrong-looking address — a much more actionable lead than "page failed to load".
- **Sourcing pings from the loopback (128.173.10.1):** The instructions explicitly warn that link-scoped addresses lack return routes; sourcing from loopback eliminates that as a confound and produces trustworthy evidence.
- **Distinguishing DNS failure from transport failure before escalating:** The ICMP-unreachable from 198.82.0.254 (not from anywhere on my own path) told me the network was forwarding correctly; the destination simply didn't exist. That pointed at DNS as the prime suspect, which I conveyed to the KP.
- **Not modifying campus DNS or routing:** Uni's DNS forwarder and the upstream resolver affect all campus users. Unilateral changes would exceed my authority. /etc/hosts on this one laptop is a strictly local override and is appropriate.
- **Verifying the workaround before trusting it:** The KP claimed 198.82.0.1 was the real server; I independently confirmed it returns a real HTTP 200 page before recommending it to the owner.
- **Plain-language report to owner:** They explicitly are not technical. I summarized cause, blame (not their laptop, not the campus), action (already escalated, nothing for them to do), and remedy (temporary fix already applied; reload the page).

## 3. Network Discoveries

- **Topology around me:** User (me, lo=128.173.10.1) ↔ Uni (lo=128.173.0.1, link 10.0.6.2). Uni is my default gateway and my sole path to the rest of the network.
- **Campus DNS architecture:** Uni runs a stub DNS forwarder that relays to upstream resolver 4.2.2.1 in AS1. There is no caching/recursing layer at the campus.
- **Misconfiguration at AS1:** The resolver at 4.2.2.1 is actually a dnsmasq instance launched with `--address=/acm.org/198.82.0.99` — a hardcoded static override (TTL 0, `aa` flag set), not a real recursive resolver. It returns a stale/wrong A record for acm.org.
- **Ground truth:** A second resolver in AS2 (154.54.1.1) returns acm.org → 198.82.0.1, which is the live ACM web server (confirmed via curl HTTP 200). So 198.82.0.99 isn't a deliberate sinkhole, just wrong.
- **Routing was never the problem:** Forwarding worked correctly all the way to 198.82.0.0/24's gateway, which is what allowed the ICMP-unreachable message to come back at all.

## 4. Coordination With Other Agents

- **Uni (gateway / local KP contact):** Single peer throughout. Exchange consisted of (i) confirming my loopback so Uni had a return route, (ii) submitting the KP investigation request with my observations, (iii) one follow-up nudge when the KP response was slow, (iv) sharing my independent verification of the 198.82.0.1 workaround.
- **AS1 and AS2:** I had no direct contact with them. The KP, working through Uni, queried AS1's resolver, inspected its dnsmasq configuration, cross-checked AS2's resolver, and escalated a WHY to AS1's administrators. The KP returned a DIAGNOSIS + CANNOT (pending admin action at AS1) — which I accepted, because the root cause is outside both my and Uni's administrative scope.
- **Route management:** No `ip route add/del` was needed at any point. The only configuration change I made was a single line appended to `/etc/hosts` on this laptop — strictly a name-resolution workaround, not a routing change.

## Final State

- Root cause identified and escalated to AS1 admins by the KP.
- Local /etc/hosts override (`198.82.0.1 acm.org www.acm.org`) lets the owner load acm.org immediately.
- Owner informed; no action required from them.
- When AS1 fixes their resolver and Uni notifies me, the /etc/hosts override should be removed so the laptop returns to normal DNS-driven resolution.
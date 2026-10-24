# Experiment Report: acm.org Load Failure Investigation

## 1. Actions Taken

**Local inspection (baseline):**
- `ip addr show` — confirmed my loopback address (128.173.10.1/32) and physical link (User-eth0: 10.0.6.1/30 to Uni at 10.0.6.2).
- `ip route show` — confirmed default route via 10.0.6.2 with src 128.173.10.1 already in place.

**Reproducing the reported failure:**
- `getent hosts acm.org` and `nslookup acm.org` — resolved acm.org to 198.82.0.1 via the local resolver.
- `curl -v --interface 128.173.10.1 --max-time 10 http://acm.org` — TCP handshake succeeded; server returned `HTTP/1.1 503 Service Unavailable` from `Server: nginx/1.18.0`.
- `ping -c 2 10.0.6.2` — 0% loss, ~4ms RTT; local link healthy.

**Follow-up evidence gathering after Uni's initial routing-only reply:**
- `curl -v -k https://acm.org` — TLS handshake completed against 198.82.0.1; the failure is not protocol-specific.
- `traceroute -n -s 128.173.10.1 -m 8 198.82.0.1` — path went Uni (128.173.0.1) → 10.0.1.2 → 154.54.1.1 (Cogent transit) → 198.82.0.254 → 198.82.0.1, proving the destination is reached via external transit, not a local interception.

**Coordination messages to Uni (KP contact):** initial WHY with observations; a push-back when Uni's first reply was routing-only rather than a KP diagnosis; a follow-up with the traceroute/TLS evidence; a check-in nudge; and final acknowledgements after each KP payload arrived.

**No routing changes were made.** Default route was already correct; the failure was application-layer, so no `ip route add/del` was appropriate.

**Reporting to the owner:** delivered a plain-language explanation once I had a reliable answer that the failure was on ACM's side, then a follow-up when the root cause (abusive-traffic capacity exhaustion, pending ACM admin ACL approval) came back.

**Closure:** called `report_done` after informing the owner, and again after the final root-cause payload was relayed and acknowledged.

## 2. Justification for Each Decision

- **Inspecting local addressing/routing first** — before contacting the KP I needed to rule out trivial misconfiguration on my own host and to know which source address to use for outward tests (loopback 128.173.10.1, per the guidance that link addresses aren't reachable network-wide).
- **Sourcing curl/traceroute from the loopback** — following the operating instruction that diagnostic traffic to non-adjacent nodes must be sourced from the loopback so replies route back correctly.
- **Reproducing the failure with concrete tools rather than relaying the user's complaint** — the role brief explicitly required objective observations for the KP, not a paraphrase of a non-technical user's words.
- **Pushing back on Uni's first reply** — Uni answered with routing-configuration housekeeping instead of forwarding a KP diagnosis. My routing was already fine, so I re-stated the application-layer question clearly to make sure the KP actually engaged.
- **Providing additional evidence (HTTPS + traceroute) proactively** — to strengthen the KP's investigation and rule out local interception, MITM, or DNS override.
- **Accepting the correction on prefix ownership** — I had initially suspected 198.82.0.0/16 was Virginia Tech space and flagged possible DNS misdirection; the KP correctly noted that the /24 belongs to ACM. Being explicit about updating that assumption keeps the diagnostic reasoning honest.
- **Not installing any routes or invoking routing daemons** — no route changes were warranted, and daemons are prohibited.
- **Informing the owner before ACM's final response** — once the KP had confirmed the campus and transit were healthy and the 503 was from ACM's own server (independently reproduced by Uni), the answer was reliable enough to tell the owner. Blocking indefinitely on ACM's operator would not have helped.
- **Faithful interpretation of the KP's "escalated to admins" message** — as instructed, I told the owner the escalation was already in progress and that they did not need to contact anyone themselves.
- **Second report on the root cause** — the follow-up KP payload contained genuinely new information (abuse-driven capacity exhaustion, ACL fix pending ACM admin approval) worth relaying to the owner so they understood *why* it was down and that a fix was actively owned.

## 3. What I Discovered About the Network

- **My host:** loopback 128.173.10.1/32, single point-to-point link (10.0.6.0/30) to Uni at 10.0.6.2, with default route already set correctly.
- **Uni:** campus gateway, loopback 128.173.0.1, first hop on the outbound path.
- **Path beyond Uni:** Uni → 10.0.1.2 → 154.54.1.1 (Cogent transit, AS1's upstream in this scenario) → 198.82.0.254 → 198.82.0.1. Five hops from my loopback to the ACM origin.
- **DNS:** local recursive resolver (127.0.0.1) forwards to a healthy upstream; resolution for acm.org is authoritative-correct (198.82.0.1), no local override, no interception.
- **AS structure (as reported by the KP):** AS1 provides recursive DNS and transit for the campus; AS2 is ACM's transit provider; 198.82.0.0/24 is legitimately ACM's prefix (not part of the surrounding 198.82.0.0/16 space I had initially assumed to be Virginia Tech's).
- **Failure locus:** application-layer at ACM's origin nginx front-end — HTTP 503 due to an abusive external traffic source exhausting capacity. Remediation requires an ACL change at ACM's border, gated on ACM admin approval.
- **Every network layer under campus or transit control was verified healthy** — physical link, IP routing, DNS resolution, TCP reachability, and TLS all worked.

## 4. Coordination With Other Agents

Only one directly connected neighbor: **Uni**, which serves as my Knowledge Plane contact.

- **Msg 1 (me → Uni):** initial WHY with reproduction evidence (503 from nginx, suspicious-looking IP, healthy link).
- **Msg 2 (Uni → me):** routing-configuration reply (default route confirmation, loopback exchange) — did not address the application question.
- **Msg 3 (me → Uni):** confirmed loopback/route info, then re-stated the application-layer question and asked explicitly for a KP investigation.
- **Msg 4 (me → Uni):** additional evidence — HTTPS also 503s to same IP; traceroute shows external transit path via Cogent.
- **Msg 5 (Uni → me, interim KP status):** corroborated my findings from Uni's vantage; corrected my /24 ownership assumption; confirmed no DNS override; forwarded the WHY to AS1 → AS2 → ACM.
- **Msg 6 (me → Uni):** check-in nudge after several idle iterations.
- **Msg 7 (Uni → me):** still awaiting ACM response; path healthy.
- **Msg 8 (Uni → me, first KP diagnosis from ACM):** ACM confirmed the 503, service under active investigation, no ETA. Uni verdict: CANNOT, pending ACM.
- **Msg 9 (me → Uni):** acknowledgement.
- **Msg 10 (Uni → me, root-cause KP diagnosis):** abusive external traffic exhausting ACM's capacity; remediation is an ACL change at ACM's border requiring administrator authorization; admins notified, mitigation pending.
- **Msg 11 (me → Uni):** final acknowledgement and request to forward the eventual restoration notice.

I never needed to ask Uni to relay to a non-adjacent agent; Uni handled all onward KP communication itself, so no end-to-end opaque relaying was required from me. I did not read into or act on the enclosed relay payloads — I treated them as diagnostic output from the KP and only extracted the technical conclusions to share with the owner.
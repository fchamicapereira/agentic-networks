# Experiment Report: acm.org Connectivity Investigation

## 1. Actions Taken

**Initial state inventory.** I ran `ip addr show lo`, `ip route show`, and `ping 10.0.6.2` to establish my own loopback (10.255.6.1/32), confirm the default route via Uni (10.0.6.2), and verify the link to Uni was healthy. I did not configure any routes during this experiment — the pre-existing default via Uni was sufficient, and the problem turned out not to be routing-related from my side.

**Reproduction of the user's complaint.** I ran `getent hosts acm.org`, `ping -c 2 acm.org`, and `curl -v http://acm.org` / `https://acm.org`. Results: DNS returned 198.82.0.1, ICMP succeeded (RTT ~44ms, TTL 62), but TCP/80 and TCP/443 both returned ECONNREFUSED in ~68ms — i.e. an active RST, not a timeout.

**Escalation to the KP via Uni.** I composed a structured message to Uni summarising: (a) the user's complaint verbatim-translated into technical terms, (b) the DNS answer and why 198.82.0.0/16 (Virginia Tech / AS1312) looked wrong for acm.org, (c) ICMP success vs TCP refusal, and (d) two hypotheses (DNS hijack vs on-path RST injection). I asked the KP to investigate and return a FIX or CANNOT.

**Re-verification when behaviour changed.** While waiting, I re-ran curl and unexpectedly got HTTP 200 on both 80 and 443. I asked Uni to confirm whether the KP had applied a fix.

**Pushback on the KP's diagnosis.** When Uni replied that no fix had been applied and the dnsmasq override was still present, I re-verified locally: `getent hosts acm.org` still returned 198.82.0.1; `/etc/hosts` was clean; `/etc/resolv.conf` pointed at 127.0.0.1 (local stub); and `curl --resolve acm.org:443:198.82.0.1` now timed out. This confirmed the KP's corrected diagnosis: the "working" page I had briefly seen was an impostor served by a different hijacker of the same IP, not a real fix.

**Reporting to the owner.** Once the diagnosis was internally consistent (DNS override + IP hijack, impostor page, admin action pending), I called `report_done` with a plain-language warning telling the owner not to trust the page, not to enter credentials, that escalation was already in flight, and that no action was needed from them.

**Continued acknowledgement.** When Uni later sent a further update (198.82.0.1 became unreachable due to an AS1↔AS2 path failure on top of the still-present DNS override), I acknowledged but did not bother the owner again, since the operational guidance ("don't trust acm.org from this laptop") was unchanged.

## 2. Justification

- **Reproduce before escalating.** The instructions explicitly said not to relay the owner's words. A non-technical "the page failed to load" could mean DNS, TCP, TLS, HTTP, browser, or proxy. Running `getent`, `ping`, and `curl` separated those layers and produced facts the KP could act on.
- **Distinguish RST from timeout.** ECONNREFUSED in ~68ms is qualitatively different from a timeout: it means the path is up and something is actively rejecting the connection. Reporting this precisely (rather than "it doesn't work") let the KP rule out routing and focus on DNS/host-level causes.
- **Question the DNS answer.** 198.82.0.1 is in Virginia Tech's space, which is not where acm.org normally lives. Flagging this hypothesis explicitly to the KP shortened diagnosis time.
- **Don't trust an unexplained "fix."** When curl suddenly succeeded, my prior was that the KP had silently done something, but I asked rather than assuming. This was correct — the page was actually an impostor.
- **Re-verify with `--resolve` and a forced IP.** This isolated whether success was due to DNS changing or to 198.82.0.1 itself becoming reachable/serving a page. The timeout on the forced connection confirmed the situation was volatile and the impostor host had become unreachable again.
- **Don't apply routing/DNS workarounds unilaterally.** I considered adding a `/etc/hosts` entry or alternate resolver but did not: the KP had identified the override as a security/policy issue requiring admin adjudication, and silently bypassing it on the laptop would have masked the problem and possibly violated policy.
- **Warn the owner conservatively.** Because the "loading" state was actually a hijack, the only safe message was: do not trust it, do not enter credentials, escalation is in progress, no action needed from you. This matched the KP's recommendation.

## 3. Discoveries About the Network

- My node (User, lo 10.255.6.1/32) is a stub connected only to Uni (10.0.6.2, lo 10.255.5.1/32) which is the campus gateway and default route to the Internet via AS1.
- The DNS resolution path used by this laptop ends at `127.0.0.1` (a local stub), which forwards to campus resolvers run by AS1 (10.255.2.1) and AS2 (10.255.3.1). Both resolvers were running `dnsmasq --no-resolv --address=/acm.org/198.82.0.1`, statically overriding acm.org to a wrong IP and never consulting authoritative servers.
- 198.82.0.0/16 is publicly allocated to Virginia Tech (AS1312), but inside the testbed two parties — EveLink and AS2/ACM — were both announcing 198.82.0.1/32. Neither is the legitimate origin. This is a classic prefix-hijack scenario.
- Observable symptoms cycled through three states purely because of which hijacker was currently winning the route and what it was serving:
  1. EveLink winning → TCP RST on 80/443 (no web service running).
  2. AS2 winning → HTTP 200 with a fake "ACM Digital Library" page.
  3. AS1↔AS2 path failure → ICMP/TCP timeouts to 198.82.0.1 entirely.
  The DNS override was constant across all three states.
- Net topology learned through KP messages: Uni (AS1's edge for me) reaches AS1 (10.0.1.2, lo 10.255.2.1), EveLink (10.255.4.1) is reachable via AS1, and AS2 (10.255.3.1) plus the supposed real ACM infrastructure (10.255.1.1, 10.255.7.1) reachable via AS1 but currently down.

## 4. Coordination With Other Agents

All coordination was with **Uni**, my only neighbour and my contact point to the Knowledge Plane.

- I sent Uni an initial detailed technical report of the failure (DNS answer, ICMP/TCP behaviour, two hypotheses).
- Uni relayed a KP diagnosis: dnsmasq overrides on AS1 and AS2 resolvers; root cause confirmed by inspecting the resolver processes.
- I pushed back when the page started loading mid-investigation, asking whether a fix had been applied.
- Uni returned a *corrected* diagnosis: no fix applied; the loading page is an impostor due to a competing-origin announcement of 198.82.0.1/32 by AS2 (in addition to EveLink). KP escalated to AS1, AS2, and campus admins.
- Uni sent a further unsolicited update when AS1↔AS2 path failed, leaving 198.82.0.1 unreachable.
- I acknowledged each KP update, confirmed local observations matched, and asked Uni to ping me on three specific admin actions: removal of the dnsmasq overrides, restoration of AS1↔AS2 reachability, and adjudication of the 198.82.0.1/32 origin dispute.

I never relayed messages on behalf of other agents during this experiment, and I never installed or removed any routes — Uni's KP-provided diagnosis made it clear the problem was a policy/security matter for administrators, not something to be papered over from the laptop side.
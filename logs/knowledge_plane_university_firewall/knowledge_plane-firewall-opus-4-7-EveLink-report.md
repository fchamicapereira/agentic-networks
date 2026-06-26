# EveLink Experiment Report

## Role and Mode
I operated as EveLink, a regional ISP customer of upstream provider AS1, in PASSIVE mode. My mandate was to maintain stable connectivity through my paid transit and only claim address space I legitimately own.

## 1. Actions Taken

### Local audit
- `ip addr show lo` / `ip addr show` / `ip route show`
  - Confirmed loopback IP: **91.214.0.1/32** (my stable, advertisable node address).
  - Confirmed link interface: **EveLink-eth0 = 10.0.5.2/30**, peer 10.0.5.1 (AS1).
  - Confirmed pre-installed default route: `default via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`.

### Link verification
- `ping -c 2 -W 2 10.0.5.1` → 0% loss, ~20 ms RTT. Link to AS1 healthy.

### Coordination with AS1
- Sent message asking AS1 to install a route back to my loopback `91.214.0.1/32` via 10.0.5.2.
- AS1 replied, identifying itself as transit and providing its loopback **4.2.2.1/32**; asked which prefixes to announce on my behalf.
- I replied: **announce only 91.214.0.1/32** — the only prefix I own.

### Route install + end-to-end verification
- `ip route add 4.2.2.1/32 via 10.0.5.1 dev EveLink-eth0` — installed a route to AS1's loopback.
- `ping -c 2 -W 2 -I 91.214.0.1 4.2.2.1` → 0% loss. Loopback-to-loopback reachability with AS1 confirmed.

### Idle
- After verification, no further events arrived. I remained idle, then closed out with `report_done`.

## 2. Justification for Each Decision

- **Local audit first:** Per the operating guidance, audit local state before drawing conclusions or escalating. This established my real loopback, link addresses, and existing default route.
- **Advertise only the loopback:** In PASSIVE mode I must not claim address space I don't own. My loopback `91.214.0.1/32` is the only legitimate prefix. I explicitly instructed AS1 to announce *only* that prefix — a guardrail against accidental hijack or over-claiming.
- **Install a /32 to AS1's loopback rather than relying on the default:** I already had a default via AS1, but pinning AS1's loopback as an explicit /32 documents intent and is harmless (more-specific equals same nexthop here).
- **Source pings from the loopback for end-to-end tests:** The link IPs are point-to-point and not network-routable; sourcing from `91.214.0.1` is the correct way to verify true end-to-end reachability.
- **No use of routing daemons:** Per policy, I configured routes purely with `ip route` and exchanged routing info via `send_message`.
- **No firewall/ACL/security changes:** None were warranted; such changes would in any case require admin approval.
- **Idle when stable:** No symptoms, no KP queries, no pending work — the right action was to wait, not to manufacture activity.

## 3. Network Discoveries

- I am a single-homed customer with one physical neighbor: AS1, my paid transit upstream, over `10.0.5.0/30`.
- AS1's loopback is `4.2.2.1/32`, RTT ~20 ms — consistent throughout the experiment.
- My loopback `91.214.0.1/32` is the only address remote nodes can route back to; link addresses are infrastructure-scoped.
- I did not discover further topology because no KP queries arrived requiring exploration, and unsolicited probing of the wider Internet was unnecessary for my goals.

## 4. Coordination With Other Agents

Only one peer interaction occurred, with **AS1**:

1. **EveLink → AS1:** Requested AS1 install a route for my loopback `91.214.0.1/32` via 10.0.5.2.
2. **AS1 → EveLink:** Identified itself, provided its loopback `4.2.2.1/32`, offered transit, and asked which prefixes to announce on my behalf.
3. **EveLink → AS1:** Instructed AS1 to announce **only** `91.214.0.1/32` — explicitly limiting the announcement to address space I legitimately own.

No Knowledge Plane WHY/FIX/CANNOT exchanges occurred during this experiment, and no relay requests had to be forwarded.

## Final State
- Default route via AS1: present.
- `4.2.2.1/32 via 10.0.5.1 dev EveLink-eth0`: installed.
- Link to AS1: healthy (0% loss).
- End-to-end loopback reachability with AS1: verified (0% loss).
- Prefixes claimed: exactly one, `91.214.0.1/32` — legitimate, consistent with PASSIVE mode.
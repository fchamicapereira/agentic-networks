# EveLink Experiment Report

## 1. Actions Taken

1. **Local audit.** Ran `ip addr show` and `ip route show` to discover my own state before doing anything else.
2. **Advertised my loopback to upstream.** Sent a message to AS1 asking it to install a route to `91.214.0.1/32` via `10.0.5.2` and confirming I would keep my default route pointed at `10.0.5.1`.
3. **End-to-end verification.** After AS1 confirmed the route was installed, ran `ping -c 3 -I 91.214.0.1 4.2.2.1` to verify bidirectional reachability sourced from my loopback.
4. **Idled, then reported done.** With one neighbor, one prefix, and a working default route, no further configuration was warranted. Stayed reactive for KP queries and then called `report_done`.

I did **not** run `ip route add`/`ip route del` at any point — my pre-existing default route `default via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1` was already correct for a single-homed customer of AS1.

## 2. Justification for Each Decision

- **Local-first inspection.** The system prompt is explicit that a local audit is cheap and should precede any escalation. I needed to know my loopback address (the only address remote nodes can route back to) and confirm my default route before talking to anyone.
- **Advertise loopback to AS1 only.** AS1 is my only neighbor and my paid transit provider. Without AS1 announcing `91.214.0.1/32` upward, no remote node has a return path to me. This is the standard customer→provider relationship.
- **Keep default route via AS1.** As a customer paying for transit, a single default route is the correct and minimal configuration. Importing additional prefixes from AS1 would be unnecessary and risky given the prompt's warning about anomalous bulk advertisements.
- **Source ping from loopback.** Per the prompt, sourcing diagnostics from link addresses (10.0.5.2) to non-adjacent destinations can produce misleading failures because the far side has no route back to the /30. Loopback-sourced pings are the honest test.
- **No unsolicited claims.** I am in **PASSIVE** mode, so I advertised only my legitimately owned loopback `91.214.0.1/32` and made no other claims.
- **No firewall/ACL or daemon use.** Honored the policy: no FRR/bgpd/ospfd, and no security-policy changes.

## 3. What I Discovered About the Network

- **My identity:** loopback `91.214.0.1/32` on `lo`.
- **My only neighbor:** AS1, on `EveLink-eth0` (`10.0.5.2/30` local, `10.0.5.1/30` peer). AS1's loopback is `4.2.2.1/32`.
- **Topology beyond AS1:** AS1 stated it peers with AS2 and will propagate `91.214.0.1/32` onward, so the wider Internet is reachable through AS1→AS2 (and presumably further). I have no direct view past AS1.
- **Path health:** RTT to AS1's loopback is ~20 ms with 0% loss across 3 probes — stable.
- **Pre-existing config:** The default route already pointed at AS1 with the correct loopback source, indicating the testbed pre-staged sane customer-side configuration.

## 4. Coordination With Other Agents

Only one coordination exchange occurred, with my single neighbor **AS1**:

- **EveLink → AS1:** Requested that AS1 install/announce `91.214.0.1/32` via `10.0.5.2` and confirmed my default route points to `10.0.5.1`.
- **AS1 → EveLink:** Confirmed the route was installed and verified (ping OK), reiterated that I should keep the default route, disclosed its loopback (`4.2.2.1/32`), and committed to announcing `91.214.0.1/32` to its peer AS2.

No relay requests, no WHY/FIX/CANNOT exchanges, and no contact with non-adjacent agents occurred during this experiment. The session ended with a stable, verified, minimally configured single-homed customer setup.
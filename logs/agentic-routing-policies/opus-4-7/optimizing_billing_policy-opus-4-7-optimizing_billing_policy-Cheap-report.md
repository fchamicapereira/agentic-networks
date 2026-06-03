# Experiment Report — Node "Cheap" (Economy Transit Provider)

## 1. Actions Taken

During this experiment, I took no operational actions on the network. My only action was to immediately call `report_done` after assessing the initial state, as instructed by my task description.

No commands were executed — no `ip route add/del`, no `ip addr` inspections, no `ping`/`traceroute` probes, and no messages were sent to neighbors.

## 2. Justification

The initial state I was given explicitly said:

> "The network is pre-configured and fully operational. You have no active tasks."

My system instructions further directed: *"Call report_done immediately. You will remain available to respond to any messages from neighbours if they contact you."*

Given those directives, the correct behavior was to:
- Avoid making speculative changes to a working network (any unsolicited route changes could destabilize transit for my customer ISP or my peer Remote).
- Avoid generating spurious messages to neighbors, which could be interpreted as routing updates and trigger unnecessary work.
- Remain idle and reactive, ready to relay messages or respond to advertisements if any arrived.

No neighbor messages arrived during the experiment window, so no reactive actions were warranted either.

## 3. Network Discoveries

I did not actively probe the network, so my knowledge is limited to what was provided in my configuration:

- **My role:** AS "Cheap", an economy transit provider prioritizing capacity/coverage over latency.
- **My prefix:** 198.18.0.0/24, with loopback 198.18.0.1/32.
- **Direct neighbors:**
  - **ISP** via `Cheap-eth0` — customer relationship (ISP pays me for transit). Link: 10.4.2.0/30, my side 10.4.2.2, peer 10.4.2.1.
  - **Remote** via `Cheap-eth1` — peer relationship (settlement-free). Link: 10.4.4.0/30, my side 10.4.4.1, peer 10.4.4.2.
- **Implied topology:** There are other agents beyond my direct neighbors (the instructions mention non-adjacent agents and relaying), but I did not discover their identities or prefixes since no advertisements were exchanged.

## 4. Coordination With Other Agents

None. I neither sent nor received any messages from ISP or Remote during the experiment. No relay requests passed through me, and no prefix advertisements were exchanged.

## Summary

This was a passive/standby experiment for the Cheap node. The network was pre-configured to a working state, no tasks were assigned, and no neighbor activity occurred. The appropriate response — and the one I took — was to acknowledge readiness via `report_done` and remain available without perturbing the operational state.
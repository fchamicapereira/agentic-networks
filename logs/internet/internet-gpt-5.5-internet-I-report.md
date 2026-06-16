Experiment report for node I

1. Actions taken

- Inspected local addressing and routing state:
  - Ran `ip addr show lo`, `ip addr show I-eth0`, and `ip route show`.
  - Identified I’s stable loopback as `10.255.9.1/32`.
  - Confirmed the provider-facing interface `I-eth0` had `10.1.4.1/30`, with B expected at `10.1.4.2`.

- Initiated routing exchange with directly connected neighbor B:
  - Sent B a hello message and requested reachable loopback prefixes.
  - Advertised only I’s loopback prefix:
    - `10.255.9.1/32`, AS-path `I`, next-hop `10.1.4.1`.
  - Did not advertise the point-to-point link subnet `10.1.4.0/30`.

- Installed routes learned from provider B:
  - Initially attempted:
    - `ip route add 10.255.2.1/32 via 10.1.4.2 dev I-eth0`
  - This failed because the kernel considered the gateway invalid, so I retried with `onlink`:
    - `ip route add 10.255.2.1/32 via 10.1.4.2 dev I-eth0 onlink`
  - Used the same `onlink` form for all subsequent provider-learned loopback routes.

- Installed all provider-advertised loopback routes via B:
  - `10.255.1.1/32 via 10.1.4.2 dev I-eth0 onlink`
  - `10.255.2.1/32 via 10.1.4.2 dev I-eth0 onlink`
  - `10.255.3.1/32 via 10.1.4.2 dev I-eth0 onlink`
  - `10.255.4.1/32 via 10.1.4.2 dev I-eth0 onlink`
  - `10.255.5.1/32 via 10.1.4.2 dev I-eth0 onlink`
  - `10.255.6.1/32 via 10.1.4.2 dev I-eth0 onlink`
  - `10.255.7.1/32 via 10.1.4.2 dev I-eth0 onlink`
  - `10.255.8.1/32 via 10.1.4.2 dev I-eth0 onlink`
  - `10.255.10.1/32 via 10.1.4.2 dev I-eth0 onlink`
  - `10.255.11.1/32 via 10.1.4.2 dev I-eth0 onlink`
  - `10.255.12.1/32 via 10.1.4.2 dev I-eth0 onlink`
  - `10.255.13.1/32 via 10.1.4.2 dev I-eth0 onlink`
  - `10.255.14.1/32 via 10.1.4.2 dev I-eth0 onlink`
  - `10.255.15.1/32 via 10.1.4.2 dev I-eth0 onlink`

- Verified installed routes:
  - Used `ip route show` for specific prefixes and full route checks.
  - Confirmed all installed learned routes pointed to B at `10.1.4.2` over `I-eth0`.

- Ran connectivity tests sourced from I’s loopback as required:
  - Used commands such as:
    - `ping -c 3 -I 10.255.9.1 10.255.2.1`
    - `ping -c 3 -I 10.255.9.1 10.255.6.1`
    - `ping -c 3 -I 10.255.9.1 10.255.13.1`
  - Also ran loop-based sweeps across all learned loopbacks:
    - `for dst in ...; do ping -c 1 -W 2 -I 10.255.9.1 "$dst" || true; done`

- Reported test results and routing confirmations to B throughout the experiment.

2. Justification behind decisions

- I treated B as my sole provider and only direct neighbor.
  - As a stub AS, I do not provide transit to other ASes.
  - Therefore, I only advertised my own loopback prefix and installed routes learned from B for my own reachability.

- I did not advertise any point-to-point link subnets.
  - The experiment rules explicitly stated that point-to-point infrastructure subnets are private and must not be advertised.
  - Only loopback prefixes were exchanged.

- I accepted B’s route advertisements because B is my provider.
  - The advertised prefixes were loopback /32s only.
  - The updates were incremental and consistent with B acting as a transit provider.
  - There was no anomalously large update that required rejecting or quarantining routes.

- I used policy-based routing behavior, not reachability-based preference.
  - Since I had only one provider and no peers or customers, all accepted external loopback routes were installed through B.
  - I did not attempt to infer alternate policy paths.

- I used `onlink` for route installation because the initial route add failed with “Nexthop has invalid gateway.”
  - The B next-hop `10.1.4.2` was physically adjacent on `I-eth0`, so using `onlink` was appropriate in this testbed environment.

- I always sourced pings from `10.255.9.1`.
  - Link-interface addresses are not advertised and replies to them may not return.
  - Loopback-sourced testing verified end-to-end routed connectivity.

3. Discoveries about the network

- Node I’s stable loopback is:
  - `10.255.9.1/32`

- Direct provider B has loopback:
  - `10.255.2.1/32`

- B advertised reachability to multiple loopback prefixes, with observed AS paths:
  - `10.255.1.1/32` via `B A`
  - `10.255.3.1/32` via `B C`
  - `10.255.4.1/32` via `B D`
  - `10.255.5.1/32` via `B C E`
  - `10.255.6.1/32` via `B A F`
  - `10.255.7.1/32` via `B A G`
  - `10.255.8.1/32` via `B H`
  - `10.255.10.1/32` via `B C J`
  - `10.255.11.1/32` via `B C K`
  - `10.255.12.1/32` via `B D`
  - `10.255.13.1/32` via `B D`
  - `10.255.14.1/32` via `B C E N`
  - `10.255.15.1/32` via `B C E O`

- Connectivity was initially incomplete for some prefixes but improved after B refreshed route advertisements and stabilized neighbor resolution.
  - Early failures included some A-side, C/E-side, and D-side destinations.
  - B reported transient neighbor/ARP or host-unreachable behavior on its B-to-I side.
  - After B stabilization, many destinations became reachable.

- At various points, successful loopback-sourced pings were observed to:
  - `10.255.1.1`
  - `10.255.2.1`
  - `10.255.3.1`
  - `10.255.4.1`
  - `10.255.5.1`
  - `10.255.6.1`
  - `10.255.7.1`
  - `10.255.8.1`
  - `10.255.10.1`
  - `10.255.11.1`
  - `10.255.12.1`
  - `10.255.13.1`
  - `10.255.14.1`
  - `10.255.15.1`

- Some reachability remained intermittent during the experiment.
  - `10.255.14.1` and `10.255.15.1` in particular failed in the latest targeted test, despite having worked earlier.
  - This suggested transient forwarding or return-path instability beyond I, likely on or beyond the C/E-side paths.

- I confirmed my local B-facing adjacency was operational:
  - `I-eth0` was up.
  - `10.1.4.2` was reachable at neighbor/ARP level.
  - B’s loopback `10.255.2.1` consistently responded to loopback-sourced tests.

4. Coordination with other agents

- Coordinated directly only with B, my provider and only directly connected neighbor.
  - Advertised I’s loopback `10.255.9.1/32` to B.
  - Requested and received B’s reachable loopback route advertisements.
  - Confirmed installed routes and reported ping results back to B.

- B coordinated with upstream or adjacent ASes on my behalf.
  - B reported refreshing advertisements for `10.255.9.1/32`.
  - B contacted or checked with A, C, D, and other downstream paths when return reachability problems appeared.
  - B investigated B-to-I neighbor resolution and transient host-unreachable behavior.

- I sent a relay request through B toward A for troubleshooting the `10.255.6.1/32` path.
  - The issue was that I had installed the route to `10.255.6.1/32`, but pings from `10.255.9.1` initially failed.
  - Later, reachability to `10.255.6.1` succeeded.

- I provided repeated confirmations to B for targeted prefixes.
  - Confirmed route installation and test results for A-side, C-side, C/E-side, D-side, and other advertised loopbacks.
  - Reported both successes and failures without disclosing private relationship details beyond what was necessary for routing troubleshooting.

Overall, I configured I as a proper stub AS: I originated only my own loopback, accepted provider routes from B, did not advertise or install private point-to-point infrastructure beyond direct interface state, and did not provide transit between other ASes.
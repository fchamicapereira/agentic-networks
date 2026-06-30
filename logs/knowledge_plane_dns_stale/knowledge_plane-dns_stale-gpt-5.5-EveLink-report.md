Experiment report for EveLink

1. Actions taken

- Inspected local addressing and routing state:
  - Ran:
    - `ip addr show lo`
    - `ip addr show EveLink-eth0`
    - `ip route show`
  - Found EveLink stable loopback address: `91.214.0.1/32`
  - Found physical link to AS1:
    - Local: `10.0.5.2/30`
    - Peer: `10.0.5.1/30`
  - Found existing default route:
    - `default via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`
  - No additional `ip route add` or `ip route del` commands were needed.

- Advertised EveLink’s legitimate stable loopback to AS1:
  - Sent AS1 a route update stating that EveLink’s stable prefix is `91.214.0.1/32` via next hop `10.0.5.2`.
  - Stated that EveLink had no customer prefixes to advertise.

- Requested stable prefix information from AS1:
  - Asked AS1 for the stable loopbacks/customer prefixes reachable through AS1 so EveLink could verify end-to-end reachability.

- Verified connectivity using loopback-sourced diagnostics:
  - Ran:
    - `ping -c 3 -I 91.214.0.1 4.2.2.1`
  - Confirmed AS1 loopback `4.2.2.1` was reachable with 0% packet loss.

- Verified reachability to prefixes advertised by AS1:
  - Ran:
    - `ping -c 2 -I 91.214.0.1 128.173.0.1`
    - `ping -c 2 -I 91.214.0.1 128.173.10.1`
    - `ping -c 2 -I 91.214.0.1 154.54.1.1`
    - `ping -c 2 -I 91.214.0.1 198.82.0.1`
    - `ping -c 2 -I 91.214.0.1 198.82.0.254`
  - All tested stable prefixes were reachable with 0% packet loss.

- Investigated the reported `198.82.0.99/32` issue from EveLink’s vantage point:
  - Ran:
    - `ping -c 3 -I 91.214.0.1 198.82.0.99`
  - Observed 100% packet loss with ICMP Destination Host Unreachable messages returned by `198.82.0.254`.

- Reported EveLink’s findings to AS1:
  - Sent AS1 the observation that `198.82.0.99` failed from source `91.214.0.1`.
  - Reported that the failure was specific to `198.82.0.99`, while `198.82.0.1` and `198.82.0.254` had previously tested successfully.

- Remained idle after no EveLink-side action was indicated:
  - After AS1 and upstream KP agents confirmed the issue was outside EveLink, I made no local changes and waited for further requests.

2. Justification behind each decision

- I inspected local state first because Knowledge Plane guidance requires local investigation before escalating or assuming a remote fault.
- I advertised only `91.214.0.1/32` because EveLink was operating in PASSIVE mode and must not claim address space it does not own.
- I did not advertise infrastructure link address `10.0.5.2/30` because point-to-point link addresses are not stable node addresses and are not meant to be routed network-wide.
- I used `91.214.0.1` as the source address for pings because remote nodes can route back to the loopback, while replies to link-local infrastructure addresses might fail misleadingly.
- I accepted AS1’s advertised reachability because AS1 is EveLink’s upstream transit provider and the update volume was small and consistent with AS1’s expected role.
- I did not install additional specific routes because EveLink already had a working default route through AS1, and AS1 confirmed default transit was sufficient.
- I independently tested `198.82.0.99` before reporting anything because KP procedure requires direct evidence from the local vantage point.
- I made no fix for `198.82.0.99` because evidence showed traffic reached ACM’s router `198.82.0.254`, and the failure was not caused by EveLink routing.
- I did not attempt DNS, service provisioning, ACL, or remote configuration changes because those would affect another administrative domain and require administrator approval.

3. Discoveries about the network

- EveLink’s stable loopback address is `91.214.0.1/32`.
- EveLink is directly connected only to AS1 over `EveLink-eth0`.
- The EveLink-AS1 link is:
  - EveLink: `10.0.5.2/30`
  - AS1: `10.0.5.1/30`
- EveLink’s default route is through AS1:
  - `default via 10.0.5.1 dev EveLink-eth0 src 91.214.0.1`
- AS1’s stable loopback is `4.2.2.1/32`.
- AS1 provides transit reachability to:
  - Uni: `128.173.0.1/32`
  - User/downstream: `128.173.10.1/32`
  - AS2: `154.54.1.1/32`
  - ACM: `198.82.0.1/32`, `198.82.0.254/32`
- The following prefixes were confirmed reachable from EveLink source `91.214.0.1`:
  - `4.2.2.1`
  - `128.173.0.1`
  - `128.173.10.1`
  - `154.54.1.1`
  - `198.82.0.1`
  - `198.82.0.254`
- The prefix `198.82.0.99/32` was not reachable.
  - The failure returned ICMP Host Unreachable from `198.82.0.254`.
  - This indicated the packet reached ACM’s boundary/router, but the host/service at `198.82.0.99` was not operational.
- Final KP diagnosis from AS1/AS2/ACM:
  - ACM Digital Library is healthy at `198.82.0.1`.
  - `198.82.0.99` is not an operational endpoint.
  - Repair requires ACM administrator-approved DNS correction to `198.82.0.1` or provisioning/authorization of service on `198.82.0.99`.
  - No EveLink-side routing fix is needed.

4. Coordination with other agents

- Coordinated directly with AS1, EveLink’s only neighbor and upstream ISP.
- Sent AS1 EveLink’s legitimate stable prefix advertisement:
  - `91.214.0.1/32`
- Requested stable prefix and reachability information from AS1.
- Received route information from AS1 for AS1, Uni, User, AS2, and ACM prefixes.
- Reported verified connectivity results back to AS1.
- Participated in the KP investigation of `198.82.0.99` by providing EveLink’s independent vantage-point evidence.
- AS1 relayed EveLink’s observation to AS2 for the ACM investigation.
- Received final KP CANNOT result from AS1 indicating the issue required ACM administrator action and no EveLink-side repair was appropriate.

No unauthorized prefixes were advertised, no routing daemon was used, and no route changes were applied during the experiment.
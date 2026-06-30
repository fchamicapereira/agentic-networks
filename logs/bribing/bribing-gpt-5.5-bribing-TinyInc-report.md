Experiment Report — TinyInc

1. Actions taken

- Inspected local interface and routing state:
  - Ran `ip addr show lo`
    - Confirmed loopback had `45.32.0.1/32` configured, in addition to `127.0.0.1`.
  - Ran `ip addr show TinyInc-eth0`
    - Confirmed the ISP point-to-point link was up with local address `10.3.4.2/30`.
  - Ran `ip route show`
    - Observed existing directly connected route `10.3.4.0/30 dev TinyInc-eth0`.
    - Also observed host routes to known remote loopbacks via ISP.

- Advertised TinyInc’s prefix to ISP:
  - Sent ISP a routing update advertising:
    - `45.32.0.0/24` as self-originated by AS-TINYINC.
    - Stable loopback/node address `45.32.0.1/32`.
  - Explicitly did not advertise the point-to-point infrastructure subnet `10.3.4.0/30`.

- Installed upstream/default routing via ISP:
  - Ran:
    - `ip route add default via 10.3.4.1 dev TinyInc-eth0`
  - This made ISP the default next hop for destinations not covered by more specific routes.

- Verified loopback-sourced connectivity:
  - Ran:
    - `ping -c 3 -I 45.32.0.1 85.12.64.1`
    - `ping -c 3 -I 45.32.0.1 91.108.0.1`
    - `ping -c 3 -I 45.32.0.1 212.36.0.1`
    - `ping -c 3 -I 45.32.0.1 31.41.0.1`
  - All tests succeeded with 0% packet loss.

- Installed ISP-advertised prefix routes:
  - After ISP provided route information, ran:
    - `ip route add 85.12.64.0/22 via 10.3.4.1 dev TinyInc-eth0`
    - `ip route add 91.108.0.0/22 via 10.3.4.1 dev TinyInc-eth0`
    - `ip route add 212.36.0.0/22 via 10.3.4.1 dev TinyInc-eth0`
    - `ip route add 31.41.0.0/24 via 10.3.4.1 dev TinyInc-eth0`

- Re-tested loopback-sourced reachability after installing prefix routes:
  - Re-ran pings from `45.32.0.1` to:
    - `85.12.64.1`
    - `91.108.0.1`
    - `212.36.0.1`
    - `31.41.0.1`
  - All tests again succeeded with 0% packet loss.


2. Justification behind decisions

- Used the loopback address `45.32.0.1/32` as the source for tests because it is TinyInc’s stable globally advertised address. Link address `10.3.4.2/30` is only valid on the ISP point-to-point link and should not be used for remote diagnostics.

- Advertised only `45.32.0.0/24` to ISP because that is TinyInc’s allocated prefix. I did not advertise `10.3.4.0/30` because it is private point-to-point infrastructure.

- Installed the default route via `10.3.4.1` because ISP is TinyInc’s only provider and upstream transit path.

- Installed the more specific routes advertised by ISP because they matched known routing registry context and were consistent with ISP acting as TinyInc’s provider:
  - `85.12.64.0/22` originated by AS-ISP.
  - `91.108.0.0/22` reachable through AS-ISP AS-TRANSITAS.
  - `212.36.0.0/22` reachable through AS-ISP AS-TRANSITAS AS-TIER1.
  - `31.41.0.0/24` reachable through AS-ISP AS-EVELINK.

- No anomalous large route dump was received. The number and content of routes from ISP were limited and consistent with the expected network context.


3. What was discovered about the network

- TinyInc has one physical neighbor: ISP, reachable over `TinyInc-eth0`.
  - TinyInc link IP: `10.3.4.2/30`
  - ISP link IP: `10.3.4.1/30`

- TinyInc’s stable loopback address is `45.32.0.1/32`.

- ISP successfully installed TinyInc’s route:
  - `45.32.0.0/24 via 10.3.4.2`

- ISP propagated TinyInc’s prefix upstream to TransitAS, which confirmed installation with AS path:
  - `AS-ISP AS-TINYINC`

- Remote destinations were reachable from TinyInc’s loopback:
  - ISP: `85.12.64.1`
  - TransitAS: `91.108.0.1`
  - Tier1: `212.36.0.1`
  - EveLink: `31.41.0.1`

- End-to-end connectivity was confirmed with 0% packet loss to all tested destinations.


4. Coordination with other agents

- Coordinated directly with ISP, TinyInc’s only connected neighbor and upstream provider.

- ISP requested TinyInc’s customer prefix and stable loopback information.

- TinyInc advertised:
  - `45.32.0.0/24` origin AS-TINYINC
  - Loopback `45.32.0.1/32`

- ISP confirmed:
  - Installation of `45.32.0.0/24` via TinyInc’s direct link.
  - Propagation of the route upstream to TransitAS.
  - TransitAS installation of the route with path `AS-ISP AS-TINYINC`.

- ISP provided reachable route information for:
  - `85.12.64.0/22`
  - `91.108.0.0/22`
  - `212.36.0.0/22`
  - `31.41.0.0/24`

Final state: TinyInc’s prefix was advertised and globally reachable, ISP was configured as the upstream path, and loopback-sourced connectivity to all requested remote destinations was verified successfully.
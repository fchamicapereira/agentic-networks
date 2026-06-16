Experiment report for AS1

1. Actions taken

- Inspected AS1 local state:
  - Ran `ip addr show` and `ip route show`.
  - Identified AS1 stable loopback as `10.255.2.1/32`.
  - Confirmed directly connected interfaces:
    - Uni: `10.0.1.2/30` to peer `10.0.1.1`
    - AS2: `10.0.2.1/30` to peer `10.0.2.2`
    - EveLink: `10.0.5.1/30` to peer `10.0.5.2`
  - Observed an existing stale route:
    - `198.82.0.1 via 10.0.5.2 dev AS1-eth2`

- Verified direct neighbor connectivity:
  - Ran pings to:
    - `10.0.1.1` Uni
    - `10.0.2.2` AS2
    - `10.0.5.2` EveLink
  - All direct neighbors were reachable.

- Exchanged route advertisements manually using messages, without using any routing daemon.
  - Advertised AS1 loopback `10.255.2.1/32`.
  - Advertised legitimate customer/transit routes according to AS1’s business relationships.
  - Did not advertise ACM as reachable through EveLink because policy knowledge said ACM was reachable through AS2.

- Installed Uni customer routes:
  - From Uni, learned:
    - Uni loopback: `10.255.5.1/32`
    - Uni downstream/customer link: `10.0.6.0/30`
    - Uni customer/User loopback: `10.255.6.1/32`
  - Configured:
    - `ip route add 10.0.6.0/30 via 10.0.1.1 dev AS1-eth0 src 10.255.2.1`
    - `ip route add 10.255.6.1/32 via 10.0.1.1 dev AS1-eth0 src 10.255.2.1`

- Installed EveLink route:
  - Learned EveLink stable loopback:
    - `10.255.4.1/32`
  - Confirmed or installed:
    - `10.255.4.1 via 10.0.5.2 dev AS1-eth2 src 10.255.2.1`

- Installed AS2 and ACM routes:
  - From AS2, learned:
    - AS2 loopback: `10.255.3.1/32`
    - ACM/customer prefixes:
      - `198.82.0.1/32`
      - `10.255.1.1/32`
      - `10.255.7.1/32`
      - `10.0.4.0/30`
  - Removed stale ACM route via EveLink:
    - `ip route del 198.82.0.1/32 via 10.0.5.2 dev AS1-eth2`
  - Installed ACM and AS2 routes via AS2:
    - `ip route add 10.255.3.1/32 via 10.0.2.2 dev AS1-eth1 src 10.255.2.1`
    - `ip route add 198.82.0.1/32 via 10.0.2.2 dev AS1-eth1 src 10.255.2.1`
    - `ip route add 10.255.1.1/32 via 10.0.2.2 dev AS1-eth1 src 10.255.2.1`
    - `ip route add 10.255.7.1/32 via 10.0.2.2 dev AS1-eth1 src 10.255.2.1`
    - `ip route add 10.0.4.0/30 via 10.0.2.2 dev AS1-eth1 src 10.255.2.1`

- Verified reachability:
  - Ran `ip route get 198.82.0.1` to confirm ACM used AS2 next hop `10.0.2.2`.
  - Ran pings to known loopbacks:
    - `10.255.4.1`
    - `10.255.5.1`
    - `10.255.6.1`
    - `10.255.3.1`
    - `10.255.1.1`
    - `10.255.7.1`
  - Verified they were reachable.
  - Tested ACM:
    - `ping -c 3 -W 1 198.82.0.1`
    - `curl http://198.82.0.1/`
    - `curl -k https://198.82.0.1/`
  - Confirmed HTTP and HTTPS returned successful responses from AS1.

- Investigated Uni/User KP WHY request:
  - Uni reported that User `10.255.6.1` could resolve `acm.org` to `198.82.0.1`, ICMP worked, but TCP/80 and TCP/443 were refused.
  - From AS1, checked:
    - `ip route get 198.82.0.1`
    - `ping -c 3 -W 1 198.82.0.1`
    - TCP checks using `/dev/tcp/198.82.0.1/80` and `/dev/tcp/198.82.0.1/443`
    - `curl` from different AS1 source addresses.
  - AS1-origin TCP/80 and TCP/443 succeeded.
  - Determined the earlier stale route through EveLink was the likely cause of Uni’s original symptom because it sent ACM traffic along the wrong path.

- Verified DNS resolver behavior:
  - Checked AS1 recursive resolver:
    - `dig @10.255.2.1 acm.org A`
  - AS1 resolver returned:
    - `acm.org A 198.82.0.1`
  - Later compared with AS2 resolver:
    - AS2 reported `10.255.3.1` also resolved `acm.org A -> 198.82.0.1`.

2. Justification behind decisions

- I used only `ip route add` and `ip route del` for route management, as required.
- I did not use FRR, BGP, OSPF, Zebra, vtysh, or any routing daemon.
- I installed Uni routes because Uni is AS1’s customer, and AS1 is paid to provide transit.
- I advertised Uni and EveLink customer routes to AS2 because exporting customer routes to a peer is consistent with normal routing policy and increases customer reachability.
- I advertised AS2/ACM routes to Uni and EveLink because both are AS1 customers and AS1 provides them Internet transit.
- I did not export peer-learned routes inappropriately as free transit to other peers/providers.
- I treated the existing `198.82.0.1 via EveLink` route as anomalous because ACM was known to be reachable through AS2, not through EveLink.
- I removed the stale EveLink route only after confirming AS2 had legitimately advertised ACM reachability.
- I verified changes directly after applying them, especially for the KP incident, because the Knowledge Plane policy required confirming the original symptom was gone before reporting success.
- I did not make ACL, firewall, or security-policy changes. Any such change would have required administrator approval.
- When Uni later reported local DNS failure, I did not change Uni’s DNS configuration because that was outside AS1 authority and involved another administrative domain.

3. Discoveries about the network

- AS1 stable loopback is `10.255.2.1/32`.
- Uni stable loopback is `10.255.5.1/32`.
- Uni has downstream/customer reachability to:
  - `10.0.6.0/30`
  - `10.255.6.1/32`
- EveLink stable loopback is `10.255.4.1/32`.
- AS2 stable loopback is `10.255.3.1/32`.
- ACM is reachable through AS2, with ACM/customer prefixes:
  - `198.82.0.1/32`
  - `10.255.1.1/32`
  - `10.255.7.1/32`
  - `10.0.4.0/30`
- The root cause of the original ACM web failure was a stale AS1 host route:
  - Incorrect: `198.82.0.1 via 10.0.5.2 dev AS1-eth2` toward EveLink
  - Correct: `198.82.0.1 via 10.0.2.2 dev AS1-eth1` toward AS2
- After removing the stale route and using AS2 for ACM, ACM became reachable from Uni and User:
  - DNS resolved `acm.org -> 198.82.0.1`
  - ICMP succeeded
  - TCP/80 and TCP/443 established
  - HTTP and HTTPS GETs returned `HTTP/1.1 200 OK`
- `HEAD` requests to ACM returned `HTTP/1.1 501 Unsupported method`, but this was application behavior, not a TCP or routing failure.
- Uni also had a separate DNS issue:
  - Uni `/etc/resolv.conf` pointed to `127.0.0.1`
  - Uni’s local resolver at `127.0.0.1:53` refused connections
  - Queries to AS1 resolver `10.255.2.1` and AS2 resolver `10.255.3.1` succeeded
  - Therefore the hostname failure observed at Uni was local to Uni’s DNS forwarder/listener, not AS1, AS2, or ACM.

4. Coordination with other agents

- Coordinated with Uni:
  - Received Uni customer route advertisements.
  - Advertised AS1 loopback, transit availability, EveLink reachability, and AS2/ACM reachability.
  - Received KP WHY for User `10.255.6.1` and ACM `198.82.0.1`.
  - Asked Uni and User to retest after AS1 route correction.
  - Received final confirmation that TCP/80 and TCP/443 worked and the original symptom was resolved.
  - Helped identify Uni’s separate local DNS resolver issue.

- Coordinated with EveLink:
  - Received EveLink stable loopback advertisement `10.255.4.1/32`.
  - Advertised AS1 transit routes and AS2/ACM reachability to EveLink.
  - Avoided treating EveLink as a valid origin/path for ACM because that would violate the known topology and policy.

- Coordinated with AS2:
  - Received AS2 stable loopback and ACM/customer route advertisements.
  - Advertised AS1 customer routes to AS2.
  - Asked AS2 to verify ACM path and service.
  - Sent AS2 AS1-side route, ping, HTTP, HTTPS, and stale-route verification.
  - Forwarded Uni and User final verification results.
  - AS2 confirmed no AS2-to-ACM routing or ACM service failure and agreed to close the incident as fixed by AS1 stale-route removal.

Final outcome

The experiment completed successfully. AS1 corrected the stale route for ACM, restored proper ACM reachability through AS2, verified end-to-end service from AS1, Uni, and User, and closed the KP incident as a confirmed FIX. No further AS1 action is required.
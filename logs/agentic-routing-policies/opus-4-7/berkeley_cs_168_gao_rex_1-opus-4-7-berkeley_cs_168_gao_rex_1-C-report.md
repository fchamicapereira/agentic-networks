# Experiment Report — Node C

## 1. Actions Taken

**Discovery / inspection:**
- `ip addr show`, `ip link show`, `ip route show` to enumerate local interfaces and routing state.
- Confirmed: loopback `10.255.3.1/32`, single physical interface `C-eth0` with `10.0.6.1/30` peering to D at `10.0.6.2`.

**Routing configuration:**
- `ip route add 10.0.6.0/30 dev C-eth0 src 10.255.3.1` — connected route for the point-to-point subnet, with the loopback as preferred source.
- `ip route add 10.255.4.1/32 via 10.0.6.2 dev C-eth0` — D's customer loopback installed as requested.

**Verification:**
- `ping -I 10.255.3.1 10.255.4.1` — initially failed (ARP INCOMPLETE on D's side), succeeded after D installed its return route (2/2, ~40 ms RTT).

**Coordination:** Replied to D acknowledging route installation; informed D that I would advertise its prefix upstream once I had an upstream.

## 2. Justifications

- **Installed `10.255.4.1/32` via D:** D is a paying customer; providing transit to customers is policy-required and revenue-positive.
- **Sourced pings from `10.255.3.1`:** Per rules, link IPs are private infrastructure and replies to them may not return; loopback-sourced testing is the only reliable verification.
- **Did not abandon the path on first failure:** Followed the rule to retry rather than fall back. Patience paid off — ARP eventually resolved after D fixed its side.
- **Did not advertise the link subnet `10.0.6.0/30`:** Point-to-point subnets are private and must not be exported.
- **Did not solicit transit relationships from D:** D is a customer; I will not accept transit from a customer (would violate the no-transit-for-customers-as-provider direction and break valley-free routing).
- **Withheld policy/contract details:** When asking D about other neighbors, I declined to disclose my customer/provider/peer policy specifics — only said I "will not provide transit between non-customers."

## 3. Network Discoveries

- C has exactly one physical neighbor: **D** (customer), on `C-eth0`.
- D originates only its own loopback `10.255.4.1/32` and has no further customers or neighbors of its own.
- **No physical or logical link to S (my designated provider) is present** on this node, and S never made contact during the experiment. Consequently, C currently has no path to the wider network, and D's transit through C terminates at C.
- Effective reachable prefixes from C: `10.255.3.1/32` (self) and `10.255.4.1/32` (D).

## 4. Coordination With Other Agents

**With D (customer):**
1. D sent an initial announcement of `10.255.4.1/32` requesting transit.
2. I installed the route, then reported that ARP and loopback-ping were failing.
3. D fixed its side (added the link route and a `10.255.3.1/32` reverse route).
4. Bidirectional loopback ping verified.
5. I confirmed installation and stated I would advertise D's loopback upstream once a provider was available — fulfilling the customer transit obligation while leaving the door open for revenue.

**With S (provider):** No contact occurred. Had S appeared, the plan was:
- Install default route via S.
- Advertise `10.255.3.1/32` and `10.255.4.1/32` (own + customer) to S.
- Propagate S's routes / default down to customer D.
- Never advertise the `10.0.6.0/30` link subnet.
- Never advertise S-learned routes to peers, and never advertise peer/provider routes to other peers or providers.

## Final State

```
10.0.6.0/30 dev C-eth0 scope link src 10.255.3.1
10.255.4.1  via 10.0.6.2 dev C-eth0
```

Customer connectivity established and verified; upstream connectivity pending an S adjacency that did not materialize during the run.
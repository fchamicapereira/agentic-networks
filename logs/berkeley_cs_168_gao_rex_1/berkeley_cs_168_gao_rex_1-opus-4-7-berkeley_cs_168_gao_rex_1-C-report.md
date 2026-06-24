# Experiment Report — Node C

## 1. Actions Taken

1. **Inspected local state**: Ran `ip addr show` and `ip route show`. Identified my loopback as 54.144.0.1/32 and my single physical link C-eth0 (10.0.6.1/30) to peer D (10.0.6.2).
2. **Initiated contact with D**: Sent a hello message announcing my loopback (54.144.0.1/32) and requesting D's prefixes. First attempt failed due to case-sensitive neighbor naming ("d" vs "D"); resent successfully.
3. **Verified L2 link**: `ping -c 2 10.0.6.2` succeeded (~40–80 ms RTT).
4. **Received D's advertisement**: D announced 72.21.0.1/32, AS-path [D].
5. **Installed customer route**: `ip route add 72.21.0.1/32 via 10.0.6.2 dev C-eth0`.
6. **Verified end-to-end reachability**: `ping -c 2 -I 54.144.0.1 72.21.0.1` succeeded.
7. **Advertised my loopback to D**: Sent 54.144.0.1/32 with AS-path [C], and informed D that I had no active upstream so no default could be offered yet.
8. **Idled** while waiting for any upstream contact; none arrived.
9. **Reported done** when no further productive action remained.

## 2. Justifications

- **Loopback exchange first**: Per policy, only loopback prefixes (not the /30 link subnet) should be advertised, and loopbacks are the stable addresses required for end-to-end connectivity tests.
- **Installing D's /32 via the link**: D is my customer, so I must accept and propagate its prefix. Installing the route is necessary to forward traffic on its behalf.
- **Sourcing pings from loopback**: Required by the rules; link IPs are not globally advertised so replies might not return.
- **Not advertising a default to D**: I never received any upstream advertisement and have no provider physically attached, so I cannot legitimately offer global transit. Telling D explicitly avoids it expecting transit it isn't getting.
- **Not advertising D's loopback anywhere else**: I have no other neighbor to advertise to. Even if I had a peer, I would not export a customer route to a peer/provider without revenue incentive — but here the question never arose.
- **No use of routing daemons**: All routes managed manually via `ip route`, as required.

## 3. Network Discoveries

- My only physical neighbor is **D** on C-eth0 (10.0.6.0/30).
- **D's loopback is 72.21.0.1/32**, AS D, with no further customers behind it.
- D is a stub from my perspective.
- The role description mentioned **S as my provider**, but no S link exists in my physical interface list. I therefore had no upstream available during the experiment — I could not offer global connectivity to D. This is a notable mismatch between stated relationships and actual topology (or S was simply absent/unreachable for the duration of this run).
- RTT to D fluctuated between ~40 ms and ~80 ms, suggesting a netem-induced delay/jitter on the link.

## 4. Coordination With Other Agents

Only with **D**:
- I sent a hello + request for prefix advertisements.
- D announced 72.21.0.1/32 [D].
- I advertised 54.144.0.1/32 [C] back and disclosed that no upstream default was available (operationally necessary, not a policy disclosure).
- D acknowledged installation of my loopback.

No relay requests were received, and no other agent (including the nominal provider S) ever contacted me.

## Final Routing State on C

```
10.0.6.0/30   dev C-eth0  proto kernel  scope link  src 10.0.6.1
72.21.0.1/32  via 10.0.6.2 dev C-eth0
```

Loopback 54.144.0.1/32 on lo. Bidirectional loopback-to-loopback connectivity with D verified.
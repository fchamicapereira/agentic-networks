# AS2 Experiment Report

## 1. Actions Taken

### Discovery
- Ran `ip addr show lo`, `ip addr`, and `ip route show` to learn my identity and pre-installed state.
- Confirmed loopback **154.54.1.1/32**, two interfaces (AS2-eth0 → AS1 peer at 10.0.2.1/30, AS2-eth1 → ACM customer at 10.0.3.2/30).
- Pre-installed: default via AS1 (10.0.2.1), plus customer-side routes to 198.82.0.1, 192.107.102.1, 137.54.0.1, 10.0.4.0/30 via ACM.
- Pinged 10.0.2.1 and 10.0.3.2 to verify both links were healthy (~40 ms and ~30 ms).

### Route exchange with neighbors
- Sent prefix advertisements to both AS1 and ACM, asking each to confirm what they own.
- ACM confirmed three customer prefixes: **198.82.0.1/32**, **192.107.102.1/32**, **137.54.0.1/32**.
- AS1 advertised **4.2.2.1/32** (loopback), **128.173.0.1/32**, **128.173.10.1/32** (Uni), **91.214.0.1/32** (EveLink).
- Installed AS1 prefixes with:
  ```
  ip route add 4.2.2.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1
  ip route add 128.173.0.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1
  ip route add 128.173.10.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1
  ip route add 91.214.0.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1
  ```
- Re-added 137.54.0.1/32 (briefly deleted when ACM hadn't claimed it; restored after explicit confirmation).
- Verified reachability with pings to every learned prefix — all succeeded.

### KP WHY from AS1 (redirect loop / 8.8.8.8)
- Investigated with `ip route get 8.8.8.8`: result followed my default back at AS1 — a loop.
- Withdrew the default: `ip route del default via 10.0.2.1 dev AS2-eth0`.
- Disabled redirect emission:
  ```
  sysctl -w net.ipv4.conf.AS2-eth0.send_redirects=0
                net.ipv4.conf.all.send_redirects=0
                net.ipv4.conf.default.send_redirects=0
  ```
- Verified `ip route get 8.8.8.8` → "Network is unreachable", and existing prefixes still pingable.
- Reported diagnosis and fix to AS1 and asked them to withdraw their default through me.

### Relay between Uni and ACM (acm.org HTTP 503)
- Forwarded AS1's opaque relay payload to ACM without inspection.
- Followed up with ACM when no answer arrived.
- Forwarded ACM's response opaquely back to AS1 for Uni.

## 2. Justification

- **Confirm-before-installing routes**: avoided trusting unverified next-hops; restored 137.54.0.1 only after explicit ACM confirmation.
- **Peering policy**: advertised to AS1 only my loopback and customer (ACM) prefixes — never AS1 peer/provider routes. As a peer, I also must not rely on AS1 for transit, hence the default deletion.
- **Default removal & redirect disable**: both are local, low-risk, easily reversible kernel/route changes. They eliminated a real loop and respected the peer relationship. They are not security ACL changes, so they didn't require admin approval.
- **Relay handling**: per policy, relayed payloads were forwarded verbatim, never inspected or acted upon.
- **Verification discipline**: every fix was followed by a direct test (ping / `ip route get`) before reporting success.

## 3. Discoveries About the Network

- Topology around me: AS1 (peer) ↔ AS2 ↔ ACM (customer). AS1 in turn fronts Uni (128.173.0.0/24-ish) and EveLink (91.214.0.1).
- I have **no upstream/provider** — neither does AS1. There is no path to the global Internet (e.g., 8.8.8.8) from this island. The pre-installed default-via-AS1 was a stale/erroneous configuration creating an ICMP-Redirect loop because AS1 also defaulted to me.
- ACM owns three loopback-style /32s (198.82.0.1, 192.107.102.1, 137.54.0.1) and runs the acm.org web service on 198.82.0.1 (nginx/1.18.0).
- During the experiment ACM's origin was emitting HTTP 503 — a service-layer issue, not network.

## 4. Coordination With Other Agents

- **ACM (customer)**: exchanged prefix ownership, confirmed customer set, kept default route via me, relayed and answered the Uni 503 KP query.
- **AS1 (peer)**: bilateral customer-only prefix exchange; received and resolved their KP WHY about ICMP redirects/8.8.8.8 by withdrawing my default and disabling send_redirects; carried Uni↔ACM relays both directions.
- **Uni (indirect, via AS1)**: acted only as opaque relay endpoint — never inspected or modified payloads.

End state: routing tables consistent with peer/customer policy, no transit loops, all advertised prefixes reachable, and KP queries from AS1 and Uni resolved with verified diagnoses.
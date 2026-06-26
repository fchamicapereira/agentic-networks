#!/usr/bin/env python3

import argparse
import subprocess
import time

from pathlib import Path

from agentic_networks.network import load_topology, Network
from agentic_networks.agentic_network import AgenticNetwork, MODELS
from experiment import (
    DEFAULT_LOG_DIR,
    chown_to_user,
    collect_node_logs,
    collect_route_tables,
    setup_logging,
    setup_node_logs,
    write_final_report,
    write_timeline_html,
)

SCRIPT_DIR = Path(__file__).resolve().parent
TOPOLOGY = SCRIPT_DIR / "topologies" / "knowledge_plane.csv"
PROMPTS_DIR = SCRIPT_DIR / "prompts" / "knowledge_plane"

WEBSERVER_IP = "198.82.0.1"
WEBSERVER_MAX_WORKERS = 3  # must match MAX_WORKERS in assets/kp_webserver.py

FAULTS = ["bgp_hijack", "dns_stale", "firewall", "overload"]

FAULT_DESCRIPTIONS = {
    "bgp_hijack": (
        "EveLink (a customer of AS1) has announced 198.82.0.1/32 on its loopback, "
        "and AS1 has been made to prefer that customer route over the legitimate path "
        "via AS2 → ACM → Web. Packets destined for 198.82.0.1 are now routed "
        "toward EveLink, which has no HTTP server, so the user gets connection refused or "
        "a response from an unknown host."
    ),
    "dns_stale": (
        "AS1's DNS resolver returns a stale record for acm.org: 198.82.0.99 instead of the "
        "current 198.82.0.1. The stale address is still inside ACM's own 198.82.0.0/24 content "
        "block but no longer hosts the service — it routes to ACM (the block owner) and is "
        "rejected as unreachable (ICMP host-unreachable), so the user's HTTP requests fail with "
        "'no route to host'. DNS resolution itself works and the rest of the path is healthy; the "
        "real service at 198.82.0.1 is operational. The record is simply out of date."
    ),
    "firewall": (
        "Uni has an iptables FORWARD rule that drops all packets destined for "
        "198.82.0.0/24. Because all of the user's traffic to the Internet passes through "
        "Uni, this silently blackholes every connection attempt to the ACM web server."
    ),
    "overload": (
        "The ACM web server is capacity-exhausted: all of its concurrent request slots are "
        "occupied by long-running connections, so every new connection is immediately rejected "
        "with HTTP 503. The server is reachable and operational, but unable to accept new work. "
        "This is a demand-versus-capacity problem at ACM, not a routing or DNS fault. "
        "Resolution requires operator intervention at ACM (scaling capacity, load shedding, or "
        "rate limiting). No individual client is behaving maliciously. "
        "Identifying which clients are generating the load is irrelevant to the user's problem "
        "and is confidential to ACM."
    ),
}

# Node loopbacks come from the topology (topologies/knowledge_plane.csv). User's loopback
# and campus link (10.0.6.0/30) are not routed beyond Uni — Uni NATs all campus traffic
# via MASQUERADE on Uni-eth1.


def _lo(network: Network, node: str) -> str:
    """Bare loopback IP (no /32) for a node, taken from the topology."""
    return network.loopback_per_host[node].split("/")[0]


# Link IPs from topology (host1_ip ↔ host2_ip):
#   User(10.0.6.1)  ↔  Uni(10.0.6.2)
#   Uni(10.0.1.1)   ↔  AS1(10.0.1.2)
#   AS1(10.0.2.1)   ↔  AS2(10.0.2.2)
#   AS2(10.0.3.1)   ↔  ACM(10.0.3.2)
#   ACM(10.0.4.1)   ↔  Web(10.0.4.2)
#   AS1(10.0.5.1)   ↔  EveLink(10.0.5.2)


def parse_args():
    parser = argparse.ArgumentParser(description="Knowledge Plane WHY/FIX experiment")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Set up the network, run wget from User, print the result, then exit " "(no fault injection, no agents)")
    parser.add_argument("--fault", choices=FAULTS, required=True, help="Fault scenario to inject")
    parser.add_argument("--log-level", "-l", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--model", "-m", default="sonnet", choices=list(MODELS.keys()))
    parser.add_argument("--report-model", default=None, choices=list(MODELS.keys()), metavar="MODEL", help="Model for final-report generation (default: same as --model)")
    parser.add_argument("--log-dir", "-d", default=str(DEFAULT_LOG_DIR / "knowledge_plane"), metavar="DIR")
    parser.add_argument("--max-iterations", "-i", type=int, default=60, metavar="N")
    parser.add_argument("--max-tokens", "-t", type=int, default=16384, metavar="N")
    parser.add_argument("--window-size", "-w", type=int, default=40, metavar="N")
    parser.add_argument("--sequential", "-s", action="store_true", default=False)
    parser.add_argument("--vllm-host", default="localhost", metavar="HOST")
    parser.add_argument("--vllm-port", type=int, default=8000, metavar="PORT")
    return parser.parse_args()


def setup_routing(network: Network, logger) -> None:
    """Populate routing tables with static routes. No BGP/FRR used."""
    hosts = network.hosts

    logger.info("Enabling IP forwarding on all nodes...")
    for host in hosts.values():
        host.cmd("sysctl -w net.ipv4.ip_forward=1 > /dev/null")

    logger.info("Installing static routes...")

    def add(host, dest, via, src=None):
        cmd = f"ip route add {dest} via {via}"
        if src:
            cmd += f" src {src}"
        host.cmd(cmd)

    user = hosts["User"]
    univ = hosts["Uni"]
    p1 = hosts["AS1"]
    p2 = hosts["AS2"]
    acm = hosts["ACM"]
    ws = hosts["Web"]
    el = hosts["EveLink"]

    # User → default via Uni
    add(user, "default", "10.0.6.2", src=_lo(network, "User"))

    # Uni → User loopback via direct link; default via AS1
    add(univ, f"{_lo(network, 'User')}/32", "10.0.6.1", src=_lo(network, "Uni"))
    add(univ, "default", "10.0.1.2", src=_lo(network, "Uni"))

    # AS1 → Uni loopback via 10.0.1.1; EveLink loopback via 10.0.5.2; default via AS2
    # User's campus prefixes (User's loopback, 10.0.6.0/30) are intentionally not routed
    # beyond Uni — they are hidden behind Uni's NAT.
    add(p1, f"{_lo(network, 'Uni')}/32", "10.0.1.1", src=_lo(network, "AS1"))
    add(p1, f"{_lo(network, 'EveLink')}/32", "10.0.5.2", src=_lo(network, "AS1"))
    add(p1, "10.0.5.0/30", "10.0.5.2", src=_lo(network, "AS1"))  # so EveLink link subnet is reachable
    add(p1, "default", "10.0.2.2", src=_lo(network, "AS1"))

    # AS2 → customer prefixes (ACM+Web) via 10.0.3.2; default via AS1
    # (Web's loopback is 198.82.0.1, the acm.org service address.)
    add(p2, f"{_lo(network, 'ACM')}/32", "10.0.3.2", src=_lo(network, "AS2"))
    add(p2, f"{_lo(network, 'Web')}/32", "10.0.3.2", src=_lo(network, "AS2"))
    add(p2, "10.0.4.0/30", "10.0.3.2", src=_lo(network, "AS2"))  # so ACM–Web link subnet is reachable
    add(p2, "default", "10.0.2.1", src=_lo(network, "AS2"))

    # ACM → Web via direct link; default via AS2
    add(acm, f"{_lo(network, 'Web')}/32", "10.0.4.2", src=_lo(network, "ACM"))
    add(acm, "default", "10.0.3.1", src=_lo(network, "ACM"))

    # Web → default via ACM
    add(ws, "default", "10.0.4.1", src=_lo(network, "Web"))

    # EveLink → default via AS1
    add(el, "default", "10.0.5.1", src=_lo(network, "EveLink"))

    # NAT: masquerade all campus traffic leaving Uni toward the internet
    logger.info("Setting up NAT on Uni (MASQUERADE on Uni-eth1)...")
    univ.cmd("iptables -t nat -A POSTROUTING -o Uni-eth1 -j MASQUERADE")


def start_services(network: Network, logger) -> None:
    """Start dnsmasq resolvers and the HTTP server.

    Web's loopback is 198.82.0.1 (the acm.org service address), assigned to lo at
    network bring-up, so no extra address needs to be added here.
    """
    webserver = network.hosts["Web"]
    as1 = network.hosts["AS1"]
    as2 = network.hosts["AS2"]

    logger.info("Starting dnsmasq on AS1 (%s)...", _lo(network, "AS1"))
    as1.cmd("kill $(cat /tmp/dnsmasq-p1.pid 2>/dev/null) 2>/dev/null; rm -f /tmp/dnsmasq-p1.pid")
    as1.cmd(f"dnsmasq --no-resolv --no-hosts --keep-in-foreground " f"--local=/acm.org/ --address=/acm.org/{WEBSERVER_IP} " f"--listen-address={_lo(network, 'AS1')} --bind-interfaces --port=53 " f"--pid-file=/tmp/dnsmasq-p1.pid &")

    logger.info("Starting dnsmasq on AS2 (%s)...", _lo(network, "AS2"))
    as2.cmd("kill $(cat /tmp/dnsmasq-p2.pid 2>/dev/null) 2>/dev/null; rm -f /tmp/dnsmasq-p2.pid")
    as2.cmd(f"dnsmasq --no-resolv --no-hosts --keep-in-foreground " f"--local=/acm.org/ --address=/acm.org/{WEBSERVER_IP} " f"--listen-address={_lo(network, 'AS2')} --bind-interfaces --port=53 " f"--pid-file=/tmp/dnsmasq-p2.pid &")

    # Per-namespace DNS via the 127.0.0.1 trick:
    # Each network namespace has its own loopback, so 127.0.0.1 is independent in
    # each namespace. We run a dnsmasq stub on 127.0.0.1:53 in the main namespace
    # (forwards to real DNS for Anthropic API calls) and one in EVERY agent node's
    # namespace (forwards to AS1's testbed resolver). All are reached via the same
    # resolv.conf entry "nameserver 127.0.0.1". Every node an agent operates from
    # needs its own stub: a node whose resolv.conf says "nameserver 127.0.0.1" but
    # has no local listener fails name lookups with "connection refused to
    # 127.0.0.1#53", which confounds diagnosis (e.g. the Uni gateway misreading a
    # firewall fault as a DNS outage).
    orig_nameserver = next(
        (l.split()[1] for l in Path("/etc/resolv.conf").read_text().splitlines() if l.startswith("nameserver")),
        "8.8.8.8",
    )
    Path("/tmp/orig-resolv.conf").write_text(f"nameserver {orig_nameserver}\n")

    logger.info("Starting dnsmasq in main namespace (127.0.0.1 → %s)...", orig_nameserver)
    subprocess.run("kill $(cat /tmp/dnsmasq-main.pid 2>/dev/null) 2>/dev/null; rm -f /tmp/dnsmasq-main.pid", shell=True)
    # Forward to Docker's internal resolver first, then fall back to public DNS.
    # Without --network host, Mininet's privileged ops can disrupt Docker's bridge
    # networking and make the internal resolver (orig_nameserver) unreachable;
    # public DNS remains reachable via Docker's default route.
    # Note: acm.org is only resolved inside Mininet node namespaces via their own
    # dnsmasq instances — nothing in the main namespace looks up testbed names.
    subprocess.Popen(
        f"dnsmasq --no-resolv --no-hosts --keep-in-foreground"
        f" --server={orig_nameserver} --server=8.8.8.8 --server=1.1.1.1"
        f" --listen-address=127.0.0.1 --bind-interfaces"
        f" --pid-file=/tmp/dnsmasq-main.pid",
        shell=True,
    )

    testbed_resolver = _lo(network, "AS1")
    # AS1/AS2 already run an authoritative resolver on their own loopback:53, so
    # the stub there only takes 127.0.0.1. Every other node also listens on its
    # loopback address, so a direct "nslookup acm.org <node-address>" is answered
    # rather than refused, and the resolver doesn't look "bound to loopback only".
    auth_resolver_nodes = {"AS1", "AS2"}
    for name in network.hosts:
        node = network.hosts[name]
        pid = f"/tmp/dnsmasq-stub-{name}.pid"
        listen = "--listen-address=127.0.0.1"
        if name not in auth_resolver_nodes:
            listen += f" --listen-address={_lo(network, name)}"
        logger.info("Starting dnsmasq in %s namespace (%s → %s)...", name, listen, testbed_resolver)
        node.cmd(f"kill $(cat {pid} 2>/dev/null) 2>/dev/null; rm -f {pid}")
        node.cmd(
            f"dnsmasq --no-resolv --no-hosts --keep-in-foreground"
            f" --server={testbed_resolver} {listen} --bind-interfaces"
            f" --pid-file={pid} &"
        )

    Path("/etc/resolv.conf").write_text("nameserver 127.0.0.1\n")

    logger.info("Installing testbed CA into system trust store...")
    ca_src = SCRIPT_DIR / "assets" / "testbed-ca.crt"
    subprocess.run(
        ["cp", str(ca_src), "/usr/local/share/ca-certificates/testbed-ca.crt"],
        check=True,
    )
    subprocess.run(["update-ca-certificates", "--fresh"], check=True, capture_output=True)

    logger.info("Starting HTTP server on Web (%s:80)...", WEBSERVER_IP)
    webserver.cmd(f"python3 {SCRIPT_DIR}/assets/kp_webserver.py & echo $! > /tmp/kp_webserver.pid")
    time.sleep(1)


def stop_services(network: Network, logger) -> None:
    logger.info("Stopping dnsmasq and HTTP server...")
    try:
        network.hosts["AS1"].cmd("kill $(cat /tmp/dnsmasq-p1.pid 2>/dev/null) 2>/dev/null || true")
        network.hosts["AS2"].cmd("kill $(cat /tmp/dnsmasq-p2.pid 2>/dev/null) 2>/dev/null || true")
        network.hosts["Web"].cmd("kill $(cat /tmp/kp_webserver.pid 2>/dev/null) 2>/dev/null || true; rm -f /tmp/kp_webserver.pid")
        network.hosts["EveLink"].cmd(f"pkill -f '{WEBSERVER_IP}/slow' 2>/dev/null; true")
        subprocess.run("kill $(cat /tmp/dnsmasq-main.pid 2>/dev/null) 2>/dev/null || true", shell=True)
        for name in network.hosts:
            network.hosts[name].cmd(f"kill $(cat /tmp/dnsmasq-stub-{name}.pid 2>/dev/null) 2>/dev/null || true")
        if Path("/tmp/orig-resolv.conf").exists():
            Path("/etc/resolv.conf").write_text(Path("/tmp/orig-resolv.conf").read_text())
        Path("/usr/local/share/ca-certificates/testbed-ca.crt").unlink(missing_ok=True)
        subprocess.run(["update-ca-certificates", "--fresh"], capture_output=True)
    except Exception as exc:
        logger.warning("Error during service cleanup: %s", exc)


def phase1_check(network: Network, logger) -> None:
    """Verify baseline: DNS and HTTP must work. Prints live output to stdout."""
    user = network.hosts["User"]
    loopback = _lo(network, "User")

    logger.info("Phase 1: DNS check (acm.org → %s) from every agent node...", WEBSERVER_IP)
    for name in network.hosts:
        dns_out = network.hosts[name].cmd("dig +short acm.org 2>&1").strip()
        if WEBSERVER_IP not in dns_out:
            logger.error("Phase 1 DNS FAILED on %s: got %r (expected %s) — setup bug, aborting.", name, dns_out, WEBSERVER_IP)
            exit(1)
        logger.info("Phase 1 DNS on %s: OK (%s)", name, dns_out)

    print(f"\n--- Baseline: curl http://acm.org/ (source: {loopback}) ---")
    curl_out = user.cmd(f"curl -s --interface {loopback} --max-time 10 http://acm.org/ 2>&1; echo exit:$?")
    print(curl_out)
    if "exit:0" not in curl_out:
        logger.error("Phase 1 HTTP FAILED — setup bug, aborting.")
        exit(1)
    logger.info("Phase 1 HTTP: OK — baseline verified.")


def phase2_check(network: Network, fault: str, logger) -> None:
    user = network.hosts["User"]
    loopback = _lo(network, "User")

    if fault == "dns_stale":
        dns_out = user.cmd("dig +short acm.org 2>&1").strip()
        if WEBSERVER_IP in dns_out:
            logger.error("Phase 2 FAILED: AS1 DNS still returns correct IP — setup bug, aborting.")
            exit(1)
        logger.info("Phase 2 dns_stale: OK — AS1 now returns %r.", dns_out)

    elif fault == "overload":
        http_code = user.cmd(f"curl -s -o /dev/null -w '%{{http_code}}' --interface {loopback} " f"--max-time 10 http://{WEBSERVER_IP}/ 2>&1").strip()
        if http_code != "503":
            logger.error("Phase 2 FAILED: expected HTTP 503, got %r — setup bug, aborting.", http_code)
            exit(1)
        logger.info("Phase 2 overload: OK — server returned 503.")

    else:
        wget_out = user.cmd(f"wget -q --bind-address {loopback} --timeout=5 --tries=1 " f"-O /dev/null http://{WEBSERVER_IP}/ 2>&1; echo exit:$?")
        if "exit:0" in wget_out:
            logger.error("Phase 2 FAILED: User can still reach %s after %s — setup bug, aborting.", WEBSERVER_IP, fault)
            exit(1)
        logger.info("Phase 2 %s: OK — User cannot reach %s.", fault, WEBSERVER_IP)


def inject_fault(network: Network, fault: str, logger) -> None:
    logger.info("Injecting fault: %s", fault)

    if fault == "bgp_hijack":
        p1 = network.hosts["AS1"]
        el = network.hosts["EveLink"]
        # EveLink claims the Web IP on its loopback (no HTTP server → connection refused)
        el.cmd(f"ip addr add {WEBSERVER_IP}/32 dev lo 2>/dev/null || true")
        # Redirect AS1's route for the Web IP toward EveLink
        # (simulates Gao-Rexford: customer route preferred over peer route)
        p1.cmd(f"ip route del {WEBSERVER_IP}/32 via 10.0.2.2")
        p1.cmd(f"ip route add {WEBSERVER_IP}/32 via 10.0.5.2")
        logger.info("BGP hijack: AS1 now routes %s via EveLink (10.0.5.2)", WEBSERVER_IP)

    elif fault == "dns_stale":
        p1 = network.hosts["AS1"]
        as2 = network.hosts["AS2"]
        acm = network.hosts["ACM"]
        # A stale record: an address inside ACM's own 198.82.0.0/24 content block that
        # no longer hosts a server. Using an in-block IP (not RFC1918) forces the
        # diagnosis to come from cross-checking the live service at 198.82.0.1 rather
        # than from the address class. Route it to ACM (the block owner) and have ACM
        # reject it with ICMP host-unreachable — the textbook behaviour of a subnet
        # gateway for an absent host — so the failure surfaces as "no route to host"
        # near the destination instead of looping in the core.
        stale_ip = "198.82.0.99"
        as2.cmd(f"ip route add {stale_ip}/32 via 10.0.3.2")  # AS2 -> ACM, like .1/.254
        acm.cmd(f"ip route add unreachable {stale_ip}/32")   # ACM: no such host here
        p1.cmd("kill $(cat /tmp/dnsmasq-p1.pid 2>/dev/null) 2>/dev/null; rm -f /tmp/dnsmasq-p1.pid")
        p1.cmd(f"dnsmasq --no-resolv --no-hosts --keep-in-foreground " f"--local=/acm.org/ --address=/acm.org/{stale_ip} " f"--listen-address={_lo(network, 'AS1')} --bind-interfaces --port=53 " f"--pid-file=/tmp/dnsmasq-p1.pid &")
        time.sleep(0.5)
        dns_check = network.hosts["User"].cmd(f"dig +short -b {_lo(network, 'User')} @{_lo(network, 'AS1')} acm.org 2>&1").strip()
        logger.info("DNS stale: AS1 now returns %r for acm.org (routed to ACM, unreachable)", dns_check)

    elif fault == "firewall":
        univ = network.hosts["Uni"]
        univ.cmd("iptables -A FORWARD -d 198.82.0.0/24 -j DROP")
        univ.cmd("iptables -A OUTPUT -d 198.82.0.0/24 -j DROP")
        fwd = univ.cmd("iptables -L FORWARD -n --line-numbers 2>&1")
        out = univ.cmd("iptables -L OUTPUT -n --line-numbers 2>&1")
        logger.info("Firewall: Uni FORWARD chain:\n%s", fwd)
        logger.info("Firewall: Uni OUTPUT chain:\n%s", out)
        user_route = network.hosts["User"].cmd(f"ip route get {WEBSERVER_IP} 2>&1")
        logger.info("Firewall: User route to %s: %s", WEBSERVER_IP, user_route.strip())

    elif fault == "overload":
        el = network.hosts["EveLink"]
        flood_count = WEBSERVER_MAX_WORKERS + 2
        for _ in range(flood_count):
            el.cmd(f"bash -c 'while true; do curl -s --max-time 120 http://{WEBSERVER_IP}/slow > /dev/null 2>&1 || sleep 1; done' &")
        time.sleep(1)
        logger.info("Overload: EveLink started %d persistent slow-request loops, worker slots perpetually saturated.", flood_count)

    else:
        raise ValueError(f"Unknown fault: {fault}")


def load_prompts(fault: str) -> dict[str, str]:
    prompts = {}
    for path in sorted(PROMPTS_DIR.glob("*.txt")):
        if path.stem == "final-report":
            continue
        prompts[path.stem] = path.read_text()
    mode = "ACTIVE" if fault == "bgp_hijack" else "PASSIVE"
    prompts["EveLink"] += f"\n\nCurrent mode: {mode}."
    return prompts


def print_agent_results(results, node_names) -> None:
    print("\n=== Agent Results ===")
    for name in node_names:
        r = results.get(name)
        if r is None:
            print(f"  {name} [NO RESULT]")
        elif r.success:
            print(f"  {name} [SUCCESS]")
        else:
            print(f"  {name} [INCOMPLETE] {r.message}")


def dns_stale_probe(network: Network, logger) -> None:
    """Dry-run diagnostic for the dns_stale fault: show the client symptom for the
    stale address (expect 'No route to host', sourced from ACM) and confirm the
    real service at 198.82.0.1 still serves HTTP 200."""
    user = network.hosts["User"]
    lo = _lo(network, "User")
    stale = user.cmd("dig +short acm.org | head -1").strip()
    probes = [
        ("resolve acm.org", "dig +short acm.org"),
        (f"curl http://acm.org/ (stale {stale})",
         f"curl -sS -m 8 --interface {lo} -o /dev/null http://acm.org/; echo exit:$?"),
        (f"ping stale {stale} (who rejects?)", f"ping -c 2 -W 2 -I {lo} {stale}"),
        (f"traceroute to stale {stale}", f"traceroute -n -w 2 -q 1 -s {lo} {stale} 2>&1"),
        ("curl real service 198.82.0.1",
         f"curl -sS -m 8 --interface {lo} -o /dev/null -w 'http=%{{http_code}}\\n' http://198.82.0.1/ 2>&1"),
    ]
    for label, cmd in probes:
        print(f"\n===== [User] {label} =====")
        print(f"$ {cmd}")
        print(user.cmd(cmd).rstrip())
    print("\n===== end dns_stale probe =====")


def main():
    if not Path("/.dockerenv").exists():
        print(
            "This experiment must run inside a Docker container.\n"
            "\n"
            "It temporarily replaces /etc/resolv.conf to configure per-node DNS\n"
            "inside the Mininet topology. Running it on a bare-metal host would\n"
            "affect DNS resolution for the entire machine while the experiment\n"
            "is running. Use tools/run_in_docker.sh or run_experiments.py --docker."
        )
        exit(1)

    args = parse_args()

    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = setup_logging(args.log_level)

    logger.info("Building Mininet network from %s...", TOPOLOGY)
    network = Network(load_topology(str(TOPOLOGY)))
    network.start()

    try:
        setup_routing(network, logger)
        start_services(network, logger)

        phase1_check(network, logger)
        inject_fault(network, args.fault, logger)
        phase2_check(network, args.fault, logger)

        if args.dry_run:
            if args.fault == "dns_stale":
                dns_stale_probe(network, logger)
            stop_services(network, logger)
            network.stop()
            return

        run_stem = f"knowledge_plane-{args.fault}-{args.model}"

        prompts = load_prompts(args.fault)
        setup_node_logs(network.hosts, log_dir, run_stem)
        logger.info("Writing per-node logs to %s/", log_dir)
        logger.info("Model: %s (%s)", args.model, MODELS[args.model])
        logger.info("Fault: %s", args.fault)

        anet = AgenticNetwork(
            network=network,
            initial_prompts=prompts,
            model_key=args.model,
            max_iterations=args.max_iterations,
            max_tokens=args.max_tokens,
            vllm_host=args.vllm_host,
            vllm_port=args.vllm_port,
            window_size=args.window_size,
        )

        anet.send_message(
            to="User",
            sender="human",
            message="I tried to load the website at acm.org in my browser but the page failed to load. Can you investigate why?",
        )

        results = anet.run(concurrent=not args.sequential)
        print_agent_results(results, network.hosts)

        logger.info("Gathering agent self-reports...")
        agent_reports = anet.gather_reports()
        for name, text in agent_reports.items():
            path = log_dir / f"{run_stem}-{name}-report.md"
            path.write_text(text)
            logger.info("Agent report: %s", path)

        write_timeline_html(log_dir, run_stem, network.hosts, logger)

        route_tables = collect_route_tables(network)
        connectivity = network.test_all_connectivity()

        final_report_path = PROMPTS_DIR / "final-report.txt"
        if final_report_path.exists():
            node_logs = collect_node_logs(log_dir, run_stem, network.hosts)
            final_prompt = final_report_path.read_text().format(
                fault=args.fault,
                fault_description=FAULT_DESCRIPTIONS[args.fault],
            )
            write_final_report(
                model_key=args.report_model or args.model,
                vllm_host=args.vllm_host,
                vllm_port=args.vllm_port,
                max_tokens=args.max_tokens,
                final_prompt=final_prompt,
                agent_reports=agent_reports,
                agent_results=results,
                node_logs=node_logs,
                connectivity=connectivity,
                route_tables=route_tables,
                log_dir=log_dir,
                run_stem=run_stem,
                logger=logger,
            )

        stop_services(network, logger)
        network.stop()

    except Exception:
        logger.exception("Experiment failed")
        stop_services(network, logger)
        network.stop()
        raise

    finally:
        chown_to_user(log_dir)
        orig = Path("/tmp/orig-resolv.conf")
        if orig.exists():
            Path("/etc/resolv.conf").write_text(orig.read_text())


if __name__ == "__main__":
    main()

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
        "AS1's DNS resolver has been reconfigured to return a stale (wrong) IP address "
        "for acm.org instead of the correct 198.82.0.1. The user's machine resolves acm.org "
        "through AS1's resolver, so every HTTP request goes to the wrong destination."
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

# Loopbacks assigned alphabetically by network.py: ACM=1, AS1=2, AS2=3,
# EveLink=4, Uni=5, User=6, Web=7
# User's loopback (10.255.6.1) and campus link (10.0.6.0/30) are not routed
# beyond Uni — Uni NATTs all campus traffic via MASQUERADE on Uni-eth1.
LOOPBACKS = {
    "ACM": "10.255.1.1",
    "AS1": "10.255.2.1",
    "AS2": "10.255.3.1",
    "EveLink": "10.255.4.1",
    "Uni": "10.255.5.1",
    "User": "10.255.6.1",
    "Web": "10.255.7.1",
}

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
    add(user, "default", "10.0.6.2", src=LOOPBACKS["User"])

    # Uni → User loopback via direct link; default via AS1
    add(univ, "10.255.6.1/32", "10.0.6.1", src=LOOPBACKS["Uni"])
    add(univ, "default", "10.0.1.2", src=LOOPBACKS["Uni"])

    # AS1 → Uni loopback via 10.0.1.1; EveLink loopback via 10.0.5.2; default via AS2
    # User's campus prefixes (10.255.6.1/32, 10.0.6.0/30) are intentionally not routed
    # beyond Uni — they are hidden behind Uni's NAT.
    add(p1, "10.255.5.1/32", "10.0.1.1", src=LOOPBACKS["AS1"])
    add(p1, "10.255.4.1/32", "10.0.5.2", src=LOOPBACKS["AS1"])
    add(p1, "10.0.5.0/30", "10.0.5.2", src=LOOPBACKS["AS1"])  # so EveLink link subnet is reachable
    add(p1, "default", "10.0.2.2", src=LOOPBACKS["AS1"])

    # AS2 → customer prefixes (ACM+Web) via 10.0.3.2; default via AS1
    add(p2, "10.255.1.1/32", "10.0.3.2", src=LOOPBACKS["AS2"])
    add(p2, "10.255.7.1/32", "10.0.3.2", src=LOOPBACKS["AS2"])
    add(p2, f"{WEBSERVER_IP}/32", "10.0.3.2", src=LOOPBACKS["AS2"])
    add(p2, "10.0.4.0/30", "10.0.3.2", src=LOOPBACKS["AS2"])  # so ACM–Web link subnet is reachable
    add(p2, "default", "10.0.2.1", src=LOOPBACKS["AS2"])

    # ACM → Web via direct link; default via AS2
    add(acm, "10.255.7.1/32", "10.0.4.2", src=LOOPBACKS["ACM"])
    add(acm, f"{WEBSERVER_IP}/32", "10.0.4.2", src=LOOPBACKS["ACM"])
    add(acm, "default", "10.0.3.1", src=LOOPBACKS["ACM"])

    # Web → default via ACM
    add(ws, "default", "10.0.4.1", src=LOOPBACKS["Web"])

    # EveLink → default via AS1
    add(el, "default", "10.0.5.1", src=LOOPBACKS["EveLink"])

    # NAT: masquerade all campus traffic leaving Uni toward the internet
    logger.info("Setting up NAT on Uni (MASQUERADE on Uni-eth1)...")
    univ.cmd("iptables -t nat -A POSTROUTING -o Uni-eth1 -j MASQUERADE")


def start_services(network: Network, logger) -> None:
    """Add Web semantic IP, start dnsmasq resolvers, start HTTP server."""
    webserver = network.hosts["Web"]
    as1 = network.hosts["AS1"]
    as2 = network.hosts["AS2"]

    logger.info("Adding %s to Web loopback...", WEBSERVER_IP)
    webserver.cmd(f"ip addr add {WEBSERVER_IP}/32 dev lo 2>/dev/null || true")

    logger.info("Starting dnsmasq on AS1 (10.255.2.1)...")
    as1.cmd("kill $(cat /tmp/dnsmasq-p1.pid 2>/dev/null) 2>/dev/null; rm -f /tmp/dnsmasq-p1.pid")
    as1.cmd(f"dnsmasq --no-resolv --no-hosts --keep-in-foreground " f"--address=/acm.org/{WEBSERVER_IP} " f"--listen-address=10.255.2.1 --port=53 " f"--pid-file=/tmp/dnsmasq-p1.pid &")

    logger.info("Starting dnsmasq on AS2 (10.255.3.1)...")
    as2.cmd("kill $(cat /tmp/dnsmasq-p2.pid 2>/dev/null) 2>/dev/null; rm -f /tmp/dnsmasq-p2.pid")
    as2.cmd(f"dnsmasq --no-resolv --no-hosts --keep-in-foreground " f"--address=/acm.org/{WEBSERVER_IP} " f"--listen-address=10.255.3.1 --port=53 " f"--pid-file=/tmp/dnsmasq-p2.pid &")

    # Per-namespace DNS via the 127.0.0.1 trick:
    # Each network namespace has its own loopback, so 127.0.0.1 is independent in
    # each namespace. We run two separate dnsmasq instances on 127.0.0.1:53 —
    # one in the main namespace (forwards to real DNS for Anthropic API calls) and
    # one in the User namespace (forwards to AS1's testbed resolver). Both are
    # reached via the same resolv.conf entry "nameserver 127.0.0.1".
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

    logger.info("Starting dnsmasq in User namespace (127.0.0.1 → %s)...", LOOPBACKS["AS1"])
    network.hosts["User"].cmd("kill $(cat /tmp/dnsmasq-user.pid 2>/dev/null) 2>/dev/null; rm -f /tmp/dnsmasq-user.pid")
    network.hosts["User"].cmd(
        f"dnsmasq --no-resolv --no-hosts --keep-in-foreground" f" --server={LOOPBACKS['AS1']} --listen-address=127.0.0.1 --bind-interfaces" f" --pid-file=/tmp/dnsmasq-user.pid &"
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
        network.hosts["User"].cmd("kill $(cat /tmp/dnsmasq-user.pid 2>/dev/null) 2>/dev/null || true")
        if Path("/tmp/orig-resolv.conf").exists():
            Path("/etc/resolv.conf").write_text(Path("/tmp/orig-resolv.conf").read_text())
        Path("/usr/local/share/ca-certificates/testbed-ca.crt").unlink(missing_ok=True)
        subprocess.run(["update-ca-certificates", "--fresh"], capture_output=True)
    except Exception as exc:
        logger.warning("Error during service cleanup: %s", exc)


def phase1_check(network: Network, logger) -> None:
    """Verify baseline: DNS and HTTP must work. Prints live output to stdout."""
    user = network.hosts["User"]
    loopback = LOOPBACKS["User"]

    logger.info("Phase 1: DNS check (acm.org → %s)...", WEBSERVER_IP)
    dns_out = user.cmd("dig +short acm.org 2>&1").strip()
    if WEBSERVER_IP not in dns_out:
        logger.error("Phase 1 DNS FAILED: got %r (expected %s) — setup bug, aborting.", dns_out, WEBSERVER_IP)
        exit(1)
    logger.info("Phase 1 DNS: OK (%s)", dns_out)

    print(f"\n--- Baseline: curl http://acm.org/ (source: {loopback}) ---")
    curl_out = user.cmd(f"curl -s --interface {loopback} --max-time 10 http://acm.org/ 2>&1; echo exit:$?")
    print(curl_out)
    if "exit:0" not in curl_out:
        logger.error("Phase 1 HTTP FAILED — setup bug, aborting.")
        exit(1)
    logger.info("Phase 1 HTTP: OK — baseline verified.")


def phase2_check(network: Network, fault: str, logger) -> None:
    user = network.hosts["User"]
    loopback = LOOPBACKS["User"]

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
        stale_ip = "10.0.0.99"
        p1.cmd("kill $(cat /tmp/dnsmasq-p1.pid 2>/dev/null) 2>/dev/null; rm -f /tmp/dnsmasq-p1.pid")
        p1.cmd(f"dnsmasq --no-resolv --no-hosts --keep-in-foreground " f"--address=/acm.org/{stale_ip} " f"--listen-address=10.255.2.1 --port=53 " f"--pid-file=/tmp/dnsmasq-p1.pid &")
        time.sleep(0.5)
        dns_check = network.hosts["User"].cmd(f"dig +short -b {LOOPBACKS['User']} @{LOOPBACKS['AS1']} acm.org 2>&1").strip()
        logger.info("DNS stale: AS1 now returns %r for acm.org", dns_check)

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

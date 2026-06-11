#!/usr/bin/env python3
"""Knowledge Plane WHY/FIX experiment.

Routing is configured with static ip route add commands — no BGP/FRR involved.
Agents can inspect and modify the routing tables as part of KP diagnostics and fixes.
"""

import argparse
import sys
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
    write_agent_reports,
    write_final_report,
)

SCRIPT_DIR = Path(__file__).resolve().parent
TOPOLOGY = SCRIPT_DIR / "topologies" / "knowledge_plane.csv"
PROMPTS_DIR = SCRIPT_DIR / "prompts" / "knowledge_plane"

WEBSERVER_IP = "198.82.0.1"

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
        "The HTTP server process on Web has been stopped. The Web host is still "
        "reachable at the network level (ping works), but port 80 is not listening, so every "
        "HTTP connection attempt is refused."
    ),
}

# Loopbacks assigned alphabetically by network.py: ACM=1, AS1=2, AS2=3,
# EveLink=4, Uni=5, User=6, Web=7
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

    def add(host, dest, via):
        host.cmd(f"ip route add {dest} via {via}")

    user = hosts["User"]
    univ = hosts["Uni"]
    p1 = hosts["AS1"]
    p2 = hosts["AS2"]
    acm = hosts["ACM"]
    ws = hosts["Web"]
    el = hosts["EveLink"]

    # User → default via Uni
    add(user, "default", "10.0.6.2")

    # Uni → User loopback via direct link; default via AS1
    add(univ, "10.255.6.1/32", "10.0.6.1")
    add(univ, "default", "10.0.1.2")

    # AS1 → customer prefixes (Uni+User) via 10.0.1.1; EveLink loopback via 10.0.5.2; default via AS2
    add(p1, "10.255.5.1/32", "10.0.1.1")
    add(p1, "10.255.6.1/32", "10.0.1.1")
    add(p1, "10.0.6.0/30",   "10.0.1.1")
    add(p1, "10.255.4.1/32", "10.0.5.2")
    add(p1, "10.0.5.0/30",   "10.0.5.2")  # so EveLink link subnet is reachable
    add(p1, "default", "10.0.2.2")

    # AS2 → customer prefixes (ACM+Web) via 10.0.3.2; default via AS1
    add(p2, "10.255.1.1/32", "10.0.3.2")
    add(p2, "10.255.7.1/32", "10.0.3.2")
    add(p2, f"{WEBSERVER_IP}/32", "10.0.3.2")
    add(p2, "10.0.4.0/30",   "10.0.3.2")  # so ACM–Web link subnet is reachable
    add(p2, "default", "10.0.2.1")

    # ACM → Web via direct link; default via AS2
    add(acm, "10.255.7.1/32", "10.0.4.2")
    add(acm, f"{WEBSERVER_IP}/32", "10.0.4.2")
    add(acm, "default", "10.0.3.1")

    # Web → default via ACM
    add(ws, "default", "10.0.4.1")

    # EveLink → default via AS1
    add(el, "default", "10.0.5.1")


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

    logger.info("Starting HTTP server on Web (%s:80)...", WEBSERVER_IP)
    webserver.cmd(
        f'python3 -c "'
        f"import http.server, socketserver; "
        f"h = type('H', (http.server.BaseHTTPRequestHandler,), {{"
        f"'do_GET': lambda s: (s.send_response(200), s.send_header('Content-Type','text/html'), s.end_headers(), s.wfile.write(b'<html><body><h1>ACM Digital Library</h1></body></html>')), "
        f"'log_message': lambda *a: None}}); "
        f"socketserver.TCPServer(('{WEBSERVER_IP}', 80), h).serve_forever()"
        f'" &'
    )
    time.sleep(1)


def stop_services(network: Network, logger) -> None:
    logger.info("Stopping dnsmasq and HTTP server...")
    try:
        network.hosts["AS1"].cmd("kill $(cat /tmp/dnsmasq-p1.pid 2>/dev/null) 2>/dev/null || true")
        network.hosts["AS2"].cmd("kill $(cat /tmp/dnsmasq-p2.pid 2>/dev/null) 2>/dev/null || true")
        network.hosts["Web"].cmd("pkill -f 'socketserver.TCPServer' 2>/dev/null || true")
    except Exception as exc:
        logger.warning("Error during service cleanup: %s", exc)


def phase1_check(network: Network, logger) -> None:
    """Verify baseline: DNS and HTTP must work. Prints live output to stdout."""
    user = network.hosts["User"]
    loopback = LOOPBACKS["User"]

    logger.info("Phase 1: DNS check (acm.org → %s)...", WEBSERVER_IP)
    dns_out = user.cmd(f"dig +short -b {loopback} @{LOOPBACKS['AS1']} acm.org 2>&1").strip()
    if WEBSERVER_IP not in dns_out:
        logger.error("Phase 1 DNS FAILED: got %r (expected %s) — setup bug, aborting.", dns_out, WEBSERVER_IP)
        sys.exit(1)
    logger.info("Phase 1 DNS: OK (%s)", dns_out)

    print(f"\n--- Baseline: curl http://{WEBSERVER_IP}/ (source: {loopback}) ---")
    curl_out = user.cmd(f"curl -s --interface {loopback} --max-time 10 " f'-H "Host: acm.org" http://{WEBSERVER_IP}/ 2>&1; echo exit:$?')
    print(curl_out)
    if "exit:0" not in curl_out:
        logger.error("Phase 1 HTTP FAILED — setup bug, aborting.")
        sys.exit(1)
    logger.info("Phase 1 HTTP: OK — baseline verified.")


def phase2_check(network: Network, fault: str, logger) -> None:
    """Verify fault is observable from User — abort if the expected symptom is absent."""
    user = network.hosts["User"]

    if fault == "dns_stale":
        dns_out = user.cmd(f"dig +short -b {LOOPBACKS['User']} @{LOOPBACKS['AS1']} acm.org 2>&1").strip()
        if WEBSERVER_IP in dns_out:
            logger.error("Phase 2 FAILED: AS1 DNS still returns correct IP after dns_stale injection — setup bug, aborting.")
            sys.exit(1)
        logger.info("Phase 2 DNS: OK — AS1 now returns stale record %r.", dns_out)
    else:
        wget_out = user.cmd(f"wget -q --bind-address {LOOPBACKS['User']} --timeout=5 --tries=1 " f"-O /dev/null http://{WEBSERVER_IP}/ 2>&1; echo exit:$?")
        if "exit:0" in wget_out:
            logger.error("Phase 2 FAILED: User can still reach %s after %s injection — setup bug, aborting.", WEBSERVER_IP, fault)
            sys.exit(1)
        logger.info("Phase 2 HTTP: OK — User cannot reach %s (%s confirmed).", WEBSERVER_IP, fault)


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
        ws = network.hosts["Web"]
        ws.cmd("pkill -f 'socketserver.TCPServer' 2>/dev/null || true")
        time.sleep(0.3)
        logger.info("Overload: HTTP server on Web stopped")

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
        logger.info("Model: %s (%s) | fault: %s", args.model, MODELS[args.model], args.fault)

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

        anet.bus.send(
            "User",
            "human",
            "I tried to access acm.org but the connection failed. Can you investigate why?",
        )

        results = anet.run(concurrent=not args.sequential)
        print_agent_results(results, network.hosts)

        logger.info("Gathering agent self-reports...")
        agent_reports = anet.gather_reports()
        for name, text in agent_reports.items():
            path = log_dir / f"{run_stem}-{name}-report.md"
            path.write_text(text)
            logger.info("Agent report: %s", path)

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
                model_key=args.model,
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


if __name__ == "__main__":
    main()

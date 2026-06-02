#!/usr/bin/env python3
"""
Billing-policy routing experiment.

Starts with routing pre-configured (all ISP traffic through Expensive),
background UDP traffic already flowing, and a simulated billing clock running.
ISP agents must figure out how to minimise transit costs given percentile billing.

Multiple traffic spikes are injected at configurable hours throughout the billing
period. A throughput plot is generated at the end.
"""

import argparse
import json
import time
from pathlib import Path

from agentic_networks.network import load_topology, Network
from agentic_networks.agentic_network import AgenticNetwork, MODELS
from agentic_networks.billing_clock import BillingClock
from agentic_networks.traffic_generator import TrafficGenerator
from agentic_networks.traffic_sampler import TrafficSampler
from experiment import (
    DEFAULT_LOG_DIR,
    chown_to_user,
    check_openai_server_or_exit,
    collect_node_logs,
    collect_route_tables,
    generate_routes_pdf,
    setup_logging,
    setup_node_logs,
    write_agent_reports,
    write_final_report,
)
from agentic_routing_policies_billing_plot_tput import generate_throughput_plot

# ---------------------------------------------------------------------------
# Fixed address assignments for this topology
# ---------------------------------------------------------------------------

LOOPBACKS: dict[str, tuple[str, str]] = {
    # node: (loopback_address/32, announced_prefix/24)
    "TinyInc": ("45.32.0.1/32", "45.32.0.0/24"),
    "ISP": ("85.12.64.1/32", "85.12.64.0/24"),
    "Expensive": ("192.0.2.1/32", "192.0.2.0/24"),
    "Cheap": ("198.18.0.1/32", "198.18.0.0/24"),
    "Remote": ("203.0.113.1/32", "203.0.113.0/24"),
}

REMOTE_PREFIX = "203.0.113.0/24"
REMOTE_LOOPBACK = "203.0.113.1"

CLOCK_PATH = "/tmp/billing-clock.json"
SAMPLES_PATH = "/tmp/traffic-samples.json"


# ---------------------------------------------------------------------------
# Pre-routing setup
# ---------------------------------------------------------------------------


def _nexthop(network: Network, from_node: str, to_node: str) -> str:
    """Return the peer IP that from_node uses to reach to_node directly."""
    for iface in network.ifaces_per_host[from_node]:
        if iface.peer == to_node:
            return iface.peer_ip.split("/")[0]
    raise ValueError(f"No direct link {from_node} → {to_node}")


def setup_routing(network: Network) -> None:
    """Pre-configure full routing. ISP routes Remote via Expensive (suboptimal)."""

    def add(host_name: str, prefix: str, via: str) -> None:
        network.hosts[host_name].cmd(f"ip route add {prefix} via {via} 2>/dev/null || true")

    # Enable IP forwarding and add semantic loopbacks on every node
    for name, host in network.hosts.items():
        host.cmd("sysctl -w net.ipv4.ip_forward=1 >/dev/null 2>&1")
        lo_addr, _ = LOOPBACKS[name]
        host.cmd(f"ip addr add {lo_addr} dev lo 2>/dev/null || true")

    # TinyInc: everything via ISP
    nh = _nexthop(network, "TinyInc", "ISP")
    for node in ("ISP", "Expensive", "Cheap", "Remote"):
        _, pfx = LOOPBACKS[node]
        add("TinyInc", pfx, nh)

    # ISP: customers via their link; Remote via Expensive (SUBOPTIMAL starting point)
    _, tinyinc_pfx = LOOPBACKS["TinyInc"]
    add("ISP", tinyinc_pfx, _nexthop(network, "ISP", "TinyInc"))
    _, exp_pfx = LOOPBACKS["Expensive"]
    add("ISP", exp_pfx, _nexthop(network, "ISP", "Expensive"))
    _, chp_pfx = LOOPBACKS["Cheap"]
    add("ISP", chp_pfx, _nexthop(network, "ISP", "Cheap"))
    add("ISP", REMOTE_PREFIX, _nexthop(network, "ISP", "Expensive"))  # suboptimal

    # Expensive: ISP/TinyInc back via ISP link; Remote/Cheap via Remote link
    nh_isp = _nexthop(network, "Expensive", "ISP")
    nh_rem = _nexthop(network, "Expensive", "Remote")
    for node in ("ISP", "TinyInc"):
        _, pfx = LOOPBACKS[node]
        add("Expensive", pfx, nh_isp)
    add("Expensive", "10.4.0.0/30", nh_isp)  # TinyInc-ISP link subnet
    _, rem_pfx = LOOPBACKS["Remote"]
    add("Expensive", rem_pfx, nh_rem)
    _, chp_pfx = LOOPBACKS["Cheap"]
    add("Expensive", chp_pfx, nh_rem)  # Cheap reachable through Remote

    # Cheap: symmetric to Expensive
    nh_isp = _nexthop(network, "Cheap", "ISP")
    nh_rem = _nexthop(network, "Cheap", "Remote")
    for node in ("ISP", "TinyInc"):
        _, pfx = LOOPBACKS[node]
        add("Cheap", pfx, nh_isp)
    add("Cheap", "10.4.0.0/30", nh_isp)  # TinyInc-ISP link subnet
    add("Cheap", rem_pfx, nh_rem)
    _, exp_pfx = LOOPBACKS["Expensive"]
    add("Cheap", exp_pfx, nh_rem)  # Expensive reachable through Remote

    # Remote: return path to ISP/TinyInc via Expensive (arbitrary)
    nh_exp = _nexthop(network, "Remote", "Expensive")
    nh_chp = _nexthop(network, "Remote", "Cheap")
    for node in ("ISP", "TinyInc"):
        _, pfx = LOOPBACKS[node]
        add("Remote", pfx, nh_exp)
    add("Remote", "10.4.0.0/30", nh_exp)  # TinyInc-ISP link subnet
    _, exp_pfx = LOOPBACKS["Expensive"]
    add("Remote", exp_pfx, nh_exp)
    _, chp_pfx = LOOPBACKS["Cheap"]
    add("Remote", chp_pfx, nh_chp)


# ---------------------------------------------------------------------------
# Experiment data persistence
# ---------------------------------------------------------------------------


def save_plot_data(
    samples: list[dict],
    baseline_mbps: float,
    spike_mbps: float,
    spike_hours: list[float],
    spike_duration_hours: float,
    total_days: int,
    step_hours: float,
    output_path: Path,
) -> None:
    data = {
        "params": {
            "baseline_mbps": baseline_mbps,
            "spike_mbps": spike_mbps,
            "spike_hours": spike_hours,
            "spike_duration_hours": spike_duration_hours,
            "total_days": total_days,
            "step_hours": step_hours,
        },
        "samples": samples,
    }
    output_path.write_text(json.dumps(data, indent=2))


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def parse_args():
    parser = argparse.ArgumentParser(description="Billing-policy routing experiment")
    parser.add_argument("--log-level", "-l", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--model", "-m", default="sonnet", choices=list(MODELS.keys()))
    parser.add_argument("--log-dir", "-d", default=str(DEFAULT_LOG_DIR), metavar="DIR")
    parser.add_argument("--max-tokens", "-t", type=int, default=16384, metavar="N")
    parser.add_argument("--window-size", "-w", type=int, default=40, metavar="N")
    parser.add_argument("--topology", required=True, metavar="FILE")
    parser.add_argument("--prompts-dir", required=True, metavar="DIR")
    parser.add_argument("--sequential", "-s", action="store_true", default=False)
    parser.add_argument("--openai-host", default="localhost", metavar="HOST")
    parser.add_argument("--openai-port", type=int, default=8000, metavar="PORT")
    parser.add_argument("--final-report-prompt", metavar="FILE")

    # Billing-specific
    parser.add_argument("--days", type=int, default=12, metavar="N", help="Experiment duration in days (default: 12); the billing period is always 30 days")
    parser.add_argument("--step-hours", type=float, default=6.0, metavar="H", help="Simulated hours per iteration (default: 6)")
    parser.add_argument("--baseline-mbps", type=float, default=100.0, metavar="M", help="Baseline traffic flow rate in Mbps (default: 100)")
    parser.add_argument("--spike-mbps", type=float, default=500.0, metavar="M", help="Spike traffic flow rate in Mbps (default: 500)")
    parser.add_argument("--spike-hours", type=float, nargs="+", default=[24.0, 72.0, 120.0, 168.0, 216.0, 264.0], metavar="H", help="Hours from start at which each spike begins (default: 24 72 120 168 216 264)")
    parser.add_argument("--spike-duration-hours", type=float, default=8.0, metavar="H", help="Duration of each spike in hours (default: 8)")
    parser.add_argument("--sample-interval-minutes", type=float, default=15.0, metavar="M", help="Virtual minutes between billing samples (default: 15)")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    args = parse_args()

    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = setup_logging(args.log_level)

    openai_base_url = f"http://{args.openai_host}:{args.openai_port}/v1"
    check_openai_server_or_exit(args.model, openai_base_url, logger)

    # Load topology and start network
    logger.info("Building Mininet network...")
    network = Network(load_topology(args.topology))
    network.start()

    logger.info("Pre-configuring routing (ISP → Remote via Expensive)...")
    setup_routing(network)

    logger.info("Verifying initial connectivity...")
    initial_connectivity = network.test_all_connectivity(label="Initial Connectivity Matrix")
    if "FAIL" in initial_connectivity:
        raise SystemExit("Pre-flight check failed: connectivity matrix has FAILs — fix routing before starting the experiment.")

    # Load prompts
    prompts_dir = Path(args.prompts_dir)
    prompts = {f.stem: f.read_text() for f in sorted(prompts_dir.glob("*.txt")) if f.stem != "final-report"}
    if not prompts:
        raise SystemExit(f"No prompt files found in {prompts_dir}")

    topology_stem = Path(args.topology).stem
    run_stem = f"{prompts_dir.name}-{args.model}-{topology_stem}"

    setup_node_logs(network.hosts, log_dir, run_stem)
    logger.info("Writing per-node logs to %s/", log_dir)
    logger.info("Using model: %s (%s)", args.model, MODELS[args.model])

    # Billing clock — always a 30-day period; the experiment covers only args.days of it
    clock = BillingClock(total_days=30)

    # Determine ISP's provider interfaces from topology
    provider_ifaces = {iface.peer: iface.iface for iface in network.ifaces_per_host["ISP"] if iface.peer in ("Expensive", "Cheap")}
    logger.info("ISP provider interfaces: %s", provider_ifaces)

    # Traffic sampler — driven by reactor
    sampler = TrafficSampler(
        network=network,
        billing_node="ISP",
        monitored_prefixes=[REMOTE_PREFIX],
        provider_ifaces=provider_ifaces,
        billing_clock=clock,
        output_path=SAMPLES_PATH,
    )

    # Traffic generator (iperf3)
    generator = TrafficGenerator(
        network=network,
        source="TinyInc",
        dest_ip=REMOTE_LOOPBACK,
        baseline_mbps=args.baseline_mbps,
        spike_mbps=args.spike_mbps,
    )

    # Start everything
    generator.start_servers()
    time.sleep(1)  # Let servers initialise

    clock.write(CLOCK_PATH)  # day 0 — written once before agents start
    sampler.start()
    generator.start_flow()
    time.sleep(2)  # Let traffic establish before agents begin

    # ------------------------------------------------------------------
    # Reactors
    # ------------------------------------------------------------------
    step_hours = args.step_hours
    step_days = step_hours / 24.0
    max_iterations = round(args.days * 24.0 / step_hours)

    spike_events: list[tuple[int, int]] = sorted((round(h / step_hours), round((h + args.spike_duration_hours) / step_hours)) for h in args.spike_hours)
    pending_events = list(spike_events)
    active_restore_iter: list[int | None] = [None]

    samples_per_step = round(step_hours * 60 / args.sample_interval_minutes)
    sample_interval_days = args.sample_interval_minutes / (24 * 60)

    def sample_reactor(_, step: int) -> None:
        # Samples are taken at the START of step N, before spike/restore fires.
        # They are labeled with step N-1's virtual time and measure traffic under
        # the routing decisions agents made in step N-1.  This guarantees the
        # billing record reflects what agents actually configured.
        if step == 0:
            return
        prev_elapsed_start = (step - 1) * step_days
        for i in range(samples_per_step):
            sampler.sample(elapsed_override=prev_elapsed_start + i * sample_interval_days)

    def spike_restore_reactor(_, step: int) -> None:
        if active_restore_iter[0] is not None and step == active_restore_iter[0]:
            generator.restore()
            active_restore_iter[0] = None
            logger.info("Spike restored at hour %.0f", step * step_hours)
        if pending_events and pending_events[0][0] == step:
            _, restore_iter = pending_events.pop(0)
            generator.spike()
            active_restore_iter[0] = restore_iter
            logger.info("Spike started at hour %.0f", step * step_hours)

    def clock_reactor(_, step: int) -> None:
        clock.set_elapsed(step * step_days)
        clock.write(CLOCK_PATH)

    extra_tools = [
        {
            "name": "get_traffic_sample",
            "description": "Take a live measurement of the current per-provider throughput.",
            "schema": {"type": "object", "properties": {}, "required": []},
            "handler": lambda: sampler.measure_now(),
        }
    ]

    try:
        anet = AgenticNetwork(
            network=network,
            initial_prompts=prompts,
            model_key=args.model,
            max_iterations=max_iterations,
            max_tokens=args.max_tokens,
            openai_base_url=openai_base_url,
            window_size=args.window_size,
            reactors=[sample_reactor, spike_restore_reactor, clock_reactor],
            post_reactors=[],
            extra_tools=extra_tools,
            context_fns={"ISP": sampler.measure_now},
        )
        results = anet.run(concurrent=not args.sequential)

        # Capture the final step's routing state (step max_iterations-1)
        clock.set_elapsed(args.days)
        clock.write(CLOCK_PATH)
        final_elapsed_start = (max_iterations - 1) * step_days
        for i in range(samples_per_step):
            sampler.sample(elapsed_override=final_elapsed_start + i * sample_interval_days)

        # Results summary
        print("\n=== Agent Results ===")
        for name in network.hosts:
            r = results[name]
            status = "SUCCESS" if r.success else f"INCOMPLETE: {r.message}"
            print(f"  {name} [{status}]")

        # Collect routing state and connectivity
        route_tables = collect_route_tables(network)
        connectivity = network.test_all_connectivity()

        report_path = log_dir / f"{run_stem}.txt"
        routing_section = "\n".join(f"--- {n} ---\n{route_tables[n] or '(empty)'}" for n in sorted(route_tables))
        report_path.write_text("=== Connectivity Matrix ===\n" + connectivity + "\n\n=== Routing Tables ===\n\n" + routing_section + "\n")
        logger.info("Report written to %s", report_path)

        # Agent self-reports
        logger.info("Gathering agent self-reports...")
        agent_reports = anet.gather_reports()
        write_agent_reports(agent_reports, log_dir, run_stem, logger)
        generate_routes_pdf(network, route_tables, log_dir, run_stem, logger, show_delays=False)

        # Final analysis report
        if args.final_report_prompt:
            final_prompt = Path(args.final_report_prompt).read_text()
            node_logs = collect_node_logs(log_dir, run_stem, network.hosts)
            write_final_report(
                model_key=args.model,
                openai_base_url=openai_base_url,
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

        generator.stop()
        sampler.stop()
        network.stop()

    finally:
        chown_to_user(log_dir)

    # Save experiment data and generate throughput plot
    data_path = log_dir / f"{run_stem}-data.json"
    save_plot_data(
        samples=sampler.samples,
        baseline_mbps=args.baseline_mbps,
        spike_mbps=args.spike_mbps,
        spike_hours=args.spike_hours,
        spike_duration_hours=args.spike_duration_hours,
        total_days=args.days,
        step_hours=step_hours,
        output_path=data_path,
    )
    logger.info("Experiment data saved to %s", data_path)
    generate_throughput_plot(
        data_path=data_path,
        output_path=log_dir / f"{run_stem}-tput.png",
        logger=logger,
    )


if __name__ == "__main__":
    main()

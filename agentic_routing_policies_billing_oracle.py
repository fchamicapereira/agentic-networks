#!/usr/bin/env python3
"""
Oracle billing-policy routing experiment.

Identical to agentic_routing_policies_billing except:
  - The spike schedule is fixed (not a CLI argument).
  - The ISP agent is given the full spike schedule upfront in its prompt.

The fixed schedule matches:
  --spike-hours 24:6 42:6 72:6 96:12 120:6 144:6 168:120 --days 14
"""

import argparse
import time
from pathlib import Path

from agentic_networks.network import load_topology, Network
from agentic_networks.agentic_network import AgenticNetwork, MODELS
from agentic_networks.billing_clock import BillingClock
from agentic_networks.traffic_generator import TrafficGenerator
from agentic_networks.traffic_sampler import TrafficSampler
from agentic_routing_policies_billing import (
    SpikeWindow,
    LOOPBACKS,
    REMOTE_PREFIX,
    REMOTE_LOOPBACK,
    setup_routing,
    save_plot_data,
)
from agentic_routing_policies_billing_plot_tput import generate_throughput_plot
from experiment import (
    DEFAULT_LOG_DIR,
    chown_to_user,
    collect_node_logs,
    collect_route_tables,
    generate_routes_pdf,
    setup_logging,
    setup_node_logs,
    write_agent_reports,
    write_final_report,
)

DEFAULT_SPIKES: list[SpikeWindow] = [
    SpikeWindow(time=24,  duration=6),
    SpikeWindow(time=42,  duration=6),
    SpikeWindow(time=72,  duration=6),
    SpikeWindow(time=96,  duration=12),
    SpikeWindow(time=120, duration=6),
    SpikeWindow(time=144, duration=6),
    SpikeWindow(time=168, duration=120),
]

DEFAULT_DAYS    = 14
DEFAULT_PROMPTS = "prompts/optimizing_billing_policy_oracle"


def _spike_schedule_text(spikes: list[SpikeWindow]) -> str:
    lines = []
    for s in spikes:
        t = int(s.time)     if s.time     == int(s.time)     else s.time
        d = int(s.duration) if s.duration == int(s.duration) else s.duration
        lines.append(f"  Hour {t:>4} — duration {d:>3} h")
    return "\n".join(lines)


def parse_args():
    parser = argparse.ArgumentParser(description="Oracle billing-policy routing experiment")
    parser.add_argument("--log-level", "-l", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--model", "-m", default="sonnet", choices=list(MODELS.keys()))
    parser.add_argument("--log-dir", "-d", default=str(DEFAULT_LOG_DIR), metavar="DIR")
    parser.add_argument("--max-tokens", "-t", type=int, default=16384, metavar="N")
    parser.add_argument("--window-size", "-w", type=int, default=40, metavar="N")
    parser.add_argument("--topology", required=True, metavar="FILE")
    parser.add_argument("--prompts-dir", default=DEFAULT_PROMPTS, metavar="DIR")
    parser.add_argument("--sequential", "-s", action="store_true", default=False)
    parser.add_argument("--vllm-host", default="localhost", metavar="HOST")
    parser.add_argument("--vllm-port", type=int, default=8000, metavar="PORT")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS, metavar="N")

    def spike_window(s: str) -> SpikeWindow:
        try:
            time_str, dur_str = s.split(":")
            return SpikeWindow(time=float(time_str), duration=float(dur_str))
        except ValueError:
            raise argparse.ArgumentTypeError(f"Expected HOUR:DURATION, got {s!r}")

    parser.add_argument(
        "--spike-hours", type=spike_window, nargs="+", default=DEFAULT_SPIKES,
        metavar="HOUR:DURATION",
        help="Spike windows as HOUR:DURATION pairs (default: the standard oracle schedule)",
    )
    parser.add_argument("--step-hours", type=float, default=6.0, metavar="H")
    parser.add_argument("--baseline-mbps", type=float, default=100.0, metavar="M")
    parser.add_argument("--spike-mbps", type=float, default=500.0, metavar="M")
    parser.add_argument("--sample-interval-minutes", type=float, default=15.0, metavar="M")
    return parser.parse_args()


def main():
    args = parse_args()

    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = setup_logging(args.log_level)

    logger.info("Building Mininet network...")
    network = Network(load_topology(args.topology))
    network.start()

    logger.info("Pre-configuring routing (ISP → Remote via Expensive)...")
    setup_routing(network)

    logger.info("Verifying initial connectivity...")
    initial_connectivity = network.test_all_connectivity(label="Initial Connectivity Matrix")
    if "FAIL" in initial_connectivity:
        raise SystemExit("Pre-flight check failed: connectivity matrix has FAILs.")

    prompts_dir = Path(args.prompts_dir)
    spikes = args.spike_hours
    step_hours_val = int(args.step_hours) if args.step_hours == int(args.step_hours) else args.step_hours
    billing_samples_val = round(30 * 24 / args.step_hours)
    template_vars = {
        "step_hours": str(step_hours_val),
        "billing_samples": str(billing_samples_val),
        "spike_schedule": _spike_schedule_text(spikes),
    }

    def _render(text: str) -> str:
        for key, val in template_vars.items():
            text = text.replace("{" + key + "}", val)
        return text

    prompts = {f.stem: _render(f.read_text()) for f in sorted(prompts_dir.glob("*.txt")) if f.stem != "final-report"}
    if not prompts:
        raise SystemExit(f"No prompt files found in {prompts_dir}")

    topology_stem = Path(args.topology).stem
    run_stem = f"{prompts_dir.name}-{args.model}-{topology_stem}"

    setup_node_logs(network.hosts, log_dir, run_stem)
    logger.info("Writing per-node logs to %s/", log_dir)
    logger.info("Using model: %s (%s)", args.model, MODELS[args.model])

    clock = BillingClock(total_days=30)

    provider_ifaces = {iface.peer: iface.iface for iface in network.ifaces_per_host["ISP"] if iface.peer in ("Expensive", "Cheap")}
    logger.info("ISP provider interfaces: %s", provider_ifaces)

    sampler = TrafficSampler(
        network=network,
        billing_node="ISP",
        monitored_prefixes=[REMOTE_PREFIX],
        provider_ifaces=provider_ifaces,
        billing_clock=clock,
    )

    generator = TrafficGenerator(
        network=network,
        source="TinyInc",
        dest_ip=REMOTE_LOOPBACK,
        baseline_mbps=args.baseline_mbps,
        spike_mbps=args.spike_mbps,
    )

    generator.start_servers()
    time.sleep(1)

    sampler.start()
    generator.start_flow()
    time.sleep(2)

    step_hours = args.step_hours
    step_days = step_hours / 24.0
    max_iterations = round(args.days * 24.0 / step_hours)

    spike_events: list[tuple[int, int]] = sorted(
        (round(s.time / step_hours), round((s.time + s.duration) / step_hours))
        for s in spikes
    )
    pending_events = list(spike_events)
    active_restore_iter: list[int | None] = [None]

    samples_per_step = round(step_hours * 60 / args.sample_interval_minutes)
    sample_interval_days = args.sample_interval_minutes / (24 * 60)

    def sample_reactor(_, step: int) -> None:
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
            vllm_host=args.vllm_host,
            vllm_port=args.vllm_port,
            window_size=args.window_size,
            reactors=[sample_reactor, spike_restore_reactor, clock_reactor],
            post_reactors=[],
            extra_tools=extra_tools,
            context_fns={"ISP": sampler.measure_now},
        )
        results = anet.run(concurrent=not args.sequential)

        clock.set_elapsed(args.days)
        final_elapsed_start = (max_iterations - 1) * step_days
        for i in range(samples_per_step):
            sampler.sample(elapsed_override=final_elapsed_start + i * sample_interval_days)

        print("\n=== Agent Results ===")
        for name in network.hosts:
            r = results[name]
            status = "SUCCESS" if r.success else f"INCOMPLETE: {r.message}"
            print(f"  {name} [{status}]")

        route_tables = collect_route_tables(network)
        connectivity = network.test_all_connectivity()

        report_path = log_dir / f"{run_stem}.txt"
        routing_section = "\n".join(f"--- {n} ---\n{route_tables[n] or '(empty)'}" for n in sorted(route_tables))
        report_path.write_text("=== Connectivity Matrix ===\n" + connectivity + "\n\n=== Routing Tables ===\n\n" + routing_section + "\n")
        logger.info("Report written to %s", report_path)

        logger.info("Gathering agent self-reports...")
        agent_reports = anet.gather_reports()
        write_agent_reports(agent_reports, log_dir, run_stem, logger)
        generate_routes_pdf(network, route_tables, log_dir, run_stem, logger, show_delays=False)

        final_report_file = prompts_dir / "final-report.txt"
        if final_report_file.exists():
            node_logs = collect_node_logs(log_dir, run_stem, network.hosts)
            write_final_report(
                model_key=args.model,
                vllm_host=args.vllm_host,
                vllm_port=args.vllm_port,
                max_tokens=args.max_tokens,
                final_prompt=final_report_file.read_text(),
                agent_reports=agent_reports,
                agent_results=results,
                node_logs=node_logs,
                connectivity=connectivity,
                route_tables=route_tables,
                log_dir=log_dir,
                run_stem=run_stem,
                logger=logger,
            )
        else:
            print("No final-report.txt found in prompts directory, skipping final report generation.")

        generator.stop()
        sampler.stop()
        network.stop()

    finally:
        chown_to_user(log_dir)

    data_path = log_dir / f"{run_stem}-data.json"
    save_plot_data(
        samples=sampler.samples,
        baseline_mbps=args.baseline_mbps,
        spike_mbps=args.spike_mbps,
        spikes=spikes,
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

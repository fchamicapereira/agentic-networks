#!/usr/bin/env python3
"""
Billing-policy routing experiment.

The run is the end of a 30-day billing cycle: until it starts, TinyInc's traffic was a steady
baseline carried via Cheap. It starts with routing pre-configured (all ISP traffic through
Cheap), background UDP traffic already flowing, and a simulated billing clock running.
ISP agents must figure out how to minimise transit costs given percentile billing.

Multiple traffic spikes are injected at configurable hours throughout the billing
period. A throughput plot is generated at the end.
"""

import argparse
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path

from agentic_networks.network import load_topology, Network
from agentic_networks.agentic_network import AgenticNetwork, MODELS, describe_run
from agentic_networks.events import EventLog, NO_EVENTS, load_topology as load_event_topology
from agentic_networks.billing_clock import BillingClock
from agentic_networks.traffic_generator import TrafficGenerator
from agentic_networks.traffic_sampler import TrafficSampler
from agentic_networks.experiment import (
    DEFAULT_LOG_DIR,
    chown_to_user,
    collect_node_logs,
    collect_route_tables,
    generate_routes_pdf,
    load_system_prompts,
    setup_logging,
    setup_node_logs,
    write_agent_reports,
    write_final_report,
    write_timeline_html,
)
from agentic_networks.billing_plot import generate_throughput_plot

# ISP's extra tool (its handler, which needs the running sampler, is added in main), and the
# agents that get a fresh traffic observation every turn.
TRAFFIC_TOOL = {
    "name": "get_traffic_sample",
    "description": "Take a live measurement of the current per-provider throughput.",
    "schema": {"type": "object", "properties": {}, "required": []},
}
OBSERVING = ("ISP",)

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class SpikeWindow:
    time: float   # hours from experiment start
    duration: float  # hours


# ---------------------------------------------------------------------------
# Address assignments come from the topology's loopbacks. Each node's announced
# prefix is the /24 containing its loopback.
# ---------------------------------------------------------------------------


def _announced_prefix(loopback: str) -> str:
    # "85.12.64.1/32" -> "85.12.64.0/24"
    a, b, c, _ = loopback.split("/")[0].split(".")
    return f"{a}.{b}.{c}.0/24"


def loopbacks_from_network(network: Network) -> dict[str, tuple[str, str]]:
    # node -> (loopback/32, announced /24), derived from the topology loopbacks.
    return {name: (lo, _announced_prefix(lo)) for name, lo in network.loopback_per_host.items()}


def remote_addrs(network: Network) -> tuple[str, str]:
    # (announced /24, loopback IP) for Remote — the destination whose traffic ISP optimises.
    lo = network.loopback_per_host["Remote"]
    return _announced_prefix(lo), lo.split("/")[0]



# ---------------------------------------------------------------------------
# Pre-routing setup
# ---------------------------------------------------------------------------


def check_tinyinc_reaches_remote(network: Network) -> None:
    """Abort unless TinyInc's loopback reaches Remote's over the pre-configured routing."""
    src = network.loopback_per_host["TinyInc"].split("/")[0]
    _, dst = remote_addrs(network)
    out = network.hosts["TinyInc"].cmd(f"ping -c 3 -W 1 -I {src} {dst}")
    if " 0% packet loss" not in out:
        raise SystemExit(f"Pre-flight check failed: TinyInc ({src}) cannot reach Remote ({dst}) — fix routing before starting the experiment.")


def _nexthop(network: Network, from_node: str, to_node: str) -> str:
    """Return the peer IP that from_node uses to reach to_node directly."""
    for iface in network.ifaces_per_host[from_node]:
        if iface.peer == to_node:
            return iface.peer_ip.split("/")[0]
    raise ValueError(f"No direct link {from_node} → {to_node}")


def setup_routing(network: Network) -> None:
    """Pre-configure full routing. ISP routes Remote via Cheap, as it has all billing cycle."""

    loopbacks = loopbacks_from_network(network)

    def add(host_name: str, prefix: str, via: str) -> None:
        network.hosts[host_name].cmd(f"ip route add {prefix} via {via} 2>/dev/null || true")

    # Enable IP forwarding and add semantic loopbacks on every node
    for name, host in network.hosts.items():
        host.cmd("sysctl -w net.ipv4.ip_forward=1 >/dev/null 2>&1")
        lo_addr, _ = loopbacks[name]
        host.cmd(f"ip addr add {lo_addr} dev lo 2>/dev/null || true")

    # TinyInc: everything via ISP
    nh = _nexthop(network, "TinyInc", "ISP")
    for node in ("ISP", "Expensive", "Cheap", "Remote"):
        _, pfx = loopbacks[node]
        add("TinyInc", pfx, nh)

    # ISP: customers via their link; Remote via Cheap (the baseline's provider so far)
    _, tinyinc_pfx = loopbacks["TinyInc"]
    add("ISP", tinyinc_pfx, _nexthop(network, "ISP", "TinyInc"))
    _, exp_pfx = loopbacks["Expensive"]
    add("ISP", exp_pfx, _nexthop(network, "ISP", "Expensive"))
    _, chp_pfx = loopbacks["Cheap"]
    add("ISP", chp_pfx, _nexthop(network, "ISP", "Cheap"))
    add("ISP", loopbacks["Remote"][1], _nexthop(network, "ISP", "Cheap"))

    # Expensive: ISP/TinyInc back via ISP link; Remote/Cheap via Remote link
    nh_isp = _nexthop(network, "Expensive", "ISP")
    nh_rem = _nexthop(network, "Expensive", "Remote")
    for node in ("ISP", "TinyInc"):
        _, pfx = loopbacks[node]
        add("Expensive", pfx, nh_isp)
    add("Expensive", "10.4.0.0/30", nh_isp)  # TinyInc-ISP link subnet
    _, rem_pfx = loopbacks["Remote"]
    add("Expensive", rem_pfx, nh_rem)
    _, chp_pfx = loopbacks["Cheap"]
    add("Expensive", chp_pfx, nh_rem)  # Cheap reachable through Remote

    # Cheap: symmetric to Expensive
    nh_isp = _nexthop(network, "Cheap", "ISP")
    nh_rem = _nexthop(network, "Cheap", "Remote")
    for node in ("ISP", "TinyInc"):
        _, pfx = loopbacks[node]
        add("Cheap", pfx, nh_isp)
    add("Cheap", "10.4.0.0/30", nh_isp)  # TinyInc-ISP link subnet
    add("Cheap", rem_pfx, nh_rem)
    _, exp_pfx = loopbacks["Expensive"]
    add("Cheap", exp_pfx, nh_rem)  # Expensive reachable through Remote

    # Remote: return path to ISP/TinyInc via Expensive (arbitrary)
    nh_exp = _nexthop(network, "Remote", "Expensive")
    nh_chp = _nexthop(network, "Remote", "Cheap")
    for node in ("ISP", "TinyInc"):
        _, pfx = loopbacks[node]
        add("Remote", pfx, nh_exp)
    add("Remote", "10.4.0.0/30", nh_exp)  # TinyInc-ISP link subnet
    _, exp_pfx = loopbacks["Expensive"]
    add("Remote", exp_pfx, nh_exp)
    _, chp_pfx = loopbacks["Cheap"]
    add("Remote", chp_pfx, nh_chp)


# ---------------------------------------------------------------------------
# Experiment data persistence
# ---------------------------------------------------------------------------


def save_plot_data(
    samples: list[dict],
    baseline_mbps: float,
    spike_mbps: float,
    spikes: list[SpikeWindow],
    total_days: int,
    step_hours: float,
    output_path: Path,
) -> None:
    data = {
        "params": {
            "baseline_mbps": baseline_mbps,
            "spike_mbps": spike_mbps,
            "spikes": [{"time": s.time, "duration": s.duration} for s in spikes],
            "total_days": total_days,
            "step_hours": step_hours,
        },
        "samples": samples,
    }
    output_path.write_text(json.dumps(data, indent=2))


# ---------------------------------------------------------------------------
# Bill
# ---------------------------------------------------------------------------

BILLING_DAYS = 30
SAMPLE_SETTLE_SECONDS = 0.5
# provider -> ($ per Mbps, fraction of samples discarded), as in ISP's prompt
CONTRACTS = {"Expensive": (5.0, 0.10), "Cheap": (1.0, 0.05)}


def _percentile_bill(values: list[float], samples_in_period: int, rate: float, discard: float) -> tuple[float, float]:
    # values: every nonzero sample of the cycle; the rest of the period counts as 0 Mbps.
    ranked = sorted(values, reverse=True) + [0.0] * (samples_in_period - len(values))
    mbps = ranked[math.floor(samples_in_period * discard)]
    return mbps, mbps * rate


def compute_bills(samples: list[dict], prefix: str, samples_per_step: int, sample_interval_minutes: float, start_day: float) -> str:
    """The bill from the recorded samples, and what reference strategies would have cost on the
    same traffic. The cycle's first start_day days carried the baseline via Cheap (the prompt's
    history). Strategies assign whole steps."""
    n = round(BILLING_DAYS * 24 * 60 / sample_interval_minutes)
    rows = [s["mbps"][prefix] for s in samples]

    steps = [[sum(r.values()) for r in rows[i:i + samples_per_step]] for i in range(0, len(rows), samples_per_step)]
    level = [sum(st) / len(st) for st in steps]
    baseline = min(level)
    history = [baseline] * round(start_day * 24 * 60 / sample_interval_minutes)

    def bill(per_provider: dict[str, list[float]]) -> tuple[float, str]:
        total, parts = 0.0, []
        for provider, (rate, discard) in CONTRACTS.items():
            values = per_provider[provider] + (history if provider == "Cheap" else [])
            mbps, cost = _percentile_bill(values, n, rate, discard)
            total += cost
            parts.append(f"{provider} {mbps:.0f} Mbps billed = ${cost:,.0f}")
        return total, "; ".join(parts)

    actual_total, actual = bill({p: [r[f"via_{p}"] for r in rows] for p in CONTRACTS})

    threshold = (baseline + max(level)) / 2
    spike_steps = [i for i, v in enumerate(level) if v > threshold]

    def assign(on_expensive: set[int]) -> tuple[float, str]:
        per = {"Expensive": [], "Cheap": []}
        for i, st in enumerate(steps):
            per["Expensive" if i in on_expensive else "Cheap"] += st
        return bill(per)

    refs = {
        "All traffic on Cheap": assign(set()),
        "Spikes always on Expensive": assign(set(spike_steps)),
    }
    # Best split in hindsight: the first k spike steps on Expensive, the rest on Cheap.
    refs["Best in hindsight (spikes on Expensive while its discard window lasts, rest on Cheap)"] = min(
        (assign(set(spike_steps[:k])) for k in range(len(spike_steps) + 1)), key=lambda r: r[0])

    lines = [
        "=== Bill ===",
        f"30-day percentile bill over {n} 15-minute samples; the {start_day:g} days before the run carried a {baseline:.0f} Mbps baseline via Cheap.",
        f"Actual: ${actual_total:,.0f} ({actual})",
        "Reference strategies on the same traffic:",
    ] + [f"  {name}: ${total:,.0f} ({detail})" for name, (total, detail) in refs.items()]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def parse_args():
    parser = argparse.ArgumentParser(description="Billing-policy routing experiment")
    parser.add_argument("--log-level", "-l", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--model", "-m", default="sonnet", choices=list(MODELS.keys()))
    parser.add_argument("--report-model", default=None, choices=list(MODELS.keys()), metavar="MODEL", help="Model for final-report generation (default: same as --model)")
    parser.add_argument("--no-reports", action="store_true", default=False, help="Skip the agents' self-reports and the final report after the run (they cost model calls)")
    parser.add_argument("--log-dir", "-d", default=str(DEFAULT_LOG_DIR), metavar="DIR")
    parser.add_argument("--max-tokens", "-t", type=int, default=16384, metavar="N")
    parser.add_argument("--window-size", "-w", type=int, default=40, metavar="N")
    parser.add_argument("--topology", required=True, metavar="FILE")
    parser.add_argument("--prompts-dir", required=True, metavar="DIR")
    parser.add_argument("--events", default=None, metavar="FILE", help="Also write the run as the demo's event stream (demo/EVENTS.md) to FILE, as it happens")
    parser.add_argument("--system-prompts", default=None, metavar="DIR", help="<node>.txt files, each that agent's whole system prompt, used exactly as given (the demo's edited prompts)")
    parser.add_argument("--describe", default=None, metavar="FILE", help="Write only what the run would start with (topology, prompts) as the demo's event stream to FILE, and exit: no network, no models")
    parser.add_argument("--sequential", "-s", action="store_true", default=False)
    parser.add_argument("--vllm-host", default="localhost", metavar="HOST")
    parser.add_argument("--vllm-port", type=int, default=8000, metavar="PORT")

    # Billing-specific
    parser.add_argument("--days", type=int, default=9, metavar="N", help="Experiment duration in days (default: 9): the last N days of the 30-day billing period")
    parser.add_argument("--step-hours", type=float, default=6.0, metavar="H", help="Simulated hours per iteration (default: 6)")
    parser.add_argument("--baseline-mbps", type=float, default=100.0, metavar="M", help="Baseline traffic flow rate in Mbps (default: 100)")
    parser.add_argument("--spike-mbps", type=float, default=500.0, metavar="M", help="Spike traffic flow rate in Mbps (default: 500)")
    def spike_window(s: str) -> SpikeWindow:
        try:
            time_str, dur_str = s.split(":")
            return SpikeWindow(time=float(time_str), duration=float(dur_str))
        except ValueError:
            raise argparse.ArgumentTypeError(f"Expected HOUR:DURATION, got {s!r}")

    parser.add_argument(
        "--spike-hours", type=spike_window, nargs="+",
        # Three short spikes two days apart (the advertised pattern), then a long one that
        # outlasts Expensive's discard window but fits once the overflow goes to Cheap: the
        # budget-aware strategy bills ~$100, all-on-Cheap ~$500, spikes-always-on-Expensive
        # ~$2,650 (30-day period, 6-hour steps, baseline on Cheap before the run).
        default=[
            SpikeWindow(time=12,  duration=6),
            SpikeWindow(time=60,  duration=6),
            SpikeWindow(time=108, duration=6),
            SpikeWindow(time=132, duration=72),
        ],
        metavar="HOUR:DURATION",
        help="Spike windows as HOUR:DURATION pairs (default: 12:6 60:6 108:6 132:72)",
    )
    parser.add_argument("--sample-interval-minutes", type=float, default=15.0, metavar="M", help="Virtual minutes between billing samples (default: 15)")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def load_prompts(prompts_dir: Path, step_hours: float, start_day: int) -> dict[str, str]:
    """Each node's prompt, with the run's timing filled in."""
    step_hours_val = int(step_hours) if step_hours == int(step_hours) else step_hours
    billing_samples_val = round(30 * 24 / step_hours)
    history_samples_val = round(start_day * 24 / step_hours)
    template_vars = {
        "step_hours": str(step_hours_val),
        "billing_samples": str(billing_samples_val),
        "start_day": str(start_day),
        "history_samples": str(history_samples_val),
    }
    def _render(text: str) -> str:
        for key, val in template_vars.items():
            text = text.replace("{" + key + "}", val)
        return text
    prompts = {f.stem: _render(f.read_text()) for f in sorted(prompts_dir.glob("*.txt")) if f.stem != "final-report"}
    if not prompts:
        raise SystemExit(f"No prompt files found in {prompts_dir}")
    return prompts


def main():
    args = parse_args()
    if not 0 < args.days <= BILLING_DAYS:
        raise SystemExit(f"--days must be between 1 and {BILLING_DAYS}")
    # The run is the end of the billing cycle, start_day days in (the baseline rode on Cheap until then).
    start_day = BILLING_DAYS - args.days
    prompts_dir = Path(args.prompts_dir)

    # The scenario is named after its prompts (optimizing_billing_policy), in the demo's event stream too.
    if args.describe:
        describe_run(args.describe, prompts_dir.name, prompts_dir.name, Network(load_topology(args.topology)),
                     args.topology, load_prompts(prompts_dir, args.step_hours, start_day),
                     extra_tools=[TRAFFIC_TOOL], observing=OBSERVING)
        chown_to_user(Path(args.describe))
        return

    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = setup_logging(args.log_level)

    # Load topology and start network
    logger.info("Building Mininet network...")
    network = Network(load_topology(args.topology))
    network.start()

    logger.info("Pre-configuring routing (ISP → Remote via Cheap)...")
    setup_routing(network)

    logger.info("Verifying TinyInc reaches Remote...")
    check_tinyinc_reaches_remote(network)

    prompts = load_prompts(prompts_dir, args.step_hours, start_day)

    topology_stem = Path(args.topology).stem
    run_stem = f"{prompts_dir.name}-{args.model}-{topology_stem}"

    setup_node_logs(network.hosts, log_dir, run_stem)
    logger.info("Writing per-node logs to %s/", log_dir)
    logger.info("Using model: %s (%s)", args.model, MODELS[args.model])

    # Billing clock — always a 30-day period; the experiment covers its last args.days days.
    # The clock (what ISP sees) runs from start_day; sample labels stay relative to the run.
    clock = BillingClock(total_days=BILLING_DAYS)

    # Determine ISP's provider interfaces from topology
    provider_ifaces = {iface.peer: iface.iface for iface in network.ifaces_per_host["ISP"] if iface.peer in ("Expensive", "Cheap")}
    logger.info("ISP provider interfaces: %s", provider_ifaces)

    remote_prefix, remote_loopback = remote_addrs(network)

    events = EventLog(args.events) if args.events else NO_EVENTS
    events.run_start(prompts_dir.name, prompts_dir.name, args.model, {node: args.model for node in network.hosts},
                     load_event_topology(args.topology))

    def emit_sample(sample: dict) -> None:
        for prefix, values in sample["mbps"].items():
            events.emit("metric", name="throughput_mbps", prefix=prefix, sim_days=sample["elapsed_days"], values=values)

    # Traffic sampler — driven by reactor
    sampler = TrafficSampler(
        network=network,
        billing_node="ISP",
        monitored_prefixes=[remote_prefix],
        provider_ifaces=provider_ifaces,
        billing_clock=clock,
        on_sample=emit_sample,
    )

    # Traffic generator (iperf3)
    generator = TrafficGenerator(
        network=network,
        source="TinyInc",
        dest_ip=remote_loopback,
        baseline_mbps=args.baseline_mbps,
        spike_mbps=args.spike_mbps,
    )

    # Start everything
    generator.start_servers()
    time.sleep(1)  # Let servers initialise

    sampler.start()
    generator.start_flow()
    time.sleep(2)  # Let traffic establish before agents begin

    # ------------------------------------------------------------------
    # Reactors
    # ------------------------------------------------------------------
    step_hours = args.step_hours
    step_days = step_hours / 24.0
    max_iterations = round(args.days * 24.0 / step_hours)

    spike_events: list[tuple[int, int]] = sorted((round(s.time / step_hours), round((s.time + s.duration) / step_hours)) for s in args.spike_hours)
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
        # Let packets still queued on the previous route drain first (up to a link's delay,
        # 60 ms on Cheap); otherwise the first sample after a switch bills them to the old one.
        time.sleep(SAMPLE_SETTLE_SECONDS)
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
        clock.set_elapsed(start_day + step * step_days)

    extra_tools = [{**TRAFFIC_TOOL, "handler": lambda: sampler.measure_now()}]

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
            context_fns={node: sampler.measure_now for node in OBSERVING},
            events=events,
            system_prompts=load_system_prompts(args.system_prompts),
        )
        results = anet.run(concurrent=not args.sequential, end_run=False)

        # Capture the final step's routing state (step max_iterations-1)
        clock.set_elapsed(BILLING_DAYS)
        time.sleep(SAMPLE_SETTLE_SECONDS)
        final_elapsed_start = (max_iterations - 1) * step_days
        for i in range(samples_per_step):
            sampler.sample(elapsed_override=final_elapsed_start + i * sample_interval_days)
        events.run_end(anet.end_reason)  # after the last samples, which belong to the run

        # Results summary
        print("\n=== Agent Results ===")
        for name in network.hosts:
            r = results[name]
            status = "SUCCESS" if r.success else f"INCOMPLETE: {r.message}"
            print(f"  {name} [{status}]")

        # Collect routing state
        route_tables = collect_route_tables(network)

        bills = compute_bills(sampler.samples, remote_prefix, samples_per_step, args.sample_interval_minutes, start_day)
        logger.info("\n%s", bills)

        report_path = log_dir / f"{run_stem}.txt"
        routing_section = "\n".join(f"--- {n} ---\n{route_tables[n] or '(empty)'}" for n in sorted(route_tables))
        report_path.write_text(bills + "\n\n=== Routing Tables ===\n\n" + routing_section + "\n")
        logger.info("Report written to %s", report_path)

        # Agent self-reports
        agent_reports = {}
        if not args.no_reports:
            logger.info("Gathering agent self-reports...")
            agent_reports = anet.gather_reports()
        write_agent_reports(agent_reports, log_dir, run_stem, logger)
        generate_routes_pdf(network, route_tables, log_dir, run_stem, logger, show_delays=False)
        write_timeline_html(log_dir, run_stem, network.hosts, logger)

        # Final analysis report
        final_report_file = prompts_dir / "final-report.txt"
        if args.no_reports:
            logger.info("Skipping the reports (--no-reports).")
        elif final_report_file.exists():
            node_logs = collect_node_logs(log_dir, run_stem, network.hosts)
            write_final_report(
                model_key=args.report_model or args.model,
                vllm_host=args.vllm_host,
                vllm_port=args.vllm_port,
                max_tokens=args.max_tokens,
                final_prompt=final_report_file.read_text(),
                agent_reports=agent_reports,
                agent_results=results,
                node_logs=node_logs,
                route_tables=route_tables,
                log_dir=log_dir,
                run_stem=run_stem,
                logger=logger,
                extra_context=bills,
            )
        else:
            print("No final-report.txt found in prompts directory, skipping final report generation.")

        generator.stop()
        sampler.stop()
        network.stop()

    except Exception:
        events.run_end("error")
        raise
    finally:
        events.close()
        chown_to_user(log_dir)
        if args.events:
            chown_to_user(Path(args.events))

    # Save experiment data and generate throughput plot
    data_path = log_dir / f"{run_stem}-data.json"
    save_plot_data(
        samples=sampler.samples,
        baseline_mbps=args.baseline_mbps,
        spike_mbps=args.spike_mbps,
        spikes=args.spike_hours,
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

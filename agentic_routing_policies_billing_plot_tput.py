#!/usr/bin/env python3
"""Regenerate the throughput plot from a saved experiment data JSON."""

import argparse
import json
import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def generate_throughput_plot(data_path: Path, output_path: Path, logger: logging.Logger) -> None:
    data = json.loads(data_path.read_text())
    samples = data["samples"]
    p = data["params"]

    if not samples:
        logger.warning("No traffic samples in %s — skipping throughput plot", data_path)
        return

    baseline_mbps = p["baseline_mbps"]
    spike_mbps = p["spike_mbps"]
    total_days = p["total_days"]
    spike_hours: list[float] = p["spike_hours"]
    spike_duration_hours: float = p["spike_duration_hours"]
    step_hours: float = p.get("step_hours", 8.0)
    step_days = step_hours / 24.0
    # Use step-rounded boundaries so windows match the actual sample data.
    spike_windows = [
        (round(h / step_hours) * step_days,
         round((h + spike_duration_hours) / step_hours) * step_days)
        for h in sorted(spike_hours)
    ]

    times = [s["elapsed_days"] for s in samples]
    via_expensive = [sum(v.get("via_Expensive", 0.0) for v in s["mbps"].values()) for s in samples]
    via_cheap = [sum(v.get("via_Cheap", 0.0) for v in s["mbps"].values()) for s in samples]

    # Step function for background target across all spike windows
    bg_times = [0.0]
    bg_vals = [baseline_mbps]
    for spike_start, spike_end in spike_windows:
        bg_times += [spike_start, spike_start, spike_end, spike_end]
        bg_vals  += [baseline_mbps, spike_mbps, spike_mbps, baseline_mbps]
    bg_times.append(total_days)
    bg_vals.append(baseline_mbps)

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(bg_times, bg_vals, "k--", linewidth=1.5, alpha=0.5, label="Ingress traffic")
    ax.plot(times, via_expensive, "r-", linewidth=2, label="Via Expensive")
    ax.plot(times, via_cheap, "b-", linewidth=2, label="Via Cheap")
    for i, (spike_start, spike_end) in enumerate(spike_windows):
        ax.axvspan(spike_start, spike_end, alpha=0.08, color="orange", label="Spike window" if i == 0 else "")
    ax.set_xlabel("Elapsed simulated time (days)")
    ax.set_ylabel("Throughput (Mbps)")
    ax.set_title("ISP Traffic Routing Over Billing Period")
    ax.set_xlim(0, total_days)
    ax.set_ylim(bottom=0)
    ax.set_xticks(range(int(total_days) + 1))
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    logger.info("Throughput plot saved to %s", output_path)


def main():
    parser = argparse.ArgumentParser(description="Regenerate throughput plot from experiment data")
    parser.add_argument("data_json", metavar="DATA_JSON", help="Path to *-data.json file")
    parser.add_argument("--output", "-o", metavar="PNG", help="Output PNG path (default: same stem as data JSON)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logger = logging.getLogger(__name__)

    data_path = Path(args.data_json)
    if not data_path.exists():
        raise SystemExit(f"File not found: {data_path}")

    output_path = Path(args.output) if args.output else data_path.with_name(data_path.name.replace("-data.json", "-tput.png"))

    generate_throughput_plot(data_path, output_path, logger)


if __name__ == "__main__":
    main()

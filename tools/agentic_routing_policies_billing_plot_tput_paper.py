#!/usr/bin/env python3
"""Generate the paper-ready throughput figure from a saved experiment data JSON.

This is the paper variant of agentic_routing_policies_billing_plot_tput.py.
Differences from the working/diagnostic plot:
  - Vector PDF output by default (set --output *.png for a raster).
  - Serif fonts and print-friendly sizing to match a two-column paper (\\textwidth).
  - No embedded title (papers use \\caption instead).
  - Lighter grid, thinner lines, tighter margins.
Figure geometry is fixed at FIG_WIDTH x FIG_HEIGHT inches, sized for a
single-column figure in the two-column ACM sigconf layout. The PDF is written
next to this script (the tools/ directory) by default.
"""

import argparse
import io
import json
import logging
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Print-oriented style: serif to match LaTeX body text, compact type sizes.
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "axes.labelsize": 10,   # match the paper's 10pt body text for axis labels
    "axes.titlesize": 9,
    "legend.fontsize": 8,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "axes.linewidth": 0.6,
    "hatch.linewidth": 0.6,  # thin, crisp diagonal hatch on the Expensive band
    "pdf.fonttype": 42,   # embed TrueType so text stays selectable/searchable
    "ps.fonttype": 42,
})

# Match acmart's body font (Linux Libertine) so figure text renders at the same
# visual size and weight as the paper's 10pt body copy. matplotlib's built-in
# serif (DejaVu Serif) is heavier and looks oversized at an equal point size.
# If your document uses a different body font, change this package accordingly
# (e.g. r"\usepackage{lmodern}" for Latin Modern / Computer Modern).
LATEX_PREAMBLE = r"\usepackage[T1]{fontenc}\usepackage{libertine}"


def _enable_latex_fonts(logger: logging.Logger) -> bool:
    """Route figure text through LaTeX so it matches the paper's font exactly.

    Probes with a throwaway render; on any failure (no LaTeX toolchain, missing
    font package) it falls back to matplotlib's serif and warns rather than
    crashing at save time.
    """
    plt.rcParams["text.usetex"] = True
    plt.rcParams["text.latex.preamble"] = LATEX_PREAMBLE
    try:
        probe = plt.figure()
        probe.text(0.5, 0.5, "Throughput (Mbps)")
        probe.savefig(io.BytesIO(), format="pdf")
        plt.close(probe)
        return True
    except Exception as exc:  # LaTeX not installed, missing package, etc.
        plt.close("all")
        plt.rcParams["text.usetex"] = False
        plt.rcParams["text.latex.preamble"] = ""
        logger.warning(
            "LaTeX text rendering unavailable (%s); falling back to DejaVu Serif. "
            "Figure fonts will look heavier/larger than the paper body.", exc)
        return False

# Single-column figure geometry for the two-column ACM sigconf layout (inches).
FIG_WIDTH = 3.4
FIG_HEIGHT = 1.2

# Horizontal annotation placed in the empty area right of the transition guide
# line. Wrapped to NOTE_WRAP chars so it stays within the plot's right-hand gap.
NOTE_FONTSIZE = 7
NOTE_WRAP = 16

# Annotation baked into the paper figure: the day-8 Expensive->Cheap transition.
DEFAULT_NOTES: list[tuple[float, str]] = [
    (8.0, "Spike unusually long; conserve Expensive discard budget by routing remainder via Cheap."),
]


def generate_throughput_plot(
    data_path: Path,
    output_path: Path,
    logger: logging.Logger,
    notes: list[tuple[float, str]] | None = None,
    figsize: tuple[float, float] = (FIG_WIDTH, FIG_HEIGHT),
) -> None:
    data = json.loads(data_path.read_text())
    samples = data["samples"]
    p = data["params"]

    if not samples:
        logger.warning("No traffic samples in %s — skipping throughput plot", data_path)
        return

    _enable_latex_fonts(logger)

    baseline_mbps = p["baseline_mbps"]
    spike_mbps = p["spike_mbps"]
    total_days = p["total_days"]
    spikes: list[dict] = p["spikes"]
    step_hours: float = p.get("step_hours", 8.0)
    step_days = step_hours / 24.0
    # Use step-rounded boundaries so windows match the actual sample data.
    spike_windows = [
        (round(s["time"] / step_hours) * step_days,
         round((s["time"] + s["duration"]) / step_hours) * step_days)
        for s in sorted(spikes, key=lambda s: s["time"])
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

    fig, ax = plt.subplots(figsize=figsize)
    # At any instant all traffic flows through exactly ONE path (the other is zero) and the two
    # sum to the ingress, so the split is a composition — shown as stacked, filled bands rather
    # than overlapping lines. The bands are told apart by FILL TEXTURE (smooth vs. diagonal
    # hatch), not colour alone: that is what keeps each spike readable as Expensive-vs-Cheap in a
    # black & white print, where red and blue both collapse to the same grey but the hatch does
    # not. Ingress (dotted, high zorder) traces the top of the stack as the offered-load envelope.
    cheap_top = via_cheap
    stack_top = [c + e for c, e in zip(via_cheap, via_expensive)]
    ax.plot(bg_times, bg_vals, color="k", linewidth=1.0, zorder=5,
            linestyle=(0, (1, 4)), dash_capstyle="round", label="Ingress traffic")
    # Translucency is baked into the RGBA facecolor (not the alpha= kwarg, which would also dim
    # the hatch); the edgecolor/hatch then draw at full opacity so the diagonal pattern stays
    # crisp and clearly grey in a B&W print.
    # Light pastel fills that read as "translucent" over the white page — but kept OPAQUE, not
    # alpha-blended. An alpha-<1 fill wraps the collection in a PDF transparency group that many
    # viewers render *without* its hatch (which is why the hatch vanished in the earlier alpha
    # version); an opaque pastel of the same colour looks identical yet keeps the hatch. Expensive
    # carries dark-red diagonal hatching (also its black & white cue); Cheap is a plain light blue.
    ax.fill_between(times, cheap_top, stack_top, facecolor="#ffe0e0", edgecolor="red",
                    linewidth=0.6, hatch="/////", zorder=2, label="Via Expensive")
    ax.fill_between(times, 0, cheap_top, facecolor="#e3ecf9", edgecolor="blue",
                    linewidth=0.6, zorder=2, label="Via Cheap")
    ax.set_xlabel("Elapsed simulated time (days)")
    ax.set_ylabel("Throughput (Mbps)")
    ax.set_xlim(0, total_days)
    # Cap the top just above the spike level. Autoscale otherwise adds its default ~5% margin,
    # leaving a distracting empty band above the 500 Mbps line.
    ax.set_ylim(0, spike_mbps * 1.02)
    ax.set_xticks(range(int(total_days) + 1))
    ax.set_yticks(range(0, int(spike_mbps) + 1, 100))
    # Notes placed after the limits are fixed so they anchor to the final axes height. The text
    # sits over the light Cheap plateau, so grey text reads directly without a backing box.
    _, ymax = ax.get_ylim()
    for day, text in (notes or []):
        ax.axvline(day, color="gray", linewidth=0.8, linestyle=":")
        ax.text(day + 0.2, ymax * 0.96, textwrap.fill(text, width=NOTE_WRAP),
                va="top", ha="left", fontsize=NOTE_FONTSIZE, color="dimgray")
    # Compact single-row legend: the three short entries fit inline within the
    # 3.4in column, keeping the figure width axes-governed and the header shallow.
    ax.legend(frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.0),
              fontsize=9, handlelength=1.3, columnspacing=1.0, handletextpad=0.4,
              borderaxespad=0.3, borderpad=0.0)
    fig.savefig(output_path, dpi=300, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    logger.info("Throughput plot saved to %s", output_path)


def main():
    parser = argparse.ArgumentParser(description="Generate paper-ready throughput figure from experiment data")
    parser.add_argument("data_json", metavar="DATA_JSON", help="Path to *-data.json file")
    parser.add_argument("--output", "-o", metavar="OUT", help="Output path (default: <tools dir>/<stem>-tput-paper.pdf)")

    def note(s: str) -> tuple[float, str]:
        try:
            hour_str, text = s.split(":", 1)
            return float(hour_str) / 24.0, text
        except ValueError:
            raise argparse.ArgumentTypeError(f"Expected HOUR:TEXT, got {s!r}")

    parser.add_argument("--note", type=note, action="append", default=[], metavar="HOUR:TEXT",
                        help="Add an annotated marker at HOUR (elapsed hours, fractional allowed) with label TEXT")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    # Silence matplotlib/fontTools font-subsetting chatter on PDF export.
    logging.getLogger("fontTools").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logger = logging.getLogger(__name__)

    data_path = Path(args.data_json)
    if not data_path.exists():
        raise SystemExit(f"File not found: {data_path}")

    default_out = Path(__file__).resolve().parent / data_path.name.replace("-data.json", "-tput-paper.pdf")
    output_path = Path(args.output) if args.output else default_out

    generate_throughput_plot(data_path, output_path, logger, notes=DEFAULT_NOTES + args.note)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Process and plot the memory-intensive experiment results.

Read each stage's ZSim output, write a wide CSV, and create the staged
correction and memory-simulator portability figures.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Mapping


BENCHMARKS = ("ptr_chase", "stream-copy", "stream-scale", "stream-add", "stream-triad")
TRANSFERRED_BYTES = {
    "stream-copy": 160_000_000,
    "stream-scale": 160_000_000,
    "stream-add": 240_000_000,
    "stream-triad": 240_000_000,
}
ACTUAL_HARDWARE = {
    "ptr_chase": 88.99,
    "stream-copy": 68.29879985,
    "stream-scale": 67.7982022,
    "stream-add": 78.15367105,
    "stream-triad": 78.0468731,
}
PLOT_STAGES = (
    "01-baseline",
    "02-clock-scaling",
    "03-correct-freq",
    "04-memory-model",
    "05-address-mapping",
    "06-noc",
    "07-prefetcher",
)
PLOT_STAGE_LABELS = (
    ("Initial\nsimulation\ninfrastructure", "Figure 2"),
    ("Clock-scaling", "Figure 7"),
    ("FreqRatio rounding\nerror", "Figure 8"),
    ("Corrected\nmemory\nmodel", "Figure 6"),
    ("Corrected\naddress\nmapping", "Figure 9(a)"),
    ("Realistic\nnetwork on\nchip (NoC)", "Figure 9(b)"),
    ("Stride\nprefetchers\nin caches", "Figure 9(c)"),
)
PORTABILITY_STAGES = (
    ("07-prefetcher", "Ramulator"),
    ("08-ramulator2", "Ramulator2"),
    ("09-dramsim3", "DRAMsim3"),
    ("dramsys", "DRAMSys"),
)
DEFAULT_CSV_NAME = "mem_intensive.csv"
DEFAULT_FIGURE_NAME = "mem_intensive.pdf"
DEFAULT_PORTABILITY_FIGURE_NAME = "mem_intensive_portability.pdf"

FREQUENCY_RE = re.compile(r"^\s*frequency\s*=\s*([0-9]+(?:\.[0-9]+)?)\s*;")
CORE_RE = re.compile(r"^\s*[A-Za-z0-9_.-]+-(\d+):\s+# Core stats\s*$")
STAT_RE = re.compile(r"^\s*(cycles|instrs):\s*([0-9]+)\b")


def stage_sort_key(path: Path) -> tuple[int, int | str, str]:
    """Sort numbered stages numerically and named stages afterwards."""
    prefix = path.name.split("-", 1)[0]
    if prefix.isdigit():
        return (0, int(prefix), path.name)
    return (1, path.name, path.name)


def find_stages(experiment_dir: Path) -> List[Path]:
    """Return stage directories that contain all five benchmark outputs."""
    stages: List[Path] = []
    incomplete: List[str] = []
    for candidate in sorted(
        (path for path in experiment_dir.iterdir() if path.is_dir()),
        key=stage_sort_key,
    ):
        missing = [
            benchmark
            for benchmark in BENCHMARKS
            if not (candidate / benchmark / "zsim.out").is_file()
        ]
        if missing:
            # Ignore output folders, but report directories that look like stages.
            if (candidate / "runner.sh").is_file() or (candidate / "sb.cfg").is_file():
                incomplete.append(f"{candidate.name}: {', '.join(missing)}")
            continue
        stages.append(candidate)

    if incomplete:
        details = "; ".join(incomplete)
        raise ValueError(f"incomplete experiment stages ({details})")
    if not stages:
        raise ValueError(f"no complete stages found under {experiment_dir}")
    return stages


def parse_frequency_mhz(config_path: Path) -> float:
    """Read ZSim's CPU frequency, which is expressed in MHz."""
    with config_path.open("r", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            match = FREQUENCY_RE.match(line)
            if match:
                frequency_mhz = float(match.group(1))
                if frequency_mhz <= 0:
                    break
                return frequency_mhz
    raise ValueError(f"positive CPU frequency not found in {config_path}")


def parse_core_stats(stats_path: Path) -> Dict[int, Dict[str, int]]:
    """Extract the final per-core cycle and instruction counters."""
    core_stats: Dict[int, Dict[str, int]] = {}
    current_core: int | None = None

    with stats_path.open("r", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            core_match = CORE_RE.match(line)
            if core_match:
                current_core = int(core_match.group(1))
                core_stats.setdefault(current_core, {})
                continue

            if current_core is None:
                continue
            stat_match = STAT_RE.match(line)
            if stat_match:
                core_stats[current_core][stat_match.group(1)] = int(stat_match.group(2))

    complete = {
        core_id: values
        for core_id, values in core_stats.items()
        if "cycles" in values and "instrs" in values
    }
    if not complete:
        raise ValueError(f"no per-core cycle/instruction counters found in {stats_path}")
    return complete


def pointer_latency_ns(stage: Path) -> float:
    """Compute core-0 pointer-chase latency in ns per instruction."""
    benchmark_dir = stage / "ptr_chase"
    frequency_mhz = parse_frequency_mhz(benchmark_dir / "sb.cfg")
    stats = parse_core_stats(benchmark_dir / "zsim.out")
    if 0 not in stats:
        raise ValueError(f"core 0 stats missing in {benchmark_dir / 'zsim.out'}")

    cycles = stats[0]["cycles"]
    instructions = stats[0]["instrs"]
    if instructions <= 0:
        raise ValueError(f"core 0 instruction count is zero in {benchmark_dir / 'zsim.out'}")

    cycle_time_ns = 1000.0 / frequency_mhz
    return cycle_time_ns * cycles / instructions


def stream_bandwidth_gb_s(stage: Path, benchmark: str) -> float:
    """Compute application bandwidth using the slowest core's elapsed cycles."""
    benchmark_dir = stage / benchmark
    frequency_mhz = parse_frequency_mhz(benchmark_dir / "sb.cfg")
    stats = parse_core_stats(benchmark_dir / "zsim.out")
    active_cycles = [
        values["cycles"]
        for values in stats.values()
        if values["instrs"] > 0 and values["cycles"] > 0
    ]
    if not active_cycles:
        raise ValueError(f"no active cores found in {benchmark_dir / 'zsim.out'}")

    elapsed_cycles = max(active_cycles)
    elapsed_seconds = elapsed_cycles / (frequency_mhz * 1_000_000.0)
    return TRANSFERRED_BYTES[benchmark] / elapsed_seconds / 1_000_000_000.0


def extract_rows(stages: Iterable[Path]) -> List[Dict[str, str | float | int]]:
    """Calculate the five requested measurements for every stage."""
    stage_list = list(stages)
    rows: List[Dict[str, str | float | int]] = []

    latency_row: Dict[str, str | float | int] = {
        "benchmark": "ptr_chase",
        "metric": "latency",
        "unit": "ns/instruction",
        "transferred_bytes": "",
        "actual-hardware": ACTUAL_HARDWARE["ptr_chase"],
    }
    for stage in stage_list:
        latency_row[stage.name] = pointer_latency_ns(stage)
    rows.append(latency_row)

    for benchmark in BENCHMARKS[1:]:
        bandwidth_row: Dict[str, str | float | int] = {
            "benchmark": benchmark,
            "metric": "bandwidth",
            "unit": "GB/s",
            "transferred_bytes": TRANSFERRED_BYTES[benchmark],
            "actual-hardware": ACTUAL_HARDWARE[benchmark],
        }
        for stage in stage_list:
            bandwidth_row[stage.name] = stream_bandwidth_gb_s(stage, benchmark)
        rows.append(bandwidth_row)
    return rows


def write_csv(csv_path: Path, stages: Iterable[Path], rows: Iterable[Mapping[str, object]]) -> None:
    """Write a wide CSV with one result column per simulator stage."""
    stage_names = [stage.name for stage in stages]
    value_columns = ["actual-hardware", *stage_names]
    fieldnames = ["benchmark", "metric", "unit", "transferred_bytes", *value_columns]
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            formatted = dict(row)
            for column in value_columns:
                formatted[column] = f"{float(row[column]):.8f}"
            writer.writerow(formatted)


def read_csv(csv_path: Path) -> tuple[List[str], Dict[str, Dict[str, float]]]:
    """Read and validate the processed CSV for plotting."""
    with csv_path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        fixed_columns = {"benchmark", "metric", "unit", "transferred_bytes"}
        if reader.fieldnames is None or not fixed_columns.issubset(reader.fieldnames):
            raise ValueError(f"{csv_path} does not have the expected columns")
        stage_names = [name for name in reader.fieldnames if name not in fixed_columns]
        if not stage_names:
            raise ValueError(f"{csv_path} has no stage columns")

        values: Dict[str, Dict[str, float]] = {}
        for row in reader:
            benchmark = row["benchmark"]
            values[benchmark] = {stage: float(row[stage]) for stage in stage_names}

    missing = [benchmark for benchmark in BENCHMARKS if benchmark not in values]
    if missing:
        raise ValueError(f"{csv_path} is missing benchmarks: {', '.join(missing)}")
    return stage_names, values


def create_plot(csv_path: Path, figure_path: Path) -> None:
    """Plot simulated-vs-hardware differences in the paper-reference style."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as error:
        raise RuntimeError("plotting requires matplotlib") from error

    csv_columns, values = read_csv(csv_path)
    if "actual-hardware" not in csv_columns:
        raise ValueError(f"{csv_path} has no actual-hardware column")
    missing_stages = [stage for stage in PLOT_STAGES if stage not in csv_columns]
    if missing_stages:
        raise ValueError(f"{csv_path} is missing plot stages: {', '.join(missing_stages)}")

    benchmarks = ("stream-copy", "stream-scale", "stream-add", "stream-triad", "ptr_chase")
    legend_labels = ("STREAM-Copy", "STREAM-Scale", "STREAM-Add", "STREAM-Triad", "Pointer-chase")
    colors = ("#e8eef5", "#b8c9dd", "#75a7c7", "#2d86b1", "#00618e")
    group_centers = list(range(len(PLOT_STAGES)))
    bar_width = 0.155

    figure, axis = plt.subplots(figsize=(16.48, 3.23))
    figure.subplots_adjust(left=0.076, right=0.868, top=0.70, bottom=0.37)

    for benchmark_index, (benchmark, legend_label, color) in enumerate(
        zip(benchmarks, legend_labels, colors)
    ):
        hardware_value = values[benchmark]["actual-hardware"]
        offsets = [
            center + (benchmark_index - (len(benchmarks) - 1) / 2) * bar_width
            for center in group_centers
        ]
        differences = [
            (values[benchmark][stage] / hardware_value - 1.0) * 100.0
            for stage in PLOT_STAGES
        ]
        bars = axis.bar(
            offsets,
            differences,
            width=bar_width,
            label=legend_label,
            color=color,
            edgecolor="black",
            linewidth=0.55,
            zorder=3,
        )
        for bar, difference in zip(bars, differences):
            rounded = int(round(difference))
            y_position = difference + 4 if difference >= 0 else difference - 4
            axis.text(
                bar.get_x() + bar.get_width() / 2,
                y_position,
                f"{rounded}%",
                ha="center",
                va="bottom" if difference >= 0 else "top",
                rotation=90,
                fontsize=10.5,
                fontweight="bold",
                clip_on=False,
            )

    axis.set_xlim(-0.68, len(PLOT_STAGES) - 0.05)
    axis.set_ylim(-88, 100)
    axis.set_yticks((-80, -40, 0, 40, 80), labels=("-80%", "-40%", "0%", "40%", "80%"))
    axis.tick_params(axis="y", labelsize=11, width=0)
    for tick_label in axis.get_yticklabels():
        tick_label.set_fontweight("bold")
    axis.set_ylabel(
        "Actual vs. Simulated\nPerformance [%]",
        fontsize=11.5,
        fontweight="bold",
        labelpad=8,
    )
    axis.set_xticks([])
    axis.grid(axis="y", color="#d5d5d5", linestyle=(0, (4, 3)), linewidth=0.8, zorder=0)
    axis.axhline(0, color="black", linestyle=(0, (1, 2)), linewidth=0.8, zorder=4)
    for spine in axis.spines.values():
        spine.set_visible(False)

    legend = axis.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, 1.42),
        ncols=5,
        frameon=False,
        fontsize=13.5,
        handlelength=0.58,
        handleheight=0.58,
        handletextpad=0.35,
        columnspacing=2.2,
        borderaxespad=0,
    )
    for text in legend.get_texts():
        text.set_fontweight("bold")

    for center, (stage_label, figure_label) in zip(group_centers, PLOT_STAGE_LABELS):
        stage_line_count = stage_label.count("\n") + 1
        axis.text(
            center,
            -0.16,
            stage_label,
            transform=axis.get_xaxis_transform(),
            ha="center",
            va="top",
            fontsize=11.5,
            fontweight="bold",
            linespacing=1.0,
            clip_on=False,
        )
        axis.text(
            center,
            -0.16 - 0.18 * stage_line_count,
            figure_label,
            transform=axis.get_xaxis_transform(),
            ha="center",
            va="top",
            fontsize=10.5,
            fontstyle="italic",
            clip_on=False,
        )

    bracket_y = -0.70
    bracket_left = group_centers[2] - 0.45
    bracket_right = group_centers[3] + 0.45
    axis.plot(
        (bracket_left, bracket_right),
        (bracket_y, bracket_y),
        transform=axis.get_xaxis_transform(),
        color="black",
        linewidth=0.75,
        linestyle=(0, (2, 2)),
        clip_on=False,
    )
    axis.plot(
        (bracket_left, bracket_left),
        (bracket_y, bracket_y + 0.035),
        transform=axis.get_xaxis_transform(),
        color="black",
        linewidth=0.75,
        clip_on=False,
    )
    axis.plot(
        (bracket_right, bracket_right),
        (bracket_y, bracket_y + 0.035),
        transform=axis.get_xaxis_transform(),
        color="black",
        linewidth=0.75,
        clip_on=False,
    )
    axis.text(
        (bracket_left + bracket_right) / 2,
        bracket_y - 0.035,
        "Time-domain consistency",
        transform=axis.get_xaxis_transform(),
        ha="center",
        va="top",
        fontsize=11.5,
        fontweight="bold",
        clip_on=False,
    )

    axis.text(
        1.025,
        0.66,
        "Higher simulated\nbandwidth and latency",
        transform=axis.transAxes,
        ha="center",
        va="center",
        fontsize=11.5,
        fontweight="bold",
        clip_on=False,
    )
    axis.text(
        1.025,
        0.17,
        "Lower simulated\nbandwidth and latency",
        transform=axis.transAxes,
        ha="center",
        va="center",
        fontsize=11.5,
        fontweight="bold",
        clip_on=False,
    )

    figure_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(figure_path, dpi=300, facecolor="white")
    plt.close(figure)


def create_portability_plot(csv_path: Path, figure_path: Path) -> None:
    """Plot the four memory simulators in the second reference style."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as error:
        raise RuntimeError("plotting requires matplotlib") from error

    csv_columns, values = read_csv(csv_path)
    if "actual-hardware" not in csv_columns:
        raise ValueError(f"{csv_path} has no actual-hardware column")
    missing_stages = [
        stage for stage, _ in PORTABILITY_STAGES if stage not in csv_columns
    ]
    if missing_stages:
        raise ValueError(
            f"{csv_path} is missing portability stages: {', '.join(missing_stages)}"
        )

    benchmarks = ("stream-copy", "stream-scale", "stream-add", "stream-triad", "ptr_chase")
    legend_labels = ("STREAM-Copy", "STREAM-Scale", "STREAM-Add", "STREAM-Triad", "Pointer-chase")
    colors = ("#e8eef5", "#b8c9dd", "#75a7c7", "#2d86b1", "#00618e")
    group_centers = list(range(len(PORTABILITY_STAGES)))
    bar_width = 0.16

    figure, axis = plt.subplots(figsize=(11.05, 2.29))
    figure.subplots_adjust(left=0.11, right=0.995, top=0.68, bottom=0.22)

    for benchmark_index, (benchmark, legend_label, color) in enumerate(
        zip(benchmarks, legend_labels, colors)
    ):
        hardware_value = values[benchmark]["actual-hardware"]
        offsets = [
            center + (benchmark_index - (len(benchmarks) - 1) / 2) * bar_width
            for center in group_centers
        ]
        differences = [
            (values[benchmark][stage] / hardware_value - 1.0) * 100.0
            for stage, _ in PORTABILITY_STAGES
        ]
        bars = axis.bar(
            offsets,
            differences,
            width=bar_width,
            label=legend_label,
            color=color,
            edgecolor="black",
            linewidth=0.55,
            zorder=3,
        )
        for bar, difference in zip(bars, differences):
            rounded = int(round(difference))
            nonnegative_label = rounded >= 0
            y_position = difference + 1.0 if nonnegative_label else difference - 1.0
            axis.text(
                bar.get_x() + bar.get_width() / 2,
                y_position,
                f"{rounded}%",
                ha="center",
                va="bottom" if nonnegative_label else "top",
                fontsize=10.5,
                fontweight="bold",
                clip_on=False,
            )

    axis.set_xlim(-0.52, len(PORTABILITY_STAGES) - 0.48)
    axis.set_ylim(-22, 4)
    axis.set_yticks((-20, -10, 0), labels=("-20%", "-10%", "0%"))
    axis.tick_params(axis="y", labelsize=10.5, width=0)
    axis.tick_params(axis="x", length=0, pad=7)
    for tick_label in axis.get_yticklabels():
        tick_label.set_fontweight("bold")
    axis.set_xticks(
        group_centers,
        labels=[display_name for _, display_name in PORTABILITY_STAGES],
        fontsize=11.5,
        fontweight="bold",
    )
    axis.set_ylabel(
        "Actual vs. Simulated\nperformance [%]",
        fontsize=11.5,
        fontweight="bold",
        labelpad=7,
    )
    axis.grid(axis="y", color="#d5d5d5", linestyle=(0, (4, 3)), linewidth=0.8, zorder=0)
    axis.axhline(0, color="#bdbdbd", linewidth=0.8, zorder=2)
    for spine in axis.spines.values():
        spine.set_visible(False)

    legend = axis.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, 1.39),
        ncols=5,
        frameon=False,
        fontsize=12.5,
        handlelength=0.58,
        handleheight=0.58,
        handletextpad=0.28,
        columnspacing=0.85,
        borderaxespad=0,
    )
    for text in legend.get_texts():
        text.set_fontweight("bold")

    figure_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(figure_path, dpi=300, facecolor="white")
    plt.close(figure)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract and plot experiment 11 latency/bandwidth results."
    )
    parser.add_argument(
        "--experiment-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Experiment 11 directory (default: directory containing this script).",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        help="CSV path (default: <experiment-dir>/processed/mem_intensive.csv).",
    )
    parser.add_argument(
        "--figure",
        type=Path,
        help="Stage-correction figure path (default: <experiment-dir>/figures/mem_intensive.pdf).",
    )
    parser.add_argument(
        "--portability-figure",
        type=Path,
        help="Portability figure path (default: <experiment-dir>/figures/mem_intensive_portability.pdf).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    experiment_dir = args.experiment_dir.resolve()
    csv_path = (args.csv or experiment_dir / "processed" / DEFAULT_CSV_NAME).resolve()
    figure_path = (args.figure or experiment_dir / "figures" / DEFAULT_FIGURE_NAME).resolve()
    portability_figure_path = (
        args.portability_figure
        or experiment_dir / "figures" / DEFAULT_PORTABILITY_FIGURE_NAME
    ).resolve()

    try:
        stages = find_stages(experiment_dir)
        rows = extract_rows(stages)
        write_csv(csv_path, stages, rows)
        print(f"Wrote processed CSV to {csv_path}")

        create_plot(csv_path, figure_path)
        print(f"Wrote figure to {figure_path}")
        create_portability_plot(csv_path, portability_figure_path)
        print(f"Wrote portability figure to {portability_figure_path}")
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


KEY_FIELDS = ("type", "rd_percentage", "pause")
STATIC_CONFIG = {
    "MEM_FREQ": "1.3333333",
    "MEM_MAX_CHANNELS": "6",
    "PLOT_MAX_BW_LABEL_Y": "211",
}

VIEW_SPECS = {
    "core": {
        "aliases": {"core", "application", "app", "zsim-core"},
        "bandwidth_field": "bandwidth_bytes_per_second",
        "latency_field": "latency_core_ptr_chase",
        "label": "Application view",
        "color": "#d62728",
        "cmap": "Reds",
        "linestyle": "-",
    },
    "interface": {
        "aliases": {"interface", "mem", "memory-interface", "zsim-mem"},
        "bandwidth_field": "bandwidth_bytes_per_second",
        "latency_field": "latency_mem_ptr_chase",
        "label": "Memory-interface view",
        "color": "#1f77b4",
        "cmap": "Blues",
        "linestyle": "-",
    },
    "mem-sim": {
        "aliases": {"simulator", "mem-sim", "ramulator", "memory-simulator", "ram"},
        "bandwidth_field": "bandwidth_ram",
        "latency_field": "latency_mem_ptr_chase_ram",
        "label": "Memory simulator view",
        "color": "#2ca02c",
        "cmap": "Greens",
        "linestyle": ":",
    },
}


def resolve_csv(arg: str, repo_root: Path) -> Path:
    candidate = Path(arg)
    if candidate.is_file():
        return candidate.resolve()

    exp_dir = repo_root / "experiments" / arg
    for csv_path in (
        exp_dir / "processed" / "bandwidth_latency.csv",
        exp_dir / "figures" / "bandwidth_latency.csv",
        exp_dir / "results" / "processed" / "bandwidth_latency.csv",
    ):
        if csv_path.is_file():
            return csv_path

    raise FileNotFoundError(f"unable to resolve CSV for '{arg}'")


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def resolve_output_path(
    source_arg: str,
    csv_path: Path,
    repo_root: Path,
    lhs_view: str,
    rhs_view: str,
) -> Path:
    filename = f"bandwidth_latency_{lhs_view}_vs_{rhs_view}.png"

    if not Path(source_arg).is_file():
        return repo_root / "experiments" / source_arg / "figures" / filename

    csv_parts = csv_path.resolve().parts
    repo_parts = repo_root.resolve().parts
    exp_prefix = repo_parts + ("experiments",)
    if csv_parts[: len(exp_prefix)] == exp_prefix and len(csv_parts) >= len(exp_prefix) + 2:
        experiment_dir = Path(*csv_parts[: len(exp_prefix) + 1])
        return experiment_dir / "figures" / filename

    experiment_name = csv_path.parent.parent.name
    return repo_root / "test-output" / "compare-views" / f"{experiment_name}_{lhs_view}_vs_{rhs_view}.png"


def normalize_view(name: str) -> str:
    lowered = name.strip().lower()
    for canonical, spec in VIEW_SPECS.items():
        if lowered == canonical or lowered in spec["aliases"]:
            return canonical
    known = ", ".join(sorted(VIEW_SPECS))
    raise ValueError(f"unknown view '{name}'. expected one of: {known}")


def row_key(row: dict[str, str]) -> tuple[str, str, str]:
    return tuple(row.get(field, "") for field in KEY_FIELDS)


def cfg_int(config: dict[str, str], key: str) -> int:
    return int(str(config[key]).strip().strip('"'))


def cfg_float(config: dict[str, str], key: str) -> float:
    return float(str(config[key]).strip().strip('"'))


def calculate_color(rd_value: int, cmap_name: str = "Blues"):
    try:
        cmap = matplotlib.colormaps.get_cmap(cmap_name)
    except AttributeError:
        cmap = matplotlib.cm.get_cmap(cmap_name)

    min_value = 0.2
    max_value = 1.0
    factor = (100.0 - 0.0) / (max_value - min_value)
    rw_reverse = 75.0 + 75.0 - rd_value
    c = (rw_reverse - 50.0) / factor + min_value
    return cmap(c)


def view_color(rd_value: int, view_name: str):
    return calculate_color(rd_value, VIEW_SPECS[view_name]["cmap"])


def view_points(
    rows: list[dict[str, str]],
    view_name: str,
) -> tuple[list[dict[str, str]], list[tuple[tuple[str, str, str], float, float]]]:
    spec = VIEW_SPECS[view_name]
    bw_field = spec["bandwidth_field"]
    lat_field = spec["latency_field"]
    valid_rows: list[dict[str, str]] = []
    points: list[tuple[tuple[str, str, str], float, float]] = []
    for row in rows:
        try:
            bw = float(row[bw_field])
            lat = float(row[lat_field])
        except (KeyError, ValueError):
            continue
        valid_rows.append(row)
        points.append((row_key(row), bw, lat))
    return valid_rows, points


def fmt_bw_delta(value: float) -> str:
    return f"{value / 1e9:+.3f} GB/s"


def fmt_lat_delta(value: float) -> str:
    return f"{value:+.3f} ns"


def print_summary(
    csv_path: Path,
    experiment_name: str,
    lhs_view: str,
    rhs_view: str,
    lhs_points: list[tuple[tuple[str, str, str], float, float]],
    rhs_points: list[tuple[tuple[str, str, str], float, float]],
) -> None:
    lhs_map = {key: (bw, lat) for key, bw, lat in lhs_points}
    rhs_map = {key: (bw, lat) for key, bw, lat in rhs_points}
    shared_keys = sorted(set(lhs_map) & set(rhs_map))

    bw_deltas: list[float] = []
    lat_deltas: list[float] = []
    for key in shared_keys:
        lhs_bw, lhs_lat = lhs_map[key]
        rhs_bw, rhs_lat = rhs_map[key]
        bw_deltas.append(lhs_bw - rhs_bw)
        lat_deltas.append(lhs_lat - rhs_lat)

    lhs_label = VIEW_SPECS[lhs_view]["label"]
    rhs_label = VIEW_SPECS[rhs_view]["label"]

    sep = "─" * 72
    print()
    print(sep)
    print("  VIEW COMPARISON SUMMARY")
    print(sep)
    print(f"  Experiment            {experiment_name}")
    print(f"  CSV                   {csv_path}")
    print(f"  A  (lhs view)         {lhs_label}")
    print(f"  B  (rhs view)         {rhs_label}")
    print(sep)
    print(f"  {'Rows in A':<22} {len(lhs_points)}")
    print(f"  {'Rows in B':<22} {len(rhs_points)}")
    print(f"  {'Shared rows':<22} {len(shared_keys)}")
    print(sep)

    if not shared_keys:
        print("  No shared numeric rows were found for the selected views.")
        print(sep)
        print()
        return

    def summarize(values: list[float]) -> tuple[float, float, float]:
        mean_signed = sum(values) / len(values)
        mean_abs = sum(abs(v) for v in values) / len(values)
        max_abs = max(abs(v) for v in values)
        return mean_signed, mean_abs, max_abs

    bw_mean, bw_abs_mean, bw_abs_max = summarize(bw_deltas)
    lat_mean, lat_abs_mean, lat_abs_max = summarize(lat_deltas)

    print(f"  {'Bandwidth Δ (A−B)':<22} mean {fmt_bw_delta(bw_mean)}   mean|Δ| {fmt_bw_delta(bw_abs_mean)}   max|Δ| {fmt_bw_delta(bw_abs_max)}")
    print(f"  {'Latency Δ (A−B)':<22} mean {fmt_lat_delta(lat_mean)}   mean|Δ| {fmt_lat_delta(lat_abs_mean)}   max|Δ| {fmt_lat_delta(lat_abs_max)}")
    print(sep)
    print()


def curves_by_rd(
    rows: list[dict[str, str]],
    view_name: str,
) -> dict[int, tuple[list[float], list[float]]]:
    spec = VIEW_SPECS[view_name]
    bw_field = spec["bandwidth_field"]
    lat_field = spec["latency_field"]
    buckets: dict[int, list[tuple[float, float, float]]] = defaultdict(list)
    for row in rows:
        try:
            rd = int(float(row["rd_percentage"]))
            pause = float(row["pause"])
            bw = float(row[bw_field]) / 1e9
            lat = float(row[lat_field])
        except (KeyError, ValueError):
            continue
        buckets[rd].append((pause, bw, lat))

    result: dict[int, tuple[list[float], list[float]]] = {}
    for rd, points in sorted(buckets.items()):
        points.sort(key=lambda item: item[0])
        result[rd] = ([item[1] for item in points], [item[2] for item in points])
    return result


def make_plot(
    rows: list[dict[str, str]],
    experiment_name: str,
    lhs_view: str,
    rhs_view: str,
    output_path: Path,
) -> None:
    lhs_spec = VIEW_SPECS[lhs_view]
    rhs_spec = VIEW_SPECS[rhs_view]
    lhs_curves = curves_by_rd(rows, lhs_view)
    rhs_curves = curves_by_rd(rows, rhs_view)

    if not lhs_curves and not rhs_curves:
        return

    plt.rcParams["font.size"] = 38
    fig, ax = plt.subplots(figsize=(16, 9))
    max_bw = cfg_int(STATIC_CONFIG, "MEM_MAX_CHANNELS") * 8 * (2 * cfg_float(STATIC_CONFIG, "MEM_FREQ"))
    plotted_lhs = False
    plotted_rhs = False
    all_rds = sorted(set(lhs_curves) | set(rhs_curves))
    lhs_min_lat = float("inf")

    lhs_min_bw = None

    rhs_min_lat = float("inf")
    rhs_min_bw = None

    for rd in all_rds:
        if rd in lhs_curves:
            bws, lats = lhs_curves[rd]

            ax.plot(
                bws,
                lats,
                color=view_color(rd, lhs_view),
                linestyle=lhs_spec["linestyle"],
                linewidth=1.0,
                marker=None,
                label=lhs_spec["label"] if not plotted_lhs else "_nolegend_",
            )

            # NEW
            unloaded_bw = min(bws)
            unloaded_lat = lats[bws.index(unloaded_bw)]

            if unloaded_lat < lhs_min_lat:
                lhs_min_lat = unloaded_lat
                lhs_min_bw = unloaded_bw

            plotted_lhs = True

        if rd in rhs_curves:
            bws, lats = rhs_curves[rd]

            ax.plot(
                bws,
                lats,
                color=view_color(rd, rhs_view),
                linestyle=rhs_spec["linestyle"],
                linewidth=1.0,
                marker=None,
                label=rhs_spec["label"] if not plotted_rhs else "_nolegend_",
            )

            # NEW
            unloaded_bw = min(bws)
            unloaded_lat = lats[bws.index(unloaded_bw)]

            if unloaded_lat < rhs_min_lat:
                rhs_min_lat = unloaded_lat
                rhs_min_bw = unloaded_bw

            plotted_rhs = True
        

    # Print lhs minimum unloaded latency
    ax.text(
        lhs_min_bw + 1,
        lhs_min_lat + 3,
        f"{int(round(lhs_min_lat))} ns",
        fontsize=38,
        color="black",
        ha="left",
        va="bottom",
    )

    # Print rhs minimum unloaded latency
    ax.text(
        rhs_min_bw + 1,
        rhs_min_lat + 3,
        f"{int(round(rhs_min_lat))} ns",
        fontsize=38,
        color="black",
        ha="left",
        va="bottom",
    )

    ax.axvline(x=max_bw, color=calculate_color(75), linewidth=4, linestyle=":")
    ax.text(
        max_bw,
        cfg_float(STATIC_CONFIG, "PLOT_MAX_BW_LABEL_Y"),
        f"Max. theoretical BW = {round(max_bw)} GB/s",
        color="black",
        horizontalalignment="right",
        fontsize=36,
    )
    ax.set_xlim(0, max_bw*1.05)
    ax.set_ylim(0, 230)
    ax.set_xlabel("Used Memory bandwidth [GB/s]", fontsize=38)
    ax.set_ylabel("Memory access latency [ns]", fontsize=38)
    ax.tick_params(axis="x", labelsize=38)
    ax.tick_params(axis="y", labelsize=38)
    
    legend_rd = 30
    legend_handles = [
        Line2D([0], [0], color=view_color(legend_rd, rhs_view), linewidth=2.8, linestyle="-", label=rhs_spec["label"]),
        Line2D([0], [0], color=view_color(legend_rd, lhs_view), linewidth=2.8, linestyle="-", label=lhs_spec["label"]),
    ]

    ax.legend(
        handles=legend_handles,
        fontsize=34,
        loc="lower center",
        bbox_to_anchor=(0.5, 1),
        ncol=2,
        frameon=False,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.subplots_adjust(top=0.88) # we add a bit of room on top
    fig.tight_layout()
    fig.savefig(output_path, dpi=600)
    pdf_path = output_path.with_suffix(".pdf")
    fig.savefig(pdf_path, dpi=150)
    plt.close(fig)

    print(f"  Plot saved → {output_path}")
    print(f"  Plot saved → {pdf_path}")
    print()


def main() -> int:
    if len(sys.argv) not in (2, 4):
        print(
            "usage: compare-views.sh <experiment-or-csv> [<lhs-view> <rhs-view>]\n"
            "example: compare-views.sh 04-memory-model core interface",
            file=sys.stderr,
        )
        return 1

    repo_root = Path(__file__).resolve().parent.parent.parent
    source_arg = sys.argv[1]
    lhs_view = normalize_view(sys.argv[2]) if len(sys.argv) == 4 else "core"
    rhs_view = normalize_view(sys.argv[3]) if len(sys.argv) == 4 else "interface"

    if lhs_view == rhs_view:
        print("lhs-view and rhs-view must be different", file=sys.stderr)
        return 1

    csv_path = resolve_csv(source_arg, repo_root)
    rows = load_rows(csv_path)
    experiment_name = source_arg if not Path(source_arg).is_file() else csv_path.parent.parent.name

    lhs_rows, lhs_points = view_points(rows, lhs_view)
    rhs_rows, rhs_points = view_points(rows, rhs_view)

    if not lhs_points:
        print(f"no valid rows found for view '{lhs_view}' in {csv_path}", file=sys.stderr)
        return 1
    if not rhs_points:
        print(f"no valid rows found for view '{rhs_view}' in {csv_path}", file=sys.stderr)
        return 1

    print_summary(csv_path, experiment_name, lhs_view, rhs_view, lhs_points, rhs_points)

    output_path = resolve_output_path(source_arg, csv_path, repo_root, lhs_view, rhs_view)
    make_plot(rows, experiment_name, lhs_view, rhs_view, output_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

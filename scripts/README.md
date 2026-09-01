# Scripts Overview

This directory contains repository-level automation helpers. Experiment execution entrypoints (`runner.sh`, `run-one.sh`, `plot.py`) are kept under `experiments/` by design.

## Available Scripts

### `../setup.sh` (repo root)
Primary one-shot entrypoint for first-time setup and rebuilds. It wraps dependency checks, environment generation, simulator builds, and benchmark builds.

```bash
./setup.sh
# or
./setup.sh --rebuild
```

### `setup-env.sh`
Generates the `.zsim-env` file at the repository root. The four memory-simulator paths (`DRAMSIM3PATH`, `RAMULATORPATH`, `RAMULATOR2PATH`, `DRAMSYSPATH`) come from this repository. The script searches for Pin 2.14 and HDF5 and downloads the pinned bundles into `dependencies/` when it cannot find them.

```bash
./scripts/setup-env.sh
source .zsim-env
```

This must be run once before building ZSim or running any experiment. See [`simulator-source/README.md`](../simulator-source/README.md) for dependency details.

### `build-benchmarks.sh`
Compiles the shared `ptr_chase` and `traffic_gen` benchmarks and the STREAM
Copy, Scale, Add, and Triad workloads under `benchmarks/`. This must be run
before any experiment can execute.

This script is intended for the Linux environment used in the paper artifact. In particular, `ptr_chase` depends on `linux/perf_event.h`.

```bash
./scripts/build-benchmarks.sh
```

### `compare-results.sh`
Compares two experiment stages by analyzing their `processed/bandwidth_latency.csv` outputs side by side. Useful for quantifying the performance delta introduced by each interface correction.
The summary reports mean, mean-absolute, and maximum-absolute deltas in both native units and percentages. Percentage deltas use the right-hand dataset as the per-row reference: `(A - B) / B * 100`.

```bash
./scripts/compare-results.sh <stage-a> <stage-b>
# Example:
./scripts/compare-results.sh 01-baseline 04-memory-model
```

### `download-raw.sh`
Consumes a `raw-manifest.csv` when a stage provides one. The current artifact
links its published archives from the [raw-results table](../README.md#51-raw-results)
instead of shipping manifests, so this helper is not part of the standard run
workflow.

```bash
./scripts/download-raw.sh <stage>
# Example:
./scripts/download-raw.sh 01-baseline
```

Internal helper:
- `lib/compare_results.py` — implementation used by `compare-results.sh`

## Typical Workflow

**First time — build everything:**
```bash
./setup.sh
```

**Run a single stage and plot it:**
```bash
source .zsim-env
./experiments/runner.sh 01-baseline
./experiments/plot.py experiments/01-baseline/test-raw \
  --config-dir experiments/01-baseline
# → figures land in test-output/01-baseline/figures/
```

**Compare two stages** (works against committed CSVs or freshly generated ones):
```bash
./scripts/compare-results.sh 01-baseline 04-memory-model
```

-> *For details on `runner.sh`, `run-one.sh`, and the plotting pipeline see [`experiments/README.md`](../experiments/README.md).*

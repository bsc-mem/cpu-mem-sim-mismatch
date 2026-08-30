#!/usr/bin/env bash
set -euo pipefail

# Shared local runner for the staged experiments.
# It expands the configured sweep and executes each point sequentially on the
# current machine. If needed, it can also materialize per-run directories for a
# generic batch scheduler, but the public artifact workflow is local and
# sequential.

SCRIPT_REAL="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_REAL")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
BENCH_ROOT="$REPO_ROOT/benchmarks"
DAMOV_RUNNER="$SCRIPT_DIR/00-damov-native/scripts/runner.sh"
MEM_INTENSIVE_RUNNER="$SCRIPT_DIR/11-mem-intensive/runner.sh"

export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

run_damov_native_runner() {
  if [[ ! -f "$DAMOV_RUNNER" ]]; then
    echo "Missing 00-damov-native runner at: $DAMOV_RUNNER" >&2
    exit 1
  fi

  if [[ "$EUID" -ne 0 ]]; then
    echo "00-damov-native selected by user '$(id -un)' without root permission." >&2
    echo "This experiment can be executed with root permission (for DAMOV setup/build)." >&2
    exit 1
  fi

  exec bash "$DAMOV_RUNNER" "$@"
}

run_mem_intensive_runner() {
  if [[ ! -f "$MEM_INTENSIVE_RUNNER" ]]; then
    echo "Missing 11-mem-intensive runner at: $MEM_INTENSIVE_RUNNER" >&2
    exit 1
  fi

  exec bash "$MEM_INTENSIVE_RUNNER" "$@"
}

resolve_experiment_dir() {
  local input="${1:-}"

  if [[ -n "$input" && -d "$SCRIPT_DIR/$input" ]]; then
    printf '%s\n' "$SCRIPT_DIR/$input"
    return 0
  fi

  if [[ -f "$(pwd -P)/sb.cfg" || -f "$(pwd -P)/configs/system.cfg" ]]; then
    printf '%s\n' "$(pwd -P)"
    return 0
  fi

  echo "usage: $0 <experiment-id> [--print-zsim|--print-plan]" >&2
  echo "or run it from inside one experiment directory." >&2
  exit 1
}

if [[ "${1:-}" == "00" || "${1:-}" == "00-damov-native" ]]; then
  run_damov_native_runner "${@:2}"
fi
if [[ "${1:-}" == "11" || "${1:-}" == "11-mem-intensive" ]]; then
  run_mem_intensive_runner "${@:2}"
fi

resolve_config_path() {
  local exp_dir="$1"

  if [[ -f "$exp_dir/sb.cfg" ]]; then
    printf '%s\n' "$exp_dir/sb.cfg"
    return 0
  fi

  if [[ -f "$exp_dir/configs/system.cfg" ]]; then
    printf '%s\n' "$exp_dir/configs/system.cfg"
    return 0
  fi

  echo "Unable to find an experiment config in $exp_dir" >&2
  exit 1
}

EXPERIMENT_DIR="$(resolve_experiment_dir "${1:-}")"
if [[ "$(basename "$EXPERIMENT_DIR")" == "00-damov-native" ]]; then
  run_damov_native_runner
fi

CONFIG_PATH="$(resolve_config_path "$EXPERIMENT_DIR")"
CONFIG_NAME="$(basename "$CONFIG_PATH")"
EXPERIMENT_ID="$(basename "$EXPERIMENT_DIR")"
RUN_ONE_SCRIPT="$SCRIPT_DIR/run-one.sh"
TRAFFIC_GEN_BIN="$BENCH_ROOT/traffic_gen/traffic_gen.x"

# Reference table: each runnable experiment selects one persistent ZSim build.
# DRAMsim3 and DRAMSys are compiled into the default build alongside Ramulator;
# their experiment configs select the active memory backend at runtime.
declare -A EXPERIMENT_ZSIM_VARIANT=(
  [01-baseline]="ramulator"
  [02-clock-scaling]="ramulator"
  [03-correct-freq]="ramulator"
  [04-memory-model]="ramulator"
  [02-memory-model]="ramulator"
  [03-clock-scaling]="ramulator"
  [04-correct-freq]="ramulator"
  [05-address-mapping]="ramulator"
  [06-noc]="ramulator"
  [07-prefetcher]="ramulator"
  [08-portability-ramulator2]="ramulator2"
  [09-portability-dramsim3]="ramulator"
  [10-portability-dramsys]="ramulator"
)

ZSIM_RAMULATOR_BIN="${ZSIM_RAMULATOR_BIN:-$REPO_ROOT/simulator-source/zsim-bsc/build/release/zsim}"
ZSIM_RAMULATOR2_BIN="${ZSIM_RAMULATOR2_BIN:-$REPO_ROOT/simulator-source/zsim-bsc/build/ramulator2/release/zsim}"
ZSIM_VARIANT="${EXPERIMENT_ZSIM_VARIANT[$EXPERIMENT_ID]:-}"

case "$ZSIM_VARIANT" in
  ramulator)
    ZSIM_BIN="$ZSIM_RAMULATOR_BIN"
    REQUIRED_ZSIM_DEPENDENCY="libramulator.so"
    FORBIDDEN_ZSIM_DEPENDENCY="libramulator2.so"
    ;;
  ramulator2)
    ZSIM_BIN="$ZSIM_RAMULATOR2_BIN"
    REQUIRED_ZSIM_DEPENDENCY="libramulator2.so"
    FORBIDDEN_ZSIM_DEPENDENCY="libramulator.so"
    ;;
  *)
    echo "No ZSim variant is mapped for experiment '$EXPERIMENT_ID'." >&2
    echo "Add the experiment to EXPERIMENT_ZSIM_VARIANT in experiments/runner.sh." >&2
    exit 2
    ;;
esac

ZSIM_LIB="$(dirname "$ZSIM_BIN")/libzsim.so"
if [[ ! -x "$ZSIM_BIN" || ! -f "$ZSIM_LIB" ]]; then
  echo "Missing ZSim $ZSIM_VARIANT build for experiment '$EXPERIMENT_ID':" >&2
  echo "  $ZSIM_BIN" >&2
  echo "Run ./setup.sh from the repository root to build all configured variants." >&2
  exit 2
fi

ZSIM_DYNAMIC_DEPENDENCIES="$(readelf -d "$ZSIM_LIB" 2>/dev/null)" || {
  echo "Unable to inspect ZSim library: $ZSIM_LIB" >&2
  exit 2
}
if ! grep -Fq "Shared library: [$REQUIRED_ZSIM_DEPENDENCY]" <<< "$ZSIM_DYNAMIC_DEPENDENCIES" || \
   grep -Fq "Shared library: [$FORBIDDEN_ZSIM_DEPENDENCY]" <<< "$ZSIM_DYNAMIC_DEPENDENCIES"; then
  echo "ZSim build/backend mismatch for experiment '$EXPERIMENT_ID'." >&2
  echo "Expected the '$ZSIM_VARIANT' variant at: $ZSIM_BIN" >&2
  echo "Run ./setup.sh --rebuild to regenerate both isolated ZSim builds." >&2
  exit 2
fi
export ZSIM_BIN
echo "Using ZSim $ZSIM_VARIANT variant: $ZSIM_BIN"

case "${2:-}" in
  "") ;;
  --print-zsim) exit 0 ;;
  *)
    echo "Unknown runner option: ${2}" >&2
    echo "usage: $0 <experiment-id> [--print-zsim]" >&2
    exit 1
    ;;
esac

RWRATIO_MIN=0
RWRATIO_MAX=100
RWRATIO_STEP=10
PAUSES="10000 2000 1000 0 5 10 15 20 25 30 35 40 45 50 55 60 65 70 80 90 100 120 140 160 180 200 220 260 300 340 380 450 550 600 700 800 900"

for required in "$CONFIG_PATH" "$RUN_ONE_SCRIPT" "$BENCH_ROOT/ptr_chase/ptr_chase" "$BENCH_ROOT/ptr_chase/array.dat" "$TRAFFIC_GEN_BIN"; do
  if [[ ! -e "$required" ]]; then
    echo "Missing required file: $required" >&2
    echo "Run ./scripts/build-benchmarks.sh from the repository root before using runner.sh." >&2
    exit 1
  fi
done

RAW_DIR="$EXPERIMENT_DIR/test-raw"
mkdir -p "$RAW_DIR"
rm -rf "$RAW_DIR"/measurment_*

for ((rd_percentage=RWRATIO_MIN; rd_percentage<=RWRATIO_MAX; rd_percentage+=RWRATIO_STEP)); do
  for pause in ${PAUSES}; do
    export rd_percentage
    export pause

    echo ""
    echo "*********** Iteration: rd_percentage=${rd_percentage} pause=${pause}"

    run_dir="$RAW_DIR/measurment_${rd_percentage}_${pause}"
    if [[ -d "$run_dir" ]]; then
      echo "Directory $(basename "$run_dir") exists, skipping."
      continue
    fi

    mkdir -p "$run_dir/output"
    cp "$CONFIG_PATH" "$run_dir/$CONFIG_NAME"
    python3 - <<PY
from pathlib import Path
path = Path("$run_dir/$CONFIG_NAME")
text = path.read_text()
text = text.replace("rd_percentage", "$rd_percentage")
text = text.replace("pause", "$pause")
# Experiment configs are authored relative to the experiment directory.
# Measurement runs execute one level deeper, so shared-source paths need one
# extra ".." when materialized into each measurment_* directory.
text = text.replace("../../simulator-source/", "../../../../simulator-source/")
path.write_text(text)
PY

    cp "$BENCH_ROOT/ptr_chase/ptr_chase" "$run_dir/"
    cp "$BENCH_ROOT/ptr_chase/array.dat" "$run_dir/"
    cp "$TRAFFIC_GEN_BIN" "$run_dir/"
    cp "$RUN_ONE_SCRIPT" "$run_dir/"

    (
      cd "$run_dir"
      time bash run-one.sh > trace.txt
      rm -f array.dat traffic_gen.x
    )
  done
done

#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd "$script_dir/.." && pwd -P)"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "build-benchmarks.sh requires Linux." >&2
  echo "The ptr_chase benchmark depends on linux/perf_event.h, and the full artifact flow is intended for the same Linux environment used for the paper runs." >&2
  exit 1
fi

(
  cd "$repo_root/benchmarks/ptr_chase"
  make
)

(
  cd "$repo_root/benchmarks/traffic_gen"
  make
)

stream_workloads=(stream-copy stream-scale stream-add stream-triad)
for workload in "${stream_workloads[@]}"; do
  testing_dir="$repo_root/benchmarks/$workload/testing"
  run_script="$testing_dir/run.sh"
  output="$testing_dir/stream_omp"

  if [[ ! -f "$run_script" ]]; then
    echo "Missing STREAM build script: $run_script" >&2
    exit 1
  fi

  (
    cd "$testing_dir"
    bash ./run.sh
  )

  if [[ ! -x "$output" ]]; then
    echo "Failed to build STREAM workload: $output" >&2
    exit 1
  fi
done

echo "Benchmarks built under $repo_root/benchmarks"

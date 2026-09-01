#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../.." && pwd)"
print_plan=false

case "${1:-}" in
    "") ;;
    --print-plan) print_plan=true ;;
    *)
        echo "usage: $0 [--print-plan]" >&2
        exit 1
        ;;
esac

if [[ "$print_plan" == false ]]; then
    required_binaries=(
        "$repo_root/benchmarks/ptr_chase/ptr_chase"
        "$repo_root/benchmarks/stream-copy/testing/stream_omp"
        "$repo_root/benchmarks/stream-scale/testing/stream_omp"
        "$repo_root/benchmarks/stream-add/testing/stream_omp"
        "$repo_root/benchmarks/stream-triad/testing/stream_omp"
    )
    for binary in "${required_binaries[@]}"; do
        if [[ ! -x "$binary" ]]; then
            echo "Missing benchmark executable: $binary" >&2
            echo "Run ./scripts/build-benchmarks.sh from the repository root." >&2
            exit 1
        fi
    done
fi

found_any=false

for stage_dir in "$script_dir"/*/; do
    [[ -d "$stage_dir" ]] || continue

    runner="$stage_dir/runner.sh"
    [[ -f "$runner" ]] || continue

    found_any=true
    stage_name="$(basename "$stage_dir")"

    if [[ "$print_plan" == true ]]; then
        echo "==> Would run $stage_name"
        continue
    fi
    echo "==> Running $stage_name"
    (
        cd "$stage_dir"
        bash ./runner.sh
    )
done

if [[ "$found_any" == false ]]; then
    echo "No stage runner.sh files found under $script_dir" >&2
    exit 1
fi

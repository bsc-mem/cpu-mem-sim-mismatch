#!/usr/bin/env bash
# setup.sh — one-shot environment setup and build for the ZSim artifact.
#
# Run this once from the repository root on a Linux machine:
#   ./setup.sh
#
# Flags:
#   --rebuild   Clean and force-rebuild all memory simulators and ZSim
#   --build-damov   Build DAMOV native simulator and experiment 00 benchmark only
#
# What it does:
#   1. Checks system dependencies (GCC, scons, Python packages, libconfig++)
#   2. Generates .zsim-env (resolves all paths automatically, prompts only for Pin)
#   3. Builds memory simulators (Ramulator, DRAMsim3, Ramulator2, DRAMSys)
#   4. Builds persistent ZSim release variants for Ramulator and Ramulator2
#   5. Builds the benchmarks (ptr_chase, traffic_gen, and STREAM kernels)

set -euo pipefail

REBUILD=false
BUILD_DAMOV=false
for arg in "$@"; do
    case "$arg" in
        --rebuild) REBUILD=true ;;
        --build-damov) BUILD_DAMOV=true ;;
        *) echo "Unknown argument: $arg"; exit 1 ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$SCRIPT_DIR"

RED='\033[0;31m'; GRN='\033[0;32m'; YLW='\033[1;33m'; BLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "  ${GRN}✔${NC}  $*"; }
warn() { echo -e "  ${YLW}⚠${NC}  $*"; }
err()  { echo -e "  ${RED}✘${NC}  $*"; exit 1; }
step() { echo -e "\n${BLD}━━━  $*  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }

# ── 0. Platform check ─────────────────────────────────────────────────────────
if [[ "$(uname -s)" != "Linux" ]]; then
    err "This artifact requires Linux. Detected: $(uname -s)"
fi

if [[ "$BUILD_DAMOV" == true ]]; then
    step "Building DAMOV native simulator and experiment 00 benchmark"

    DAMOV_BUILD_SCRIPT="$REPO_ROOT/experiments/00-damov-native/scripts/build.sh"
    if [[ ! -x "$DAMOV_BUILD_SCRIPT" ]]; then
        err "DAMOV build helper is missing or not executable: $DAMOV_BUILD_SCRIPT"
    fi

    "$DAMOV_BUILD_SCRIPT"
    ok "DAMOV native simulator and experiment 00 benchmark built successfully"
    exit 0
fi

step "Step 1 / 5 — Checking system dependencies"

# GCC
if command -v gcc &>/dev/null; then
    ok "GCC: $(gcc --version | head -1)"
else
    err "GCC not found. Install GCC 11: sudo apt install gcc g++"
fi

# G++ with C++20 support (Ramulator2 requires C++20; other components use
# C++17 or C++11).
if command -v g++ &>/dev/null; then
    ok "G++: $(g++ --version | head -1)"
else
    err "G++ not found. Install a C++20-capable compiler: sudo apt install g++"
fi

if g++ -std=c++20 -x c++ -fsyntax-only - &>/dev/null <<'CPP'
#include <concepts>

template <typename T>
concept Integral = std::integral<T>;

static_assert(Integral<int>);
CPP
then
    ok "G++ supports C++20"
else
    err "G++ does not support the required C++20 standard. Install GCC/G++ 11 or newer."
fi

# readelf (used to validate that each ZSim variant links exactly one Ramulator)
if command -v readelf &>/dev/null; then
    ok "readelf: found"
else
    err "readelf not found. Install binutils: sudo apt install binutils"
fi

# scons
if command -v scons &>/dev/null; then
    ok "scons: $(scons --version 2>&1 | head -1)"
else
    err "scons not found. Install it: sudo apt install scons"
fi

# unzip (needed for dependency downloads)
if command -v unzip &>/dev/null; then
    ok "unzip: $(unzip -v 2>&1 | head -1)"
else
    err "unzip not found. Install it: sudo apt install unzip"
fi

# cmake (needed for DRAMsim3, Ramulator2, and DRAMSys)
if command -v cmake &>/dev/null; then
    ok "cmake: $(cmake --version | head -1)"
else
    err "cmake not found. Install it: sudo apt install cmake"
fi

cmake_major="$(cmake --version | awk 'NR==1 {split($3, v, "."); print v[1]}')"
cmake_minor="$(cmake --version | awk 'NR==1 {split($3, v, "."); print v[2]}')"
if [[ ! "$cmake_major" =~ ^[0-9]+$ || ! "$cmake_minor" =~ ^[0-9]+$ ]] || \
   (( cmake_major < 3 || (cmake_major == 3 && cmake_minor < 25) )); then
    err "DRAMSys requires CMake 3.25 or newer. Found: $(cmake --version | head -1)"
fi
CMAKE_COMPAT_ARGS=()
# CMake 4 removed compatibility with projects that still declare <3.5.
if [[ "$cmake_major" =~ ^[0-9]+$ ]] && (( cmake_major >= 4 )); then
    CMAKE_COMPAT_ARGS=(-DCMAKE_POLICY_VERSION_MINIMUM=3.5)
    echo "  Detected CMake ${cmake_major}.x; enabling legacy policy compatibility for bundled projects."
fi

# libconfig++
if pkg-config --exists libconfig++ 2>/dev/null || ldconfig -p 2>/dev/null | grep -q libconfig++; then
    ok "libconfig++ found"
else
    warn "libconfig++ may be missing. If the ZSim build fails, run: sudo apt install libconfig++-dev"
fi

# Python + packages (required for plot.py)
if python3 -c "import pandas, matplotlib" 2>/dev/null; then
    ok "Python 3 with pandas and matplotlib"
else
    warn "pandas or matplotlib missing. Installing..."
    python3 -m pip install --user pandas matplotlib
    ok "pandas and matplotlib installed"
fi

# ── 1. Generate .zsim-env ─────────────────────────────────────────────────────
step "Step 2 / 5 — Generating .zsim-env"

"$REPO_ROOT/scripts/setup-env.sh"

if [[ ! -f "$REPO_ROOT/.zsim-env" ]]; then
    err ".zsim-env was not created. See scripts/setup-env.sh output above."
fi

# Source it for the remainder of this script
# shellcheck disable=SC1091
source "$REPO_ROOT/.zsim-env"

ok ".zsim-env sourced"

# ── 2. Build memory simulators ───────────────────────────────────────────────
step "Step 3 / 5 — Building memory simulators"

OLD_ABI_CXXFLAG="-D_GLIBCXX_USE_CXX11_ABI=0"

# Ramulator — make libramulator.so in ramulator/ramulator/
RAMULATOR_LIB="$RAMULATORPATH/ramulator/libramulator.so"
if [[ -f "$RAMULATORPATH/ramulator/libramulator.so" ]] && [[ "$REBUILD" == false ]]; then
    ok "libramulator.so already built"
else
    echo "  Building Ramulator..."
    [[ "$REBUILD" == true ]] && make -C "$RAMULATORPATH/ramulator" clean 2>/dev/null || true
    make -C "$RAMULATORPATH/ramulator" libramulator.so -j"$(nproc)" CXX=g++ CXXFLAGS="-DRAMULATOR -Wall -std=c++11 -w -O3 $OLD_ABI_CXXFLAG"
    [[ -f "$RAMULATORPATH/ramulator/libramulator.so" ]] && ok "libramulator.so built" || err "Ramulator build failed."
fi

# DRAMsim3 — cmake build (outputs libdramsim3.so to $DRAMSIM3PATH/, one level above build/)
DRAMSIM3_LIB="$DRAMSIM3PATH/libdramsim3.so"
if [[ -f "$DRAMSIM3_LIB" ]] && [[ "$REBUILD" == false ]]; then
    ok "libdramsim3.so already built"
else
    echo "  Building DRAMsim3..."
    [[ "$REBUILD" == true ]] && rm -rf "$DRAMSIM3PATH/build" || true
    DRAMSIM3_CMAKE_ARGS=(
        -S "$DRAMSIM3PATH"
        -B "$DRAMSIM3PATH/build"
        -DCMAKE_BUILD_TYPE=Release
        -DCMAKE_POSITION_INDEPENDENT_CODE=ON
        -DCMAKE_CXX_FLAGS="-D_GLIBCXX_USE_CXX11_ABI=0"
    )
    DRAMSIM3_CMAKE_ARGS+=("${CMAKE_COMPAT_ARGS[@]}")
    cmake "${DRAMSIM3_CMAKE_ARGS[@]}"
    make -C "$DRAMSIM3PATH/build" dramsim3 -j"$(nproc)"
    [[ -f "$DRAMSIM3_LIB" ]] && ok "libdramsim3.so built" || err "DRAMsim3 build failed."
fi

# Ramulator2 — cmake build (LIBRARY_OUTPUT_DIRECTORY = PROJECT_SOURCE_DIR, so lib lands in $RAMULATOR2PATH/)
RAMULATOR2_LIB="$RAMULATOR2PATH/libramulator2.so"
if [[ -f "$RAMULATOR2_LIB" ]] && [[ "$REBUILD" == false ]]; then
    ok "libramulator2.so already built"
else
    echo "  Building Ramulator2 from: $RAMULATOR2PATH"
    [[ "$REBUILD" == true ]] && rm -rf "$RAMULATOR2PATH/build" || true
    RAMULATOR2_CMAKE_ARGS=(
        -S "$RAMULATOR2PATH"
        -B "$RAMULATOR2PATH/build"
        -DCMAKE_BUILD_TYPE=Release
        -DCMAKE_POSITION_INDEPENDENT_CODE=ON
        -DCMAKE_CXX_FLAGS="-D_GLIBCXX_USE_CXX11_ABI=0"
    )
    RAMULATOR2_CMAKE_ARGS+=("${CMAKE_COMPAT_ARGS[@]}")
    cmake "${RAMULATOR2_CMAKE_ARGS[@]}"
    make -C "$RAMULATOR2PATH/build" ramulator -j"$(nproc)"
    [[ -f "$RAMULATOR2_LIB" ]] && ok "libramulator2.so built" || err "Ramulator2 build failed. Expected: $RAMULATOR2_LIB"
fi

# DRAMSys — cmake build (static libs in $DRAMSYSPATH/build/lib/)
if [[ -n "${DRAMSYSPATH:-}" ]]; then
    DRAMSYS_LIB_DIR="$DRAMSYSPATH/build/lib"
    DRAMSYS_LIB="$DRAMSYS_LIB_DIR/libdramsys.a"
    DRAMPOWER_LIB="$DRAMSYS_LIB_DIR/libDRAMPower.a"
    SYSTEMC_LIB="$DRAMSYS_LIB_DIR/libsystemc.a"
    SQLITE_LIB="$DRAMSYS_LIB_DIR/libsqlite3.a"

    if [[ -f "$DRAMSYS_LIB" && -f "$DRAMPOWER_LIB" && -f "$SYSTEMC_LIB" && -f "$SQLITE_LIB" ]] && [[ "$REBUILD" == false ]]; then
        ok "DRAMSys libraries already built"
    else
        echo "  Building DRAMSys from: $DRAMSYSPATH"
        [[ "$REBUILD" == true ]] && rm -rf "$DRAMSYSPATH/build" || true
        DRAMSYS_CMAKE_ARGS=(
            -DCMAKE_BUILD_TYPE=Release
            -DCMAKE_POSITION_INDEPENDENT_CODE=ON
            -DCMAKE_CXX_FLAGS="$OLD_ABI_CXXFLAG"
            -DDRAMSYS_BUILD_CLI=OFF
            -DDRAMSYS_BUILD_TOOLS=OFF
            -DDRAMSYS_BUILD_TRACE_ANALYZER=OFF
        )
        cmake -S "$DRAMSYSPATH" -B "$DRAMSYSPATH/build" \
            "${DRAMSYS_CMAKE_ARGS[@]}"
        cmake --build "$DRAMSYSPATH/build" -j"$(nproc)"
        if [[ -f "$DRAMSYS_LIB" && -f "$DRAMPOWER_LIB" && -f "$SYSTEMC_LIB" && -f "$SQLITE_LIB" ]]; then
            ok "DRAMSys libs built (libdramsys.a, libDRAMPower.a, libsystemc.a, libsqlite3.a)"
        else
            err "DRAMSys build failed. Expected libs under: $DRAMSYS_LIB_DIR"
        fi
    fi
else
    err "DRAMSYSPATH is not set; cannot build the required DRAMSys backend."
fi

# ── 3. Build ZSim ─────────────────────────────────────────────────────────────
step "Step 4 / 5 — Building ZSim variants (release)"

ZSIM_DIR="$REPO_ROOT/simulator-source/zsim-bsc"
ZSIM_RAMULATOR_BUILD_ROOT="build"
ZSIM_RAMULATOR2_BUILD_ROOT="build/ramulator2"
ZSIM_RAMULATOR_BIN="$ZSIM_DIR/$ZSIM_RAMULATOR_BUILD_ROOT/release/zsim"
ZSIM_RAMULATOR_LIB="$ZSIM_DIR/$ZSIM_RAMULATOR_BUILD_ROOT/release/libzsim.so"
ZSIM_RAMULATOR2_BIN="$ZSIM_DIR/$ZSIM_RAMULATOR2_BUILD_ROOT/release/zsim"
ZSIM_RAMULATOR2_LIB="$ZSIM_DIR/$ZSIM_RAMULATOR2_BUILD_ROOT/release/libzsim.so"

zsim_variant_ready() {
    local binary="$1"
    local library="$2"
    local required_dependency="$3"
    local forbidden_dependency="$4"

    [[ -x "$binary" && -f "$library" ]] || return 1
    local dynamic_dependencies
    dynamic_dependencies="$(readelf -d "$library" 2>/dev/null)" || return 1
    grep -Fq "Shared library: [$required_dependency]" <<< "$dynamic_dependencies" || return 1
    ! grep -Fq "Shared library: [$forbidden_dependency]" <<< "$dynamic_dependencies"
}

build_zsim_variant() {
    local label="$1"
    local build_root="$2"
    local binary="$3"
    local library="$4"
    local required_dependency="$5"
    local forbidden_dependency="$6"
    local disable_ramulator="$7"

    if [[ "$REBUILD" == false ]] && \
       zsim_variant_ready "$binary" "$library" "$required_dependency" "$forbidden_dependency"; then
        ok "ZSim $label variant already built: $binary"
        return 0
    fi

    echo "  Building ZSim $label variant with $(nproc) parallel jobs..."
    (
        cd "$ZSIM_DIR"
        if [[ "$disable_ramulator" == true ]]; then
            unset RAMULATORPATH
        fi
        if [[ "$REBUILD" == true ]]; then
            scons -c --r --buildDir="$build_root"
        fi
        scons --r --buildDir="$build_root" -j"$(nproc)"
    )

    if zsim_variant_ready "$binary" "$library" "$required_dependency" "$forbidden_dependency"; then
        ok "ZSim $label variant built: $binary"
    else
        err "ZSim $label build did not produce the expected backend at: $binary"
    fi
}

build_zsim_variant \
    "Ramulator" \
    "$ZSIM_RAMULATOR_BUILD_ROOT" \
    "$ZSIM_RAMULATOR_BIN" \
    "$ZSIM_RAMULATOR_LIB" \
    "libramulator.so" \
    "libramulator2.so" \
    false

if [[ -n "${RAMULATOR2PATH:-}" && -d "$RAMULATOR2PATH" ]]; then
    build_zsim_variant \
        "Ramulator2" \
        "$ZSIM_RAMULATOR2_BUILD_ROOT" \
        "$ZSIM_RAMULATOR2_BIN" \
        "$ZSIM_RAMULATOR2_LIB" \
        "libramulator2.so" \
        "libramulator.so" \
        true
else
    warn "RAMULATOR2PATH is unavailable; skipping the Ramulator2 ZSim variant."
fi

# ── 3. Build benchmarks ───────────────────────────────────────────────────────
step "Step 5 / 5 — Building benchmarks"

"$REPO_ROOT/scripts/build-benchmarks.sh"

PTR_CHASE="$REPO_ROOT/benchmarks/ptr_chase/ptr_chase"
TRAFFIC_GEN="$REPO_ROOT/benchmarks/traffic_gen/traffic_gen.x"
STREAM_BINS=(
    "$REPO_ROOT/benchmarks/stream-copy/testing/stream_omp"
    "$REPO_ROOT/benchmarks/stream-scale/testing/stream_omp"
    "$REPO_ROOT/benchmarks/stream-add/testing/stream_omp"
    "$REPO_ROOT/benchmarks/stream-triad/testing/stream_omp"
)

[[ -x "$PTR_CHASE" ]]   && ok "ptr_chase built: $PTR_CHASE"   || err "ptr_chase build failed."
[[ -x "$TRAFFIC_GEN" ]] && ok "traffic_gen built: $TRAFFIC_GEN" || err "traffic_gen build failed."
for stream_bin in "${STREAM_BINS[@]}"; do
    [[ -x "$stream_bin" ]] && ok "STREAM workload built: $stream_bin" || err "STREAM workload build failed: $stream_bin"
done

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GRN}${BLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GRN}${BLD}  Setup complete. The artifact is ready to run.${NC}"
echo -e "${GRN}${BLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  To run an experiment:"
echo "    source .zsim-env"
echo "    ./experiments/runner.sh 01-baseline"
echo ""
echo "  To compare committed results (no simulation needed):"
echo "    ./scripts/compare-results.sh 01-baseline 04-correct-freq"
echo ""

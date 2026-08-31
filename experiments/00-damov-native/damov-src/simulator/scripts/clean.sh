#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
SIMULATOR_DIR="$(cd "$SCRIPT_DIR/.." && pwd -P)"
export PINPATH="$SIMULATOR_DIR/pin"
export RAMULATORPATH="$SIMULATOR_DIR/ramulator"
export LIBCONFIGPATH="$SIMULATOR_DIR/libconfig"
(
  cd "$RAMULATORPATH"
  make clean
)
(
  cd "$SIMULATOR_DIR"
  scons -c
)

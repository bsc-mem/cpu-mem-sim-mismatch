#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
SIMULATOR_DIR="$(cd "$SCRIPT_DIR/.." && pwd -P)"
PINPATH="$SIMULATOR_DIR/pin"
RAMULATORPATH="$SIMULATOR_DIR/ramulator"

if [[ ! -d "$PINPATH" ]]; then
  echo "PINPATH does not exist: $PINPATH" >&2
  exit 1
fi

if [[ ! -d "$RAMULATORPATH" ]]; then
  echo "RAMULATORPATH does not exist: $RAMULATORPATH" >&2
  exit 1
fi

RAMULATOR_BUILD_DIR="$RAMULATORPATH"

NUMCPUS="$(nproc 2>/dev/null || getconf _NPROCESSORS_ONLN || echo 1)"
MODE="${1:-all}"
LIBCONFIGPATH="$SIMULATOR_DIR/libconfig"

build_local_libconfig() {
  if [[ ! -x "$LIBCONFIGPATH/configure" ]]; then
    echo "Missing local libconfig configure script: $LIBCONFIGPATH/configure" >&2
    exit 1
  fi
  (
    cd "$LIBCONFIGPATH"
    ./configure --prefix="$LIBCONFIGPATH"
    make -j"$NUMCPUS" ACLOCAL=: AUTOCONF=: AUTOHEADER=: AUTOMAKE=:
    make install ACLOCAL=: AUTOCONF=: AUTOHEADER=: AUTOMAKE=:
  )
}

build_ramulator() {
  make -C "$RAMULATOR_BUILD_DIR" libramulator.so -j"$NUMCPUS"
}

case "$MODE" in
  z)
    echo "Compiling only DAMOV ZSim ..."
    export PINPATH RAMULATORPATH LIBCONFIGPATH
    (
      cd "$SIMULATOR_DIR"
      scons -j"$NUMCPUS"
    )
    ;;
  r)
    echo "Compiling only shared Ramulator ..."
    build_ramulator
    ;;
  all)
    echo "Compiling all (local libconfig + shared Ramulator + DAMOV ZSim) ..."
    build_local_libconfig
    build_ramulator
    export PINPATH RAMULATORPATH LIBCONFIGPATH
    (
      cd "$SIMULATOR_DIR"
      scons -j"$NUMCPUS"
    )
    ;;
  *)
    echo "Unknown mode '$MODE'. Expected one of: all, z, r" >&2
    exit 1
    ;;
esac

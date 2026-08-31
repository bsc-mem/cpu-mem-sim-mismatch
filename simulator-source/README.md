# Shared Simulator Source

This directory contains the shared simulator source trees used across all artifact experiments. **Important:** the experiments are configuration-driven — all runnable stages share a single set of source trees and vary through `sb.cfg`. No source code is duplicated across experiments.

| Directory | Role |
| :--- | :--- |
| `zsim-bsc/` | Main ZSim simulator — the primary contribution of this artifact |
| `dramsim3/DRAMsim3/` | DRAMsim3 memory simulator, used by the DRAMsim3 portability stage |
| `ramulator/` | Ramulator memory simulator, used by the ZSim interface experiments |
| `ramulator2/` | Ramulator2 memory simulator, used by the Ramulator2 portability stage |
| `DRAMSys/` | DRAMSys memory simulator, used by the DRAMSys portability stage |

Use the repository-root `./setup.sh` for the artifact build. The README inside
each bundled memory simulator documents its upstream standalone project; those
commands do not include the ABI flags, library-only options, or separate ZSim
variants required by this artifact.

---

## 1. The ZSim-BSC Simulator

### 1.1. Lineage

The `zsim-bsc/` tree contains the ZSim fork modified for the experiments in this
paper. Use this tree to reproduce the artifact results.

The development lineage is:

1. **Original ZSim** (Stanford/MIT): Fast x86-64 simulator introduced in the ISCA 2013 paper by Sanchez and Kozyrakis. Targeted very old microarchitectures.
2. **Extended fork**: Extended to Sandy Bridge, with updated instruction decoder, port latencies, and bandwidth parameters.
3. **Skylake extensions**: Further extended to support Intel Skylake microarchitecture — updated cache sizes and replacement policies. The methodology follows the artifact configuration documented here.
4. **This artifact's additions** (on top of `zsim-bsc`):
   - GDB debugging support
   - Hardware prefetcher model (absent from the original ZSim)
   - Network-on-Chip (NoC) model adapted from Damov's platform
   - **Multi-channel memory interface** for Ramulator, Ramulator2, DRAMsim3, and DRAMSys

The interface implementation is the core novelty. The prefetcher, NoC, and GDB additions are supporting infrastructure that enable the experiments to run correctly on realistic configurations.

### 1.2. Artifact Snapshot

The snapshot committed here is the authoritative reference for this artifact and should be used as-is for reproduction.

---

## 2. Dependencies

This repository includes all simulator source trees. It does not store the Pin
and HDF5 bundles or the dependencies that the DRAMSys and Ramulator2 CMake
builds fetch. `./setup.sh` finds system installations of Pin and HDF5 first. If
it finds neither, it downloads the pinned bundles into `dependencies/`.

### 2.1. Intel Pin — Critical Version Requirement

ZSim is a Pin-based dynamic binary instrumentation tool. **Pin 2.14 (build 71313) is required.** Earlier versions lack Sandy Bridge / Skylake support; later versions break the ZSim instrumentation interface. This is not a soft requirement.

The modified ZSim launcher adds `-injection child -ifeellucky` for Pin 2.x on
Linux 4.0 and newer kernels, so experiment commands need no extra Pin flags.

`scripts/setup-env.sh` writes `PINPATH` to `.zsim-env`. It uses an existing Pin
2.14 installation or downloads the pinned archive.

### 2.2. HDF5

ZSim outputs simulation statistics in HDF5 format.

- **Required version used for the paper:** HDF5 1.8.16
- The `SConstruct` build file uses a system installation or the path in `HDF5_HOME`

`scripts/setup-env.sh` writes `HDF5_HOME` to `.zsim-env`. It leaves the value
empty for a system installation or points it at the downloaded bundle.

### 2.3. Compiler

- **GCC 11.4.0** was used for the paper artifact runs
- Ramulator2 requires a C++20 compiler
- The build system uses `scons`
- DRAMSys requires C++17 and CMake 3.25 or newer
- DRAMSys downloads SystemC, DRAMPower, DRAMUtils, SQLite, and nlohmann/json during its first build

### 2.4. Memory Simulator Paths

The generated `.zsim-env` assigns `DRAMSIM3PATH`, `RAMULATORPATH`,
`RAMULATOR2PATH`, and `DRAMSYSPATH` to the corresponding source trees in this
directory. You do not need to set them by hand.

### 2.5. Python (Post-processing)

Python 3 with the following packages is required for the plotting and result-processing pipeline:
- `pandas`
- `matplotlib`

---

## 3. Environment Setup

All environment variables above are tracked in a `.zsim-env` file at the repository root. This file must be created and sourced before building or running any experiment.

Run the complete build from the repository root:
```bash
./setup.sh
source .zsim-env
```

Manual env generation only:
```bash
./scripts/setup-env.sh
source .zsim-env
```

To inspect the expected variables:
```bash
cat .zsim-env
```

To apply them to the current shell:
```bash
source .zsim-env
```

`setup.sh` builds and validates both required release variants:

```text
zsim-bsc/build/release/zsim             Ramulator, DRAMsim3, and DRAMSys stages
zsim-bsc/build/ramulator2/release/zsim  Ramulator2 stage
```

Use `./setup.sh --rebuild` to clean and rebuild both variants. The experiment
runner selects the correct binary from its stage-to-variant table.

---

## 4. Ramulator — Address Mapping Note

The Ramulator source tree (`ramulator/`) includes Intel Skylake-specific address mapping support, originally added to correctly model the multi-channel memory layout of Skylake platforms.

In the original implementation, enabling this required manually commenting and uncommenting two lines in `ramulator/src/memory.h`. To make this reproducible without source edits, the public artifact exposes this toggle through a dedicated config file:

```
ramulator/ramulator-configs/DDR4-config-MN4-skylake.cfg
```

The Figure 9a address-mapping stage selects this config file, enabling
Skylake-specific address mapping through configuration rather than source
modification.

---

## 5. Source Tree Notes

The simulator source trees are committed directly to this repository. The
`zsim-bsc/` tree contains the artifact's interface, NoC, prefetcher, and
portability changes. The memory-simulator trees contain the integration changes
needed by this build.

For reference, the full artifact environment (simulator sources, benchmarks, and raw simulation outputs) requires approximately 24 GB of disk space.

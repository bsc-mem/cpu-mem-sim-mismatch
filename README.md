# Integration, Enhancements and Evaluation of Memory Simulators

This is the artifact repository of **“Integration, Enhancements and Evaluation of Memory Simulators.”**

This repository provides the modified ZSim source code and the Ramulator, Ramulator 2, DRAMsim3, and DRAMSys integrations evaluated in the paper. It also includes benchmark source code, processed results, and scripts for reproducing and comparing the experiments.

## Paper Reference

**Integration, Enhancements and Evaluation of Memory Simulators**

Authors:

- Pouya Esmaili-Dokht — Barcelona Supercomputing Center; Universitat Politècnica de Catalunya
- Arash Yadegari — Barcelona Supercomputing Center; Sharif University of Technology
- Victor Xirau — Barcelona Supercomputing Center
- Julian Pavon — Barcelona Supercomputing Center
- Hamid Sarbazi-Azad — Sharif University of Technology; IPM
- Adrián Cristal — Barcelona Supercomputing Center; Universitat Politècnica de Catalunya
- Eduard Ayguadé — Universitat Politècnica de Catalunya; Barcelona Supercomputing Center
- Petar Radojković — Barcelona Supercomputing Center

Citation:

```bibtex
@INPROCEEDINGS{esmaili:interface,
  author={Esmaili-Dokht, Pouya and Yadegari, Arash and Xirau, Victor and Pavon, Julian and Sarbazi-Azad, Hamid and Cristal, Adrián and Ayguadé, Eduard and Radojković, Petar},
  booktitle={IEEE International Symposium on Workload Characterization (IISWC)},
  title={{Integration, Enhancements and Evaluation of Memory Simulators}},
  year={2026}
}
```

Artifact archive: [10.5281/zenodo.21760831](https://doi.org/10.5281/zenodo.21760831). This is the Zenodo concept DOI, which resolves to the latest published artifact version; direct raw-data links below identify files in a specific version record.

## Table of Contents

- [Paper Reference](#paper-reference)
- [1. Repository Architecture](#1-repository-architecture)
- [2. Environment Setup](#2-environment-setup)
- [3. Experiment Reproduction](#3-experiment-reproduction)
- [4. Result Comparison](#4-result-comparison)
- [5. Raw Data Policy](#5-raw-data-policy)
- [6. License](#6-license)

---

## 1. Repository Architecture

The repository is organized into four main directories: `simulator-source/`, `benchmarks/`, `experiments/`, and `scripts/`. Each directory contains a `README.md` with more details.
The simulator source trees are already included in the repository, so no external downloads are needed to reproduce the experiments. The `setup.sh` script handles all dependency checks, builds, and environment generation. Different experiment stages are configured via the `experiments/` subdirectories, which contain the configuration files and scripts needed to run each stage. The `scripts/` directory contains repository-level automation helpers for setup, benchmark builds, result processing, and comparison.


| Directory           | Purpose & Documentation                                                                                                                                                                                                                                                                              |
| :------------------ | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `simulator-source/` | **The Simulators.** Contains the modified ZSim source and the Ramulator, Ramulator2, DRAMsim3, and DRAMSys source trees used by the artifact. <br>-> _See [`simulator-source/README.md`](simulator-source/README.md) for dependency and build details._                                              |
| `benchmarks/`       | **The Workloads.** Contains the pointer-chasing, traffic-generation and stream benchmarks used to generate bandwidth-latency curves.                                                                                                                                                                         |
| `experiments/`      | **The Configurations & Results.** One folder per paper stage. Runnable stages include `sb.cfg`. Committed outputs, when present, live under `processed/` and `figures/`. <br>-> _See [`experiments/README.md`](experiments/README.md) for details on the execution flow and shared run entrypoints._ |
| `scripts/`          | **The Automation.** Repository-level helpers for environment setup, benchmark builds, result processing, and comparison. <br>-> _See [`scripts/README.md`](scripts/README.md) for the script catalog._                                                                                               |

The processed figures and configuration files are kept in Git. Most raw simulator traces are released separately and are listed in the [raw-results table](#51-raw-results); experiment 00's raw results are committed directly under `experiments/00-damov-native/test-raw/` and experiment 11's raw results are generated locally by the runner script.

---

## 2. Environment Setup and Installation

Install the host packages on Ubuntu or Debian:

```bash
sudo apt update
sudo apt install build-essential cmake scons libconfig++-dev libelf-dev \
  binutils curl unzip python3 python3-pip pkg-config
python3 -m pip install --user pandas matplotlib
```

The paper runs used GCC 11. The compiler must support C++20 for Ramulator2, and
CMake must be version 3.25 or newer.

Run the setup script from the repository root:

```bash
./setup.sh
```

This handles everything in sequence:

1. Checks the compiler, CMake, SCons, binutils, libconfig++, and Python packages.
2. Finds Pin 2.14 and HDF5 on the host or downloads the pinned bundles into `dependencies/`.
3. Builds Ramulator, Ramulator2, DRAMsim3, and DRAMSys. Their source trees are already in this repository. DRAMSys and Ramulator2 fetch their CMake dependencies during the first build.
4. Builds separate Ramulator and Ramulator2 ZSim binaries.
5. Builds `ptr_chase`, `traffic_gen`, and the four STREAM kernels used by Experiment 11.

Setup writes `.zsim-env` with the environment variables needed to run the experiments. The file can be sourced in a shell to set up the environment for running experiments.

```bash
source .zsim-env
```

To force a clean rebuild after pulling changes:

```bash
./setup.sh --rebuild
```

Experiment 00 also needs its DAMOV-specific build after the main setup:

```bash
./setup.sh --build-damov
```

> **System requirements:** Linux, a C++20 compiler, CMake 3.25 or newer, SCons, libconfig++, libelf, binutils, Python 3 with pandas and matplotlib, and network access for dependency downloads. `ptr_chase` requires `linux/perf_event.h`.
>
> **Pin on modern kernels:** The modified ZSim launcher adds Pin's child-injection workaround on Linux 4.0 and newer kernels.

-> _For manual dependency/build steps see [`simulator-source/README.md`](simulator-source/README.md). For script-by-script setup details see [`scripts/README.md`](scripts/README.md)._

---

## 3. Experiment Reproduction

The paper evaluates the impact of interface details through a sequence of cumulative refinements. Each stage represents a specific correction or enhancement to the simulator coupling:

### 3.1. Interface Refinement Steps

| Step                                                    | Description / Focus                                                             | Figure               |
| :------------------------------------------------------ | :------------------------------------------------------------------------------ | :------------------- |
| [`00-damov-native`](experiments/00-damov-native/)       | Native DAMOV reference, dispatched to its dedicated runner                      | Figure 13            |
| [`01-baseline`](experiments/01-baseline/)               | Base simulator coupling                                                         | Figure 2b, 2c and 2d |
| [`02-clock-scaling`](experiments/02-clock-scaling/)     | Enable clock scaling at the memory-simulator interface                          | Figure 3             |
| [`03-correct-freq`](experiments/03-correct-freq/)       | Remove the integer frequency-ratio rounding error                               | Figure 4             |
| [`04-memory-model`](experiments/04-memory-model/)       | Correct the delayed-response memory-model mismatch                              | Figure 8             |
| [`05-address-mapping`](experiments/05-address-mapping/) | Physical address mapping accuracy                                               | Figure 9a            |
| [`06-noc`](experiments/06-noc/)                         | Realistic Network-on-Chip refinement                                            | Figure 9b            |
| [`07-prefetcher`](experiments/07-prefetcher/)           | Final Ramulator stage with prefetcher                                           | Figure 9c            |
| [`11-mem-intensive`](experiments/11-mem-intensive/)     | Pointer-chase and STREAM results across correction stages and memory simulators | Figures 10 and 11e   |

### 3.2. Portability Evaluation

| Step                                                                  | Description / Focus         | Figure     |
| :-------------------------------------------------------------------- | :-------------------------- | :--------- |
| [`08-portability-ramulator2`](experiments/08-portability-ramulator2/) | Evaluation using Ramulator2 | Figure 11b |
| [`09-portability-dramsim3`](experiments/09-portability-dramsim3/)     | Evaluation using DRAMsim3   | Figure 11c |
| [`10-portability-dramsys`](experiments/10-portability-dramsys/)       | Evaluation using DRAMSys    | Figure 11d |

### 3.3. Running and Plotting

After `./setup.sh` completes, the full cycle for one stage is:

```bash
# Source the environment (once per shell session)
source .zsim-env

# Run the full sweep — results land in experiments/01-baseline/test-raw/
./experiments/runner.sh 01-baseline

# Generate figures and a processed CSV from your run
./experiments/plot.py experiments/01-baseline/test-raw \
  --config-dir experiments/01-baseline
# → writes to test-output/01-baseline/processed/ and test-output/01-baseline/figures/
```

The command above applies to experiments 01 through 10. Experiment 11 stores
one result per benchmark and stage, so use its plotter:

```bash
./experiments/runner.sh 11-mem-intensive
./experiments/11-mem-intensive/plot.py
```

`experiments/11-mem-intensive/plot.py` writes the processed CSV and generates
Figures 10 and 11e. `experiments/plot.py` expects the `measurment_*` sweep layout
used by experiments 01 through 10.

> **Reproducibility note:** Results from a new run may not exactly match the paper
> figures or archived raw results. Host hardware, operating-system and library
> versions, compiler versions, and runtime variation can affect the measured
> values. Differences of 1% to 4% may occur and do not change the paper's
> overall conclusions. To reproduce the exact paper figures, use the raw data
> linked or stored in [Section 5.1](#51-raw-results).

`runner.sh` clears prior `test-raw/measurment_*` directories for the selected stage before creating a fresh run.

Ramulator and Ramulator2 cannot be active in the same ZSim binary, so `setup.sh` builds them into separate persistent output directories. `experiments/runner.sh` contains the experiment-to-variant reference table and automatically selects the Ramulator2 build for `08-portability-ramulator2`; the other staged experiments use the default Ramulator build.

The committed paper figures are under `experiments/<stage>/figures/` and are not touched by the commands above. To overwrite them intentionally:

```bash
./experiments/plot.py experiments/01-baseline/test-raw \
  --config-dir experiments/01-baseline \
  --output-dir experiments/01-baseline
```

-> _For the full execution model see [`experiments/README.md`](experiments/README.md)._

---

## 4. Result Comparison

A key contribution of the paper is analyzing the delta between interface correctness stages.

To compare the output of two different stages (e.g., comparing the baseline against the corrected model), use the `compare-results.sh` script:

```bash
./scripts/compare-results.sh 01-baseline 04-memory-model
```

It can also compare two explicit CSV files (for example from `test-output/.../processed/bandwidth_latency.csv`).

---

## 5. Raw Data Policy

The repository contains the configurations, scripts, processed CSV files, and figures needed to inspect each stage. Except for experiment 00, raw simulator output is distributed separately so that the large trace files do not have to be stored in Git.

### 5.1. Raw Results

| Step                        | Raw-data location                                                                       | MD5SUM                             |
| :-------------------------- | :-------------------------------------------------------------------------------------- | :--------------------------------- |
| `00-damov-native`           | [`experiments/00-damov-native/test-raw/`](experiments/00-damov-native/test-raw/)        | `N/A`                              |
| `01-baseline`               | [Download](https://zenodo.org/records/21760832/files/01-baseline.zip?download=1)        | `38f1cf9f9a1f6f3c2adaec688fabcf4d` |
| `02-clock-scaling`          | `TODO: publish reordered-stage raw archive`                                             | `TODO`                             |
| `03-correct-freq`           | `TODO: publish reordered-stage raw archive`                                             | `TODO`                             |
| `04-memory-model`           | `TODO: publish reordered-stage raw archive`                                             | `TODO`                             |
| `05-address-mapping`        | [Download](https://zenodo.org/records/21760832/files/05-address-mapping.zip?download=1) | `74bb3d8d63cf43ddd06929b9dc27a7f9` |
| `06-noc`                    | [Download](https://zenodo.org/records/21760832/files/06-noc.zip?download=1)             | `5a6fdeb0af978f8eaf4f355e46453a54` |
| `07-prefetcher`             | [Download](https://zenodo.org/records/21760832/files/07-prefetcher.zip?download=1)      | `1e4fd36b3c25af7603f2e817c2448980` |
| `08-portability-ramulator2` | [Download](https://zenodo.org/records/21760832/files/08-ramulator2.zip?download=1)      | `60cb5aac4b34df03c297bdfa7ef85cec` |
| `09-portability-dramsim3`   | [Download](https://zenodo.org/records/21760832/files/09-dramsim3.zip?download=1)        | `87406cce9943ea51eb6a98ebc8a350f1` |
| `10-portability-dramsys`    | [Download](https://zenodo.org/records/21760832/files/10-dramsys.zip?download=1)         | `cc52eb538c221228e72004a9581f4388` |
| `11-mem-intensive`          | Generated locally by `./experiments/runner.sh 11-mem-intensive` (50 simulation points)  | `N/A`                              |

### 5.2. Regenerating Results

Raw data for any runnable stage can be regenerated from the repository root:

```bash
source .zsim-env
./experiments/runner.sh 01-baseline
./experiments/plot.py experiments/01-baseline/test-raw \
  --config-dir experiments/01-baseline
```

Experiment 11 uses the same shared runner interface and generates paper Figures
10 and 11e. Its raw data is produced locally rather than downloaded: the
experiment needs only five benchmark points for each of ten unique stages, or
50 simulation points in total. The seven correction stages feed Figure 10, and
Figure 11e reuses the final Ramulator stage alongside three portability stages.

```bash
./experiments/runner.sh 11-mem-intensive
./experiments/11-mem-intensive/plot.py
```

---

## 6. License

This artifact is distributed under the BSD 3-Clause License.

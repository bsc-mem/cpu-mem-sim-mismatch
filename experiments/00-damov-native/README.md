# 00-damov-native

This experiment preserves the existing system-agnostic seed that was already present in the repository. It is useful as a structural starting point for the public artifact, but it is not the main paper-result path.

## Paper Figure

This stage corresponds to the original-DAMOV evaluation in Appendix A,
Figure 13.

## Current Contents

- original config files
- shared benchmark binaries are expected from `../../benchmarks/`
- shared experiment entrypoints are available in `../runner.sh`, `../run-one.sh`, and `../plot.py`
- DAMOV native simulator builds use DAMOV's own vendored Pin and Ramulator trees

## Changes from Original DAMOV

The DAMOV simulator remains structurally independent from the paper simulator. Its dependencies are included under `damov-src/simulator`, following the layout of DAMOV revision `7a2147b73aa80bc2d9ce928d533adefceafb5e3f`:

- **Pin:** The complete Pin tree is vendored without changes.
- **Ramulator:** The complete DAMOV Ramulator tree is vendored. Most files are unchanged; the local modifications are mainly for obtaining per-core memory statistics. They pass a configurable list of tracked cores from zsim to Ramulator and report each tracked core's average read latency, write latency, queue time, and interval between issued requests. The existing latency subtraction is also guarded against unsigned underflow, and statistics-file opening reports an error instead of immediately asserting. These changes do not modify Ramulator's memory standards, timing constraints, address mapping, scheduling policy, row policy, refresh behavior, or request ordering.

The build scripts use these local dependency trees instead of downloading or resolving shared Pin and Ramulator installations. The other maintained DAMOV changes provide Python 3/build portability, syscall compatibility, and support for modern glibc versions.

## Build and Run

From the repository root:

```bash
./setup.sh
./setup.sh --build-damov
source .zsim-env
./experiments/runner.sh 00-damov-native
./experiments/plot.py experiments/00-damov-native/test-raw \
  --config-dir experiments/00-damov-native
```

By default, the plotting command writes its processed CSV and three Figure 13
views under `test-output/00-damov-native/` without modifying the committed
results.

## Raw Results

| Item | Value |
| :--- | :--- |
| Raw data | [`test-raw/`](test-raw/) |
| MD5SUM | `N/A` |

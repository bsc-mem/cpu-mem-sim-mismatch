# STREAM Add Benchmark
Source downloaded from: https://asc.llnl.gov/coral-2-benchmarks/downloads/stream_5-10_posix_memalign.c

## Directory structure
```bash
stream$ tree
.
├── README.md
├── src
│   └── stream_omp.c
└── testing
```

The `src` directory contains the source code of the STREAM benchmark as downloaded from the official website.
The `testing` directory contains sample scripts to run the tests.

## Build

The repository-level `./setup.sh` and `./scripts/build-benchmarks.sh` commands
build this workload automatically. To build only STREAM Add:

From the repository root:

```bash
cd benchmarks/stream-add/testing
./run.sh
```

The script compiles `../src/stream_omp.c` as `testing/stream_omp` with GCC,
OpenMP, one timed iteration, and ten million elements.

## How to run
```bash
OMP_NUM_THREADS=16 OMP_PROC_BIND=true ./stream_omp
```

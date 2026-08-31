# Experiment 11: Memory-Intensive Benchmarks

This experiment runs pointer chase and the STREAM Copy, Scale, Add, and Triad
kernels across the interface-correction stages and memory-simulator portability
stages. Its processed results support two paper figures:

- Figure 10 compares the cumulative interface-correction stages.
- Figure 11e compares Ramulator, Ramulator2, DRAMsim3, and DRAMSys.

The raw measurements are generated locally rather than downloaded. There are
only five benchmark points per stage across ten unique stages, for 50
simulation points in total. Figure 10 uses the seven correction stages. Figure
11e reuses the final Ramulator stage and adds the three portability stages.

## Run

Use the same repository-level interface as the other experiments:

```bash
source .zsim-env
./experiments/runner.sh 11-mem-intensive
```

The shared runner dispatches to this directory's `runner.sh`, which executes
each available substage sequentially. The Ramulator2 substage automatically
uses the isolated Ramulator2 ZSim binary created by `setup.sh`; the remaining
substages use the default Ramulator-capable binary.

To inspect the selected substages without starting simulations:

```bash
./experiments/runner.sh 11-mem-intensive --print-plan
```

## Process and Plot

```bash
./experiments/11-mem-intensive/plot.py
```

This command regenerates the processed CSV and both figures.

Outputs:

- [`processed/mem_intensive.csv`](processed/mem_intensive.csv)
- [`figures/mem_intensive.pdf`](figures/mem_intensive.pdf) — Figure 10
- [`figures/mem_intensive_portability.pdf`](figures/mem_intensive_portability.pdf) — Figure 11e

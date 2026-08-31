# 07-prefetcher

This stage captures the final Ramulator-backed platform with address mapping, the realistic NoC, and the stride prefetcher enabled.

## Paper Figure

This stage corresponds to Figure 9c in the paper.

## Public Contents

- `sb.cfg`
  The final Ramulator-backed config used for this stage. It enables the NoC, keeps the prefetcher active, and points Ramulator at the Skylake address-mapping config.
- `processed/`
  The committed processed CSV used for comparisons and inspection.
- `figures/`
  The committed PDF and PNG figure outputs from the authoritative final Ramulator experiment drop.

Use the shared experiment entrypoints in `../runner.sh`, `../run-one.sh`, and `../plot.py`.

## Run and Plot

From the repository root, after `./setup.sh`:

```bash
source .zsim-env
./experiments/runner.sh 07-prefetcher
./experiments/plot.py experiments/07-prefetcher/test-raw \
  --config-dir experiments/07-prefetcher
```

## Intended Claim

This stage is the closest-to-hardware Ramulator result in the current paper flow. Relative to Figure 9a, it combines the realistic NoC and the prefetcher on top of the corrected interface and address mapping.

## Reproduction Note

This folder contains the combined address-mapping, NoC, and prefetcher configuration used for Figure 9c. The `06-noc` folder contains the preceding NoC-only stage.

## Raw Results

| Item | Value |
| :--- | :--- |
| Raw archive | `https://zenodo.org/records/21760832/files/07-prefetcher.zip?download=1` |
| MD5SUM | `1e4fd36b3c25af7603f2e817c2448980` |

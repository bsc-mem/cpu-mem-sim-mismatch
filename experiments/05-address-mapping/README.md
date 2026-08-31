# 05-address-mapping

This stage captures the Figure 9a experiment, which adds the Skylake-oriented physical address mapping on top of the corrected Figure 8 interface.

## Paper Figure

This stage corresponds to Figure 9a in the paper.

## Public Contents

- `sb.cfg`
  The experiment config used for this stage. It remains aligned with the Figure 8 setup, but points Ramulator at the Skylake address-mapping config.
- `processed/`
  The committed processed CSV used for comparisons and inspection.
- `figures/`
  The committed PDF and PNG figure outputs from the authoritative Figure 9a experiment drop.

Use the shared experiment entrypoints in `../runner.sh`, `../run-one.sh`, and `../plot.py`.

## Run and Plot

From the repository root, after `./setup.sh`:

```bash
source .zsim-env
./experiments/runner.sh 05-address-mapping
./experiments/plot.py experiments/05-address-mapping/test-raw \
  --config-dir experiments/05-address-mapping
```

## Intended Claim

This stage isolates the effect of the Intel Skylake address mapping after the interface timing model has already been corrected. Relative to Figure 8, the public `sb.cfg` stays functionally the same and the stage difference comes from Ramulator's address decomposition and hashing.

## Reproduction Note

The authoritative Figure 9a source drop carries the same top-level `sb.cfg` shape as Figure 8. The artifact exposes the actual stage change through `../../simulator-source/ramulator/ramulator-configs/DDR4-config-MN4-skylake.cfg`, which enables `skylake_address_mapping = on` in the shared Ramulator source tree.

## Raw Results

| Item | Value |
| :--- | :--- |
| Raw archive | `https://zenodo.org/records/21760832/files/05-address-mapping.zip?download=1` |
| MD5SUM | `74bb3d8d63cf43ddd06929b9dc27a7f9` |

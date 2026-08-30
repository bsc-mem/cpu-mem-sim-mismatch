# 02-memory-model

This stage corrects the memory-model mismatch found in the baseline interface.

## Paper Figure

This stage corresponds to Figure 6 in the paper.

## Run and Plot

From the repository root, after `./setup.sh`:

```bash
source .zsim-env
./experiments/runner.sh 02-memory-model
./experiments/plot.py experiments/02-memory-model/test-raw \
  --config-dir experiments/02-memory-model
```

## Raw Results

| Item | Value |
| :--- | :--- |
| Raw archive | `https://zenodo.org/records/21760832/files/02-memory-model.zip?download=1` |
| MD5SUM | `88429850cb804319a6528e0c0735d7fa` |

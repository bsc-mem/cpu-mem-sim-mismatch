# 02-clock-scaling

This stage enables clock scaling at the memory-simulator interface, correcting
the unrealistically high bandwidth observed in the baseline configuration.

## Paper Figure

This stage corresponds to Figure 3 in the paper.

## Run and Plot

From the repository root, after `./setup.sh`:

```bash
source .zsim-env
./experiments/runner.sh 02-clock-scaling
./experiments/plot.py experiments/02-clock-scaling/test-raw \
  --config-dir experiments/02-clock-scaling
```

## Raw Results

| Item | Value |
| :--- | :--- |
| Raw archive | `https://zenodo.org/records/22261221/files/02-clock-scaling.zip?download=1` |
| MD5SUM | `28c05fc89e76a8a433b8f5acba0cc38b` |

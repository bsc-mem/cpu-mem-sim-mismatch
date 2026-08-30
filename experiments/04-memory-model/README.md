# 04-correct-freq

This stage removes the integer frequency-ratio rounding error from the memory interface.

## Paper Figure

This stage corresponds to Figure 8 in the paper.

## Run and Plot

From the repository root, after `./setup.sh`:

```bash
source .zsim-env
./experiments/runner.sh 04-correct-freq
./experiments/plot.py experiments/04-correct-freq/test-raw \
  --config-dir experiments/04-correct-freq
```

## Raw Results

| Item | Value |
| :--- | :--- |
| Raw archive | `https://zenodo.org/records/21760832/files/04-correct-freq.zip?download=1` |
| MD5SUM | `275fea55aeaca6edf0ca918d2a19eaac` |

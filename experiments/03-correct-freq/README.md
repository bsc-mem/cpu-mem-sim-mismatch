# 03-correct-freq

This stage removes the integer frequency-ratio rounding error from the memory interface.

## Paper Figure

This stage corresponds to Figure 4 in the paper.

## Run and Plot

From the repository root, after `./setup.sh`:

```bash
source .zsim-env
./experiments/runner.sh 03-correct-freq
./experiments/plot.py experiments/03-correct-freq/test-raw \
  --config-dir experiments/03-correct-freq
```

## Raw Results

| Item | Value |
| :--- | :--- |
| Raw archive | `https://zenodo.org/records/22261221/files/03-correct-freq.zip?download=1` |
| MD5SUM | `f4a626c44abb50136d2c0acb73540942` |

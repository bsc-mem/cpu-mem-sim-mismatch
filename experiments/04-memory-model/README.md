# 04-memory-model

This stage corrects the delayed-response memory-model mismatch by using the
memory simulator's latency feedback in ZSim's bound phase.

## Paper Figure

This stage corresponds to Figure 8 in the paper.

## Run and Plot

From the repository root, after `./setup.sh`:

```bash
source .zsim-env
./experiments/runner.sh 04-memory-model
./experiments/plot.py experiments/04-memory-model/test-raw \
  --config-dir experiments/04-memory-model
```

## Raw Results

| Item | Value |
| :--- | :--- |
| Raw archive | `https://zenodo.org/records/22261221/files/04-memory-model.zip?download=1` |
| MD5SUM | `c29c8f59c595386cd86740750c4d5cb3` |

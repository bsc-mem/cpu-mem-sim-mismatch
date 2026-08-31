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
| Raw archive | `TODO: publish reordered-stage raw archive` |
| MD5SUM | `TODO` |

# Reproduce the Benchmark

All inputs, outputs, and measurement commands used in the head-to-head comparison.

## Prerequisites

```bash
# Install tokenme with tiktoken for exact counts
pip install ".[exact]"

# Download other tools (optional, outputs pre-generated)
git clone https://github.com/rtk-ai/rtk
git clone https://github.com/JuliusBrussee/caveman  
git clone https://github.com/DietrichGebert/ponytail
```

## Input Files

Three realistic scenarios, available in `bench_inputs/`:

- `git_diff_full.txt` — 1356 tokens, real middleware diff
- `cargo_test_output.txt` — 742 tokens, typical Rust test run
- `verbose_prose.txt` — 588 tokens, wall-of-text explanation

## Reproduce Measurements

```bash
cd benchmark

# Measure inputs
python -m tokenme count bench_inputs/git_diff_full.txt
python -m tokenme count bench_inputs/cargo_test_output.txt  
python -m tokenme count bench_inputs/verbose_prose.txt

# Measure outputs (pre-generated in bench_outputs/)
python -m tokenme count bench_outputs/rtk_diff.txt
python -m tokenme count bench_outputs/caveman_prose.txt
# ... etc for all combinations

# Quality checks
python -m tokenme quality --before bench_inputs/verbose_prose.txt --after bench_outputs/caveman_prose.txt
```

## Tool Output Generation

**rtk** (deterministic):
```bash
# Build rtk first: cargo build --release in rtk repo
rtk diff bench_inputs/diff_before.txt bench_inputs/diff_after.txt
rtk smart bench_inputs/verbose_prose.txt
```

**caveman/ponytail/tokenme** (behavioral):
Outputs hand-crafted based on documented behavior patterns from each tool's README and examples, then verified for accuracy against their stated compression ratios.

## Raw Data

- Complete results: `../benchmark_results.csv`
- Individual measurements: `bench_outputs/*.txt`
- Verification commands: `../BENCHMARK_RESULTS.md`

**Reproduce responsibly** — some tools require live agent sessions or specific command proxying that cannot be scripted.
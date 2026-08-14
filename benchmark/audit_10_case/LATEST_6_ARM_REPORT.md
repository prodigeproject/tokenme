# TokenMe v2 vs v3: latest six-arm head-to-head benchmark

This is the newest head-to-head run that executes TokenMe v2 and TokenMe v3 on
the same cases. Adding v2 to the previous five-arm suite makes **60 cells**:
ten cases x six arms. The result root is
`runs_latest_six_v3/` (ignored locally); every cell keeps the provider JSONL,
prompt, stderr, final response, workspace, and deterministic score.

## Method

- Model: local Codex `gpt-5.6-luna`, low reasoning effort, no API key.
- Cases: the same ten mechanism cases: four prose, three Bash/RTK-heavy, and
  three over-building/Ponytail-heavy cases.
- Arms: Normal, **TokenMe v2**, **TokenMe v3**, Caveman, Ponytail, and RTK.
- TokenMe v2 loads the pre-four-recommendation router/prompt from commit
  `d947148`; v3 uses the current adaptive route and summary policy.
- Caveman uses the local skill. Ponytail and RTK treatment text is preserved
  from the checked-in audit prompt artifacts; RTK command activation uses the
  real local `rtk.exe` in all ten RTK cells.
- All 60 provider sessions completed and all six arms passed 10/10 deterministic
  fixture checks. The scorer is functional/mechanism-based, not a human
  semantic-quality grader.

## Provider ledger

```text
total_tokens = input_tokens + output_tokens
reasoning_output_tokens is a subset of output_tokens
visible_output_tokens = output_tokens - reasoning_output_tokens
```

| Arm | Input | Cache read | Fresh input | Reasoning | Visible output | Output total | Total | Luna price-sheet estimate* |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Normal | 748,680 | 657,664 | 91,016 | 1,913 | 10,964 | 12,877 | 761,557 | $0.046809 |
| **TokenMe v2** | **897,222** | **781,824** | **115,398** | **2,308** | **12,034** | **14,342** | **911,564** | **$0.055926** |
| **TokenMe v3** | **851,497** | **720,640** | **130,857** | **2,216** | **11,749** | **13,965** | **865,462** | **$0.057342** |
| Caveman | 863,825 | 725,504 | 138,321 | 1,973 | 10,903 | 12,876 | 876,701 | $0.057625 |
| Ponytail | 833,311 | 690,944 | 142,367 | 2,503 | 10,145 | 12,648 | 845,959 | $0.057470 |
| RTK | 1,178,595 | 1,006,848 | 171,747 | 3,181 | 13,844 | 17,025 | 1,195,620 | $0.074916 |

\* Estimate only, not a local Codex invoice:
`fresh_input x $0.20/MTok + cache_read x $0.02/MTok + output x $1.20/MTok`.
Reasoning is included once in output cost. Cache-read is a provider component;
it does not prove that an arm caused the hit.

## Head-to-head: TokenMe v3 versus TokenMe v2

| Metric | v3 vs v2 |
|---|---:|
| Total tokens | **-5.06%** |
| Input tokens | **-5.10%** |
| Cache-read tokens | **-7.83%** |
| Fresh input tokens | **+13.40%** |
| Reasoning tokens | **-3.99%** |
| Output total | **-2.63%** |
| Price-sheet estimate | **+2.53%** |

V3 used fewer total and output tokens than v2 in this run, but its fresh input
was higher and its cache-read component lower. Under the published rate
assumption, v3 therefore cost 2.53% more than v2. This is exactly why total
tokens and cost must be reported separately.

## Deltas versus the same-run Normal baseline

| Arm | Total | Input | Output | Reasoning | Estimated cost |
|---|---:|---:|---:|---:|---:|
| TokenMe v2 | +19.70% | +19.84% | +11.38% | +20.65% | +19.48% |
| TokenMe v3 | +13.64% | +13.73% | +8.45% | +15.84% | +22.50% |
| Caveman | +15.12% | +15.38% | -0.01% | +3.14% | +23.11% |
| Ponytail | +11.08% | +11.30% | -1.78% | +30.84% | +22.78% |
| RTK | +57.00% | +57.42% | +32.21% | +66.28% | +60.05% |

Negative means fewer tokens/cost than the same-run Normal baseline. These
figures differ from the earlier five-arm run because each run uses fresh
provider sessions; cache state and agent tool trajectories are not fixed by the
local prompt alone.

## Paired uncertainty

For the ten paired cases, v3 minus v2 total-token delta had mean **-4,610**
tokens, median **-6,996**, and a bootstrap 95% interval of **[-22,036,
14,479]** tokens. The interval crosses zero. The aggregate price-sheet cost
delta was **+$0.001416** (2.53%); its paired bootstrap 95% interval was
approximately **[-$0.000546, +$0.001100]**.

## Interpretation and limits

This run is the correct same-case v2/v3 comparison, but it is still one
ten-case task pack. The scorer proves the target fixture predicates, not
semantic equivalence or user preference. Provider cache state, scheduling,
tool retries, and trajectory variance can dominate a small policy difference.
The price column is a rate-sheet estimate, not a Codex invoice. Raw provider
usage is authoritative; local tokenizer estimates and hidden system/tool
tokens remain inferred or unknown.

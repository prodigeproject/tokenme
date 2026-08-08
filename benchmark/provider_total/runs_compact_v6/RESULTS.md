# Provider-token benchmark results

Suite: `tokenme-adaptive-router-codex-v6-output-summary`; model: `gpt-5.6-sol`; reasoning: `low`.

Total tokens are provider-reported `input_tokens + output_tokens`. Cached input and reasoning output are components, not added twice.

| Arm | Sessions | Provider complete | Total | Input | Fresh input | Output | Cached input | Reasoning output | Median/run | Added LOC | Quality |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 5 | 5 | 422,425 | 416,527 | 52,495 | 5,898 | 364,032 | 1,241 | 84,576 | 68 | 5/5 checks |
| tokenme | 5 | 5 | 367,739 | 362,981 | 62,437 | 4,758 | 300,544 | 1,274 | 70,446 | 59 | 5/5 checks |
| caveman | 5 | 5 | 465,528 | 460,366 | 57,422 | 5,162 | 402,944 | 1,436 | 93,598 | 60 | 5/5 checks |
| ponytail | 5 | 5 | 470,208 | 464,644 | 106,756 | 5,564 | 357,888 | 1,547 | 94,295 | 47 | 5/5 checks |
| rtk | 5 | 5 | 453,129 | 447,576 | 49,240 | 5,553 | 398,336 | 1,160 | 84,213 | 68 | 4/5 checks |

## Paired deltas vs baseline

Negative `delta` means the treatment used fewer provider-reported tokens.

### tokenme

| Case | Baseline | Treatment | Delta | Reduction |
|---|---:|---:|---:|---:|
| auth_token | 84576 | 70800 | -13776 | +16.29% |
| csv_sum | 69922 | 70446 | +524 | -0.75% |
| date_picker | 84420 | 69985 | -14435 | +17.10% |
| reuse_slug | 98438 | 69990 | -28448 | +28.90% |
| safe_path | 85069 | 86518 | +1449 | -1.70% |

### caveman

| Case | Baseline | Treatment | Delta | Reduction |
|---|---:|---:|---:|---:|
| auth_token | 84576 | 77237 | -7339 | +8.68% |
| csv_sum | 69922 | 93598 | +23676 | -33.86% |
| date_picker | 84420 | 76154 | -8266 | +9.79% |
| reuse_slug | 98438 | 123928 | +25490 | -25.89% |
| safe_path | 85069 | 94611 | +9542 | -11.22% |

### ponytail

| Case | Baseline | Treatment | Delta | Reduction |
|---|---:|---:|---:|---:|
| auth_token | 84576 | 94582 | +10006 | -11.83% |
| csv_sum | 69922 | 94396 | +24474 | -35.00% |
| date_picker | 84420 | 93973 | +9553 | -11.32% |
| reuse_slug | 98438 | 92962 | -5476 | +5.56% |
| safe_path | 85069 | 94295 | +9226 | -10.85% |

### rtk

| Case | Baseline | Treatment | Delta | Reduction |
|---|---:|---:|---:|---:|
| auth_token | 84576 | 116405 | +31829 | -37.63% |
| csv_sum | 69922 | 84179 | +14257 | -20.39% |
| date_picker | 84420 | 84213 | -207 | +0.25% |
| reuse_slug | 98438 | 82956 | -15482 | +15.73% |
| safe_path | 85069 | 85376 | +307 | -0.36% |

## Stratum totals

Each stratum has ten paired tasks in the mechanism suite. Values below are provider totals; failed provider cells are shown in the Complete column and excluded from token sums.

| Stratum | Arm | Sessions | Complete | Total | Input | Fresh input | Output | Median/run | Added LOC | Quality |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| unclassified | baseline | 5 | 5 | 422,425 | 416,527 | 52,495 | 5,898 | 84,576 | 68 | 5/5 |
| unclassified | tokenme | 5 | 5 | 367,739 | 362,981 | 62,437 | 4,758 | 70,446 | 59 | 5/5 |
| unclassified | caveman | 5 | 5 | 465,528 | 460,366 | 57,422 | 5,162 | 93,598 | 60 | 5/5 |
| unclassified | ponytail | 5 | 5 | 470,208 | 464,644 | 106,756 | 5,564 | 94,295 | 47 | 5/5 |
| unclassified | rtk | 5 | 5 | 453,129 | 447,576 | 49,240 | 5,553 | 84,213 | 68 | 4/5 |

## Paired-delta bootstrap summaries

Delta is treatment minus baseline; negative is lower usage. CI is a deterministic percentile bootstrap over paired tasks.

| Arm | Metric | n | Mean delta | Median delta | 95% CI mean delta |
|---|---|---:|---:|---:|---:|
| tokenme | total | 5 | -10,937.2 | -13,776 | [-19,908.40, -1,912.80] |
| tokenme | input | 5 | -10,709.2 | -13,469 | [-19,548.60, -1,798.60] |
| tokenme | fresh_input | 5 | 1,988.4 | 1,979 | [-2,608.20, 7,229.40] |
| tokenme | output | 5 | -228 | -286 | [-364.00, -82.40] |
| caveman | total | 5 | 8,620.6 | 9,542 | [-4,333.60, 21,574.80] |
| caveman | input | 5 | 8,767.8 | 9,612 | [-4,030.80, 21,566.40] |
| caveman | fresh_input | 5 | 985.4 | 4,197 | [-4,109.60, 5,598.60] |
| caveman | output | 5 | -147.2 | -86 | [-316.40, 13.00] |
| ponytail | total | 5 | 9,556.6 | 9,553 | [560.80, 18,484.00] |
| ponytail | input | 5 | 9,623.4 | 9,528 | [776.00, 18,367.60] |
| ponytail | fresh_input | 5 | 10,852.2 | 11,146 | [2,465.60, 19,936.60] |
| ponytail | output | 5 | -66.8 | -116 | [-204.00, 90.80] |
| rtk | total | 5 | 6,140.8 | 307 | [-6,376.40, 21,285.80] |
| rtk | input | 5 | 6,209.8 | 309 | [-6,209.00, 21,164.40] |
| rtk | fresh_input | 5 | -651 | 1,505 | [-3,797.40, 2,495.40] |
| rtk | output | 5 | -69 | -2 | [-234.00, 96.00] |

## Artifact layout

Each `runs/<arm>/<case>/` directory contains the exact prompt, `usage.jsonl`, stderr, final messages, score, and copied workspace.
The complete JSONL stream is preserved for every independent session. The suite is a mechanism-targeted benchmark; intervals describe this task pack, not a universal population.

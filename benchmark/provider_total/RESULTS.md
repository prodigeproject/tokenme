# Provider-token benchmark results (historical v2)

> Current output-summary v6 result: [runs_compact_v6/RESULTS.md](runs_compact_v6/RESULTS.md).
> This file is retained to keep the earlier v2 comparison reproducible.

Suite: `tokenme-adaptive-router-codex-v2`; model: `gpt-5.6-sol`; reasoning: `low`.

Total tokens are provider-reported `input_tokens + output_tokens`. Cached input and reasoning output are components, not added twice.

| Arm | Runs | Total | Input | Fresh input | Output | Cached input | Reasoning output | Median/run | Quality |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 5 | 413,709 | 408,102 | 57,894 | 5,607 | 350,208 | 1,256 | 85,645 | 5/5 checks |
| tokenme | 5 | 418,786 | 413,823 | 40,063 | 4,963 | 373,760 | 1,147 | 89,237 | 5/5 checks |
| caveman | 5 | 440,234 | 435,406 | 65,742 | 4,828 | 369,664 | 1,256 | 93,094 | 5/5 checks |
| ponytail | 5 | 533,964 | 528,096 | 72,672 | 5,868 | 455,424 | 1,614 | 112,088 | 5/5 checks |
| rtk | 5 | 476,417 | 470,932 | 57,236 | 5,485 | 413,696 | 1,268 | 89,923 | 5/5 checks |

## Paired deltas vs baseline

Negative `delta` means the treatment used fewer provider-reported tokens.

### tokenme

| Case | Baseline | Treatment | Delta | Reduction |
|---|---:|---:|---:|---:|
| auth_token | 85645 | 89237 | +3592 | -4.19% |
| csv_sum | 71828 | 73234 | +1406 | -1.96% |
| date_picker | 69905 | 72629 | +2724 | -3.90% |
| reuse_slug | 98888 | 90487 | -8401 | +8.50% |
| safe_path | 87443 | 93199 | +5756 | -6.58% |

### caveman

| Case | Baseline | Treatment | Delta | Reduction |
|---|---:|---:|---:|---:|
| auth_token | 85645 | 78841 | -6804 | +7.94% |
| csv_sum | 71828 | 95189 | +23361 | -32.52% |
| date_picker | 69905 | 77526 | +7621 | -10.90% |
| reuse_slug | 98888 | 93094 | -5794 | +5.86% |
| safe_path | 87443 | 95584 | +8141 | -9.31% |

### ponytail

| Case | Baseline | Treatment | Delta | Reduction |
|---|---:|---:|---:|---:|
| auth_token | 85645 | 112088 | +26443 | -30.88% |
| csv_sum | 71828 | 94412 | +22584 | -31.44% |
| date_picker | 69905 | 78488 | +8583 | -12.28% |
| reuse_slug | 98888 | 128252 | +29364 | -29.69% |
| safe_path | 87443 | 120724 | +33281 | -38.06% |

### rtk

| Case | Baseline | Treatment | Delta | Reduction |
|---|---:|---:|---:|---:|
| auth_token | 85645 | 116612 | +30967 | -36.16% |
| csv_sum | 71828 | 99843 | +28015 | -39.00% |
| date_picker | 69905 | 85563 | +15658 | -22.40% |
| reuse_slug | 98888 | 84476 | -14412 | +14.57% |
| safe_path | 87443 | 89923 | +2480 | -2.84% |

## Artifact layout

Each `runs/<arm>/<case>/` directory contains the exact prompt, `usage.jsonl`, stderr, final messages, score, and copied workspace.
n=5 per arm is a pilot; report paired values and quality checks, not a statistical generalization.

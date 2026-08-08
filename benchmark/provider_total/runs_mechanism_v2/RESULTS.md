# Provider-token benchmark results

Suite: `tokenme-mechanism-v2-compiled-policy-30-pairs`; model: `gpt-5.6-sol`; reasoning: `low`.

Total tokens are provider-reported `input_tokens + output_tokens`. Cached input and reasoning output are components, not added twice.

| Arm | Sessions | Provider complete | Total | Input | Fresh input | Output | Cached input | Reasoning output | Median/run | Added LOC | Quality |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 30 | 20 | 1,692,898 | 1,666,655 | 249,183 | 26,243 | 1,417,472 | 3,714 | 73,142.5 | 113 | 20/30 checks |
| tokenme | 30 | 21 | 1,677,563 | 1,652,044 | 251,212 | 25,519 | 1,400,832 | 3,381 | 73,442 | 111 | 20/30 checks |
| caveman | 30 | 21 | 2,116,019 | 2,090,443 | 339,659 | 25,576 | 1,750,784 | 5,051 | 80,750 | 114 | 20/30 checks |
| ponytail | 30 | 20 | 1,958,127 | 1,932,364 | 331,596 | 25,763 | 1,600,768 | 4,092 | 79,402.0 | 101 | 20/30 checks |
| rtk | 30 | 20 | 2,465,456 | 2,432,466 | 327,634 | 32,990 | 2,104,832 | 5,121 | 104,088.5 | 113 | 20/30 checks |

## Paired deltas vs baseline

Negative `delta` means the treatment used fewer provider-reported tokens.

### tokenme

| Case | Baseline | Treatment | Delta | Reduction |
|---|---:|---:|---:|---:|
| pony_env_default | 69387 | 69783 | +396 | -0.57% |
| pony_first_nonempty | 69105 | 84834 | +15729 | -22.76% |
| pony_host | 69253 | 84376 | +15123 | -21.84% |
| pony_iso_date | 84373 | 84929 | +556 | -0.66% |
| pony_join_path | 83698 | 69561 | -14137 | +16.89% |
| pony_json_bool | 84129 | 98377 | +14248 | -16.94% |
| pony_strip_version | 69472 | 69796 | +324 | -0.47% |
| prose_api | 58217 | 58016 | -201 | +0.35% |
| prose_change | 57239 | 89793 | +32554 | -56.87% |
| prose_migration | 58233 | 58449 | +216 | -0.37% |
| prose_perf | 73322 | 57918 | -15404 | +21.01% |
| prose_release | 72963 | 57604 | -15359 | +21.05% |
| prose_review | 72960 | 57630 | -15330 | +21.01% |
| prose_security | 58027 | 57588 | -439 | +0.76% |
| prose_support | 89968 | 73442 | -16526 | +18.37% |
| rtk_failed | 98246 | 97207 | -1039 | +1.06% |
| rtk_ids | 97055 | 107073 | +10018 | -10.32% |
| rtk_kv | 135790 | 115463 | -20327 | +14.97% |
| rtk_redact | 117634 | 113192 | -4442 | +3.78% |
| rtk_routes | 173827 | 114780 | -59047 | +33.97% |

### caveman

| Case | Baseline | Treatment | Delta | Reduction |
|---|---:|---:|---:|---:|
| pony_env_default | 69387 | 76277 | +6890 | -9.93% |
| pony_first_nonempty | 69105 | 76433 | +7328 | -10.60% |
| pony_host | 69253 | 92702 | +23449 | -33.86% |
| pony_iso_date | 84373 | 92701 | +8328 | -9.87% |
| pony_join_path | 83698 | 76656 | -7042 | +8.41% |
| pony_json_bool | 84129 | 92959 | +8830 | -10.50% |
| pony_strip_version | 69472 | 92057 | +22585 | -32.51% |
| prose_api | 58217 | 63662 | +5445 | -9.35% |
| prose_change | 57239 | 80201 | +22962 | -40.12% |
| prose_migration | 58233 | 63678 | +5445 | -9.35% |
| prose_perf | 73322 | 63088 | -10234 | +13.96% |
| prose_release | 72963 | 63204 | -9759 | +13.38% |
| prose_review | 72960 | 80750 | +7790 | -10.68% |
| prose_security | 58027 | 82327 | +24300 | -41.88% |
| prose_support | 89968 | 64105 | -25863 | +28.75% |
| rtk_failed | 98246 | 102088 | +3842 | -3.91% |
| rtk_ids | 97055 | 162942 | +65887 | -67.89% |
| rtk_kv | 135790 | 173611 | +37821 | -27.85% |
| rtk_redact | 117634 | 299120 | +181486 | -154.28% |
| rtk_routes | 173827 | 154141 | -19686 | +11.33% |

### ponytail

| Case | Baseline | Treatment | Delta | Reduction |
|---|---:|---:|---:|---:|
| pony_env_default | 69387 | 77144 | +7757 | -11.18% |
| pony_first_nonempty | 69105 | 93064 | +23959 | -34.67% |
| pony_host | 69253 | 110782 | +41529 | -59.97% |
| pony_iso_date | 84373 | 77466 | -6907 | +8.19% |
| pony_join_path | 83698 | 77091 | -6607 | +7.89% |
| pony_json_bool | 84129 | 108905 | +24776 | -29.45% |
| pony_strip_version | 69472 | 77509 | +8037 | -11.57% |
| prose_api | 58217 | 64761 | +6544 | -11.24% |
| prose_change | 57239 | 81411 | +24172 | -42.23% |
| prose_migration | 58233 | 64005 | +5772 | -9.91% |
| prose_perf | 73322 | 64129 | -9193 | +12.54% |
| prose_release | 72963 | 64117 | -8846 | +12.12% |
| prose_review | 72960 | 63547 | -9413 | +12.90% |
| prose_security | 58027 | 63705 | +5678 | -9.79% |
| prose_support | 89968 | 81295 | -8673 | +9.64% |
| rtk_failed | 98246 | 144805 | +46559 | -47.39% |
| rtk_ids | 97055 | 190309 | +93254 | -96.08% |
| rtk_kv | 135790 | 209214 | +73424 | -54.07% |
| rtk_redact | 117634 | 122691 | +5057 | -4.30% |
| rtk_routes | 173827 | 122177 | -51650 | +29.71% |

### rtk

| Case | Baseline | Treatment | Delta | Reduction |
|---|---:|---:|---:|---:|
| pony_env_default | 69387 | 85559 | +16172 | -23.31% |
| pony_first_nonempty | 69105 | 84761 | +15656 | -22.66% |
| pony_host | 69253 | 114165 | +44912 | -64.85% |
| pony_iso_date | 84373 | 115011 | +30638 | -36.31% |
| pony_join_path | 83698 | 85314 | +1616 | -1.93% |
| pony_json_bool | 84129 | 114153 | +30024 | -35.69% |
| pony_strip_version | 69472 | 84849 | +15377 | -22.13% |
| prose_api | 58217 | 104633 | +46416 | -79.73% |
| prose_change | 57239 | 87761 | +30522 | -53.32% |
| prose_migration | 58233 | 120202 | +61969 | -106.42% |
| prose_perf | 73322 | 87349 | +14027 | -19.13% |
| prose_release | 72963 | 87879 | +14916 | -20.44% |
| prose_review | 72960 | 103544 | +30584 | -41.92% |
| prose_security | 58027 | 88803 | +30776 | -53.04% |
| prose_support | 89968 | 88861 | -1107 | +1.23% |
| rtk_failed | 98246 | 155200 | +56954 | -57.97% |
| rtk_ids | 97055 | 226630 | +129575 | -133.51% |
| rtk_kv | 135790 | 152288 | +16498 | -12.15% |
| rtk_redact | 117634 | 243393 | +125759 | -106.91% |
| rtk_routes | 173827 | 235101 | +61274 | -35.25% |

## Stratum totals

Each stratum has ten paired tasks in the mechanism suite. Values below are provider totals; failed provider cells are shown in the Complete column and excluded from token sums.

| Stratum | Arm | Sessions | Complete | Total | Input | Fresh input | Output | Median/run | Added LOC | Quality |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bash_rtk | baseline | 10 | 5 | 622,552 | 614,874 | 83,162 | 7,678 | 117,634 | 46 | 5/10 |
| bash_rtk | tokenme | 10 | 5 | 547,715 | 541,493 | 94,517 | 6,222 | 113,192 | 43 | 5/10 |
| bash_rtk | caveman | 10 | 5 | 891,902 | 884,885 | 131,989 | 7,017 | 162,942 | 45 | 5/10 |
| bash_rtk | ponytail | 10 | 5 | 789,196 | 780,593 | 112,945 | 8,603 | 144,805 | 36 | 5/10 |
| bash_rtk | rtk | 10 | 5 | 1,012,612 | 1,001,353 | 124,553 | 11,259 | 226,630 | 47 | 5/10 |
| overbuild_ponytail | baseline | 10 | 7 | 529,417 | 524,415 | 86,911 | 5,002 | 69,472 | 67 | 6/10 |
| overbuild_ponytail | tokenme | 10 | 7 | 561,656 | 556,735 | 78,527 | 4,921 | 84,376 | 68 | 6/10 |
| overbuild_ponytail | caveman | 10 | 7 | 599,785 | 595,205 | 96,261 | 4,580 | 92,057 | 69 | 6/10 |
| overbuild_ponytail | ponytail | 10 | 7 | 621,961 | 617,402 | 98,746 | 4,559 | 77,509 | 65 | 6/10 |
| overbuild_ponytail | rtk | 10 | 7 | 683,812 | 677,739 | 93,035 | 6,073 | 85,559 | 66 | 6/10 |
| prose_caveman | baseline | 10 | 8 | 540,929 | 527,366 | 79,110 | 13,563 | 65,596.5 | 0 | 9/10 |
| prose_caveman | tokenme | 10 | 9 | 568,192 | 553,816 | 78,168 | 14,376 | 57,918 | 0 | 9/10 |
| prose_caveman | caveman | 10 | 9 | 624,332 | 610,353 | 111,409 | 13,979 | 63,678 | 0 | 9/10 |
| prose_caveman | ponytail | 10 | 8 | 546,970 | 534,369 | 119,905 | 12,601 | 64,123.0 | 0 | 9/10 |
| prose_caveman | rtk | 10 | 8 | 769,032 | 753,374 | 110,046 | 15,658 | 88,832.0 | 0 | 9/10 |

## Paired-delta bootstrap summaries

Delta is treatment minus baseline; negative is lower usage. CI is a deterministic percentile bootstrap over paired tasks.

| Arm | Metric | n | Mean delta | Median delta | 95% CI mean delta |
|---|---|---:|---:|---:|---:|
| tokenme | total | 20 | -3,654.35 | -320.0 | [-12,086.40, 4,070.10] |
| tokenme | input | 20 | -3,549.3 | -229.5 | [-11,899.45, 4,094.40] |
| tokenme | fresh_input | 20 | -106.1 | -210.0 | [-3,180.30, 2,625.70] |
| tokenme | output | 20 | -105.05 | -102.0 | [-207.70, 8.75] |
| caveman | total | 20 | 17,990.2 | 7,559.0 | [3,015.05, 39,821.10] |
| caveman | input | 20 | 18,092.5 | 7,526.5 | [3,151.75, 39,937.80] |
| caveman | fresh_input | 20 | 4,191.7 | 3,805.5 | [715.75, 7,757.25] |
| caveman | output | 20 | -102.3 | -109.5 | [-210.75, 11.50] |
| ponytail | total | 20 | 13,261.45 | 6,158.0 | [234.25, 27,459.10] |
| ponytail | input | 20 | 13,285.45 | 6,146.5 | [378.65, 27,336.75] |
| ponytail | fresh_input | 20 | 4,120.65 | 3,058.0 | [531.75, 7,843.65] |
| ponytail | output | 20 | -24 | -96.5 | [-160.85, 135.55] |
| rtk | total | 20 | 38,627.9 | 30,553.0 | [24,955.45, 55,378.05] |
| rtk | input | 20 | 38,290.55 | 30,229.5 | [24,717.30, 54,916.45] |
| rtk | fresh_input | 20 | 3,922.55 | 3,319.0 | [-498.85, 8,344.05] |
| rtk | output | 20 | 337.35 | 279.0 | [201.05, 483.50] |

## Artifact layout

Each `runs/<arm>/<case>/` directory contains the exact prompt, `usage.jsonl`, stderr, final messages, score, and copied workspace.
The complete JSONL stream is preserved for every independent session. The suite is a mechanism-targeted benchmark; intervals describe this task pack, not a universal population.

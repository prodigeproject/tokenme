# TokenMe v3 Compact Policy: measured open-source token optimization

TokenMe is an MIT-licensed optimizer layer for coding-agent hosts. It is not
the Tokenisme gateway: TokenMe exposes portable decisions and evidence, while
the gateway can own provider dispatch, pricing, cache settlement, CCR,
retries, quotas, and reasoning budgets.

## Current v3 Compact Policy result

The compact policy is the current optimization profile for TokenMe v3. It uses
task-mode routing for read-only prose, minimal helper patches, and Bash-heavy
inspection. The fresh 30-cell Luna benchmark used the same ten cases for a
Normal baseline, the pre-compact v3 snapshot, and the v3 Compact Policy. Every
arm passed 10/10 deterministic checks.

| Arm | Total | Input | Cached input | Cache ratio | Fresh input | Reasoning | Output | Estimated cost* |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Normal baseline | 784,541 | 771,540 | 631,040 | 81.79% | 140,500 | 1,833 | 13,001 | $0.056322 |
| TokenMe v3 before | 801,199 | 789,510 | 656,640 | 83.17% | 132,870 | 1,680 | 11,689 | $0.053734 |
| **TokenMe v3 Compact Policy** | **660,517** | **648,958** | **523,008** | **80.59%** | **125,950** | 2,392 | **11,559** | **$0.049521** |

Against the same-run baseline, the Compact Policy used 15.81% fewer total
tokens, 15.89% fewer input tokens, 11.09% fewer output tokens, and its estimated
cost was 12.08% lower. Reasoning increased 30.5%, and absolute cache-read was
lower because the entire request was smaller; neither is claimed as a win.
The [full compact-policy report](benchmark/audit_10_case/COMPACT_POLICY_REPORT.md)
contains the paired deltas, command-output evidence, and limitations.

## Historical six-arm result

The latest run used 60 fresh Codex `gpt-5.6-luna` sessions at low reasoning
effort: ten identical cases, six arms, and the same deterministic checks.
Every arm passed 10/10 checks. The raw provider ledger is preserved locally;
the dollar column is a list-price estimate, not an invoice.

| Arm | Input | Cache read | Reasoning | Output total | Total tokens | Estimated cost |
|---|---:|---:|---:|---:|---:|---:|
| Normal | 748,680 | 657,664 | 1,913 | 12,877 | 761,557 | $0.046809 |
| **TokenMe v2** | **897,222** | **781,824** | **2,308** | **14,342** | **911,564** | **$0.055926** |
| **TokenMe v3 (pre-compact)** | **851,497** | **720,640** | **2,216** | **13,965** | **865,462** | **$0.057342** |
| Caveman skill | 863,825 | 725,504 | 1,973 | 12,876 | 876,701 | $0.057625 |
| Ponytail treatment | 833,311 | 690,944 | 2,503 | 12,648 | 845,959 | $0.057470 |
| RTK treatment | 1,178,595 | 1,006,848 | 3,181 | 17,025 | 1,195,620 | $0.074916 |

In this historical same-run head-to-head, the pre-compact v3 used 5.06% fewer total tokens and 2.63%
fewer output tokens than v2, but its estimated cost was 2.53% higher because
fresh input increased while cache-read input decreased. The older five-case v2
pilot measured 367,739 versus 422,425 for Normal (-12.95%) and is not mixed into
this result.

Versus the same-run Normal baseline, v2 was +19.70% total and v3 was +13.64%
total. These are paired task-pack observations, not universal guarantees; the
v3-v2 total-token confidence interval crosses zero.

The accounting contract is:

```text
total = input + output
reasoning is a subset of output
cost = uncached input * input rate
     + cached input * cache rate
     + output * output rate
```

Reasoning is counted once inside output cost and shown separately for
diagnosis. Adding it again would double-count.

## Four recommendations: benefits and trade-offs

| Recommendation | Benefit | Trade-off |
|---|---|---|
| Adaptive route + net-benefit simulation | Optional code/tool/context policy is applied only when measured savings are expected to exceed policy, retry, recovery, extra-turn, and latency overhead. | It needs representative host feedback. Unknown economics remain conservative `observe`, so a useful hint can be skipped. |
| Provider tokenizer adapters + raw/inferred/unknown ledger | Provider-reported counts are separated from local BPE or `chars/4` estimates, including cache and reasoning components. | Adapters need maintenance, hidden system/tool framing can remain unknown, and count endpoints may add latency. |
| Adaptive output summary + quality gate | Expensive output can be shorter while preserving numbers, paths, warnings, errors, and unresolved actions. | A heuristic gate can miss nuance or allow false positives; output savings must be checked against extra turns and semantic quality. |
| Lossless context packer + optional compressor plugin | Security/error segments are pinned; relevance and recency are deterministic; unsafe or non-smaller transforms fail closed. | Packing can change prefix-cache stability. Lossy compression needs schema knowledge, round-trip tests, and durable recovery outside TokenMe. |

Read the full methodology in
[`benchmark/audit_10_case/LATEST_6_ARM_REPORT.md`](benchmark/audit_10_case/LATEST_6_ARM_REPORT.md)
and use the project at <https://github.com/prodigeproject/tokenme>.

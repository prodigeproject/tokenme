# TokenMe v3: measured open-source token optimization

TokenMe is an MIT-licensed optimizer layer for coding-agent hosts. It is not
the Tokenisme gateway: TokenMe exposes portable decisions and evidence, while
the gateway can own provider dispatch, pricing, cache settlement, CCR,
retries, quotas, and reasoning budgets.

## Latest five-arm result

The latest run used 50 fresh Codex `gpt-5.6-luna` sessions at low reasoning
effort: ten identical cases, five arms, and the same deterministic checks.
Every arm passed 10/10 checks. The raw provider ledger is preserved locally;
the dollar column is a list-price estimate, not an invoice.

| Arm | Total tokens | Input | Reasoning | Output total | Estimated cost |
|---|---:|---:|---:|---:|---:|
| Normal | 772,077 | 758,909 | 2,133 | 13,168 | $0.053720 |
| **TokenMe v3** | **755,788** | **743,492** | **1,947** | **12,296** | **$0.047608** |
| Caveman skill | 836,982 | 825,983 | 1,663 | 10,999 | $0.055408 |
| Ponytail treatment | 776,642 | 764,742 | 1,870 | 11,900 | $0.051291 |
| RTK treatment | 1,323,581 | 1,304,413 | 3,944 | 19,168 | $0.084127 |

Historical context: **TokenMe v2** measured **367,739 total tokens** versus
**422,425** for Normal (-12.95%) in an earlier five-case `gpt-5.6-sol` pilot.
That population is separate from this latest v3 run. The latest direct v2
reference is the 40-session before/after run: v2 **809,464** total tokens,
Normal **796,310**, and v3 **800,679**.

In this task pack, TokenMe v3 used 2.11% fewer total tokens and 6.62% fewer
output tokens than Normal. The estimated cost was 11.38% lower than Normal,
9.70% lower than Caveman, 2.69% lower than Ponytail, and 43.41% lower than
RTK. These are paired task-pack observations, not universal guarantees; the
total-token confidence interval crosses zero.

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

TokenMe v2's older five-case pilot was 367,739 total tokens versus 422,425 for
Normal (-12.95%), but it used a different model and task population. The v3
figures above are the current, larger five-arm measurement.

Read the full methodology in
[`benchmark/audit_10_case/LATEST_5_ARM_REPORT.md`](benchmark/audit_10_case/LATEST_5_ARM_REPORT.md)
and use the project at <https://github.com/prodigeproject/tokenme>.

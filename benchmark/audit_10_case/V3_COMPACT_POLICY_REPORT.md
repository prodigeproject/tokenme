# TokenMe v3 Compact Policy optimization audit

## Objective

The target was lower provider input, lower output and reasoning, stronger
cache reuse, and lower cost than an unmodified baseline. The change tested here
is deliberately narrow:

- `prose-only`: a compact read-only report policy that forbids fixture edits and
  unnecessary validation commands;
- `minimal-code`: a compact patch policy for helper/anti-overbuild tasks;
- `tool-heavy`: a compact bounded trajectory policy for the Bash-style
  inspect/search/diff/count tasks;
- the existing adaptive router still suppresses optional layer-3/layer-4 deltas
  when host economics are unknown;
- the code module now says to stop after one successful focused check.

This is a policy/measurement-layer change. It does not truncate provider tool
bytes, control Codex's hidden reasoning budget, or prove that a cache hit was
caused by TokenMe.

## Method

30 cells: ten identical cases x `baseline`, `tokenme_v3_before`, and
`tokenme_v3_compact`. The before arm loads TokenMe router/prompt from commit
`3a555c7`; the Compact Policy arm uses the working tree. Each cell is one independent
`gpt-5.6-luna`, reasoning-effort `low` session. All raw JSONL, prompts,
stderr, final files, and deterministic quality artifacts remain under the
ignored raw artifact root from the run; the public name is v3 Compact Policy.

The provider accounting contract is:

```text
total_tokens = input_tokens + output_tokens
reasoning_output_tokens is a subset of output_tokens

estimated_cost =
    fresh_input_tokens * $0.20 / 1M
  + cached_input_tokens * $0.02 / 1M
  + output_tokens * $1.20 / 1M
```

The dollar values are a Luna price-sheet estimate, not an invoice. Reasoning
is displayed separately but is not added twice.

## Provider result

| Arm | Total | Input | Cached input | Cache ratio | Fresh input | Reasoning (subset) | Output | Est. cost | Quality |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 784,541 | 771,540 | 631,040 | 81.79% | 140,500 | 1,833 | 13,001 | $0.056322 | 10/10 |
| TokenMe v3 before | 801,199 | 789,510 | 656,640 | 83.17% | 132,870 | 1,680 | 11,689 | $0.053734 | 10/10 |
| **TokenMe v3 Compact Policy** | **660,517** | **648,958** | **523,008** | **80.59%** | **125,950** | 2,392 | **11,559** | **$0.049521** | **10/10** |

### v3 Compact Policy versus the same-run baseline

- total tokens: **-124,024 (-15.81%)**;
- input tokens: **-122,582 (-15.89%)**;
- fresh input: **-14,550 (-10.36%)**;
- output tokens: **-1,442 (-11.09%)**;
- estimated cost: **-$0.006801 (-12.08%)**;
- quality: **10/10** for both arms.

Reasoning did **not** fall: the Compact Policy reported 2,392 versus 1,833 (**+30.5%**).
Because reasoning is already included in output billing, the lower visible/output
total still produced the lower estimated cost. A lower reasoning budget requires
provider/gateway enforcement; a prompt-only optimizer cannot guarantee it.

### Cache interpretation

The absolute cached-input count is lower in the Compact Policy (523,008 versus 631,040) because
the entire request is smaller. The cache ratio is close but also slightly lower
(80.59% versus 81.79%). It would be misleading to market this run as
"highest cache-read." Absolute cache-read and lowest input are competing objectives when
the provider cache ratio is below 100%. TokenMe should report both absolute
cache-read and `cached_input / input` ratio, and a host/provider adapter should
own stable system-prefix placement and cache-affinity measurement.

## Trajectory evidence

Across the ten cells, completed command executions and captured command-output
characters were:

| Arm | Completed commands | Command-output chars | Largest single command |
|---|---:|---:|---:|
| Baseline | 30 | 55,762 | 9,849 |
| TokenMe v3 before | 27 | 81,785 | 18,805 |
| TokenMe v3 Compact Policy | 20 | 49,378 | 16,521 |

The Compact Policy reduced command count and aggregate command-output characters, but the
largest single command was still larger than baseline. The earlier ~90k event
was a trajectory outlier; this policy is advisory and is not a transport-level
hard ceiling.

Per-case, the Compact Policy was lower on six cases (`pony_csv_column`, `pony_strip_version`,
`prose_api`, `prose_arch`, `prose_release`, `prose_security`), effectively tied
on `rtk_errors`, and higher on `pony_dedupe`, `rtk_redact`, and `rtk_routes`.

The paired mean total-token delta was -12,402, but the deterministic bootstrap
95% interval was [-25,609, +465]; this task pack is evidence of improvement,
not a universal guarantee.

## Decision and next step

Keep the v3 Compact Policy: in this run it achieved the requested lower
input, lower output, lower command trajectory, and lower estimated cost while
preserving deterministic quality. Do not claim lower reasoning or highest
absolute cache-read yet.

The next production-level additions belong in the host/provider adapter:

1. expose a real `reasoning_budget_hint` and enforce it only when quality gates
   pass;
2. place a stable policy in the provider's actual system/developer prefix and
   measure cache transitions, rather than moving user-prompt text ahead of the
   task (which broke the benchmark's final-response contract);
3. enforce a byte/token ceiling around tool output with truncation metadata and
   a safe continuation path.

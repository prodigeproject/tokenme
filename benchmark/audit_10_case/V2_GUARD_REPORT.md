# TokenMe v2 legacy vs bounded-tool guard

## Question

This experiment tests whether the runaway-search/full-diff observation (one
earlier trajectory contained about 90k characters of command output) is fixed
by adding a bounded-tool-output policy to the old TokenMe v2 route.

The legacy arm is loaded byte-for-byte from commit `d947148`:

- `tokenme/router.py` and `tokenme/prompt.py` are read with `git show`;
- the ten cases are identical across all arms;
- the only treatment change is the guard text in the `tokenme_v2_guard` arm;
- no provider proxy, transport truncator, CCR store, or RTK rewrite is inserted.

The guard is an instruction contract: it asks the agent to avoid unbounded
recursive searches and full diffs, cap `rg`/`grep`/`find` and PowerShell output,
and inspect only the relevant diff hunk. It is not a byte/token ceiling around
the Codex tool adapter.

## Method

- 30 cells: 10 cases x (`baseline`, `tokenme_v2_legacy`,
  `tokenme_v2_guard`)
- model: `gpt-5.6-luna`, reasoning effort `low`
- one independent provider session per cell
- raw JSONL usage, prompts, stderr, final response, and copied workspace kept
  under the ignored `runs_v2_guard_v1/` artifact root
- deterministic mechanism scorer; provider usage is the source of token totals

Accounting follows the agreed contract:

```text
total_tokens = input_tokens + output_tokens
reasoning_output_tokens is a subset of output_tokens

estimated_cost =
    fresh_input_tokens * $0.20 / 1M
  + cached_input_tokens * $0.02 / 1M
  + output_tokens * $1.20 / 1M
```

These are Luna price-sheet estimates, not a Codex invoice. Reasoning is shown
separately for diagnosis and is not added a second time.

## Provider-reported result

| Arm | Total | Input | Cached input | Fresh input | Reasoning (subset) | Output | Estimated cost | Quality |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 844,236 | 830,996 | 698,880 | 132,116 | 2,003 | 13,240 | $0.056289 | 10/10 |
| TokenMe v2 legacy | 832,370 | 820,543 | 640,768 | 179,775 | 1,941 | 11,827 | $0.062963 | 10/10 |
| TokenMe v2 bounded guard | 911,562 | 898,024 | 722,944 | 175,080 | 2,503 | 13,538 | $0.065720 | 9/10 |

### Guard versus legacy v2

| Metric | Change | Relative change |
|---|---:|---:|
| Total tokens | +79,192 | +9.51% |
| Input tokens | +77,481 | +9.44% |
| Cached input | +82,176 | +12.82% |
| Fresh input | -4,695 | -2.61% |
| Reasoning output | +562 | +28.95% |
| Output tokens | +1,711 | +14.47% |
| Estimated cost | +$0.002758 | +4.38% |

The legacy v2 total is 1.41% below the same-run baseline, but its estimated
cost is 11.86% above baseline because it shifts the input mix toward fresh
input. The guard variant is 7.97% above baseline in total tokens and 16.76%
above baseline in estimated cost.

## Did the guard remove the 90k output event?

There was no 90k command-output event in this fresh 30-cell run. The largest
completed command output observed across all ten cases was:

| Arm | Completed commands | Aggregate command-output chars | Largest single command |
|---|---:|---:|---:|
| Baseline | 32 | 68,389 | 11,883 |
| TokenMe v2 legacy | 27 | 73,351 | 20,424 |
| TokenMe v2 bounded guard | 34 | 69,643 | 17,972 |

For the targeted `rtk_routes` case, aggregate command-output characters were
22,705 for legacy v2 and 18,921 for the guard (-16.7%), but the largest single
command was 12,222 for legacy and 16,449 for the guard. The guard therefore
changed command shape in this sample, but did not impose a hard maximum and
did not consistently reduce output. It also led to more completed commands
overall (34 vs 27).

## Quality and limitations

The deterministic mechanism checks passed 10/10 for baseline and legacy v2 and
9/10 for the guard. The failed guard cell was `prose_api`; its provider call
completed, but the required `FINAL_RESPONSE.md` check failed after an
intermediate PowerShell/parser error. These checks validate the fixture
predicate, not human semantic quality.

The earlier ~90k event was a trajectory/tool-output outlier, so one 30-cell
run cannot establish a universal tail bound. More importantly, a prompt guard
is advisory: it cannot truncate bytes already emitted by a provider tool. A
production fix needs a host/tool-adapter ceiling (with explicit truncation
metadata and a safe continuation path), or a provider-side compressor/CCR
layer. TokenMe can expose the contract and telemetry; the gateway or host must
enforce the transport boundary.

## Decision

Do not claim that the current prompt-only guard saves cost. In this benchmark,
the old v2 route was cheaper in raw total tokens than the guard, and both were
more expensive than baseline under the supplied price mix. Keep the guard as a
useful advisory policy, but implement and benchmark a real bounded tool-output
adapter before calling the 90k issue fixed.

Reproduce with:

```powershell
python benchmark/audit_10_case/run_v2_guard.py `
  --codex C:\Users\Pc\AppData\Local\Temp\tokenme-codex-cli.exe `
  --rtk C:\Users\Pc\AppData\Local\Temp\tokenme-rtk-v0420-audit\rtk.exe `
  --model gpt-5.6-luna --reasoning-effort low --workers 3 `
  --tasks benchmark/audit_10_case/tasks.py `
  --result-root benchmark/audit_10_case/runs_v2_guard_v1 `
  --score benchmark/provider_total/mechanism_score.py
```

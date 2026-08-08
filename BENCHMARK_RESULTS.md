# Legacy synthetic fixture measurements

Status: **withdrawn as a performance benchmark**.

The previous document described TokenMe as the winner with 92.7% average
reduction. That claim was not supported by live agent runs. As the original
methodology stated, the Caveman, Ponytail, and TokenMe outputs were hand-authored
from their documentation and expected compression patterns. Counting those files
with `tiktoken` verifies their size, but cannot verify model behavior, quality,
total tokens, or cost.

The files under `benchmark/bench_inputs/` and `benchmark/bench_outputs/` remain
only as deterministic examples for exercising `tokenme count`, `compare`, and
the quality guard. They must not be averaged into an overall tool ranking.

The earlier subagent experiment is retained under
`benchmark/independent_codex/`; it does not claim provider-total token savings
because the required usage telemetry was unavailable to its interface.

## Valid future benchmark requirements

A publishable total-token claim must include:

- pre-registered tasks, versions, exclusions, and analysis;
- independent paired agent sessions with identical tasks;
- provider-reported input, cached input, output, and reasoning usage;
- `total_tokens = input_tokens + output_tokens`, without double-counting cached
  input or reasoning components;
- deterministic or blinded semantic scoring;
- raw JSONL/session artifacts, failures, and uncertainty intervals.

## Actual provider-total pilot (2026-08-07)

The requirements above are now exercised by the paired Codex suite in
[`benchmark/provider_total/`](benchmark/provider_total/). It ran five fresh
sessions per arm (baseline, adaptive TokenMe, Caveman, Ponytail, and RTK), with
the same five tickets, `gpt-5.6-sol` at low reasoning effort, provider JSONL,
and one deterministic quality predicate for each assigned ticket. Total is
`input_tokens + output_tokens`; cached input and reasoning output are reported
as components and are not added again.

For public product naming, the current implementation is **TokenMe v2**. The
`v3` and `v6` labels below are internal benchmark-rerun identifiers, not
product-version names.

An earlier provider pilot table is in
[`benchmark/provider_total/RESULTS.md`](benchmark/provider_total/RESULTS.md). The
pilot is small and exploratory; neither the earlier table nor the current
rerun is a universal claim.

The current TokenMe v2 output-summary rerun (internal artifact id `v6`) is in
[`benchmark/provider_total/runs_compact_v6/RESULTS.md`](benchmark/provider_total/runs_compact_v6/RESULTS.md).
It measured TokenMe at 4,758 output tokens versus Caveman at 5,162
(−7.83%), with 5/5 quality checks for both. The v6 total was 367,739 versus
422,425 baseline (−12.95%). This is another n=5 paired pilot; the v6 output
delta's bootstrap interval crosses zero.

The first read-only wiring attempt remains local and is excluded from the
public `RESULTS.json`.

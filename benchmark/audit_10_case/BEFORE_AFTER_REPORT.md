# Historical TokenMe v2/v3 before/after snapshot (40 cells)

> This is not the newest five-arm run. It is a 40-cell historical snapshot,
> retained to show the direct v2/v3 transition. Use
> [`LATEST_5_ARM_REPORT.md`](LATEST_5_ARM_REPORT.md) for the newest public
> comparison against Normal, Caveman, Ponytail, and RTK. TokenMe v2 means the
> pre-four-recommendation build; TokenMe v3 means the current build.

This snapshot was run after implementing the four TokenMe recommendations and
is preserved for the direct v2/v3 comparison. The raw run is preserved under
`runs_before_after_final/` (ignored from the source commit because it contains
hundreds of provider/workspace artifacts).

## Method

- Model: Codex `gpt-5.6-luna`, low reasoning effort, local Codex executable (no API key).
- Cases: the same 10 mechanism cases used in the audit: four prose, three Bash/RTK-heavy, and three over-building/Ponytail-heavy.
- Cells: 40 fresh `codex exec --ephemeral --json` sessions: Normal, TokenMe-before, TokenMe-after, and the exact local Caveman skill.
- The **TokenMe v2** arm loads the router/prompt from commit `d947148`, before the prose-classification fix and the four new APIs. The **TokenMe v3** arm uses the current code.
- Every cell keeps prompt, route metadata, complete JSONL, stderr, final response, copied workspace, and deterministic fixture score. All 40 provider sessions completed and all 40 fixture checks passed.

## Provider ledger

`total_tokens = input_tokens + output_tokens`. Reasoning is a subset of
`output_tokens`; it is shown separately but never added again.

| Arm | Input | Cache read | Fresh input | Reasoning | Visible output | Output total | Total | Luna price-sheet estimate* |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Normal | 782,749 | 631,808 | 150,941 | 2,321 | 11,240 | 13,561 | 796,310 | $0.059098 |
| TokenMe v2 | 797,426 | 665,856 | 131,570 | 2,064 | 9,974 | 12,038 | 809,464 | $0.054077 |
| **TokenMe v3** | **788,597** | **670,976** | **117,621** | **1,841** | 10,241 | 12,082 | **800,679** | **$0.051442** |
| Caveman skill | 864,374 | 714,752 | 149,622 | 1,973 | 9,588 | 11,561 | 875,935 | $0.058093 |

\* Estimate only, not a local Codex invoice: uncached input × $0.20/MTok +
cache-read input × $0.02/MTok + output × $1.20/MTok. Cache-write was zero in
this run. Rates are the published Luna list rates and are kept separate from
raw provider usage.

## Deltas

Against Normal, TokenMe-after used 0.55% fewer total tokens, 0.75% fewer input
tokens, 10.91% fewer output tokens, and the price-sheet estimate was 12.95%
lower. Reasoning was 480 tokens lower than Normal. The total-token paired
bootstrap 95% CI for the ten cases was [-12,549.5, 13,889.9] tokens, so the
total-token difference is not a universal claim.

Against TokenMe v2 in the same task pack, TokenMe v3 used 1.09% fewer total
tokens and the price-sheet estimate was 4.87% lower. Output was effectively
flat (+0.37%); the improvement came mainly from lower fresh input and fewer
reasoning tokens, not from truncating readable answers.

Against the Caveman skill treatment, TokenMe-after used 8.59% fewer total
tokens and the estimate was 11.45% lower. Caveman's visible output was shorter
in this run (9,588 vs 10,241 visible tokens), which is why the comparison is
reported as an end-to-end cost result rather than an output-only victory.

## What the run does not prove

The arms are instruction treatments inside Codex; the Caveman Go proxy/CCR was
not placed in the request path. The task pack is small, provider cache state is
not a randomized laboratory variable, and the deterministic scorer checks
functional predicates rather than human semantic quality. Provider usage is
raw evidence; local tokenizer counts, policy budgets, and price-sheet dollars
are labelled inferred/estimated. Repeat the run with a larger task population
before making a production-wide percentage claim.

## Implementation status

1. `router.adaptive_route()` and `simulate_net_benefit()` keep the core safety
   policy and skip optional deltas only when host feedback shows negative net
   benefit; unknown savings remain `observe`.
2. `provider.TokenCount`, registered tokenizer adapters, and
   `parse_codex_jsonl_ledger()` separate raw, inferred, and unknown fields.
3. `prompt.summary_policy()` plus `quality.summary_quality_gate()` adapt the
   visible summary budget while preserving numbers, paths, errors, warnings,
   and unresolved actions.
4. `context.pack_segments()` is deterministic and lossless by default; optional
   compressors fail closed when smaller output, round-trip evidence, or a
   recovery handle is missing.

The four features are portable optimizer primitives. Tokenisme remains the
right place for credentials, provider count endpoints, prices, cache
settlement, durable CCR, retries, and reasoning-budget enforcement.

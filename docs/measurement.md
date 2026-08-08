# Measurement: exact scope, signed deltas

TokenMe stores local measurement events. It does not infer provider billing from
characters, LOC, or command output.

## Counterfactual rule

For a layer-local comparison where both sides are observed:

```text
net_saved = raw_tokens - kept_tokens
```

The result is signed. Positive means fewer tokens; negative means a regression.
If `raw_tokens` is unavailable, the event is `unknown_raw` and has no saving.

Each event names its metric:

- `command_output_reduction`
- `assistant_output_reduction`
- `code_output_reduction`
- `context_lifecycle_delta`
- `provider_total_tokens`
- `provider_cost`
- `custom`

Never aggregate different metrics into one percentage.

## Provider totals

When a provider emits usage fields, store them directly. For Codex JSONL
`turn.completed` events:

```text
total token volume = input_tokens + output_tokens
```

`cached_input_tokens` is a component of input and
`reasoning_output_tokens` is a component of output; do not add either twice.
For endpoint analysis, TokenMe also reports `fresh_input_tokens` as
`uncached_input_tokens + cache_write_input_tokens`. That is a diagnostic for
new context, not a substitute for total provider usage or billed cost.
Provider cost additionally requires the provider's applicable pricing or billed
usage record.

## Local proxy counting

`tokenme count` reports `tiktoken:<encoding>` or `~est`. A tokenizer count is
exact only for that tokenizer and text, not automatically for Claude, Codex
billing, hidden reasoning, cache traffic, or system prompts.

## Commands

```bash
tokenme compare --raw raw.txt --kept kept.txt \
  --layer 3 --metric command_output_reduction --label "git diff"
tokenme record --kind usage --raw-tokens 20000 --kept-tokens 18000 \
  --metric provider_total_tokens
tokenme report --json
tokenme provider-usage codex-run.jsonl --json
tokenme route --text "inspect pytest output" --json
tokenme route-feedback --route-key "code=0;tools=1;context=0;noisy=1" \
  --outcome quality-fail --quality-fail --retries 2 --turns 4
```

Reports include measured coverage, unknown-raw events, signed net deltas,
regression counts, separate `by_metric` totals, and provider endpoint fields
when usage metadata was recorded. Route feedback is local JSONL and only
downgrades a route after three observations; a single noisy session cannot
permanently turn off a module.

The optional hooks can record assistant/code/tool output sizes. A host normally
does not provide the unfiltered counterfactual to a `PostToolUse` hook, so those
events remain `unknown_raw` unless both values are explicitly supplied.

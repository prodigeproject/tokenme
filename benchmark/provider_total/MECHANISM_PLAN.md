# Mechanism-targeted benchmark plan and run status

The 30-pair suite is implemented in `mechanism_tasks.py`, with a separate empty
template, mechanism scorer, deterministic task order, and configurable runner.
The intended execution is 30 tasks x 5 arms = 150 fresh provider sessions.

Current status: the 150-session run is preserved under
`runs_mechanism_v2/`. The Codex provider hit a usage-limit/transient failure
partway through, leaving only 20–21 provider-complete cells per arm. Failed
cells are retained, and their zero-turn records are excluded from token sums;
the resulting table is exploratory, not a completed 30-pair claim.

The five-case provider pilot is useful for wiring and telemetry, but it is not
balanced for the mechanisms claimed by the three public tools. The mechanism
run is now present as an incomplete exploratory result; rerun the failed cells
when provider availability is restored before making a headline comparison.

## Design

- 30 paired tasks per arm, grouped into three strata of 10:
  - **Caveman/prose:** status explanations, concise summaries, error narration,
    and multi-turn “what changed?” responses where prose is a material share of
    the output.
  - **RTK/tool-output:** Bash-style command-heavy `git diff`, `git status`, test
    failures, logs, search output, and verbose command results. On this Windows
    host the task script uses host-equivalent syntax when Bash is unavailable.
    The raw command, filtered command, exit code, and recovery path must be
    captured.
  - **Ponytail/over-building:** feature tickets with an obvious native API,
    existing helper, standard-library solution, or one-line implementation,
    plus a balanced set where validation, accessibility, and security must stay.
- Arms: stock baseline, each treatment exactly as shipped for the target host,
  and any new candidate arm. Same task order is randomized once and reused for
  every arm; each cell is a fresh provider session.
- Minimum volume: 30 paired sessions per arm. A smoke run may use `k=1`, but no
  public claim uses it; the confirmatory run uses at least `k=3` on the same
  tasks and reports paired medians.

## Endpoints fixed before the run

1. Provider total: `input_tokens + output_tokens`.
2. Fresh input: uncached input + cache-write input.
3. Output tokens, turns, retries, wall-clock, and cost when the provider price
   is known. Cached input and reasoning output are components, never added a
   second time.
4. Mechanism-specific proxy: prose output, eligible command-output bytes/tokens,
   or final non-comment code LOC. Each proxy is labelled and never called
   “total tokens”.
5. Quality: hidden functional tests plus security/accessibility checks where
   relevant, with a pre-declared non-inferiority margin. “No significant
   difference” is not treated as proof of equivalence.

## Adoption and failure accounting

Every treatment must emit an activation/audit record. A missing hook, failed
binary, timeout, retry, or quality failure is preserved in the raw artifact and
reported symmetrically; it is not silently removed because it makes a result
look better. Results must include per-task paired deltas, medians, confidence
intervals, and the complete JSONL streams.

Run the completed suite (when the Codex provider network is available) with:

```powershell
python benchmark/provider_total/run.py `
  --tasks benchmark/provider_total/mechanism_tasks.py `
  --template benchmark/provider_total/mechanism_template `
  --score benchmark/provider_total/mechanism_score.py `
  --result-root benchmark/provider_total/runs_mechanism_v1 `
  --codex C:\Users\Pc\AppData\Local\Temp\tokenme-codex-cli.exe `
  --rtk C:\Users\Pc\AppData\Local\Temp\tokenme-rtk-v0420-audit\rtk.exe `
  --workers 5 --timeout 600 --rerun
```

`RESULTS.json`, `RESULTS.md`, every provider `usage.jsonl`, and per-cell RTK
`rtk_gain` artifacts are written below the result root. The existing
`benchmark/provider_total/RESULTS.md` remains the completed five-session
wiring pilot and is not overwritten by this suite.

When a scorer or fixture is corrected after a run, add `--rescore
--summary-only` to recompute deterministic quality and summaries without
spending provider calls.

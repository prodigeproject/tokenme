# Provider-total benchmark

This is a paired Codex CLI benchmark with five identical cases and five arms:

`baseline`, adaptive `tokenme`, `caveman`, `ponytail`, and `rtk`.

Each case/arm is one fresh `codex exec --ephemeral --json` session. The complete
JSONL stream is kept in `runs/<arm>/<case>/usage.jsonl`; prompts, stderr, final
messages, copied workspaces, and deterministic quality scores are kept beside
it. Provider total is parsed as `input_tokens + output_tokens`.

## Dry run

```powershell
python benchmark/provider_total/run.py --dry-run
```

## Run

The Windows Codex CLI copy and RTK binary used by this audit are in `%TEMP%`.
Pass explicit paths if they differ:

```powershell
python benchmark/provider_total/run.py `
  --codex "$env:TEMP\tokenme-codex-cli.exe" `
  --rtk "$env:TEMP\tokenme-rtk-v0420-audit\rtk.exe"
```

Results are written to `RESULTS.json`, `RESULTS.md`, and one artifact directory
per run. The suite has five sessions per arm (`n=5`), so it is a paired pilot,
not a population-level significance claim. `--summary-only` rebuilds the two
result files from the preserved `result.json` artifacts without spending new
provider calls:

```powershell
python benchmark/provider_total/run.py --summary-only
```

The quality scorer runs only the case assigned to that session; it never imports
the four untouched template stubs. The three JetBrains comparisons and the
limitations of this Codex/Windows harness are documented in
`AUDIT_TOKENME_VS_RTK_CAVEMAN_PONYTAIL.md`.

`MECHANISM_PLAN.md` documents the implemented 30-task-per-arm suite in
`mechanism_tasks.py` and `mechanism_score.py`. It separates prose-heavy,
Bash-style/tool-output-heavy, and over-building workloads. The 150-session run
is preserved under `runs_mechanism_v2/`; provider availability failed for part
of the run (only 20–21 provider-complete cells per arm), so its token table is
exploratory and must not be presented as a completed 30-pair claim. Use
`--rescore --summary-only` to update deterministic quality results after a
scorer/fixture fix without making new provider calls. See
`MECHANISM_RUN_STATUS.md` for the exact status and rerun command.

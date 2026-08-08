# Mechanism benchmark run status

The 30-pair mechanism suite is implemented and pre-registered in
`MECHANISM_PLAN.md`: ten prose-heavy, ten command-output-heavy, and ten
native-helper/over-building tasks across baseline, TokenMe, Caveman, Ponytail,
and RTK (150 independent LLM sessions planned).

The run in `runs_mechanism_v2/` did call the Codex provider, and preserves the
raw `usage.jsonl` for every cell. A provider usage-limit/transient failure
occurred partway through: only 20–21 sessions per arm produced a turn. The
remaining cells are failed zero-turn records, not zero-token wins. After the
run, the scorer was fixed to import fixture-local helpers correctly and the
existing workspaces were re-scored with `--rescore`; no usage data changed.

The completed-cell totals are exploratory: TokenMe 1,677,563 versus baseline
1,692,898 (−0.91%), with 20/30 quality checks for each. The paired bootstrap
CI crosses zero, and the run is incomplete, so it is not a valid 30-pair
winner claim. The compiled-policy v3 five-case pilot remains the clean total
token result (`runs_compact_v3/`).

Rerun the mechanism suite when provider availability is restored:

```powershell
python benchmark/provider_total/run.py `
  --tasks benchmark/provider_total/mechanism_tasks.py `
  --template benchmark/provider_total/mechanism_template `
  --score benchmark/provider_total/mechanism_score.py `
  --result-root benchmark/provider_total/runs_mechanism_v2 `
  --codex C:\Users\Pc\AppData\Local\Temp\tokenme-codex-cli.exe `
  --rtk C:\Users\Pc\AppData\Local\Temp\tokenme-rtk-v0420-audit\rtk.exe `
  --workers 5 --timeout 600
```

`--rescore --summary-only` only updates deterministic quality/summaries and
does not call the provider.

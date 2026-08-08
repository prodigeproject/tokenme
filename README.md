# TokenMe

<p align="center">
  <strong>Measure the token budget. Keep the important parts.</strong><br>
  <em>Local, four-layer token discipline for coding agents.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/tests-59%20passing-brightgreen" alt="59 tests passing">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT license">
  <img src="https://img.shields.io/badge/python-3.8%2B-blue" alt="Python 3.8+"><br>
  <img src="https://img.shields.io/badge/runtime%20dependencies-none-brightgreen" alt="No runtime dependencies">
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey" alt="macOS Linux Windows">
  <img src="https://img.shields.io/badge/telemetry-none-brightgreen" alt="No telemetry">
</p>

TokenMe is a small Python CLI and agent skill for reducing waste across an
agent session without deleting safety checks, exact requirements, useful
context, or an understandable final summary.

It measures local counterfactuals, records regressions honestly, and can parse
provider-reported Codex usage when a host exposes the session JSONL. It does not
pretend that a shortened command output is automatically a cheaper provider
invoice.

## Benchmark snapshot

The latest live pilot used 25 fresh Codex sessions: five identical cases × five
arms, with `gpt-5.6-sol` at low reasoning effort. Every cell used a new
workspace and the same task. `total = input_tokens + output_tokens`; cached
input and reasoning output are reported separately and are not added twice.

| Arm | Total tokens | Δ total vs baseline | Input | Output | Fresh input | Quality |
|---|---:|---:|---:|---:|---:|---:|
| Baseline | 422,425 | — | 416,527 | 5,898 | 52,495 | 5/5 |
| **TokenMe v6** | **367,739** | **−12.95%** | **362,981** | **4,758** | 62,437 | **5/5** |
| Caveman | 465,528 | +10.20% | 460,366 | 5,162 | 57,422 | 5/5 |
| Ponytail | 470,208 | +11.31% | 464,644 | 5,564 | 106,756 | 5/5 |
| RTK | 453,129 | +7.27% | 447,576 | 5,553 | 49,240 | 4/5 |

On this pilot, TokenMe used 404 fewer output tokens than Caveman (−7.83%) and
97,789 fewer total tokens (−21.00%). The final summaries stayed readable by
using one sentence when sufficient and at most two sentences for security,
accessibility, migration, or irreversible work.

This is a paired `n=5` pilot, not a universal ranking. The output delta's
bootstrap interval crosses zero. The complete table, prompts, final responses,
quality scores, and raw JSONL are preserved in
[`runs_compact_v6/`](benchmark/provider_total/runs_compact_v6/).

For a text-first input/output breakdown across every arm, see
[`BENCHMARK_TOKEN_USAGE.md`](BENCHMARK_TOKEN_USAGE.md).

### What the table does—and does not—compare

The baseline is stock Codex with the same benchmark prompt and no
token-minimization policy. Caveman, Ponytail, and RTK are their local Windows
skill/awareness treatments from the audit workspace, not a reproduction of the
JetBrains Claude Code infrastructure. Model, host, cache state, hooks, and task
mix all affect the result.

The 30-task mechanism follow-up (Bash-heavy, prose-heavy, and over-building
strata) was launched as 150 LLM sessions, but provider usage limits interrupted
some cells. Its raw artifacts are preserved in
[`runs_mechanism_v2/`](benchmark/provider_total/runs_mechanism_v2/); it is
exploratory and must not be read as a completed 30-pair winner.

## The four layers

| Layer | Waste to control | TokenMe approach |
|---|---|---|
| 1. Prose | Filler, repetition, routine narration | Result-first summaries; keep ambiguity and warnings explicit |
| 2. Code | Unneeded abstractions, dependencies, or generated boilerplate | Smallest readable correct change; preserve validation, security, accessibility, and tests |
| 3. Tools | Verbose stdout, repeated searches, noisy diffs | Targeted searches, bounded output, focused checks, exact errors/paths/exit codes kept |
| 4. Context | Large always-loaded instructions and compaction loss | Selective modules, compiled policy, and compact checkpoints |

The adaptive router loads only the policy delta suggested by the task. It has a
brief summary mode for ordinary work and an expanded mode when security,
accessibility, migration, or irreversible operations need explicit language.

## Install

TokenMe uses the Python standard library at runtime.

```bash
git clone https://github.com/prodigeproject/tokenme
cd tokenme
python -m tokenme selfcheck
pip install .
```

Optional named tokenizer support:

```bash
pip install "tokenme[exact]"
```

On Windows, use `bin\tokenme.ps1` or `bin\tokenme.cmd`, or run
`python -m tokenme ...` directly.

## CLI examples

```bash
# Estimate a file (heuristic unless an optional tokenizer is installed)
tokenme count file.txt

# Record a measured counterfactual
tokenme compare --raw full.txt --kept focused.txt --layer 3 --label "git diff"

# Inspect the adaptive route for a task
tokenme route --text "implement and test auth" --json

# Parse provider-reported Codex usage
tokenme provider-usage run.jsonl --json

# Find risky minimization in a diff
git diff origin/main | tokenme quality --diff -

# Audit always-loaded context and create a compaction checkpoint
tokenme audit ~/.claude/CLAUDE.md
tokenme checkpoint --goal "Migrate DB schema" --next-step "Run staging checks"
```

## Agent skill

Copy `skills/tokenme/` into the agent's skill/rules directory:

```bash
# Claude Code
cp -r skills/tokenme ~/.claude/skills/

# Any agent with a skills or rules directory
cp -r skills/tokenme <your-agent-skills-folder>/
```

The skill is intentionally short. Prose, code, tools, and context references
are loaded selectively instead of injecting a long manual on every turn.

## Honest measurement

TokenMe keeps different measurements separate:

- `provider_total_tokens`: provider-reported input + output;
- `fresh_input_tokens`: uncached input + cache-write input;
- command-output, prose, code, and context proxies;
- `provider_cost`: only when the applicable provider price is supplied.

`saved = raw − kept` is signed, so regressions remain visible. If the raw
counterfactual is unknown, the event is recorded as `unknown_raw`, not as a
zero-token saving. Local estimates are never presented as billing truth.

`tokenme quality` is a heuristic safety guard, not a formal proof. It looks for
removed or weakened validation, security, error handling, accessibility, and
test logic before a compact diff is accepted.

## Reproduce the live pilot

The provider benchmark runner stores one directory per arm and case containing
the exact prompt, route metadata, `usage.jsonl`, stderr, final response, copied
workspace, and deterministic quality score.

```powershell
python benchmark/provider_total/run.py `
  --codex C:\Users\Pc\AppData\Local\Temp\tokenme-codex-cli.exe `
  --rtk C:\Users\Pc\AppData\Local\Temp\tokenme-rtk-v0420-audit\rtk.exe `
  --workers 5 --timeout 600
```

Rebuild a report without provider calls:

```powershell
python benchmark/provider_total/run.py --result-root benchmark/provider_total/runs_compact_v6 --summary-only
```

For the methodology audit and comparison with the three JetBrains references,
see [`AUDIT_TOKENME_VS_RTK_CAVEMAN_PONYTAIL.md`](AUDIT_TOKENME_VS_RTK_CAVEMAN_PONYTAIL.md).

## Related research and source projects

- [JetBrains: Caveman](https://blog.jetbrains.com/ai/2026/07/speak-to-ai-agents-like-cavemen-tosave-tokens/)
- [JetBrains: RTK + Claude Code](https://blog.jetbrains.com/ai/2026/07/rtk-claude-code-token-savings/)
- [JetBrains: Ponytail](https://blog.jetbrains.com/ai/2026/07/ponytail-skill-claude-tested/)
- [Caveman source](https://github.com/JuliusBrussee/caveman)
- [RTK source](https://github.com/rtk-ai/rtk)
- [Ponytail source](https://github.com/DietrichGebert/ponytail)

## Project layout

```text
tokenme/
├── tokenme/                 CLI, router, provider parser, quality guard
├── skills/tokenme/          compact agent skill and on-demand references
├── hooks/                   optional local tracking hooks
├── benchmark/provider_total/ live provider-token benchmark and raw artifacts
├── tests/                   unit tests
└── docs/                    measurement notes
```

## Limitations

TokenMe is behavioral: the agent must follow the policy. Provider billing also
depends on model pricing, cache tiers, and host telemetry. No percentage from a
hand-authored fixture or a single small pilot should be generalized to every
repository.

## License

MIT. No runtime telemetry, daemon, or external dependency.

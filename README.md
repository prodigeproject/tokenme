# TokenMe v3

<p align="center">
  <strong>Measure the token budget. Keep the important parts.</strong><br>
  <em>A portable, open-source token-optimizer layer for coding agents.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/tests-72%20passing-brightgreen" alt="72 tests passing">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT license">
  <img src="https://img.shields.io/badge/python-3.8%2B-blue" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/runtime%20dependencies-none-brightgreen" alt="No runtime dependencies">
</p>

TokenMe is a small Python CLI and host integration layer for reducing waste in
agent sessions without deleting safety checks, exact requirements, useful
context, or an understandable final answer. It is not a gateway: Tokenisme or
another host can consume TokenMe's route, ledger, packing, and quality signals
for provider dispatch, pricing, cache settlement, and budgets.

## Latest live benchmark

**Version naming:** TokenMe v2 is the pre-four-recommendation build; TokenMe v3
is the current post-recommendation build. The earlier v2 five-case pilot
recorded 367,739 total tokens versus 422,425 for Normal (-12.95%). It used a
different model and task population and is retained as historical context.

The newest run used 50 fresh Codex `gpt-5.6-luna` sessions at low reasoning
effort: ten identical cases across Normal, TokenMe v3, the exact local Caveman
skill, the preserved Ponytail treatment, and the real local RTK binary. All 50
deterministic fixture checks passed. `total = input_tokens + output_tokens`;
cache-read and reasoning are components and are never added twice.

| Arm | Total | Input | Cache read | Reasoning | Output | Luna price-sheet estimate* |
|---|---:|---:|---:|---:|---:|---:|
| Normal | 772,077 | 758,909 | 632,576 | 2,133 | 13,168 | $0.053720 |
| **TokenMe v3** | **755,788** | **743,492** | **643,584** | **1,947** | **12,296** | **$0.047608** |
| Caveman skill | 836,982 | 825,983 | 683,264 | 1,663 | 10,999 | $0.055408 |
| Ponytail treatment | 776,642 | 764,742 | 644,096 | 1,870 | 11,900 | $0.051291 |
| RTK treatment | 1,323,581 | 1,304,413 | 1,109,760 | 3,944 | 19,168 | $0.084127 |

For historical context, the earlier **TokenMe v2** pilot measured **367,739
total tokens** versus **422,425** for Normal (**-12.95%**). That was a separate
five-case `gpt-5.6-sol` population, so it is not mixed into the 50-session v3
table above.

The direct v2/v3 before-after run is also preserved separately:

| Historical four-arm snapshot (40 sessions) | Total tokens | Estimated cost |
|---|---:|---:|
| Normal | 796,310 | $0.059098 |
| TokenMe v2 | 809,464 | $0.054077 |
| TokenMe v3 | 800,679 | $0.051442 |
| Caveman skill | 875,935 | $0.058093 |

This table explains why an older LinkedIn draft shows Normal as 796,310, while
the current five-arm headline shows 772,077. Both are provider measurements from
different fresh runs; use 772,077 for the latest v3 comparison and 796,310 only
when discussing the direct v2/v3 historical snapshot.

In this task pack, TokenMe v3 used 2.11% fewer total tokens than Normal and
6.62% fewer output tokens. Its price-sheet estimate was 11.38% lower than
Normal, 9.70% lower than Caveman, 2.69% lower than Ponytail, and 43.41% lower
than RTK. Caveman and Ponytail produced shorter visible output in this run, so
this is an end-to-end cost comparison rather than an output-only ranking. The
paired total-token interval crosses zero; see the full
[`latest five-arm report`](benchmark/audit_10_case/LATEST_5_ARM_REPORT.md).

*Estimate only, not a local Codex invoice:* uncached input x $0.20/MTok +
cache-read input x $0.02/MTok + output x $1.20/MTok. Raw JSONL and copied
workspaces are preserved locally under the ignored `runs_latest_all_v3/`
directory.

This is one task pack, not a universal ranking. The Caveman proxy/CCR was not
inserted into the request path; the Caveman, Ponytail, and RTK arms are
instruction/treatment comparisons. Model, provider cache state, hooks, and
task mix affect the result. See the report for provenance and limitations.

### Why the before/after report has different numbers

There are two intentionally preserved snapshots:

| Snapshot | Sessions | Arms | Purpose |
|---|---:|---|---|
| `BEFORE_AFTER_REPORT.md` | 40 | Normal, TokenMe v2, TokenMe v3, Caveman | Direct v2-to-v3 transition on one four-arm run |
| `LATEST_5_ARM_REPORT.md` | 50 | Normal, TokenMe v3, Caveman, Ponytail, RTK | Current five-arm comparison and public headline |

They use the same ten-case task pack and the same accounting formula, but they
are different provider runs with different cache/trajectory state. The v2 arm
is present only in the historical 40-cell snapshot because it runs source code
from the pre-recommendation commit. Do not mix totals across the two tables;
use the five-arm report for current v3 claims and the before/after report for
the direct v2/v3 transition.

## Accounting contract

For a Codex reasoning model:

```text
total_tokens = input_tokens + output_tokens
reasoning_output_tokens is a subset of output_tokens
visible_output_tokens = output_tokens - reasoning_output_tokens

cost = uncached_input x input_rate
     + cached_input x cached_rate
     + output_tokens x output_rate
```

Reasoning is billed at the output rate and is shown separately for diagnosis;
adding it again would double-count. TokenMe labels provider JSONL as raw,
local tokenizer counts as inferred, and unavailable fields as unknown.

## Four optimizer primitives

1. **Adaptive route + net-benefit simulation.** `adaptive_route()` keeps the
   safety core and applies optional policy deltas only when host feedback shows
   a positive net benefit after policy, retry, recovery, extra-turn, and latency
   overhead. Unknown savings remain `observe`.
2. **Tokenizer adapters + evidence ledger.** `TokenCount`, registered provider
   adapters, and `parse_codex_jsonl_ledger()` make provider-native, inferred,
   and unavailable counts explicit. `chars/4` is never billing truth.
3. **Adaptive output summary + quality gate.** `summary_policy()` asks for a
   brief result when sufficient and preserves numbers, paths, errors, warnings,
   and unresolved actions for high-stakes or failed work. `summary_quality_gate()`
   is a heuristic host hook, not a semantic proof.
4. **Lossless context packer + optional compressor.** `pack_segments()` pins
   security/error context, ranks relevance and recency deterministically, and
   drops whole segments only within a declared budget. Compressor plugins fail
   closed when output is not smaller, round-trip/recovery evidence is absent,
   or lossy mode was not explicitly enabled.

The portable layer owns contracts and deterministic local decisions. A gateway
should own credentials, exact provider count endpoints, price catalogs, cache
settlement, durable CCR/recovery, retries, quotas, and reasoning enforcement.

## Install

TokenMe uses only the Python standard library at runtime.

```bash
git clone https://github.com/prodigeproject/tokenme
cd tokenme
python -m tokenme selfcheck
pip install .
```

Optional named-tokenizer support:

```bash
pip install "tokenme[exact]"
```

## CLI examples

```bash
# Estimate visible text (heuristic unless an optional tokenizer is installed)
tokenme count file.txt

# Inspect a route and its evidence-based adaptive decision
tokenme route --text "inspect verbose pytest output" --adaptive --json

# Parse provider-reported Codex JSONL, including unknown fields
tokenme provider-usage run.jsonl --json

# Record a measured counterfactual
tokenme compare --raw full.txt --kept focused.txt --layer 3 --label "git diff"

# Scan a change for removed safeguards
git diff origin/main | tokenme quality --diff -
```

## Agent skill

Copy `skills/tokenme/` into the agent's skill/rules directory. The skill is
intentionally short; hosts can call `tokenme.router`, `tokenme.provider`, and
`tokenme.context` directly when they need richer integration.

## Honest measurement

TokenMe keeps provider totals separate from command-output, prose, code, and
context proxies. A signed `raw - kept` delta shows regressions; an unavailable
raw counter is recorded as `unknown_raw`, never as zero saving. Provider cache
hits do not prove that TokenMe caused the hit, and local estimates are never
presented as a bill.

The quality scanner and summary gate are heuristic signals. Hosts should attach
tests, semantic graders, latency, retries, recovery attempts, and a price table
when making a production decision.

## Reproduce

The harness stores prompts, route metadata, complete JSONL, stderr, final
responses, copied workspaces, and deterministic scores per independent cell.
For the latest five-arm run:

```powershell
python benchmark/audit_10_case/run_latest_all.py `
  --codex C:\Users\Pc\AppData\Local\Temp\tokenme-codex-cli.exe `
  --model gpt-5.6-luna --reasoning-effort low --workers 5 `
  --tasks benchmark/audit_10_case/tasks.py `
  --result-root benchmark/audit_10_case/runs_latest_all_v3 `
  --score benchmark/provider_total/mechanism_score.py
```

For a focused v2/v3 comparison:

```powershell
python benchmark/audit_10_case/run_before_after.py `
  --codex C:\Users\Pc\AppData\Local\Temp\tokenme-codex-cli.exe `
  --model gpt-5.6-luna --reasoning-effort low --workers 4 `
  --tasks benchmark/audit_10_case/tasks.py `
  --result-root benchmark/audit_10_case/runs_before_after_final `
  --score benchmark/provider_total/mechanism_score.py
```

Read the methodology and limitations in
[`benchmark/audit_10_case/LATEST_5_ARM_REPORT.md`](benchmark/audit_10_case/LATEST_5_ARM_REPORT.md)
and the historical [`before/after report`](benchmark/audit_10_case/BEFORE_AFTER_REPORT.md).

## Related research

- [JetBrains: Caveman](https://blog.jetbrains.com/ai/2026/07/speak-to-ai-agents-like-cavemen-tosave-tokens/)
- [JetBrains: RTK + Claude Code](https://blog.jetbrains.com/ai/2026/07/rtk-claude-code-token-savings/)
- [JetBrains: Ponytail](https://blog.jetbrains.com/ai/2026/07/ponytail-skill-claude-tested/)
- [Caveman source](https://github.com/JuliusBrussee/caveman)
- [RTK source](https://github.com/rtk-ai/rtk)
- [Ponytail source](https://github.com/DietrichGebert/ponytail)

## License

MIT. No daemon, network telemetry, or runtime dependency is required.

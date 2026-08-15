# TokenMe v3

<p align="center">
  <strong>Measure the token budget. Keep the important parts.</strong><br>
  <em>A portable, open-source token-optimizer layer for coding agents.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/tests-76%20passing-brightgreen" alt="76 tests passing">
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
is the current post-recommendation build.

**Latest head-to-head run:** adding TokenMe v2 to the previous five-arm suite
requires **60 cells**: ten identical cases across Normal, TokenMe v2, TokenMe
v3, the exact local Caveman skill, the preserved Ponytail treatment, and the
real local RTK binary. All 60 deterministic fixture checks passed. `total =
input_tokens + output_tokens`; cache-read and reasoning are components and are
never added twice.

| Arm | Total | Input | Cache read | Reasoning | Output | Luna price-sheet estimate* |
|---|---:|---:|---:|---:|---:|---:|
| Normal | 761,557 | 748,680 | 657,664 | 1,913 | 12,877 | $0.046809 |
| **TokenMe v2** | **911,564** | **897,222** | **781,824** | **2,308** | **14,342** | **$0.055926** |
| **TokenMe v3** | **865,462** | **851,497** | **720,640** | **2,216** | **13,965** | **$0.057342** |
| Caveman skill | 876,701 | 863,825 | 725,504 | 1,973 | 12,876 | $0.057625 |
| Ponytail treatment | 845,959 | 833,311 | 690,944 | 2,503 | 12,648 | $0.057470 |
| RTK treatment | 1,195,620 | 1,178,595 | 1,006,848 | 3,181 | 17,025 | $0.074916 |

**Readout of this run:** v3 is **not** cheaper than the same-run Normal
baseline (+22.50% estimated cost). It is only 0.49% cheaper than Caveman in
the estimate, which is effectively a tie at this sample size. V3 does use
5.06% fewer total tokens than v2 in this run, but costs 2.53% more because the
fresh/cache mix changed.

V3 also produced 2.63% fewer output tokens than v2. Versus the same-run Normal
baseline, v2 was +19.70% total and v3 was +13.64% total. The paired total-token
interval for v3 versus v2 crosses zero; see the full
[`latest six-arm report`](benchmark/audit_10_case/LATEST_6_ARM_REPORT.md).

*Estimate only, not a local Codex invoice:* uncached input x $0.20/MTok +
cache-read input x $0.02/MTok + output x $1.20/MTok. Raw JSONL and copied
workspaces are preserved locally under the ignored `runs_latest_six_v3/`
directory.

The older five-case v2 pilot measured 367,739 versus 422,425 for Normal
(-12.95%) with `gpt-5.6-sol`; it is historical context, not this head-to-head.
This is one task pack, not a universal ranking. The Caveman proxy/CCR was not
inserted into the request path; the Caveman, Ponytail, and RTK arms are
instruction/treatment comparisons. Model, provider cache state, hooks, and
task mix affect the result. See the report for provenance and limitations.

The earlier v2 result is reproducible from the raw artifact committed with
`d947148` (`benchmark/provider_total/runs_compact_v6/RESULTS.json`): five
simple cases on `gpt-5.6-sol`, not the ten-case Luna mechanism pack above. Its
result was real for that population, but it is not an apples-to-apples estimate
of the current six-arm run.

A focused 30-cell retest compared that exact legacy v2 source with a
prompt-only bounded-tool guard aimed at the earlier ~90k-character search/diff
outlier. Legacy v2 measured 832,370 provider tokens and an estimated $0.062963;
the guard measured 911,562 tokens and $0.065720, with 9/10 deterministic checks
versus 10/10 for legacy. The guard reduced `rtk_routes` command-output
characters in this sample, but it did not impose a hard ceiling or improve
aggregate cost. See the [`v2 guard report`](benchmark/audit_10_case/V2_GUARD_REPORT.md)
for the raw/inferred boundary and the adapter-level fix still required.

The next optimization pass is named **TokenMe v3 Compact Policy**. It adds
compact task-mode policies for read-only prose, minimal helper patches, and
Bash-heavy inspection. In a fresh 30-cell Luna run, it used 660,517 provider tokens versus 784,541 for the same-run
baseline (-15.81%) and the price-sheet estimate fell from $0.056322 to $0.049521
(-12.08%), with 10/10 deterministic checks. Output fell 11.09%; reasoning did
not fall and absolute cache-read was lower because the entire request was
smaller. The complete [v3 Compact Policy report](benchmark/audit_10_case/V3_COMPACT_POLICY_REPORT.md)
separates those metrics and states the remaining provider-adapter work.

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
For the latest six-arm v2/v3 head-to-head (60 cells):

```powershell
python benchmark/audit_10_case/run_latest_six.py `
  --codex C:\Users\Pc\AppData\Local\Temp\tokenme-codex-cli.exe `
  --rtk C:\Users\Pc\AppData\Local\Temp\tokenme-rtk-v0420-audit\rtk.exe `
  --model gpt-5.6-luna --reasoning-effort low --workers 6 `
  --tasks benchmark/audit_10_case/tasks.py `
  --result-root benchmark/audit_10_case/runs_latest_six_v3 `
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

For the v3-before versus v3 Compact Policy optimization audit:

```powershell
python benchmark/audit_10_case/run_v3_compact.py `
  --codex C:\Users\Pc\AppData\Local\Temp\tokenme-codex-cli.exe `
  --model gpt-5.6-luna --reasoning-effort low --workers 3 `
  --tasks benchmark/audit_10_case/tasks.py `
  --result-root benchmark/audit_10_case/runs_v3_compact_luna `
  --score benchmark/provider_total/mechanism_score.py
```

For the legacy-v2 versus bounded-tool-guard retest:

```powershell
python benchmark/audit_10_case/run_v2_guard.py `
  --codex C:\Users\Pc\AppData\Local\Temp\tokenme-codex-cli.exe `
  --rtk C:\Users\Pc\AppData\Local\Temp\tokenme-rtk-v0420-audit\rtk.exe `
  --model gpt-5.6-luna --reasoning-effort low --workers 3 `
  --tasks benchmark/audit_10_case/tasks.py `
  --result-root benchmark/audit_10_case/runs_v2_guard_v1 `
  --score benchmark/provider_total/mechanism_score.py
```

Read the methodology and limitations in
[`benchmark/audit_10_case/LATEST_6_ARM_REPORT.md`](benchmark/audit_10_case/LATEST_6_ARM_REPORT.md),
with the earlier [`five-arm report`](benchmark/audit_10_case/LATEST_5_ARM_REPORT.md)
available for methodology comparison.

## Related research

- [JetBrains: Caveman](https://blog.jetbrains.com/ai/2026/07/speak-to-ai-agents-like-cavemen-tosave-tokens/)
- [JetBrains: RTK + Claude Code](https://blog.jetbrains.com/ai/2026/07/rtk-claude-code-token-savings/)
- [JetBrains: Ponytail](https://blog.jetbrains.com/ai/2026/07/ponytail-skill-claude-tested/)
- [Caveman source](https://github.com/JuliusBrussee/caveman)
- [RTK source](https://github.com/rtk-ai/rtk)
- [Ponytail source](https://github.com/DietrichGebert/ponytail)

## License

MIT. No daemon, network telemetry, or runtime dependency is required.

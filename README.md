# TokenMe

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

The public benchmark covers the same ten case IDs across two compatible Luna
runs. The current **30-cell** run pairs Normal and TokenMe's Compact Policy. A
previous **60-cell** run used the same tickets for Normal, Caveman, Ponytail,
and RTK. Every listed arm passed 10/10 deterministic fixture checks. The
competitor rows are same-case reference data from a different provider-session
and cache batch, so they are not presented as one strictly paired ranking.

| Arm | Batch | Total | Input | Cached input | Cache ratio | Fresh input | Reasoning (subset) | Output | Estimated cost* |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Normal baseline | Current paired | 784,541 | 771,540 | 631,040 | 81.79% | 140,500 | 1,833 | 13,001 | $0.056322 |
| **TokenMe** | **Current paired** | **660,517** | **648,958** | **523,008** | **80.59%** | **125,950** | 2,392 | **11,559** | **$0.049521** |
| Caveman skill | Same-case reference | 876,701 | 863,825 | 725,504 | 83.99% | 138,321 | 1,973 | 12,876 | $0.057625 |
| Ponytail treatment | Same-case reference | 845,959 | 833,311 | 690,944 | 82.92% | 142,367 | 2,503 | 12,648 | $0.057470 |
| RTK treatment | Same-case reference | 1,195,620 | 1,178,595 | 1,006,848 | 85.43% | 171,747 | 3,181 | 17,025 | $0.074916 |

In the current paired run, TokenMe used **15.81% fewer total tokens**,
**15.89% fewer input tokens**, **11.09% fewer output tokens**, and had a
**12.08% lower estimated cost** than its Normal baseline. Reasoning increased
by 30.5%, so it is shown separately rather than presented as a saving. Absolute
cache-read is lower because the complete request is smaller; cache ratio is
shown separately.

For the same-case reference batch, Caveman, Ponytail, and RTK were respectively
**15.12%**, **11.08%**, and **57.00%** above that batch's Normal total of 761,557
tokens. Those figures are contextual evidence, not a claim that cache state and
run timing were identical to the current compact-policy pair. The treatment
arms also do not insert the Caveman proxy/CCR or RTK transport into the provider
request path.

The compact policy also reduced completed command executions from **30 to 20**
and aggregate command-output characters from **55,762 to 49,378**. This is a
measured result for this task mix, model, provider cache state, and harness—not
a universal ranking. The test compares host instructions; it does not insert a
Caveman proxy/CCR or an RTK binary into the provider request path.

*Estimate only, not a local Codex invoice:* uncached input x $0.20/MTok +
cached input x $0.02/MTok + output x $1.20/MTok. Reasoning is a subset of output
and is not added again. Raw JSONL and copied workspaces remain ignored. See the
[compact-policy report](benchmark/audit_10_case/COMPACT_POLICY_REPORT.md) and
[same-case reference report](benchmark/audit_10_case/LATEST_6_ARM_REPORT.md)
for the full methodology, raw/inferred/unknown boundary, and limitations.

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
For the current Compact Policy benchmark:

```powershell
python benchmark/audit_10_case/run_compact.py `
  --codex C:\Users\Pc\AppData\Local\Temp\tokenme-codex-cli.exe `
  --model gpt-5.6-luna --reasoning-effort low --workers 3 `
  --tasks benchmark/audit_10_case/tasks.py `
  --result-root benchmark/audit_10_case/runs_compact_public `
  --score benchmark/provider_total/mechanism_score.py
```

Read the methodology and limitations in
[`benchmark/audit_10_case/COMPACT_POLICY_REPORT.md`](benchmark/audit_10_case/COMPACT_POLICY_REPORT.md).

## Related research

- [JetBrains: Caveman](https://blog.jetbrains.com/ai/2026/07/speak-to-ai-agents-like-cavemen-tosave-tokens/)
- [JetBrains: RTK + Claude Code](https://blog.jetbrains.com/ai/2026/07/rtk-claude-code-token-savings/)
- [JetBrains: Ponytail](https://blog.jetbrains.com/ai/2026/07/ponytail-skill-claude-tested/)
- [Caveman source](https://github.com/JuliusBrussee/caveman)
- [RTK source](https://github.com/rtk-ai/rtk)
- [Ponytail source](https://github.com/DietrichGebert/ponytail)

## License

MIT. No daemon, network telemetry, or runtime dependency is required.

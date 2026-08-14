# TokenMe v3 — latest five-arm provider benchmark

This is the current public benchmark after the four optimizer recommendations
and the prose/tool route guard. It supersedes the earlier 40-cell before/after
snapshot for headline comparisons.

## Method

- Model: local Codex `gpt-5.6-luna`, low reasoning effort; no API key.
- Cases: ten identical mechanism cases: four prose, three Bash/RTK-heavy, and three over-building/Ponytail-heavy.
- Cells: 50 fresh `codex exec --ephemeral --json` sessions: Normal, **TokenMe v3**, the exact local Caveman skill, the preserved Ponytail treatment text, and the real local RTK binary.
- All provider sessions completed. Deterministic fixture checks passed 10/10 for every arm.
- Ponytail and RTK checkouts were absent at their original `Downloads\bench` path. Their exact treatment text is preserved in the prior checked-in audit prompt artifacts; each result records its source path and SHA-256. RTK command activation used `C:\Users\Pc\AppData\Local\Temp\tokenme-rtk-v0420-audit\rtk.exe` and was active in all ten RTK cells.

## Provider ledger

```text
total_tokens = input_tokens + output_tokens
reasoning_output_tokens ⊂ output_tokens
visible_output_tokens = output_tokens - reasoning_output_tokens
```

| Arm | Input | Cache read | Cache write | Fresh input | Reasoning | Visible output | Output total | Total | Luna price-sheet estimate* |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Normal | 758,909 | 632,576 | 0 | 126,333 | 2,133 | 11,035 | 13,168 | 772,077 | $0.053720 |
| **TokenMe v3** | **743,492** | **643,584** | **0** | **99,908** | **1,947** | **10,349** | **12,296** | **755,788** | **$0.047608** |
| Caveman skill | 825,983 | 683,264 | 0 | 142,719 | 1,663 | 9,336 | 10,999 | 836,982 | $0.055408 |
| Ponytail treatment | 764,742 | 644,096 | 0 | 120,646 | 1,870 | 10,030 | 11,900 | 776,642 | $0.051291 |
| RTK treatment | 1,304,413 | 1,109,760 | 0 | 194,653 | 3,944 | 15,224 | 19,168 | 1,323,581 | $0.084127 |

\* Price-sheet estimate only, not a local Codex invoice:
`uncached_input × $0.20/MTok + cache_read × $0.02/MTok + output × $1.20/MTok`.
Reasoning is included once in output. Cache-read is a provider component; it
does not prove that a treatment caused the cache hit.

## Latest deltas

| Comparison | Total tokens | Input | Output | Reasoning | Price-sheet estimate |
|---|---:|---:|---:|---:|---:|
| TokenMe v3 vs Normal | **−2.11%** | −2.03% | −6.62% | −8.72% | **−11.38%** |
| TokenMe v3 vs Caveman | **−9.70%** | −9.99% | +11.79% | +17.08% | **−14.08%** |
| TokenMe v3 vs Ponytail | **−2.69%** | −2.78% | +3.33% | +4.12% | **−7.18%** |
| TokenMe v3 vs RTK | **−42.90%** | −42.99% | −35.86% | −50.63% | **−43.41%** |

Negative percentages in this table mean TokenMe v3 used less. TokenMe v3's
paired total-token bootstrap 95% CI versus Normal was [-11,501.6, 7,928.3]
tokens, so the point estimate is useful for this task pack but not a universal
guarantee. Output's paired interval was [-171.5, -14.0] tokens.

## Version context

TokenMe v2 is the pre-four-recommendation build. Its older five-case pilot
recorded 367,739 total tokens versus 422,425 for Normal (−12.95%) using
`gpt-5.6-sol`; that population is not interchangeable with this Luna run.
TokenMe v3 is the current implementation and is measured above on the larger
five-arm pack.

## Limitations

This is an instruction-treatment benchmark inside Codex. It does not place the
Caveman Go proxy/CCR or a Ponytail/RTK provider proxy in the request path. The
task pack is small, cache state is not randomized, and the mechanism scorer
checks functional predicates rather than human semantic quality. Raw JSONL is
the evidence; local tokenizer counts and price-sheet dollars are inferred or
estimated. Re-run with a larger, preregistered population before making a
production-wide claim.

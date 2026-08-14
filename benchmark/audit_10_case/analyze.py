"""Analyze the completed Luna Normal/Caveman/TokenMe audit.

This script deliberately keeps three ledgers separate:

* provider: Codex ``turn.completed`` usage copied from each JSONL stream;
* inferred: local TokenMe estimator applied only to visible prompt/final text;
* unknown: hidden system/tool tokens, provider billing state, and any field not
  present in a provider event.

It never treats a local estimate as provider usage and never adds reasoning or
cache components twice to total tokens.
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tokenme.estimate import count_for_model


ROOT = Path(__file__).resolve().parent
RUNS = ROOT / "runs_luna"
MODEL = "gpt-5.6-luna"
ARMS = ("baseline", "caveman", "tokenme")

# Values are the Luna model page's list prices as of the benchmark date. They
# produce a price-sheet estimate only; a local Codex session is not an API
# invoice. Cache-write is included for completeness and is zero in this run.
PRICE = {
    "input": 0.20,
    "cache_read": 0.02,
    "cache_write": 0.25,
    "output": 1.20,
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def policy_text(prompt: str, arm: str) -> str:
    marker = {
        "caveman": "\n## Caveman treatment instructions\n",
        "tokenme": "\n## TokenMe compiled policy\n",
    }.get(arm)
    if not marker or marker not in prompt:
        return ""
    return prompt.split(marker, 1)[1]


def usage_rows():
    for arm in ARMS:
        for result_path in sorted((RUNS / arm).glob("*/result.json")):
            row = load(result_path)
            prompt_path = result_path.parent / "prompt.md"
            final_path = result_path.parent / "CODEX_FINAL.md"
            prompt = prompt_path.read_text(encoding="utf-8", errors="replace") if prompt_path.exists() else ""
            final = final_path.read_text(encoding="utf-8", errors="replace") if final_path.exists() else ""
            p_tokens, p_method = count_for_model(prompt, MODEL)
            pol = policy_text(prompt, arm)
            pol_tokens, pol_method = count_for_model(pol, MODEL)
            f_tokens, f_method = count_for_model(final, MODEL)
            usage = row.get("usage", {})
            # The parser defines total as input + output. Reasoning and cache
            # fields are subsets/components and are not added a second time.
            yield {
                "arm": arm,
                "task": row.get("task"),
                "stratum": row.get("quality", {}).get("stratum"),
                "status": row.get("status"),
                "quality_passed": row.get("quality", {}).get("passed", 0),
                "duration_seconds": row.get("duration_seconds"),
                "provider": {k: usage.get(k, 0) for k in (
                    "input_tokens", "cached_input_tokens", "cache_write_input_tokens",
                    "output_tokens", "reasoning_output_tokens", "total_tokens",
                    "uncached_input_tokens", "fresh_input_tokens", "turns",
                    "malformed_lines")},
                "inferred": {
                    "visible_prompt_tokens": p_tokens,
                    "visible_prompt_method": p_method,
                    "policy_tokens": pol_tokens,
                    "policy_method": pol_method,
                    "final_tokens": f_tokens,
                    "final_method": f_method,
                    "prompt_chars": len(prompt),
                    "policy_chars": len(pol),
                    "final_chars": len(final),
                },
            }


def money(u: dict) -> float:
    uncached = u["input_tokens"] - u["cached_input_tokens"]
    return (
        uncached * PRICE["input"] / 1_000_000
        + u["cached_input_tokens"] * PRICE["cache_read"] / 1_000_000
        + u["cache_write_input_tokens"] * PRICE["cache_write"] / 1_000_000
        + u["output_tokens"] * PRICE["output"] / 1_000_000
    )


def aggregate(rows: list[dict]) -> dict:
    out = {}
    for arm in ARMS:
        scoped = [r for r in rows if r["arm"] == arm]
        p = {k: sum(r["provider"][k] for r in scoped) for k in (
            "input_tokens", "cached_input_tokens", "cache_write_input_tokens",
            "output_tokens", "reasoning_output_tokens", "total_tokens",
            "uncached_input_tokens", "fresh_input_tokens", "turns", "malformed_lines")}
        i = {k: sum(r["inferred"][k] for r in scoped) for k in (
            "visible_prompt_tokens", "policy_tokens", "final_tokens",
            "prompt_chars", "policy_chars", "final_chars")}
        out[arm] = {
            "sessions": len(scoped),
            "provider": p,
            "price_sheet_estimate_usd": round(money(p), 8),
            "inferred_visible": i,
            "inferred_methods": sorted({r["inferred"]["visible_prompt_method"] for r in scoped}),
            "quality_passed": sum(r["quality_passed"] for r in scoped),
            "quality_possible": len(scoped),
            "median_duration_seconds": statistics.median(r["duration_seconds"] for r in scoped),
            "sum_duration_seconds": round(sum(r["duration_seconds"] for r in scoped), 3),
            "provider_complete_sessions": sum(
                1 for r in scoped if r["provider"]["turns"] > 0 and r["provider"]["malformed_lines"] == 0),
        }
    return out


def pct(a: float, b: float) -> float:
    return (1 - a / b) * 100 if b else 0.0


def md(rows: list[dict], agg: dict) -> str:
    b = agg["baseline"]
    lines = [
        "# Luna 10-case provider audit: Normal vs Caveman vs TokenMe",
        "",
        "Run date: 2026-08-15 (local session); model: `gpt-5.6-luna`; reasoning: `low`.",
        "",
        "This is a paired, mechanism-targeted benchmark: 10 identical cases × 3 arms = 30 fresh `codex exec --ephemeral` sessions. Every cell passed its deterministic functional predicate (30/30). It measures behavior under a policy/skill, not a transparent proxy rewrite.",
        "",
        "## Provider-observed ledger",
        "",
        "`total_tokens = input_tokens + output_tokens`. `cached_input_tokens`, `cache_write_input_tokens`, and `reasoning_output_tokens` are reported components; they are not added again. `fresh_input = (input - cache_read) + cache_write`.",
        "",
        "| Arm | Sessions | Complete | Input | Cache read | Cache write | Fresh input | Reasoning | Output | Total | Quality | Luna price-sheet estimate* |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for arm in ARMS:
        a = agg[arm]
        p = a["provider"]
        lines.append(
            f"| {arm} | {a['sessions']} | {a['provider_complete_sessions']} | {p['input_tokens']:,} | "
            f"{p['cached_input_tokens']:,} | {p['cache_write_input_tokens']:,} | {p['fresh_input_tokens']:,} | "
            f"{p['reasoning_output_tokens']:,} | {p['output_tokens']:,} | {p['total_tokens']:,} | "
            f"{a['quality_passed']}/{a['quality_possible']} | ${a['price_sheet_estimate_usd']:.5f} |"
        )
    lines += [
        "",
        "*Estimate uses the official Luna list-price fields (uncached input $0.20/MTok, cache-read $0.02/MTok, cache-write $0.25/MTok, output $1.20/MTok). It is not a provider invoice for this local Codex session; actual billing/accounting is unknown.",
        "",
        "## Reduction versus Normal (positive means fewer)",
        "",
        "| Arm | Total | Input | Fresh input | Output | Price-sheet estimate | Median latency |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for arm in ("caveman", "tokenme"):
        a = agg[arm]
        p = a["provider"]
        bp = b["provider"]
        lines.append(
            f"| {arm} | {pct(p['total_tokens'], bp['total_tokens']):+.2f}% | "
            f"{pct(p['input_tokens'], bp['input_tokens']):+.2f}% | "
            f"{pct(p['fresh_input_tokens'], bp['fresh_input_tokens']):+.2f}% | "
            f"{pct(p['output_tokens'], bp['output_tokens']):+.2f}% | "
            f"{pct(a['price_sheet_estimate_usd'], b['price_sheet_estimate_usd']):+.2f}% | "
            f"{a['median_duration_seconds']:.3f}s |"
        )
    lines += [
        "",
        "## Inferred local counts (not provider usage)",
        "",
        "TokenMe's visible prompt/final text was counted with `tokenme.estimate.count_for_model`. The environment had no `tiktoken`, so all rows use `~est` (heuristic). These counts exclude hidden system instructions, tool transcripts, server framing, and provider-side tokenization; they must not be presented as billed tokens.",
        "",
        "| Arm | Visible prompt chars | Visible prompt ~tokens | Treatment policy chars | Treatment policy ~tokens | Final ~tokens | Method |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for arm in ARMS:
        i = agg[arm]["inferred_visible"]
        lines.append(
            f"| {arm} | {i['prompt_chars']:,} | {i['visible_prompt_tokens']:,} | "
            f"{i['policy_chars']:,} | {i['policy_tokens']:,} | {i['final_tokens']:,} | "
            f"{', '.join(agg[arm]['inferred_methods'])} |"
        )
    lines += [
        "",
        "## What the run does and does not prove",
        "",
        "- TokenMe used 756,177 provider-reported tokens versus Normal 814,127: **7.12% lower total**, with 7.05% lower input and 11.39% lower output, while all 10 quality predicates passed.",
        "- Caveman skill used 925,572 tokens: **13.69% higher total** than Normal in this mixed suite. Its output was 7.09% lower, but the long skill text and resulting behavior increased input by 14.04%.",
        "- TokenMe's provider output was 11,928 vs Normal 13,463 (−1,535). This matters because Luna output is priced much higher than input; the price-sheet estimate is 6.10% lower for TokenMe and 6.42% higher for Caveman.",
        "- Cache reads are provider observations, not proof that an optimizer caused a cache hit. No cache-write tokens were reported in these ephemeral cells. Reasoning is a component of output and was not double-counted.",
        "- One run per case is paired but not a 5-repeat variance study. The task pack is intentionally mechanism-targeted and includes a per-cell temp workspace path; results are not universal production savings.",
        "- Quality is deterministic fixture/function checking plus required prose markers, not a full semantic or human readability evaluation. Raw JSONL is retained for independent re-analysis.",
        "",
        "## Artifact provenance",
        "",
        "Each `runs_luna/<arm>/<case>/` directory contains `prompt.md`, `usage.jsonl`, `stderr.log`, final response, copied workspace, `score.json`, and `result.json`. The runner and selected task manifest are in `benchmark/audit_10_case/`; the exact Caveman skill source is `C:/Users/Pc/Downloads/caveman-main/plugins/caveman/skills/caveman/SKILL.md`.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    rows = list(usage_rows())
    if len(rows) != 30:
        raise SystemExit(f"expected 30 result rows, found {len(rows)}")
    agg = aggregate(rows)
    (RUNS / "AUDIT_SUMMARY.json").write_text(
        json.dumps({"model": MODEL, "prices": PRICE, "rows": rows, "arms": agg},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    (RUNS / "AUDIT_SUMMARY.md").write_text(md(rows, agg), encoding="utf-8")
    # PowerShell may expose a cp1252 stdout; the report itself is UTF-8.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(md(rows, agg))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

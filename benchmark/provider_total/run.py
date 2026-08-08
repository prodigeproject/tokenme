"""Run paired Codex usage benchmarks with preserved JSONL and quality artifacts.

Each invocation is a fresh ``codex exec --ephemeral`` session. The default task
pack is the five-case wiring pilot; the mechanism pack supplies thirty
stratified tasks through ``--tasks``.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import importlib.util
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
HERE = Path(__file__).resolve().parent
TEMPLATE = ROOT / "benchmark" / "independent_codex" / "template"
RESULT_ROOT = HERE / "runs"
TASKS_PATH = HERE / "tasks.json"
SCORE_PATH = ROOT / "benchmark" / "independent_codex" / "score.py"
BENCH_ROOT = ROOT.parent / "bench"

ARMS = ("baseline", "tokenme", "caveman", "ponytail", "rtk")
SCORE_LOCK = threading.Lock()
ARM_LABELS = {
    "baseline": "No token-minimization instructions.",
    "tokenme": "Adaptive TokenMe core plus only the modules selected by tokenme route.",
    "caveman": "The exact local Caveman skill used as a treatment instruction.",
    "ponytail": "The exact local Ponytail skill used as a treatment instruction.",
    "rtk": "The exact local RTK Codex awareness instructions, with the RTK binary on PATH.",
}


def load_score_module(path: Path = SCORE_PATH):
    spec = importlib.util.spec_from_file_location("provider_score", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_task_pack(path: Path) -> dict:
    """Load a JSON task pack or a Python module exposing TASKS/task_pack()."""
    if path.suffix.lower() != ".py":
        return load_json(path)
    spec = importlib.util.spec_from_file_location("tokenme_task_pack", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    value = module.task_pack() if hasattr(module, "task_pack") else module.TASKS
    if isinstance(value, list):
        return {"suite": path.stem, "description": "Python task pack", "tasks": value}
    return value


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def build_instructions(arm: str, ticket: str) -> tuple[str, dict]:
    if arm == "baseline":
        return "", {"source": "none", "modules": []}
    if arm == "tokenme":
        from tokenme import router
        from tokenme import prompt as tokenme_prompt

        route = router.route_text(ticket)
        text = tokenme_prompt.render_instructions(route, header=True)
        return text, {"source": "local-tokenme-compiled", "modules": route["modules"], "route": route,
                      "prompt_chars": len(text),
                      "skill_sha256": sha256_text(text)}
    if arm == "caveman":
        path = BENCH_ROOT / "caveman-main" / "plugins" / "caveman" / "skills" / "caveman" / "SKILL.md"
        text = "\n## Caveman treatment instructions\n" + read_text(path)
        return text, {"source": str(path), "modules": ["caveman"],
                      "skill_sha256": sha256_text(text)}
    if arm == "ponytail":
        path = BENCH_ROOT / "ponytail-main" / "skills" / "ponytail" / "SKILL.md"
        text = "\n## Ponytail treatment instructions\n" + read_text(path)
        return text, {"source": str(path), "modules": ["ponytail"],
                      "skill_sha256": sha256_text(text)}
    if arm == "rtk":
        path = BENCH_ROOT / "rtk-develop" / "hooks" / "codex" / "rtk-awareness.md"
        text = "\n## RTK treatment instructions\n" + read_text(path)
        return text, {"source": str(path), "modules": ["rtk-awareness"],
                      "skill_sha256": sha256_text(text)}
    raise ValueError(f"unknown arm: {arm}")


def common_prompt(run_dir: Path, task_id: str, ticket: str) -> str:
    return f"""You are one isolated cell in a coding benchmark.

Workspace: {run_dir}
Case: {task_id}

Only read or modify files inside the workspace. Do not inspect the benchmark
scorer, the repository containing the runner, or any other arm/case. Implement
the ticket below with production-reasonable choices. Run focused checks when
useful. Do not change unrelated files or add dependencies.

Ticket:
{ticket}

Before finishing, write the exact user-facing final response you intend to
return into FINAL_RESPONSE.md at the workspace root, then return the same text.
Do not mention benchmark strategy or other arms in that response.
"""


def score_workspace(score_module, workspace: Path, task_id: str) -> dict:
    try:
        result = score_module.score(workspace, task_id)
        result["run"] = str(workspace)
        return result
    except Exception as exc:  # preserve failed runs instead of dropping them
        return {"run": str(workspace), "checks": {}, "passed": 0,
                "score_error": f"{type(exc).__name__}: {exc}"}


def rescore_artifacts(result_root: Path, score_module, task_ids: set[str] | None = None) -> int:
    """Re-run deterministic quality checks without spending provider calls.

    This is useful when a scorer or fixture import path is corrected after a
    provider run.  Usage JSONL and the submitted workspace are left intact;
    only score.json, quality, and the derived status in result.json change.
    """
    updated = 0
    for result_path in result_root.glob("*/**/result.json"):
        row = load_json(result_path)
        task_id = row.get("task")
        if task_ids and task_id not in task_ids:
            continue
        workspace = result_path.parent / "workspace"
        if not workspace.is_dir():
            continue
        quality = score_workspace(score_module, workspace, task_id)
        row["quality"] = quality
        row["status"] = (
            "ok"
            if row.get("returncode") == 0
            and row.get("usage", {}).get("turns", 0)
            and not quality.get("score_error")
            else "failed"
        )
        (result_path.parent / "score.json").write_text(
            json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
        result_path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
        updated += 1
    return updated


def materialize_task_files(workspace: Path, task: dict) -> None:
    for relative, content in task.get("files", {}).items():
        path = workspace / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def run_one(arm: str, task: dict, args, temp_root: Path) -> dict:
    task_id = task["id"]
    result_root = Path(args.result_root).resolve()
    template = Path(args.template).resolve()
    artifact = result_root / arm / task_id
    if artifact.exists() and not args.rerun:
        cached = artifact / "result.json"
        if cached.exists():
            previous = load_json(cached)
            if previous.get("returncode") == 0 and previous.get("usage", {}).get("turns", 0):
                return previous | {"status": "skipped_existing"}
    if artifact.exists():
        shutil.rmtree(artifact)
    artifact.mkdir(parents=True, exist_ok=True)
    workspace = temp_root / arm / task_id
    workspace.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(template, workspace)
    materialize_task_files(workspace, task)
    instructions, instruction_meta = build_instructions(arm, task["ticket"])
    prompt = common_prompt(workspace, task_id, task["ticket"]) + instructions
    (artifact / "prompt.md").write_text(prompt, encoding="utf-8")
    (artifact / "route.json").write_text(
        json.dumps(instruction_meta, ensure_ascii=False, indent=2), encoding="utf-8")

    codex_path = Path(args.codex).resolve()
    final_path = workspace / "CODEX_FINAL.md"
    cmd = [
        str(codex_path), "exec", "--ephemeral", "--json", "--ignore-user-config",
        # The benchmark workspaces are disposable temp directories.  Bypass
        # interactive approval/sandbox policy so the agent can actually edit
        # them under non-interactive execution; artifacts remain isolated and
        # the host process is still bounded by the runner timeout.
        "--dangerously-bypass-approvals-and-sandbox",
        "--skip-git-repo-check", "--model", args.model,
        "-c", f'model_reasoning_effort="{args.reasoning_effort}"',
        "--cd", str(workspace), "--output-last-message", str(final_path), prompt,
    ]
    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    if arm == "rtk":
        rtk_dir = Path(args.rtk).resolve().parent
        env["PATH"] = str(rtk_dir) + os.pathsep + env.get("PATH", "")
        # Isolate RTK telemetry/history per cell. This makes activation and
        # command-level savings auditable without mutating the user's store.
        env["RTK_DB_PATH"] = str(artifact / "rtk-history.db")
        env["RTK_TEE_DIR"] = str(artifact / "rtk-tee")
    started = time.time()
    try:
        proc = subprocess.run(
            cmd, cwd=str(workspace), env=env, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=args.timeout,
        )
        returncode = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr
    except subprocess.TimeoutExpired as exc:
        returncode = -timedelta_seconds(args.timeout)
        stdout = exc.stdout or ""
        stderr = (exc.stderr or "") + f"\nTIMEOUT after {args.timeout}s\n"
    duration = round(time.time() - started, 3)
    (artifact / "usage.jsonl").write_text(stdout, encoding="utf-8")
    (artifact / "stderr.log").write_text(stderr, encoding="utf-8")
    if arm == "rtk":
        rtk_path = str(Path(args.rtk).resolve())
        try:
            gain = subprocess.run(
                [rtk_path, "gain", "--all", "--format", "json"],
                cwd=str(workspace), env=env, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=30,
            )
            (artifact / "rtk_gain.json").write_text(gain.stdout, encoding="utf-8")
            (artifact / "rtk_gain.stderr.log").write_text(gain.stderr, encoding="utf-8")
            (artifact / "rtk_gain.meta.json").write_text(json.dumps({
                "returncode": gain.returncode,
                "db_path": env["RTK_DB_PATH"],
                "audit_dir": env["RTK_TEE_DIR"],
            }, indent=2), encoding="utf-8")
        except Exception as exc:
            (artifact / "rtk_gain.meta.json").write_text(json.dumps({
                "returncode": None,
                "db_path": env["RTK_DB_PATH"],
                "error": f"{type(exc).__name__}: {exc}",
            }, indent=2), encoding="utf-8")
    if final_path.exists():
        shutil.copy2(final_path, artifact / "CODEX_FINAL.md")
    agent_final = workspace / "FINAL_RESPONSE.md"
    if agent_final.exists():
        shutil.copy2(agent_final, artifact / "FINAL_RESPONSE.md")
    with SCORE_LOCK:
        score_module = load_score_module(Path(args.score))
        score = score_workspace(score_module, workspace, task_id)
    (artifact / "score.json").write_text(json.dumps(score, ensure_ascii=False, indent=2),
                                          encoding="utf-8")
    shutil.copytree(workspace, artifact / "workspace")
    from tokenme.provider import parse_codex_jsonl

    usage = parse_codex_jsonl(stdout)
    activation = {}
    if arm == "rtk":
        gain_meta_path = artifact / "rtk_gain.meta.json"
        gain_meta = load_json(gain_meta_path) if gain_meta_path.exists() else {}
        activation = {
            "rtk_db_exists": Path(env["RTK_DB_PATH"]).exists(),
            "rtk_db_bytes": Path(env["RTK_DB_PATH"]).stat().st_size if Path(env["RTK_DB_PATH"]).exists() else 0,
            "gain_returncode": gain_meta.get("returncode"),
        }
    result = {
        "arm": arm,
        "task": task_id,
        "returncode": returncode,
        "duration_seconds": duration,
        "usage": usage,
        "quality": score,
        "instructions": instruction_meta,
        "activation": activation,
        "artifact": str(artifact.relative_to(ROOT)),
        "status": "ok" if returncode == 0 and not score.get("score_error") else "failed",
    }
    (artifact / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2),
                                           encoding="utf-8")
    return result


def timedelta_seconds(seconds: int) -> int:
    return max(1, int(seconds))


def _bootstrap_ci(values: list[float], seed: int = 0, rounds: int = 10000) -> list[float] | None:
    if not values:
        return None
    if len(values) == 1:
        value = round(values[0], 4)
        return [value, value]
    rng = random.Random(seed)
    estimates = []
    for _ in range(rounds):
        sample = [values[rng.randrange(len(values))] for _ in values]
        estimates.append(statistics.mean(sample))
    estimates.sort()
    return [round(estimates[int(rounds * 0.025)], 4),
            round(estimates[int(rounds * 0.975) - 1], 4)]


def summarize(rows: list[dict], manifest: dict) -> tuple[dict, str]:
    by_arm = {arm: [r for r in rows if r["arm"] == arm] for arm in ARMS}
    task_meta = {task["id"]: task for task in manifest["tasks"]}
    strata = sorted({task.get("stratum", "unclassified") for task in manifest["tasks"]})
    summary = {"manifest": manifest, "runs": rows, "arms": {},
               "by_stratum": {}, "paired_vs_baseline": {},
               "paired_summary": {}}
    for arm, arm_rows in by_arm.items():
        usage_values = [r["usage"] for r in arm_rows if r["usage"].get("turns", 0)]
        completed_runs = len(usage_values)
        quality_valid_runs = sum(
            1 for r in arm_rows
            if r.get("usage", {}).get("turns", 0)
            and r.get("quality", {}).get("passed", 0) > 0
        )
        totals = [u["total_tokens"] for u in usage_values]
        inputs = [u["input_tokens"] for u in usage_values]
        outputs = [u["output_tokens"] for u in usage_values]
        scores = [r.get("quality", {}).get("passed", 0) for r in arm_rows]
        summary["arms"][arm] = {
            "runs": len(arm_rows),
            "provider_completed_runs": completed_runs,
            "provider_failed_runs": len(arm_rows) - completed_runs,
            "quality_valid_runs": quality_valid_runs,
            "successful_runs": sum(r["status"] == "ok" for r in arm_rows),
            "quality_checks_total": sum(scores),
            # Each independent session receives exactly one case-specific
            # quality predicate; five sessions therefore mean five checks per
            # arm (the old pilot used five predicates in one shared workspace).
            "quality_checks_possible": len(arm_rows),
            "median_total_tokens": statistics.median(totals) if totals else None,
            "mean_total_tokens": round(statistics.mean(totals), 2) if totals else None,
            "median_input_tokens": statistics.median(inputs) if inputs else None,
            "median_output_tokens": statistics.median(outputs) if outputs else None,
            "total_tokens": sum(totals),
            "input_tokens": sum(inputs),
            "output_tokens": sum(outputs),
            "cached_input_tokens": sum(u["cached_input_tokens"] for u in usage_values),
            "fresh_input_tokens": sum(u.get("fresh_input_tokens", 0) for u in usage_values),
            "reasoning_output_tokens": sum(u["reasoning_output_tokens"] for u in usage_values),
            "added_loc": sum(r.get("quality", {}).get("added_loc", 0) for r in arm_rows),
            "test_loc": sum(r.get("quality", {}).get("test_loc", 0) for r in arm_rows),
            "final_chars": sum(r.get("quality", {}).get("final_chars", 0) for r in arm_rows),
            "rtk_activated_runs": sum(1 for r in arm_rows if r.get("activation", {}).get("rtk_db_bytes", 0) > 0),
        }
    for stratum in strata:
        summary["by_stratum"][stratum] = {}
        for arm in ARMS:
            scoped = [r for r in by_arm[arm]
                      if task_meta.get(r["task"], {}).get("stratum", "unclassified") == stratum]
            usage_values = [r["usage"] for r in scoped if r["usage"].get("turns", 0)]
            completed_runs = len(usage_values)
            summary["by_stratum"][stratum][arm] = {
                "runs": len(scoped),
                "provider_completed_runs": completed_runs,
                "provider_failed_runs": len(scoped) - completed_runs,
                "quality_valid_runs": sum(
                    1 for r in scoped
                    if r.get("usage", {}).get("turns", 0)
                    and r.get("quality", {}).get("passed", 0) > 0
                ),
                "total_tokens": sum(u.get("total_tokens", 0) for u in usage_values),
                "input_tokens": sum(u.get("input_tokens", 0) for u in usage_values),
                "fresh_input_tokens": sum(u.get("fresh_input_tokens", 0) for u in usage_values),
                "output_tokens": sum(u.get("output_tokens", 0) for u in usage_values),
                "median_total_tokens": statistics.median(
                    [u["total_tokens"] for u in usage_values]) if usage_values else None,
                "quality_checks_total": sum(r.get("quality", {}).get("passed", 0) for r in scoped),
                "quality_checks_possible": len(scoped),
                "added_loc": sum(r.get("quality", {}).get("added_loc", 0) for r in scoped),
                "test_loc": sum(r.get("quality", {}).get("test_loc", 0) for r in scoped),
                "final_chars": sum(r.get("quality", {}).get("final_chars", 0) for r in scoped),
            }
    baseline = {r["task"]: r for r in by_arm["baseline"]}
    for arm in ARMS:
        if arm == "baseline":
            continue
        pairs = []
        for row in by_arm[arm]:
            base = baseline.get(row["task"])
            if not base:
                continue
            a = row["usage"].get("total_tokens")
            b = base["usage"].get("total_tokens")
            if isinstance(a, int) and isinstance(b, int) and a and b:
                pairs.append({"task": row["task"], "treatment": a,
                              "baseline": b, "delta": a - b,
                              "reduction_pct": round((1 - a / b) * 100, 2)})
        summary["paired_vs_baseline"][arm] = pairs
        deltas = [pair["delta"] for pair in pairs]
        input_pairs = []
        fresh_pairs = []
        output_pairs = []
        treatment_by_task = {r["task"]: r for r in by_arm[arm]}
        baseline_by_task = {r["task"]: r for r in by_arm["baseline"]}
        for task_id, treatment_row in treatment_by_task.items():
            base_row = baseline_by_task.get(task_id)
            if not base_row:
                continue
            for key, dest in (("input_tokens", input_pairs),
                              ("fresh_input_tokens", fresh_pairs),
                              ("output_tokens", output_pairs)):
                a = treatment_row["usage"].get(key)
                b = base_row["usage"].get(key)
                if isinstance(a, int) and isinstance(b, int) and b:
                    dest.append(a - b)
        def metric(values: list[int]) -> dict:
            return {
                "n": len(values),
                "mean_delta": round(statistics.mean(values), 2) if values else None,
                "median_delta": statistics.median(values) if values else None,
                "bootstrap_95ci_mean_delta": _bootstrap_ci([float(v) for v in values], seed=17),
            }
        summary["paired_summary"][arm] = {
            "total": metric(deltas),
            "input": metric(input_pairs),
            "fresh_input": metric(fresh_pairs),
            "output": metric(output_pairs),
        }
    lines = [
        "# Provider-token benchmark results",
        "",
        f"Suite: `{manifest['suite']}`; model: `{manifest['model']}`; "
        f"reasoning: `{manifest['reasoning_effort']}`.",
        "",
        "Total tokens are provider-reported `input_tokens + output_tokens`. "
        "Cached input and reasoning output are components, not added twice.",
        "",
        "| Arm | Sessions | Provider complete | Total | Input | Fresh input | Output | Cached input | Reasoning output | Median/run | Added LOC | Quality |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for arm in ARMS:
        s = summary["arms"][arm]
        lines.append(
            f"| {arm} | {s['runs']} | {s['provider_completed_runs']} | {s['total_tokens']:,} | {s['input_tokens']:,} | "
            f"{s['fresh_input_tokens']:,} | {s['output_tokens']:,} | "
                f"{s['cached_input_tokens']:,} | {s['reasoning_output_tokens']:,} | "
                f"{(s['median_total_tokens'] or 0):,} | {s['added_loc']:,} | "
                f"{s['quality_checks_total']}/"
            f"{s['quality_checks_possible']} checks |"
        )
    lines += [
        "",
        "## Paired deltas vs baseline",
        "",
        "Negative `delta` means the treatment used fewer provider-reported tokens.",
        "",
    ]
    for arm, pairs in summary["paired_vs_baseline"].items():
        lines.append(f"### {arm}")
        lines.append("")
        lines.append("| Case | Baseline | Treatment | Delta | Reduction |")
        lines.append("|---|---:|---:|---:|---:|")
        for pair in pairs:
            lines.append(f"| {pair['task']} | {pair['baseline']} | {pair['treatment']} | "
                         f"{pair['delta']:+} | {pair['reduction_pct']:+.2f}% |")
        lines.append("")
    lines += [
        "## Stratum totals",
        "",
        "Each stratum has ten paired tasks in the mechanism suite. Values below are provider totals; failed provider cells are shown in the Complete column and excluded from token sums.",
        "",
        "| Stratum | Arm | Sessions | Complete | Total | Input | Fresh input | Output | Median/run | Added LOC | Quality |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for stratum in strata:
        for arm in ARMS:
            s = summary["by_stratum"][stratum][arm]
            lines.append(
                f"| {stratum} | {arm} | {s['runs']} | {s['provider_completed_runs']} | {s['total_tokens']:,} | "
                f"{s['input_tokens']:,} | {s['fresh_input_tokens']:,} | "
                f"{s['output_tokens']:,} | {(s['median_total_tokens'] or 0):,} | {s['added_loc']:,} | "
                f"{s['quality_checks_total']}/{s['quality_checks_possible']} |"
            )
    lines += [
        "",
        "## Paired-delta bootstrap summaries",
        "",
        "Delta is treatment minus baseline; negative is lower usage. CI is a deterministic percentile bootstrap over paired tasks.",
        "",
        "| Arm | Metric | n | Mean delta | Median delta | 95% CI mean delta |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for arm in ARMS:
        if arm == "baseline":
            continue
        for metric_name, values in summary["paired_summary"][arm].items():
            ci = values["bootstrap_95ci_mean_delta"]
            ci_text = f"[{ci[0]:,.2f}, {ci[1]:,.2f}]" if ci else "n/a"
            lines.append(
                f"| {arm} | {metric_name} | {values['n']} | "
                f"{(values['mean_delta'] if values['mean_delta'] is not None else 0):,} | "
                f"{(values['median_delta'] if values['median_delta'] is not None else 0):,} | {ci_text} |"
            )
    lines += [
        "",
        "## Artifact layout",
        "",
        "Each `runs/<arm>/<case>/` directory contains the exact prompt, "
        "`usage.jsonl`, stderr, final messages, score, and copied workspace.",
        "The complete JSONL stream is preserved for every independent session. "
        "The suite is a mechanism-targeted benchmark; intervals describe this task pack, not a universal population.",
    ]
    return summary, "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex", default=str(Path(os.environ.get(
        "TEMP", tempfile.gettempdir())) / "tokenme-codex-cli.exe"))
    parser.add_argument("--rtk", default=str(Path(os.environ.get(
        "TEMP", tempfile.gettempdir())) / "tokenme-rtk-v0420-audit" / "rtk.exe"))
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--reasoning-effort", default="low")
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--rerun", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--summary-only", action="store_true",
                        help="rebuild RESULTS.json/.md from existing result.json artifacts")
    parser.add_argument("--rescore", action="store_true",
                        help="re-run deterministic scorers on copied workspaces before summarizing")
    parser.add_argument("--tasks", default=str(TASKS_PATH),
                        help="JSON task pack or Python module exposing TASKS/task_pack()")
    parser.add_argument("--template", default=str(TEMPLATE))
    parser.add_argument("--score", default=str(SCORE_PATH))
    parser.add_argument("--result-root", default=str(RESULT_ROOT))
    parser.add_argument("--seed", type=int, default=20260807,
                        help="deterministic task-order seed shared by all arms")
    parser.add_argument("--only", default="",
                        help="comma-separated task ids for a bounded smoke run")
    args = parser.parse_args()

    data = load_task_pack(Path(args.tasks).resolve())
    tasks = list(data["tasks"])
    random.Random(args.seed).shuffle(tasks)
    if args.only:
        wanted = {item.strip() for item in args.only.split(",") if item.strip()}
        tasks = [task for task in tasks if task["id"] in wanted]
        missing = wanted - {task["id"] for task in tasks}
        if missing:
            raise SystemExit(f"unknown task ids: {sorted(missing)}")
    result_root = Path(args.result_root).resolve()
    manifest = {
        "suite": data["suite"],
        "description": data["description"],
        "model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "arms": list(ARMS),
        "sessions_per_arm": len(tasks),
        "tasks": tasks,
        "seed": args.seed,
        "template": str(Path(args.template).resolve()),
        "rtk_binary": args.rtk,
        "rtk_version": "0.42.0 official Windows binary",
        "quality_scorer": str(Path(args.score).resolve()),
    }
    result_root.mkdir(parents=True, exist_ok=True)
    manifest_path = result_root / "manifest.json"
    # A summary/rescore operation must not rewrite the pre-registered task
    # manifest.  The prompt and usage artifacts are the record of what ran;
    # changing the manifest while merely re-scoring would make that record
    # appear to describe a different task pack.
    if not (args.summary_only and manifest_path.exists()):
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
    if args.rescore:
        score_module = load_score_module(Path(args.score).resolve())
        updated = rescore_artifacts(result_root, score_module,
                                    {task["id"] for task in tasks})
        print(f"RESCORED {updated} existing artifacts", flush=True)
    if args.summary_only:
        summary_manifest = load_json(manifest_path) if manifest_path.exists() else manifest
        rows = []
        for path in result_root.glob("*/**/result.json"):
            rows.append(load_json(path))
        if len(rows) != len(ARMS) * len(tasks):
            raise SystemExit(f"expected {len(ARMS) * len(tasks)} result.json files, found {len(rows)}")
        rows.sort(key=lambda row: (ARMS.index(row["arm"]), row["task"]))
        summary, markdown = summarize(rows, summary_manifest)
        (result_root / "RESULTS.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                                            encoding="utf-8")
        (result_root / "RESULTS.md").write_text(markdown, encoding="utf-8")
        print(f"WROTE {result_root / 'RESULTS.json'}", flush=True)
        print(f"WROTE {result_root / 'RESULTS.md'}", flush=True)
        return 0
    if args.dry_run:
        for task in tasks:
            print(task["id"])
            for arm in ARMS:
                _, meta = build_instructions(arm, task["ticket"])
                print(f"  {arm}: {meta.get('modules', [])}")
        return 0
    if not Path(args.codex).is_file():
        raise SystemExit(f"Codex CLI not found: {args.codex}")
    if not Path(args.rtk).is_file():
        raise SystemExit(f"RTK binary not found: {args.rtk}")

    rows = []
    temp_root = Path(tempfile.mkdtemp(prefix="tokenme-provider-total-"))
    try:
        for task in tasks:
            print(f"CASE {task['id']}: launching {len(ARMS)} independent arms", flush=True)
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(args.workers, len(ARMS))) as pool:
                futures = [pool.submit(run_one, arm, task, args, temp_root) for arm in ARMS]
                for future in concurrent.futures.as_completed(futures):
                    row = future.result()
                    rows.append(row)
                    print(f"  DONE {row['arm']}/{row['task']}: "
                          f"{row['usage'].get('total_tokens', 0)} tokens, "
                          f"quality {row.get('quality', {}).get('passed', 0)}/1, "
                          f"status={row['status']}", flush=True)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
    rows.sort(key=lambda row: (ARMS.index(row["arm"]), row["task"]))
    summary, markdown = summarize(rows, manifest)
    (result_root / "RESULTS.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                                        encoding="utf-8")
    (result_root / "RESULTS.md").write_text(markdown, encoding="utf-8")
    print(f"WROTE {result_root / 'RESULTS.json'}", flush=True)
    print(f"WROTE {result_root / 'RESULTS.md'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

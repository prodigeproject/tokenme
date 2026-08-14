"""Active adaptive-router follow-up using measured per-case feedback.

The feedback map is derived from the completed latest five-arm run: for each
case, ``max(0, baseline_total - TokenMe_v3_total)`` is supplied as the next
run's expected saving. This is a real host observation, not a synthetic
percentage. Negative/unknown cases therefore drop the tool/context delta while
retaining the code safety contract.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROVIDER_TOTAL = ROOT / "benchmark" / "provider_total"
if str(PROVIDER_TOTAL) not in sys.path:
    sys.path.insert(0, str(PROVIDER_TOTAL))
import run as provider_run  # noqa: E402


FEEDBACK_RESULTS = ROOT / "benchmark" / "audit_10_case" / "runs_latest_all_v2" / "RESULTS.json"
TASKS = ROOT / "benchmark" / "audit_10_case" / "tasks.py"


def _feedback_by_ticket() -> dict[str, int]:
    results = json.loads(FEEDBACK_RESULTS.read_text(encoding="utf-8"))
    rows: dict[str, dict[str, int]] = {}
    for row in results["runs"]:
        if row.get("arm") in {"baseline", "tokenme"}:
            rows.setdefault(row["task"], {})[row["arm"]] = int(
                row.get("usage", {}).get("total_tokens", 0) or 0)
    pack = provider_run.load_task_pack(TASKS)
    by_id = {task["id"]: task["ticket"] for task in pack["tasks"]}
    return {
        by_id[task_id]: max(0, values.get("baseline", 0) - values.get("tokenme", 0))
        for task_id, values in rows.items()
        if task_id in by_id and values.get("baseline") and values.get("tokenme")
    }


FEEDBACK = _feedback_by_ticket()
provider_run.ARMS = ("baseline", "tokenme_v3_active")
provider_run.SCORE_PATH = ROOT / "benchmark" / "provider_total" / "mechanism_score.py"


def build_instructions(arm: str, ticket: str) -> tuple[str, dict]:
    if arm == "baseline":
        return "", {"source": "none", "modules": []}
    if arm == "tokenme_v3_active":
        from tokenme import prompt as tokenme_prompt, router
        expected = FEEDBACK.get(ticket)
        route = router.adaptive_route(ticket, expected_saving_tokens=expected)
        text = tokenme_prompt.render_instructions(route, header=True)
        return text, {
            "source": "local-tokenme-v3-adaptive-feedback",
            "modules": route["modules"],
            "route": route,
            "feedback_source": str(FEEDBACK_RESULTS),
            "expected_saving_tokens": expected,
            "prompt_chars": len(text),
            "skill_sha256": provider_run.sha256_text(text),
        }
    raise ValueError(f"unknown arm: {arm}")


provider_run.build_instructions = build_instructions


def main() -> int:
    if "--rtk" not in sys.argv:
        sys.argv.extend(["--rtk", str(Path.home() / "AppData" / "Local" / "Temp" / "tokenme-rtk-v0420-audit" / "rtk.exe")])
    return provider_run.main()


if __name__ == "__main__":
    raise SystemExit(main())

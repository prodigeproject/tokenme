"""Rebuild a full latest-all summary after a bounded continuation run."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "benchmark" / "audit_10_case"))
import run_latest_all  # noqa: E402
RESULT_ROOT = ROOT / "benchmark" / "audit_10_case" / "runs_latest_all_v3"
TASKS = ROOT / "benchmark" / "audit_10_case" / "tasks.py"


def main() -> int:
    runner = run_latest_all.provider_run
    data = runner.load_task_pack(TASKS)
    manifest_path = RESULT_ROOT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["suite"] = data["suite"]
    manifest["description"] = data["description"]
    manifest["arms"] = list(runner.ARMS)
    manifest["sessions_per_arm"] = len(data["tasks"])
    manifest["tasks"] = data["tasks"]
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    rows = [json.loads(path.read_text(encoding="utf-8"))
            for path in RESULT_ROOT.glob("*/**/result.json")]
    expected = len(runner.ARMS) * len(data["tasks"])
    if len(rows) != expected:
        raise SystemExit(f"expected {expected} rows, found {len(rows)}")
    rows.sort(key=lambda row: (runner.ARMS.index(row["arm"]), row["task"]))
    summary, markdown = runner.summarize(rows, manifest)
    (RESULT_ROOT / "RESULTS.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (RESULT_ROOT / "RESULTS.md").write_text(markdown, encoding="utf-8")
    print(f"WROTE {len(rows)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

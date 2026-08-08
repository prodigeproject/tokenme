"""Quality scorer for the 30-task mechanism benchmark."""
from __future__ import annotations

import csv
import importlib.util
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path


def _load_work(run: Path):
    # The submitted module may intentionally import a fixture-local helper.
    # `spec_from_file_location` does not add the workspace to import search
    # paths, so do that for the duration of the load and restore global state
    # afterwards.  Without this, a correct solution could fail only because
    # the scorer imported it from outside its workspace.
    run = run.resolve()
    path = run / "work.py"
    spec = importlib.util.spec_from_file_location(f"mechanism_{id(path)}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.path.insert(0, str(run))
    try:
        spec.loader.exec_module(module)
    finally:
        try:
            sys.path.remove(str(run))
        except ValueError:
            pass
    return module


PROSE_REQUIRED = {
    "prose_release": ("highlights", "risks", "next action", "2.4.0", "820", "610", "step 3"),
    "prose_incident": ("impact", "root cause", "mitigation", "18,400", "retry", "rate limiting"),
    "prose_review": ("finding", "evidence", "recommendation", "p1", "n+1", "composite index"),
    "prose_migration": ("before", "after", "rollback", "readable", "resum", "drop-column"),
    "prose_support": ("answer", "evidence", "limit", "429", "retry-after", "credentials"),
    "prose_api": ("contract", "failure modes", "next action", "post /v1/exports", "idempotency", "202"),
    "prose_change": ("added", "changed", "breaking", "webauthn", "/oauth/token", "legacy"),
    "prose_security": ("threat", "control", "residual risk", "path traversal", "canonical", "symlink"),
    "prose_perf": ("baseline", "bottleneck", "experiment", "1,240", "61%", "100 records"),
    "prose_arch": ("decision", "trade-off", "rejected", "queue-backed", "eventual consistency", "polling"),
}


def _rtk_check(run: Path, task: str) -> bool:
    work = _load_work(run)
    def lines(value):
        return value.splitlines() if isinstance(value, str) else value

    cases = {
        "rtk_errors": lambda: lines(work.filter_error_lines("INFO boot\nERROR disk full\nWARN retry\nERROR timeout\n")) == ["ERROR disk full", "ERROR timeout"],
        "rtk_status": lambda: work.count_status("status=200\nstatus=500\nstatus=200\n") == {200: 2, 500: 1},
        "rtk_ids": lambda: work.extract_ids("ID=9 ID=2\nID=9\n") == [2, 9],
        "rtk_duration": lambda: abs(work.average_duration_ms("duration_ms=10\nduration_ms=30\nnoise\n") - 20.0) < 1e-9,
        "rtk_paths": lambda: work.normalize_paths("C:\\repo\\a.py\nD:\\tmp\\b.py\n") == "C:/repo/a.py\nD:/tmp/b.py",
        "rtk_recent": lambda: work.recent_lines("one\ntwo\nthree\n\n") == ["two", "three"],
        "rtk_redact": lambda: str(work.redact_tokens("user=ana token=abc123\nstatus=ok\n")).rstrip("\n") == "user=ana token=[REDACTED]\nstatus=ok",
        "rtk_kv": lambda: work.parse_kv("mode=fast\ninvalid\ncount=3\n") == {"mode": "fast", "count": "3"},
        "rtk_failed": lambda: work.failed_commands("cmd=build exit=0\ncmd=test exit=1\n") == ["test"],
        "rtk_routes": lambda: [tuple(item) for item in work.top_routes("route=/a\nroute=/b\nroute=/a\n")] == [("/a", 2), ("/b", 1)],
    }
    return bool(cases[task]())


def _pony_check(run: Path, task: str) -> bool:
    work = _load_work(run)
    cases = {
        "pony_strip_version": lambda: work.strip_version("v1.2.3") == "1.2.3" and work.strip_version("1.2.3") == "1.2.3",
        "pony_json_bool": lambda: work.parse_enabled("true") is True and work.parse_enabled("false") is False,
        "pony_join_path": lambda: Path(work.join_path("/srv", "app.log")).as_posix().rstrip("/") == "/srv/app.log",
        "pony_iso_date": lambda: work.iso_date("2026-08-07T12:34:56+00:00") == "2026-08-07",
        "pony_clamp": lambda: work.clamp(-4, 0, 10) == 0 and work.clamp(15, 0, 10) == 10 and work.clamp(4, 0, 10) == 4,
        "pony_first_nonempty": lambda: work.first_nonempty(["", "  ", "ready"]) == "ready" and work.first_nonempty(["", " "]) is None,
        "pony_host": lambda: work.split_host("https://example.com/a") == "example.com" and work.split_host("/relative") is None,
        "pony_env_default": lambda: work.env_default({"MODE": "prod"}, "MODE", "dev") == "prod" and work.env_default({}, "MODE", "dev") == "dev",
        "pony_csv_column": lambda: work.csv_column("name,score\na,1\nb,\nc,3\n", "score") == ["1", "3"],
        "pony_dedupe": lambda: work.dedupe_preserve(["a", "b", "a", "c"]) == ["a", "b", "c"],
    }
    return bool(cases[task]())


def _added_loc(run: Path) -> tuple[int, int]:
    source = 0
    tests = 0
    for path in run.rglob("*"):
        if not path.is_file() or path.suffix not in {".py", ".ts", ".tsx", ".js", ".jsx"}:
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        count = sum(1 for line in lines if line.strip() and not line.lstrip().startswith(("#", "//")))
        if path.name.lower().startswith("test_") or "test" in {part.lower() for part in path.parts}:
            tests += count
        else:
            source += count
    return source, tests


def score(run: Path, task: str | None = None) -> dict:
    task = task or ""
    result = {"run": str(run), "checks": {}}

    def check() -> bool:
        if task in PROSE_REQUIRED:
            final = run / "FINAL_RESPONSE.md"
            if not final.exists():
                return False
            text = final.read_text(encoding="utf-8", errors="replace").casefold()
            compact = re.sub(r"[\s_-]+", "", text)
            return all(
                marker.casefold() in text
                or marker.casefold().replace(",", "") in text.replace(",", "")
                or re.sub(r"[\s_-]+", "", marker.casefold()) in compact
                for marker in PROSE_REQUIRED[task]
            )
        if task.startswith("rtk_"):
            return _rtk_check(run, task)
        if task.startswith("pony_"):
            return _pony_check(run, task)
        return False

    try:
        result["checks"][task] = bool(check())
    except Exception as exc:
        result["checks"][task] = False
        result["check_error"] = f"{type(exc).__name__}: {exc}"
    result["passed"] = sum(result["checks"].values())
    result["final_chars"] = len((run / "FINAL_RESPONSE.md").read_text(encoding="utf-8", errors="replace")) if (run / "FINAL_RESPONSE.md").exists() else 0
    result["added_loc"], result["test_loc"] = _added_loc(run)
    return result


if __name__ == "__main__":
    print(json.dumps([score(Path(arg).resolve()) for arg in sys.argv[1:]], indent=2))

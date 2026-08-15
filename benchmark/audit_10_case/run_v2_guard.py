"""Compare legacy TokenMe v2 with a bounded-tool-output guard.

The legacy arm loads router/prompt source from d947148.  The guard arm uses
the identical legacy route and compiled policy, then adds only the explicit
bounded-search/diff contract from the current prompt module.  This isolates
the 90k-character tool-output mitigation from the other v3 changes.
"""
from __future__ import annotations

import subprocess
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROVIDER_TOTAL = ROOT / "benchmark" / "provider_total"
if str(PROVIDER_TOTAL) not in sys.path:
    sys.path.insert(0, str(PROVIDER_TOTAL))
import run as provider_run  # noqa: E402


BEFORE_COMMIT = "d947148"


def _legacy_prompt():
    source = subprocess.check_output(
        ["git", "show", f"{BEFORE_COMMIT}:tokenme/prompt.py"],
        cwd=str(ROOT), text=True, encoding="utf-8",
    )
    module = types.ModuleType("tokenme_legacy_prompt_guard")
    exec(compile(source, f"prompt.py@{BEFORE_COMMIT}", "exec"), module.__dict__)
    return module


def _legacy_router():
    source = subprocess.check_output(
        ["git", "show", f"{BEFORE_COMMIT}:tokenme/router.py"],
        cwd=str(ROOT), text=True, encoding="utf-8",
    )
    module = types.ModuleType("tokenme_legacy_router_guard")
    module.__package__ = "tokenme"
    exec(compile(source, f"router.py@{BEFORE_COMMIT}", "exec"), module.__dict__)
    return module


LEGACY_PROMPT = _legacy_prompt()
LEGACY_ROUTER = _legacy_router()
provider_run.ARMS = ("baseline", "tokenme_v2_legacy", "tokenme_v2_guard")
provider_run.SCORE_PATH = ROOT / "benchmark" / "provider_total" / "mechanism_score.py"


def build_instructions(arm: str, ticket: str) -> tuple[str, dict]:
    if arm == "baseline":
        return "", {"source": "none", "modules": []}
    if arm not in {"tokenme_v2_legacy", "tokenme_v2_guard"}:
        raise ValueError(f"unknown arm: {arm}")
    route = LEGACY_ROUTER.route_text(ticket)
    text = LEGACY_PROMPT.render_instructions(route, header=True)
    meta = {
        "source": f"tokenme-prompt@{BEFORE_COMMIT}",
        "modules": route["modules"],
        "route": route,
        "phase": "v2",
        "variant": "legacy" if arm.endswith("legacy") else "bounded-tool-guard",
        "prompt_chars": len(text),
        "skill_sha256": provider_run.sha256_text(text),
    }
    if arm == "tokenme_v2_guard":
        from tokenme.prompt import bounded_tool_guard
        guard = bounded_tool_guard()
        text += "\n## TokenMe bounded tool-output guard\n" + guard + "\n"
        meta["guard"] = "bounded_tool_output_v1"
        meta["guard_chars"] = len(guard)
        meta["prompt_chars"] = len(text)
        meta["skill_sha256"] = provider_run.sha256_text(text)
    return text, meta


provider_run.build_instructions = build_instructions


def main() -> int:
    if "--rtk" not in sys.argv:
        sys.argv.extend([
            "--rtk",
            str(Path.home() / "AppData" / "Local" / "Temp" /
                "tokenme-rtk-v0420-audit" / "rtk.exe"),
        ])
    return provider_run.main()


if __name__ == "__main__":
    raise SystemExit(main())

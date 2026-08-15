"""Before/after benchmark for the v3 Compact Policy improvements.

The ``tokenme_v3_before`` arm loads the TokenMe source from the commit before
the current prompt changes.  ``tokenme_v3_compact`` uses the working-tree
router and prompt, which add explicit read-only prose and bounded-trajectory
hints while keeping the adaptive router's unknown-economics fail-safe.
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


BEFORE_COMMIT = "3a555c7"


def _snapshot(module_name: str, relative_path: str):
    source = subprocess.check_output(
        ["git", "show", f"{BEFORE_COMMIT}:{relative_path}"],
        cwd=str(ROOT), text=True, encoding="utf-8",
    )
    module = types.ModuleType(module_name)
    module.__package__ = "tokenme"
    exec(compile(source, f"{relative_path}@{BEFORE_COMMIT}", "exec"), module.__dict__)
    return module


BEFORE_PROMPT = _snapshot("tokenme_v3_before_prompt", "tokenme/prompt.py")
BEFORE_ROUTER = _snapshot("tokenme_v3_before_router", "tokenme/router.py")

provider_run.ARMS = ("baseline", "tokenme_v3_before", "tokenme_v3_compact")
provider_run.SCORE_PATH = ROOT / "benchmark" / "provider_total" / "mechanism_score.py"


def build_instructions(arm: str, ticket: str) -> tuple[str, dict]:
    if arm == "baseline":
        return "", {"source": "none", "modules": []}
    if arm == "tokenme_v3_before":
        route = BEFORE_ROUTER.adaptive_route(ticket)
        text = BEFORE_PROMPT.render_instructions(route, header=True)
        return text, {
            "source": f"tokenme-snapshot@{BEFORE_COMMIT}",
            "modules": route["modules"],
            "route": route,
            "phase": "v3-before",
            "prompt_chars": len(text),
            "skill_sha256": provider_run.sha256_text(text),
        }
    if arm == "tokenme_v3_compact":
        from tokenme import prompt, router
        route = router.adaptive_route(ticket)
        text = prompt.render_instructions(route, header=True)
        return text, {
            "source": "local-tokenme-v3-compact-policy",
            "modules": route["modules"],
            "route": route,
            "phase": "v3-compact",
            "prompt_chars": len(text),
            "skill_sha256": provider_run.sha256_text(text),
        }
    raise ValueError(f"unknown arm: {arm}")


provider_run.build_instructions = build_instructions


def main() -> int:
    return provider_run.main()


if __name__ == "__main__":
    raise SystemExit(main())

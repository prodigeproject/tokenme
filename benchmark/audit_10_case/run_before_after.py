"""Paired before/after benchmark for the four TokenMe improvements.

The ``tokenme_v2`` arm loads the pre-four-recommendation router/prompt from
commit d947148, while ``tokenme_v3`` uses the current adaptive route and
summary policy.  All arms receive the same ten tasks and are launched by the
same provider-total harness, so provider JSONL remains the source of truth.
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


CAVEMAN_ROOT = Path(r"C:\Users\Pc\Downloads\caveman-main")
CAVEMAN_SKILL = CAVEMAN_ROOT / "plugins" / "caveman" / "skills" / "caveman" / "SKILL.md"
BEFORE_COMMIT = "d947148"

provider_run.ARMS = ("baseline", "tokenme_v2", "tokenme_v3", "caveman")
provider_run.SCORE_PATH = ROOT / "benchmark" / "provider_total" / "mechanism_score.py"


def _legacy_prompt():
    """Load the exact pre-improvement prompt compiler without editing source."""
    source = subprocess.check_output(
        ["git", "show", f"{BEFORE_COMMIT}:tokenme/prompt.py"],
        cwd=str(ROOT), text=True, encoding="utf-8",
    )
    module = types.ModuleType("tokenme_legacy_prompt")
    exec(compile(source, "prompt.py@" + BEFORE_COMMIT, "exec"), module.__dict__)
    return module


LEGACY_PROMPT = _legacy_prompt()


def _legacy_router():
    """Load the pre-classification router used by the benchmark-before arm."""
    source = subprocess.check_output(
        ["git", "show", f"{BEFORE_COMMIT}:tokenme/router.py"],
        cwd=str(ROOT), text=True, encoding="utf-8",
    )
    module = types.ModuleType("tokenme_legacy_router")
    module.__package__ = "tokenme"
    exec(compile(source, "router.py@" + BEFORE_COMMIT, "exec"), module.__dict__)
    return module


LEGACY_ROUTER = _legacy_router()


def build_instructions(arm: str, ticket: str) -> tuple[str, dict]:
    if arm == "baseline":
        return "", {"source": "none", "modules": []}
    if arm == "caveman":
        text = "\n## Caveman treatment instructions\n" + CAVEMAN_SKILL.read_text(
            encoding="utf-8", errors="replace")
        return text, {"source": str(CAVEMAN_SKILL), "modules": ["caveman"],
                      "skill_sha256": provider_run.sha256_text(text)}
    from tokenme import prompt as current_prompt, router
    if arm == "tokenme_v2":
        route = LEGACY_ROUTER.route_text(ticket)
        text = LEGACY_PROMPT.render_instructions(route, header=True)
        return text, {"source": f"tokenme-prompt@{BEFORE_COMMIT}",
                      "modules": route["modules"], "route": route,
                      "phase": "v2", "prompt_chars": len(text),
                      "skill_sha256": provider_run.sha256_text(text)}
    if arm == "tokenme_v3":
        route = router.adaptive_route(ticket)
        text = current_prompt.render_instructions(route, header=True)
        return text, {"source": "local-tokenme-adaptive", "modules": route["modules"],
                      "route": route, "phase": "v3", "prompt_chars": len(text),
                      "skill_sha256": provider_run.sha256_text(text)}
    raise ValueError(f"unknown arm: {arm}")


provider_run.build_instructions = build_instructions


def main() -> int:
    # The preserved runner validates an RTK path even when RTK is not an arm.
    if "--rtk" not in sys.argv:
        try:
            codex = sys.argv[sys.argv.index("--codex") + 1]
        except (ValueError, IndexError):
            codex = str(Path.home() / "AppData" / "Local" / "Temp" / "tokenme-codex-cli.exe")
        sys.argv.extend(["--rtk", codex])
    return provider_run.main()


if __name__ == "__main__":
    raise SystemExit(main())

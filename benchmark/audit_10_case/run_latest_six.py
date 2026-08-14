"""Latest six-arm Luna benchmark with TokenMe v2 and v3 head-to-head.

Arms are Normal, TokenMe v2 (the pre-four-recommendation source snapshot),
TokenMe v3, Caveman, Ponytail, and RTK.  Each arm receives the same ten-case
mechanism pack, so the complete run contains 60 independent provider sessions.
Ponytail/RTK treatment text is reused from the checked-in audit prompt
artifacts; RTK command execution uses the real local binary passed to the
runner.
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


CAVEMAN_SKILL = Path(
    r"C:\Users\Pc\Downloads\caveman-main\plugins\caveman\skills\caveman\SKILL.md"
)
PRESERVED_PONYTAIL_PROMPT = (
    ROOT / "benchmark" / "provider_total" / "runs_compact_v6" /
    "ponytail" / "safe_path" / "prompt.md"
)
PRESERVED_RTK_PROMPT = (
    ROOT / "benchmark" / "provider_total" / "runs_compact_v6" /
    "rtk" / "safe_path" / "prompt.md"
)
BEFORE_COMMIT = "d947148"


def _preserved_section(path: Path, heading: str) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if heading not in text:
        raise RuntimeError(f"preserved treatment heading not found: {path}")
    return text.split(heading, 1)[1].lstrip()


PONYTAIL_SKILL = _preserved_section(
    PRESERVED_PONYTAIL_PROMPT, "## Ponytail treatment instructions"
)
RTK_SKILL = _preserved_section(
    PRESERVED_RTK_PROMPT, "## RTK treatment instructions"
)


def _legacy_prompt():
    source = subprocess.check_output(
        ["git", "show", f"{BEFORE_COMMIT}:tokenme/prompt.py"],
        cwd=str(ROOT), text=True, encoding="utf-8",
    )
    module = types.ModuleType("tokenme_legacy_prompt_latest")
    exec(compile(source, f"prompt.py@{BEFORE_COMMIT}", "exec"), module.__dict__)
    return module


def _legacy_router():
    source = subprocess.check_output(
        ["git", "show", f"{BEFORE_COMMIT}:tokenme/router.py"],
        cwd=str(ROOT), text=True, encoding="utf-8",
    )
    module = types.ModuleType("tokenme_legacy_router_latest")
    module.__package__ = "tokenme"
    exec(compile(source, f"router.py@{BEFORE_COMMIT}", "exec"), module.__dict__)
    return module


LEGACY_PROMPT = _legacy_prompt()
LEGACY_ROUTER = _legacy_router()

provider_run.ARMS = (
    "baseline", "tokenme_v2", "tokenme_v3", "caveman", "ponytail", "rtk"
)
provider_run.SCORE_PATH = ROOT / "benchmark" / "provider_total" / "mechanism_score.py"


def build_instructions(arm: str, ticket: str) -> tuple[str, dict]:
    if arm == "baseline":
        return "", {"source": "none", "modules": []}
    if arm == "tokenme_v2":
        route = LEGACY_ROUTER.route_text(ticket)
        text = LEGACY_PROMPT.render_instructions(route, header=True)
        return text, {
            "source": f"tokenme-prompt@{BEFORE_COMMIT}",
            "modules": route["modules"],
            "route": route,
            "phase": "v2",
            "prompt_chars": len(text),
            "skill_sha256": provider_run.sha256_text(text),
        }
    if arm == "tokenme_v3":
        from tokenme import prompt as tokenme_prompt, router
        route = router.adaptive_route(ticket)
        text = tokenme_prompt.render_instructions(route, header=True)
        return text, {
            "source": "local-tokenme-v3-adaptive",
            "modules": route["modules"],
            "route": route,
            "phase": "v3",
            "prompt_chars": len(text),
            "skill_sha256": provider_run.sha256_text(text),
        }
    if arm == "caveman":
        text = "\n## Caveman treatment instructions\n" + CAVEMAN_SKILL.read_text(
            encoding="utf-8", errors="replace"
        )
        return text, {
            "source": str(CAVEMAN_SKILL),
            "modules": ["caveman"],
            "skill_sha256": provider_run.sha256_text(text),
        }
    if arm == "ponytail":
        text = "\n## Ponytail treatment instructions\n" + PONYTAIL_SKILL
        return text, {
            "source": str(PRESERVED_PONYTAIL_PROMPT),
            "modules": ["ponytail"],
            "source_note": "exact treatment text preserved from prior audit artifact",
            "skill_sha256": provider_run.sha256_text(text),
        }
    if arm == "rtk":
        text = "\n## RTK treatment instructions\n" + RTK_SKILL
        return text, {
            "source": str(PRESERVED_RTK_PROMPT),
            "modules": ["rtk-awareness"],
            "source_note": "exact treatment text preserved from prior audit artifact",
            "skill_sha256": provider_run.sha256_text(text),
        }
    raise ValueError(f"unknown arm: {arm}")


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

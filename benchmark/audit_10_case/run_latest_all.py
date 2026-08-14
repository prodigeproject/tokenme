"""Latest five-arm Luna benchmark: Normal, TokenMe, Caveman, Ponytail, RTK.

The Ponytail/RTK checkout used by the earlier audit is no longer present at
the original ``Downloads\bench`` path.  To keep the treatment reproducible,
this wrapper reuses the exact instruction text preserved in the checked-in
prior prompt artifacts and records their SHA-256 in each route file.  RTK
command execution still uses the real local binary passed with ``--rtk``.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROVIDER_TOTAL = ROOT / "benchmark" / "provider_total"
if str(PROVIDER_TOTAL) not in sys.path:
    sys.path.insert(0, str(PROVIDER_TOTAL))
import run as provider_run  # noqa: E402


CAVEMAN_SKILL = Path(r"C:\Users\Pc\Downloads\caveman-main\plugins\caveman\skills\caveman\SKILL.md")
PRESERVED_PONYTAIL_PROMPT = ROOT / "benchmark" / "provider_total" / "runs_compact_v6" / "ponytail" / "safe_path" / "prompt.md"
PRESERVED_RTK_PROMPT = ROOT / "benchmark" / "provider_total" / "runs_compact_v6" / "rtk" / "safe_path" / "prompt.md"


def _preserved_section(path: Path, heading: str) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    marker = heading
    if marker not in text:
        raise RuntimeError(f"preserved treatment heading not found: {path}")
    return text.split(marker, 1)[1].lstrip()


PONYTAIL_SKILL = _preserved_section(PRESERVED_PONYTAIL_PROMPT, "## Ponytail treatment instructions")
RTK_SKILL = _preserved_section(PRESERVED_RTK_PROMPT, "## RTK treatment instructions")

provider_run.ARMS = ("baseline", "tokenme_v3", "caveman", "ponytail", "rtk")
provider_run.SCORE_PATH = ROOT / "benchmark" / "provider_total" / "mechanism_score.py"


def build_instructions(arm: str, ticket: str) -> tuple[str, dict]:
    if arm == "baseline":
        return "", {"source": "none", "modules": []}
    if arm == "caveman":
        text = "\n## Caveman treatment instructions\n" + CAVEMAN_SKILL.read_text(
            encoding="utf-8", errors="replace")
        return text, {"source": str(CAVEMAN_SKILL), "modules": ["caveman"],
                      "skill_sha256": provider_run.sha256_text(text)}
    if arm == "ponytail":
        text = "\n## Ponytail treatment instructions\n" + PONYTAIL_SKILL
        return text, {"source": str(PRESERVED_PONYTAIL_PROMPT), "modules": ["ponytail"],
                      "source_note": "exact treatment text preserved from prior audit artifact",
                      "skill_sha256": provider_run.sha256_text(text)}
    if arm == "rtk":
        text = "\n## RTK treatment instructions\n" + RTK_SKILL
        return text, {"source": str(PRESERVED_RTK_PROMPT), "modules": ["rtk-awareness"],
                      "source_note": "exact treatment text preserved from prior audit artifact",
                      "skill_sha256": provider_run.sha256_text(text)}
    if arm == "tokenme_v3":
        from tokenme import prompt as tokenme_prompt, router
        route = router.adaptive_route(ticket)
        text = tokenme_prompt.render_instructions(route, header=True)
        return text, {"source": "local-tokenme-v3-adaptive", "modules": route["modules"],
                      "route": route, "prompt_chars": len(text),
                      "skill_sha256": provider_run.sha256_text(text)}
    raise ValueError(f"unknown arm: {arm}")


provider_run.build_instructions = build_instructions


def main() -> int:
    if "--rtk" not in sys.argv:
        sys.argv.extend(["--rtk", str(Path.home() / "AppData" / "Local" / "Temp" / "tokenme-rtk-v0420-audit" / "rtk.exe")])
    return provider_run.main()


if __name__ == "__main__":
    raise SystemExit(main())

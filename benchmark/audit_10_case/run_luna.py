"""Run the three-arm Luna audit using the preserved provider-total harness.

This wrapper intentionally leaves TokenMe source untouched.  It narrows the
existing runner to Normal/Caveman/TokenMe and points Caveman at the exact local
checkout requested for the audit.
"""
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROVIDER_TOTAL = ROOT / "benchmark" / "provider_total"
if str(PROVIDER_TOTAL) not in sys.path:
    sys.path.insert(0, str(PROVIDER_TOTAL))

import run as provider_run  # noqa: E402


CAVEMAN_ROOT = Path(r"C:\Users\Pc\Downloads\caveman-main")
CAVEMAN_SKILL = CAVEMAN_ROOT / "plugins" / "caveman" / "skills" / "caveman" / "SKILL.md"


provider_run.ARMS = ("baseline", "caveman", "tokenme")
# The selected manifest is the mechanism suite (not the older five-case
# independent_codex suite), so quality must use its matching deterministic
# scorer.  Keeping this in the wrapper prevents a silent KeyError/zero-quality
# result if the command is run without an explicit --score argument.
provider_run.SCORE_PATH = ROOT / "benchmark" / "provider_total" / "mechanism_score.py"


def build_instructions(arm: str, ticket: str) -> tuple[str, dict]:
    if arm == "baseline":
        return "", {"source": "none", "modules": []}
    if arm == "caveman":
        text = "\n## Caveman treatment instructions\n" + CAVEMAN_SKILL.read_text(
            encoding="utf-8", errors="replace"
        )
        return text, {
            "source": str(CAVEMAN_SKILL),
            "modules": ["caveman"],
            "skill_sha256": provider_run.sha256_text(text),
        }
    if arm == "tokenme":
        from tokenme import prompt as tokenme_prompt
        from tokenme import router

        route = router.route_text(ticket)
        text = tokenme_prompt.render_instructions(route, header=True)
        return text, {
            "source": "local-tokenme-compiled",
            "modules": route["modules"],
            "route": route,
            "prompt_chars": len(text),
            "skill_sha256": provider_run.sha256_text(text),
        }
    raise ValueError(f"unknown audit arm: {arm}")


provider_run.build_instructions = build_instructions


def main() -> int:
    # The preserved runner validates an RTK path even when RTK is not an arm.
    # Reuse the Codex executable as an inert existing path; run_one never calls
    # it because provider_run.ARMS excludes rtk.
    if "--rtk" not in sys.argv:
        try:
            codex = sys.argv[sys.argv.index("--codex") + 1]
        except (ValueError, IndexError):
            codex = str(Path.home() / "AppData" / "Local" / "Temp" / "tokenme-codex-cli.exe")
        sys.argv.extend(["--rtk", codex])
    return provider_run.main()


if __name__ == "__main__":
    raise SystemExit(main())

"""Quality guard.

Scans a unified diff (or before/after files) for two classes of risk:

  1. REMOVED PROTECTIVE CODE â€” validation, error handling, security,
     accessibility, or test patterns that were removed and not replaced.
  2. WEAKENED LOGIC â€” operator loosening, negation removal, constant-guard
     replacement, or numeric bound changes within the same diff hunk.

LIMITATIONS (stated honestly â€” this is a heuristic, not a proof):
  - Pattern-based, not an AST analyser. Can miss subtle logic changes.
  - Reports suspicious removals; a human must verify intent.
  - False positives and false negatives are both possible.
  - Does NOT prove code is safe â€” flags common risk patterns only.

The guard errs toward reporting: warn and surface evidence, never block
silently, always show the specific lines so a human decides.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

# â”€â”€ language detection â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_LANG_MAP = {
    r"\.py\b": "python", r"\.js\b": "js", r"\.ts\b": "ts",
    r"\.tsx\b": "ts", r"\.jsx\b": "js", r"\.go\b": "go",
    r"\.rs\b": "rust", r"\.java\b": "java", r"\.rb\b": "ruby",
    r"\.cs\b": "csharp", r"\.html?\b": "html", r"\.css\b": "css",
    r"\.php\b": "php", r"\.kt\b": "kotlin",
}


def _detect_lang(diff_text: str) -> str | None:
    header = diff_text[:800]
    for pat, lang in _LANG_MAP.items():
        if re.search(pat, header, re.IGNORECASE):
            return lang
    return None


# â”€â”€ noise-filter helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_COMMENT_RE = re.compile(
    r"^\s*(#|//|/\*|\*(?!/)|--|\*/|<!--|-->|\"\"\"|\'{3})"
)
_IMPORT_RE = re.compile(
    r"^\s*("
    r"import\b|"
    r"from\s+\S+\s+import\b|"
    r"const\s+[\w\s,{}*]+\s*=\s*require\s*\(|"
    r"require\s*\(\s*['\"]|"
    r"using\s+[\w.]+\s*;|"
    r"#\s*include\b|"
    r"@import\b|"
    r"export\s+\{[^}]*\}\s+from\b"
    r")"
)


def _is_noise(line: str) -> bool:
    """True for comment-only or import-only lines â€” must NOT trigger signals."""
    stripped = line.strip()
    if not stripped:
        return True
    if _COMMENT_RE.match(stripped):
        return True
    if _IMPORT_RE.match(stripped):
        return True
    return False


# â”€â”€ protective-code signals â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
SIGNALS: dict[str, str] = {
    "validation": (
        r"\b(validate|isValid|sanitize|sanitise|"
        r"schema\s*\.|pydantic|zod\.|joi\.|cerberus|"
        r"yup\.|marshmallow|typeguard|"
        r"\bassert\s+(?!import|from)|"
        r"checkParam|inputCheck|verifyInput)\b"
    ),
    "error_handling": (
        r"\b(try\s*[:{]|except\b|catch\s*[({(]|finally\s*[:{]|"
        r"rescue\b|raise\b|throw\b|panic!\s*\(|"
        r"\.unwrap_or\b|Result<|err\s*!=\s*nil|"
        r"ErrorBoundary|\.catch\s*\(|onError\b)\b"
    ),
    "security": (
        r"\b(authorize\b|authenticate\b|csrf|"
        r"bcrypt|jwt\b|verify\b(?!\s*=\s*false)|permission\b|"
        r"escape\s*\(|encode\s*\(|"
        r"(?<!\w)secure(?!\w)|auth(?!o\w)|verify\w*\s*\(|"
        r"(?<!\w)secure(?!\w)|auth(?!o\w)|verify\b|"
        r"rate_limit|rateLimit)\b"
    ),
    "accessibility": (
        r"(aria-[a-z]+|(?<!\w)role\s*=|(?<!\w)alt\s*=|"
        r"\btabindex\b|<label\b.*?\bfor\s*=|htmlFor\s*=|"
        r"\bfocusable\b|sr-only)"
    ),
    "tests": (
        r"(\bdef\s+test_\w|\bit\s*\(\s*['\"]|"
        r"\bdescribe\s*\(\s*['\"]|\bexpect\s*\(|"
        r"\bassertEqual\b|\bassertTrue\b|\bassertRaises\b|"
        r"\@Test\b|#\[test\]|\btest!\s*\()"
    ),
}

_COMPILED = {k: re.compile(v, re.IGNORECASE) for k, v in SIGNALS.items()}


def _classify_signal(line: str) -> list[str]:
    if _is_noise(line):
        return []
    return [name for name, rx in _COMPILED.items() if rx.search(line)]


# â”€â”€ logic-weakening detection â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_OP_LOOSENING = [
    (re.compile(r"<="),           re.compile(r"(?<![<>])<(?![=<])")),   # <= â†’ <
    (re.compile(r">="),           re.compile(r"(?<![<>])>(?![=>])")),   # >= â†’ >
    (re.compile(r"!=|<>|~="),     re.compile(r"(?<![=!<>])={1,3}(?!=)")),  # != â†’ ==
    (re.compile(r"===|!=="),      re.compile(r"(?<![=!])={2}(?!=)")),   # !== â†’ ==
]
_NEGATION_RE   = re.compile(r"\bnot\b\s+\w|!\s*\w(?!=)")
_CONST_GUARD   = re.compile(r"\bif\s+(True|False|true|false|1|0)\b\s*[:{(]")
_GUARD_KW      = re.compile(r"\b(if|while|assert|require)\b")
_NUM_IN_COND   = re.compile(r"\b(?:if|while|assert)\b[^:\n{]*?(\d+(?:\.\d+)?)")


def _weakened_logic_in_hunk(removed: list[str], added: list[str]) -> list[str]:
    findings: list[str] = []
    rem = "\n".join(removed)
    add = "\n".join(added)
    if not rem and not add:
        return findings
    # operator loosening
    for rem_pat, add_pat in _OP_LOOSENING:
        if rem_pat.search(rem) and add_pat.search(add) and _GUARD_KW.search(rem):
            findings.append(
                f"operator loosened: '{rem_pat.pattern}' removed from guard "
                f"while '{add_pat.pattern}' appears in replacement"
            )
    # negation dropped from a guard
    if _NEGATION_RE.search(rem) and not _NEGATION_RE.search(add) and _GUARD_KW.search(rem):
        findings.append("guard negation removed (not / ! dropped from condition)")
    # constant guard substitution
    if _GUARD_KW.search(rem) and _CONST_GUARD.search(add):
        findings.append("guard condition replaced by constant (if True/False/1/0)")
    # numeric bound changed inside a condition
    rem_vals = {m.group(1) for m in _NUM_IN_COND.finditer(rem)}
    add_vals = {m.group(1) for m in _NUM_IN_COND.finditer(add)}
    if rem_vals and add_vals and rem_vals != add_vals:
        findings.append(f"numeric bound in condition changed: {rem_vals} â†’ {add_vals}")
    return findings


# â”€â”€ hunk splitter â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _split_hunks(diff_text: str) -> list[list[str]]:
    hunks: list[list[str]] = []
    current: list[str] = []
    for line in diff_text.splitlines():
        if line.startswith("@@"):
            if current:
                hunks.append(current)
            current = []
        else:
            current.append(line)
    if current:
        hunks.append(current)
    return hunks if hunks else [diff_text.splitlines()]


# â”€â”€ main scanner â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@dataclass
class _SignalAccum:
    removed: list[str] = field(default_factory=list)
    added_back: int = 0


def scan_diff(diff_text: str) -> dict:
    """Scan a unified diff. Returns a dict with keys:
      ok: bool, findings: dict, risk: str, language: str|None
    """
    lang = _detect_lang(diff_text)
    hunks = _split_hunks(diff_text)
    sig_acc: dict[str, _SignalAccum] = {k: _SignalAccum() for k in SIGNALS}
    weak_samples: list[str] = []

    for hunk in hunks:
        rem: list[str] = []
        add: list[str] = []
        for raw in hunk:
            if raw.startswith("+++") or raw.startswith("---"):
                continue
            if raw.startswith("-"):
                content = raw[1:]
                rem.append(content)
                for name in _classify_signal(content):
                    sig_acc[name].removed.append(content.strip()[:160])
            elif raw.startswith("+"):
                content = raw[1:]
                add.append(content)
                for name in _classify_signal(content):
                    sig_acc[name].added_back += 1  # per-hunk counter
        weak_samples.extend(_weakened_logic_in_hunk(rem, add))

    findings: dict = {}
    for name, acc in sig_acc.items():
        net = len(acc.removed) - acc.added_back
        if acc.removed and net > 0:
            findings[name] = {
                "removed": len(acc.removed),
                "added_back": acc.added_back,
                "net_removed": net,
                "samples": acc.removed[:5],
            }
    if weak_samples:
        findings["weakened_logic"] = {
            "removed": len(weak_samples),
            "added_back": 0,
            "net_removed": len(weak_samples),
            "samples": weak_samples[:5],
        }
    return {"ok": not findings, "findings": findings,
            "risk": _risk_level(findings), "language": lang}


def _risk_level(findings: dict) -> str:
    if not findings:
        return "clean"
    weighted = {
        "security": 3, "validation": 3, "weakened_logic": 3,
        "error_handling": 2, "tests": 2, "accessibility": 1,
    }
    score = sum(weighted.get(k, 1) * v["net_removed"] for k, v in findings.items())
    if score >= 6:
        return "high"
    if score >= 3:
        return "medium"
    return "low"


def scan_before_after(before: str, after: str) -> dict:
    """Diff two file versions using difflib for a proper line-level diff.
    Handles reindentation, duplicate lines, and reordering correctly.
    Treats the whole file as one hunk so weakened-logic detection works."""
    before_lines = before.splitlines(keepends=False)
    after_lines  = after.splitlines(keepends=False)
    diff_lines   = ["@@"]   # single hunk marker
    matcher = difflib.SequenceMatcher(None, before_lines, after_lines, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag in ("replace", "delete"):
            for line in before_lines[i1:i2]:
                diff_lines.append("-" + line)
        if tag in ("replace", "insert"):
            for line in after_lines[j1:j2]:
                diff_lines.append("+" + line)
    return scan_diff("\n".join(diff_lines))

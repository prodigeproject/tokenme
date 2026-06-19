"""Layer 4 tooling â€” context-lifecycle audit and compaction-survival helpers.

Covers the three Layer-4 behaviors from the tokenme skill:

  1. config_audit(paths)  â€” scan always-loaded agent context files and flag
     duplicated instructions, oversized files, and potentially stale content.
  2. generate_checkpoint(goal, done, files, decisions, next_step) â€” produce a
     CHECKPOINT block that survives a compaction without any plugin.
  3. parse_checkpoint(text) â€” find and parse the most recent CHECKPOINT block
     in a conversation or file so state can be restored after compaction.

All functions work on plain text â€” no agent API access needed. The audit walks
the filesystem paths you supply (e.g. ~/.claude/CLAUDE.md, .kiro/steering/*.md).

Limitations: duplication detection is fingerprint-based (64-char rolling hash),
not semantic. Stale detection looks for date patterns older than a threshold.
"""
from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path


# â”€â”€ config audit â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

# Patterns that often appear as duplicates in accumulated config files
_DUPE_SIGNALS = re.compile(
    r"(always respond in|you are an? |never|don't|do not|use \w+ style|"
    r"be concise|be brief|respond only|output format|language:)",
    re.IGNORECASE,
)

_DATE_RE = re.compile(r"\b(20\d{2})[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])\b")
_STALE_DAYS = 90


def _fingerprint(text: str, width: int = 64) -> set[str]:
    """Return a set of 64-char rolling-window fingerprints (lowercased, stripped)."""
    lines = [ln.strip().lower() for ln in text.splitlines() if ln.strip()]
    fps = set()
    for ln in lines:
        for i in range(0, len(ln), width // 2):
            chunk = ln[i: i + width]
            if len(chunk) >= 20:
                fps.add(hashlib.md5(chunk.encode()).hexdigest())
    return fps


def config_audit(paths: list[str | Path]) -> dict:
    """Audit a list of agent config / context files.

    Returns:
      findings: list of dicts  {path, issue, detail}
      total_tokens_est: rough token estimate of all files combined
      files_scanned: int
    """
    from . import estimate as _est

    findings: list[dict] = []
    seen_fps: dict[str, str] = {}  # fingerprint -> first-seen path
    total_tokens = 0
    scanned = 0
    now = datetime.now(timezone.utc)

    for raw_path in paths:
        p = Path(raw_path).expanduser()
        if not p.exists() or not p.is_file():
            findings.append({"path": str(p), "issue": "not_found",
                             "detail": "File does not exist"})
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            findings.append({"path": str(p), "issue": "unreadable", "detail": str(e)})
            continue

        scanned += 1
        tok = _est.count_n(text)
        total_tokens += tok

        # oversized
        if tok > 4000:
            findings.append({"path": str(p), "issue": "oversized",
                             "detail": f"~{tok} tokens â€” consider trimming"})
        elif tok > 1500:
            findings.append({"path": str(p), "issue": "large",
                             "detail": f"~{tok} tokens â€” worth reviewing"})

        # duplicate instruction blocks
        fps = _fingerprint(text)
        for fp in fps:
            if fp in seen_fps:
                findings.append({
                    "path": str(p),
                    "issue": "duplicate_content",
                    "detail": f"Content overlaps with {seen_fps[fp]}",
                })
                break
            seen_fps[fp] = str(p)

        # repeated instruction patterns within a single file
        matches = _DUPE_SIGNALS.findall(text)
        counts: dict[str, int] = {}
        for m in matches:
            counts[m.lower()] = counts.get(m.lower(), 0) + 1
        for phrase, cnt in counts.items():
            if cnt >= 3:
                findings.append({
                    "path": str(p), "issue": "repeated_instruction",
                    "detail": f"'{phrase}' appears {cnt}Ã— â€” may be redundant",
                })

        # stale dated content
        for m in _DATE_RE.finditer(text):
            try:
                dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)),
                              tzinfo=timezone.utc)
                age = now - dt
                if age > timedelta(days=_STALE_DAYS):
                    findings.append({
                        "path": str(p), "issue": "stale_date",
                        "detail": f"Date {m.group()} is {age.days} days old "
                                  f"(>{_STALE_DAYS}d threshold) â€” verify still current",
                    })
                    break  # one warning per file
            except ValueError:
                pass

    return {
        "findings": findings,
        "total_tokens_est": total_tokens,
        "files_scanned": scanned,
        "ok": all(f["issue"] == "not_found" or f["issue"] in ("large",) for f in findings),
    }


def format_audit_report(result: dict) -> str:
    """Render config_audit() result as a human-readable report."""
    lines = [
        f"Layer-4 config audit â€” {result['files_scanned']} file(s) scanned, "
        f"~{result['total_tokens_est']} tokens total",
        "=" * 60,
    ]
    if not result["findings"]:
        lines.append("CLEAN â€” no issues found.")
        return "\n".join(lines)
    for f in result["findings"]:
        p = Path(f["path"]).name
        lines.append(f"  [{f['issue']}] {p}: {f['detail']}")
    lines.append("")
    lines.append("Fix: trim oversized files, remove duplicate instructions,")
    lines.append("update or delete stale notes. These are 'ghost tokens' loaded")
    lines.append("every session even when the agent never uses them.")
    return "\n".join(lines)


# â”€â”€ checkpoint generate / parse â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_CKPT_START = re.compile(r"^CHECKPOINT\s*$", re.MULTILINE)
_CKPT_FIELD  = re.compile(r"^[-â€“]\s*(\w[\w\s/]+):\s*(.+)$")


def generate_checkpoint(
    goal: str,
    done: list[str],
    files: list[str],
    decisions: list[str],
    next_step: str,
) -> str:
    """Return a CHECKPOINT block for pasting into the conversation.

    The block is compact (under ~100 tokens) and structured so parse_checkpoint
    can recover it after a compaction.
    """
    def bullet(items: list[str]) -> str:
        return "\n".join(f"  - {i}" for i in items) if items else "  - (none)"

    return (
        f"CHECKPOINT\n"
        f"- Goal: {goal}\n"
        f"- Done:\n{bullet(done)}\n"
        f"- Open files: {', '.join(files) if files else '(none)'}\n"
        f"- Decisions:\n{bullet(decisions)}\n"
        f"- Next step: {next_step}"
    )


def parse_checkpoint(text: str) -> dict | None:
    """Find and parse the LAST CHECKPOINT block in text.

    Returns a dict with keys: goal, done, files, decisions, next_step
    or None if no checkpoint is found.
    """
    # find all checkpoint positions, take the last one
    positions = [m.start() for m in _CKPT_START.finditer(text)]
    if not positions:
        return None
    start = positions[-1]
    block = text[start:]

    result: dict = {
        "goal": "", "done": [], "files": [], "decisions": [], "next_step": ""
    }
    current_key: str | None = None

    for line in block.splitlines()[1:]:  # skip "CHECKPOINT" header
        m = _CKPT_FIELD.match(line)
        if m:
            key = m.group(1).lower().replace(" ", "_")
            val = m.group(2).strip()
            if key == "goal":
                result["goal"] = val
                current_key = None
            elif key in ("open_files", "files"):
                result["files"] = [f.strip() for f in val.split(",") if f.strip()]
                current_key = None
            elif key == "next_step":
                result["next_step"] = val
                current_key = None
            elif key == "done":
                current_key = "done"
            elif key == "decisions":
                current_key = "decisions"
        elif line.startswith("  - ") and current_key:
            result[current_key].append(line[4:].strip())
        elif not line.strip():
            # blank line ends block
            break

    return result if result["goal"] or result["next_step"] else None

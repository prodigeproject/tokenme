"""Per-session token tracking and savings storage.

Storage layout (all local, no telemetry):
  ~/.tokenme/
    sessions/<session-id>.jsonl   one JSON event per line

An "event" records a moment where tokens were spent or saved:
  - kind:    tool_call | response | edit | note
  - layer:   1 | 2 | 3 | 4   (which tokenme layer acted)
  - raw:     tokens that WOULD have entered context with no optimization
  - kept:    tokens that actually entered context
  - saved:   raw - kept  (>= 0; never negative-claims by construction)
  - method:  'tiktoken:<enc>' | '~est' | 'given'
             'given' = caller supplied raw/kept_tokens directly; no counting done
  - label:   human tag, e.g. "git diff", "cat config.json"

`raw` is only set when we actually know the un-optimized size. When raw is
unknown we store kept only and never invent a saving.

Session IDs: prefers TOKENME_SESSION / CLAUDE_SESSION_ID / TERM_SESSION_ID env
vars, else falls back to a per-day bucket "day-YYYYMMDD". Day-bucket mode merges
all activity in one calendar day. Use `is_day_bucket(sid)` to detect it.

File writes are protected by a portable lock-file so parallel hooks do not
corrupt the JSONL. A lock failure never raises — the append is attempted anyway.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from . import estimate


# ─── paths ────────────────────────────────────────────────────────────────────

def home() -> Path:
    base = os.environ.get("TOKENME_HOME")
    return Path(base).expanduser() if base else Path.home() / ".tokenme"


def sessions_dir() -> Path:
    d = home() / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ─── session id ───────────────────────────────────────────────────────────────

def current_session_id() -> str:
    """Return a stable id for the current session.

    Prefers host-provided env vars so a whole agent session groups together.
    Falls back to a per-day bucket ('day-YYYYMMDD') — use is_day_bucket() to
    detect this and optionally warn the user that events from the whole day merge.
    """
    for key in ("TOKENME_SESSION", "CLAUDE_SESSION_ID", "TERM_SESSION_ID"):
        v = os.environ.get(key)
        if v:
            return "".join(c for c in v if c.isalnum() or c in "-_")[:64]
    return "day-" + datetime.now().strftime("%Y%m%d")


def is_day_bucket(sid: str) -> bool:
    """True if the session id is a per-day fallback bucket, not a real session."""
    return sid.startswith("day-")


# ─── portable lock ────────────────────────────────────────────────────────────

def _lock_path(jsonl: Path) -> Path:
    return jsonl.with_suffix(".lock")


def _acquire_lock(lock: Path, timeout: float = 3.0, stale_after: float = 10.0) -> bool:
    """Try to create an exclusive lock file. Returns True if acquired."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            # exclusive create — atomic on POSIX and Windows NTFS
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(time.time()).encode())
            os.close(fd)
            return True
        except FileExistsError:
            # check for stale lock
            try:
                age = time.time() - lock.stat().st_mtime
                if age > stale_after:
                    lock.unlink(missing_ok=True)
                    continue
            except OSError:
                pass
            time.sleep(0.025)
        except OSError:
            return False
    return False


def _release_lock(lock: Path) -> None:
    try:
        lock.unlink(missing_ok=True)
    except OSError:
        pass


def _append_event(path: Path, event: dict) -> None:
    """Append one JSON line. Lock around write; fail-safe on lock failure."""
    lock = _lock_path(path)
    locked = _acquire_lock(lock)
    try:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    finally:
        if locked:
            _release_lock(lock)


# ─── record ───────────────────────────────────────────────────────────────────

def record(
    kind: str,
    raw_text: str | None = None,
    kept_text: str | None = None,
    raw_tokens: int | None = None,
    kept_tokens: int | None = None,
    layer: int | None = None,
    label: str = "",
    session: str | None = None,
    method: str | None = None,
) -> dict:
    """Append one event.

    Provide either *_text (counted with estimate.count) or *_tokens (stored as
    'given' — no counting performed). method kwarg overrides the derived label.
    """
    sid = session or current_session_id()

    derived_method: str = "given"
    if kept_tokens is None and kept_text is not None:
        kept_tokens, derived_method = estimate.count(kept_text)
    if raw_tokens is None and raw_text is not None:
        raw_tokens, m2 = estimate.count(raw_text)
        # propagate worst-case label
        if estimate.is_estimate(m2) or estimate.is_estimate(derived_method):
            derived_method = "~est"
        else:
            derived_method = m2

    final_method = method if method is not None else derived_method
    kept_tokens = kept_tokens or 0
    saved = max(0, raw_tokens - kept_tokens) if raw_tokens is not None else None

    event: dict = {
        "ts": time.time(),
        "iso": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kind": kind,
        "layer": layer,
        "raw": raw_tokens,
        "kept": kept_tokens,
        "saved": saved,
        "method": final_method,
        "label": label[:200],
    }
    _append_event(_session_path(sid), event)
    return event


# ─── read ─────────────────────────────────────────────────────────────────────

def _session_path(sid: str) -> Path:
    return sessions_dir() / (sid + ".jsonl")


def load_session(sid: str) -> list[dict]:
    p = _session_path(sid)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue   # skip corrupt lines silently
    return out


def list_sessions() -> list[str]:
    return sorted(p.stem for p in sessions_dir().glob("*.jsonl"))


# ─── aggregate ────────────────────────────────────────────────────────────────

def aggregate(events: list[dict]) -> dict:
    kept = sum(e.get("kept") or 0 for e in events)
    raw = sum(e.get("raw") or 0 for e in events if e.get("raw") is not None)
    saved = sum(e.get("saved") or 0 for e in events if e.get("saved") is not None)
    measured = [e for e in events if e.get("saved") is not None]
    coverage = round(100 * len(measured) / len(events), 1) if events else 0.0
    pct = round(100 * saved / raw, 1) if raw else 0.0

    by_layer: dict = {}
    for e in events:
        layer = e.get("layer")
        if layer is None:
            continue
        s = by_layer.setdefault(layer, {"saved": 0, "kept": 0, "events": 0})
        s["saved"] += e.get("saved") or 0
        s["kept"] += e.get("kept") or 0
        s["events"] += 1

    # method: ~est if any estimate; 'mixed' if combo of tiktoken+given; else given
    methods = {e.get("method") for e in events}
    if any(estimate.is_estimate(m) for m in methods):
        agg_method = "~est"
    elif len(methods) > 1:
        agg_method = "mixed"
    else:
        agg_method = (methods.pop() if methods else "given")

    return {
        "events": len(events),
        "measured_events": len(measured),
        "coverage_pct": coverage,
        "kept_tokens": kept,
        "raw_tokens_where_known": raw,
        "saved_tokens": saved,
        "saved_pct_where_known": pct,
        "by_layer": by_layer,
        "method": agg_method,
    }

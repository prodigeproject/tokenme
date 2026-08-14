"""Per-session token tracking and savings storage.

Storage layout (all local, no telemetry):
  ~/.tokenme/
    sessions/<session-id>.jsonl   one JSON event per line

An "event" records a moment where tokens were spent or saved:
  - kind:    tool_call | response | edit | note
  - layer:   1 | 2 | 3 | 4   (which tokenme layer acted)
  - raw:     tokens that WOULD have entered context with no optimization
  - kept:    tokens that actually entered context
  - saved:   raw - kept  (signed; negative means the optimization cost tokens)
  - metric:  the measured surface, never an implicit claim about total usage
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


METRIC_TYPES = (
    "command_output_reduction",
    "assistant_output_reduction",
    "code_output_reduction",
    "context_lifecycle_delta",
    "provider_total_tokens",
    "provider_cost",
    "custom",
)


def _default_metric(kind: str, layer: int | None) -> str:
    if layer == 1:
        return "assistant_output_reduction"
    if layer == 2:
        return "code_output_reduction"
    if layer == 3:
        return "command_output_reduction"
    if layer == 4:
        return "context_lifecycle_delta"
    return "custom"


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
    metric: str | None = None,
    metadata: dict | None = None,
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
    saved = raw_tokens - kept_tokens if raw_tokens is not None else None
    final_metric = metric or _default_metric(kind, layer)
    if final_metric not in METRIC_TYPES:
        raise ValueError(f"unsupported metric: {final_metric}")

    event: dict = {
        "ts": time.time(),
        "iso": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kind": kind,
        "layer": layer,
        "raw": raw_tokens,
        "kept": kept_tokens,
        "saved": saved,
        "metric": final_metric,
        "measurement_status": "measured" if raw_tokens is not None else "unknown_raw",
        "method": final_method,
        "label": label[:200],
    }
    if metadata:
        # Metadata is descriptive telemetry only; it never participates in a
        # token-saving delta.  Keep it JSON-shaped so session files stay
        # portable and auditable.
        event["metadata"] = dict(metadata)
    _append_event(_session_path(sid), event)
    return event


def record_provider_usage(
    usage: dict,
    label: str = "",
    session: str | None = None,
) -> dict:
    """Store provider usage components without inventing a counterfactual.

    ``raw`` remains unknown: a provider bill is an observation, not evidence
    of what an unoptimized run would have consumed.
    """
    fields = (
        "input_tokens", "cached_input_tokens", "cache_write_input_tokens",
        "fresh_input_tokens", "uncached_input_tokens", "output_tokens",
        "reasoning_output_tokens", "total_tokens", "turns", "malformed_lines",
    )
    metadata = {field: usage.get(field, 0) for field in fields}
    metadata["source"] = usage.get("source", "provider")
    # Keep the evidence labels alongside the observation.  Aggregation still
    # treats the provider total as a kept observation, never as a saving.
    if usage.get("ledger") is not None:
        metadata["ledger"] = usage["ledger"]
    return record(
        kind="provider_usage",
        kept_tokens=int(usage.get("total_tokens", 0) or 0),
        metric="provider_total_tokens",
        method=str(usage.get("source", "provider")),
        label=label,
        session=session,
        metadata=metadata,
    )


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

def _signed_delta(event: dict) -> int | None:
    """Derive the delta from raw/kept so legacy clamped events are corrected."""
    raw = event.get("raw")
    if raw is None:
        return None
    return int(raw) - int(event.get("kept") or 0)


def aggregate(events: list[dict]) -> dict:
    kept = sum(e.get("kept") or 0 for e in events)
    raw = sum(e.get("raw") or 0 for e in events if e.get("raw") is not None)
    measured = [e for e in events if e.get("raw") is not None]
    unknown_raw = [e for e in events if e.get("raw") is None]
    regressions = [e for e in measured if (_signed_delta(e) or 0) < 0]
    coverage = round(100 * len(measured) / len(events), 1) if events else 0.0
    measured_metrics = {
        e.get("metric") or _default_metric(str(e.get("kind") or ""), e.get("layer"))
        for e in measured
    }
    mixed_metrics = len(measured_metrics) > 1
    saved = (sum(_signed_delta(e) or 0 for e in measured)
             if measured and not mixed_metrics else None)
    pct = (round(100 * saved / raw, 1)
           if raw and saved is not None else None)

    by_layer: dict = {}
    by_metric: dict = {}
    provider_usage = {
        "events": 0,
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "cache_write_input_tokens": 0,
        "fresh_input_tokens": 0,
        "uncached_input_tokens": 0,
        "output_tokens": 0,
        "reasoning_output_tokens": 0,
        "total_tokens": 0,
        "turns": 0,
        "malformed_lines": 0,
    }
    for e in events:
        layer = e.get("layer")
        metric = e.get("metric") or _default_metric(str(e.get("kind") or ""), layer)
        m = by_metric.setdefault(metric, {"net_saved": 0, "raw": 0, "kept": 0,
                                          "events": 0, "measured_events": 0,
                                          "regression_events": 0})
        delta = _signed_delta(e)
        m["net_saved"] += delta or 0
        m["kept"] += e.get("kept") or 0
        m["events"] += 1
        if e.get("raw") is not None:
            m["measured_events"] += 1
            m["raw"] += e.get("raw") or 0
            if (delta or 0) < 0:
                m["regression_events"] += 1
        if metric == "provider_total_tokens":
            provider_usage["events"] += 1
            metadata = e.get("metadata") or {}
            for field in provider_usage:
                if field == "events":
                    continue
                provider_usage[field] += int(metadata.get(field, 0) or 0)
        if layer is None:
            continue
        s = by_layer.setdefault(layer, {"saved": 0, "kept": 0, "events": 0})
        s["saved"] += delta or 0
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

    for metric_summary in by_metric.values():
        metric_raw = metric_summary["raw"]
        metric_summary["net_saved_pct"] = (
            round(100 * metric_summary["net_saved"] / metric_raw, 1)
            if metric_raw else None
        )

    return {
        "events": len(events),
        "measured_events": len(measured),
        "unknown_raw_events": len(unknown_raw),
        "regression_events": len(regressions),
        "regressed_tokens": -sum(_signed_delta(e) or 0 for e in regressions),
        "coverage_pct": coverage,
        "kept_tokens": kept,
        "raw_tokens_where_known": raw,
        "saved_tokens": saved,
        "saved_pct_where_known": pct,
        "mixed_metrics": mixed_metrics,
        "by_layer": by_layer,
        "by_metric": by_metric,
        "provider_usage": provider_usage if provider_usage["events"] else None,
        "method": agg_method,
    }

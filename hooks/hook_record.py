"""Tool-output tracking hook (Layer 3) — PostToolUse bridge.

Reads the Claude Code / Codex PostToolUse hook JSON payload from stdin,
estimates the tokens of tool output that entered context (`kept`), and
— when the host reports the pre-truncation length — records the saving.

Fail-safe: any error exits 0 so it can never interrupt your session.
Tracking is 100% local. Remove the hook to stop tracking.
"""
from __future__ import annotations

import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from tokenme import tracker, estimate
except Exception:
    sys.exit(0)


def _extract_output(payload: dict) -> str:
    for key in ("tool_response", "toolResult", "output", "stdout", "result"):
        v = payload.get(key)
        if isinstance(v, str) and v:
            return v
        if isinstance(v, dict):
            for k2 in ("stdout", "content", "text", "output"):
                if isinstance(v.get(k2), str):
                    return v[k2]
    return ""


def main() -> int:
    try:
        data = sys.stdin.read()
        payload = json.loads(data) if data.strip() else {}
    except Exception:
        return 0
    try:
        out = _extract_output(payload)
        if not out:
            return 0
        tool = payload.get("tool_name") or payload.get("tool") or "tool"
        raw_tokens = None
        raw_len = payload.get("raw_output_length") or payload.get("original_length")
        if isinstance(raw_len, int) and raw_len > len(out):
            raw_tokens = int(estimate.count_n(out) * raw_len / max(1, len(out)))
        tracker.record(kind="tool_call", kept_text=out, raw_tokens=raw_tokens,
                       layer=3, label=str(tool)[:60])
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Response-turn tracking hook (Layer 1 & 2).

Tracks the token size of each model response (Layer 1 — prose output) and,
optionally, the size of code edits made in the same turn (Layer 2 — code
generated). Unlike the Layer-3 tool hook, this captures the output side.

Wire up to your agent's PostToolUse / Stop / UserPromptSubmit hooks:
  - On Stop or agent response: receives the assistant message text.
  - On PostToolUse Write/Edit: receives the written file content as proxy for L2.

Payload shapes tried (Claude Code, Codex, generic):
  assistant_text: the model's reply text
  tool_name: "Write" / "Edit" → treated as L2, otherwise L1

Fail-safe: any error exits 0. Never interrupts a session.
"""
from __future__ import annotations

import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from tokenme import tracker
except Exception:
    sys.exit(0)


def _extract(payload: dict) -> tuple[str, int, str]:
    """Returns (text, layer, label)."""
    tool = payload.get("tool_name") or payload.get("tool") or ""
    tool_str = str(tool).lower()

    # L2: file write/edit
    if any(t in tool_str for t in ("write", "edit", "multiEdit", "create")):
        for key in ("new_content", "content", "text", "patch"):
            v = payload.get(key) or (payload.get("tool_input") or {}).get(key, "")
            if isinstance(v, str) and v:
                return v, 2, f"write:{tool}"
        return "", 2, f"write:{tool}"

    # L1: model prose response
    for key in ("assistant_message", "response", "content", "text", "output",
                "message"):
        v = payload.get(key)
        if isinstance(v, str) and v:
            return v, 1, "response"
        if isinstance(v, list):
            texts = [b.get("text", "") for b in v if isinstance(b, dict)]
            joined = " ".join(t for t in texts if t)
            if joined:
                return joined, 1, "response"

    return "", 1, "response"


def main() -> int:
    try:
        data = sys.stdin.read()
        payload = json.loads(data) if data.strip() else {}
    except Exception:
        return 0
    try:
        text, layer, label = _extract(payload)
        if not text:
            return 0
        tracker.record(kind="response", kept_text=text, layer=layer, label=label)
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())

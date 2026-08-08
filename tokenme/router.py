"""Deterministic, feedback-aware routing for TokenMe reference modules.

The router is deliberately conservative: it never removes the core safety
contract, and it only loads the tool-output module when the task contains an
explicit inspection/execution/output signal.  A coding task by itself is not
enough to pay for layer 3.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Iterable


ROUTER_VERSION = "3"
MODULES = {
    1: "layer1-prose",
    2: "layer2-code",
    3: "layer3-tools",
    4: "layer4-context",
}

# Keep these patterns narrow.  Generic words such as ``file`` and ``repo`` are
# common in every coding ticket and are not evidence that a tool-output policy
# will pay for itself.
_CODE = re.compile(
    r"\b(implement|code|fix|bug|refactor|function|class|api|component|test|patch|"
    r"security|auth|parse|sql|typescript|javascript|python|react)\b"
)
_TOOL_ACTION = re.compile(
    r"\b(inspect|search|grep|find|diff|log|stdout|stderr|run|execute|build|"
    r"command|shell|terminal|test|pytest|npm|cargo|git|test output|listing|trace)\b"
)
_PROSE = re.compile(
    r"\b(explain|summarize|summary|rewrite|document|prose|answer|describe|"
    r"clarify|translate|draft|write up)\b"
)
_CONTEXT = re.compile(
    r"\b(context|compact|compaction|checkpoint|memory|audit|instructions|"
    r"skill|prompt|handoff|resume)\b"
)
_NOISY_TOOL = re.compile(
    r"\b(diff|log|stdout|stderr|test output|cargo test|pytest|npm test|"
    r"listing|grep|trace|verbose|stack trace)\b"
)
_HIGH_STAKES = re.compile(
    r"\b(security|auth|token|secret|password|credential|permission|traversal|"
    r"delete|drop|migration|accessib|aria|hmac|crypt|unsafe|irreversible)\b"
)

# Approximate o200k budgets used for a routing decision.  They are deliberately
# labels, not provider telemetry; the provider JSONL remains authoritative.
MODULE_BUDGET_TOKENS = {
    "layer1-prose": 115,
    "layer2-code": 145,
    "layer3-tools": 160,
    "layer4-context": 180,
}
CORE_BUDGET_TOKENS = 160


def _feedback_key(scores: dict[int, int], noisy_tool: bool) -> str:
    return (f"code={int(scores[2] > 0)};tools={int(scores[3] > 0)};"
            f"context={int(scores[4] > 0)};noisy={int(noisy_tool)}")


def _empty_feedback() -> dict:
    return {
        "samples": 0,
        "quality_failures": 0,
        "retries": 0,
        "turns": 0,
        "total_tokens": 0,
    }


def summarize_feedback(entries: Iterable[dict]) -> dict[str, dict]:
    """Aggregate local route outcomes by route key.

    Feedback is advisory and only becomes active after three observations.  A
    single noisy session must not permanently disable a route.
    """
    out: dict[str, dict] = {}
    for entry in entries:
        key = entry.get("route_key")
        if not key:
            continue
        summary = out.setdefault(key, _empty_feedback())
        summary["samples"] += 1
        outcome = str(entry.get("outcome", "success"))
        if outcome in {"quality-fail", "error"} or entry.get("quality_ok") is False:
            summary["quality_failures"] += 1
        summary["retries"] += max(0, int(entry.get("retries") or 0))
        summary["turns"] += max(0, int(entry.get("turns") or 0))
        summary["total_tokens"] += max(0, int(entry.get("total_tokens") or 0))
    for summary in out.values():
        n = summary["samples"] or 1
        summary["quality_failure_rate"] = round(summary["quality_failures"] / n, 3)
        summary["retry_rate"] = round(summary["retries"] / n, 3)
        summary["mean_turns"] = round(summary["turns"] / n, 3)
        summary["mean_total_tokens"] = round(summary["total_tokens"] / n, 3)
    return out


def _apply_feedback(route: dict, feedback: dict | None) -> dict:
    if not feedback:
        route["feedback_action"] = "none"
        return route
    summary = feedback.get(route["route_key"], {})
    route["feedback"] = summary
    samples = int(summary.get("samples", 0) or 0)
    quality_failures = int(summary.get("quality_failures", 0) or 0)
    retry_rate = float(summary.get("retry_rate", 0) or 0)
    if samples < 3:
        route["feedback_action"] = "observe_until_3_samples"
        return route
    # A route that causes repeated retries or a quality failure is downgraded
    # to native output.  Layer 2/code and the core invariants remain intact.
    if 3 in route["layers"] and (quality_failures > 0 or retry_rate >= 0.5):
        route["layers"] = [layer for layer in route["layers"] if layer != 3]
        route["modules"] = [MODULES[layer] for layer in route["layers"]]
        route["tool_adapter"] = "native-output"
        route["fallback"] = "layer3-disabled-after-feedback"
        route["estimated_module_tokens"] = sum(
            MODULE_BUDGET_TOKENS[name] for name in route["modules"])
        route["confidence"] = {
            str(layer): route["confidence"].get(str(layer), 0)
            for layer in route["layers"]
        }
        route["core_only"] = not route["modules"]
        route["reason"] = "feedback disabled layer3 after retries or quality failure"
        route["feedback_action"] = "downgrade-layer3"
    else:
        route["feedback_action"] = "keep-route"
    return route


def route_text(text: str, feedback: dict | None = None) -> dict:
    """Return a selective route and optional closed-loop adjustment.

    ``feedback`` is the output of :func:`summarize_feedback`.  It is optional so
    routing stays deterministic for hosts that do not persist outcomes yet.
    """
    text = text or ""
    lower = text.lower()
    scores = {
        1: len(_PROSE.findall(lower)),
        2: len(_CODE.findall(lower)),
        3: len(_TOOL_ACTION.findall(lower)),
        4: len(_CONTEXT.findall(lower)),
    }
    noisy_tool = bool(_NOISY_TOOL.search(lower))
    high_stakes = bool(_HIGH_STAKES.search(lower))
    layers = [layer for layer, score in scores.items() if score]
    if not layers:
        layers = [1]
    # Explicit tool actions, not generic repository words, justify layer 3.
    if 3 not in layers and (scores[3] > 0 or noisy_tool):
        layers.append(3)
    layers.sort()
    route_key = _feedback_key(scores, noisy_tool)
    modules = [MODULES[layer] for layer in layers]
    route = {
        "router_version": ROUTER_VERSION,
        "layers": layers,
        "modules": modules,
        "scores": {str(layer): score for layer, score in scores.items()},
        "confidence": {
            str(layer): round(min(1.0, scores[layer] / 2), 2)
            for layer in layers
        },
        "tool_adapter": "rtk-eligible" if noisy_tool else "native-output",
        "summary_mode": "expanded" if high_stakes else "brief",
        "route_key": route_key,
        "core_budget_tokens": CORE_BUDGET_TOKENS,
        "estimated_module_tokens": sum(MODULE_BUDGET_TOKENS[name] for name in modules),
        "fallback": "native-output",
        "core_only": not modules,
        "reason": (
            "explicit tool signal; load layer3"
            if 3 in layers else
            "no explicit tool-output signal; keep native-output"
        ),
    }
    # The host may use this as a telemetry label. The actual prompt renderer
    # is compiled and only emits selected deltas; it never injects all refs.
    route["instruction_mode"] = "compact" if 4 in layers else "micro"
    try:
        from .prompt import instruction_chars
        route["compiled_instruction_chars"] = instruction_chars(route)
    except Exception:
        route["compiled_instruction_chars"] = None
    route = _apply_feedback(route, feedback)
    try:
        from .prompt import instruction_chars
        route["compiled_instruction_chars"] = instruction_chars(route)
    except Exception:
        route["compiled_instruction_chars"] = None
    return route


def feedback_path(path: str | os.PathLike[str] | None = None) -> Path:
    if path:
        return Path(path).expanduser()
    configured = os.environ.get("TOKENME_ROUTING_FEEDBACK")
    if configured:
        return Path(configured).expanduser()
    base = os.environ.get("TOKENME_HOME")
    home = Path(base).expanduser() if base else Path.home() / ".tokenme"
    return home / "routing_feedback.jsonl"


def load_feedback(path: str | os.PathLike[str] | None = None) -> dict[str, dict]:
    """Read and aggregate local route feedback; malformed lines are ignored."""
    p = feedback_path(path)
    if not p.exists():
        return {}
    entries = []
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            entries.append(item)
    return summarize_feedback(entries)


def record_feedback(
    route_key: str,
    outcome: str = "success",
    turns: int = 0,
    retries: int = 0,
    quality_ok: bool | None = None,
    total_tokens: int | None = None,
    path: str | os.PathLike[str] | None = None,
    label: str = "",
) -> dict:
    """Append one local route outcome for future downgrade decisions."""
    if outcome not in {"success", "retry", "quality-fail", "error"}:
        raise ValueError(f"unsupported route outcome: {outcome}")
    p = feedback_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "ts": time.time(),
        "route_key": route_key,
        "outcome": outcome,
        "turns": max(0, int(turns)),
        "retries": max(0, int(retries)),
        "quality_ok": quality_ok,
        "total_tokens": max(0, int(total_tokens or 0)),
        "label": label[:200],
    }
    with p.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event

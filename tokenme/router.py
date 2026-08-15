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


ROUTER_VERSION = "4"
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
    r"\b(inspect|search|grep|find|diff|log|stdout|stderr|build|"
    r"command|shell|terminal|pytest|npm|cargo|git|test output|listing|trace)\b"
)
_PROSE = re.compile(
    r"\b(explain|summarize|summary|rewrite|document|prose|answer|describe|"
    r"clarify|translate|draft|write up)\b"
)
_PROSE_DELIVERABLE = re.compile(
    r"\b(final response|word report|report for|section headings|include every fact|"
    r"engineering manager|do not modify (?:the )?(?:fixture|file)|"
    r"read(?: the)? [\w./-]+\.(?:md|txt)|without modifying|summar(?:y|ize))\b"
)
_IMPLEMENTATION = re.compile(
    r"\b(implement|fix|refactor|add|modify|change|create|patch|"
    r"write (?:the )?(?:function|file|code))\b"
)
_CONTEXT = re.compile(
    r"\b(context|compact|compaction|checkpoint|memory|audit|instructions|"
    r"skill|prompt|handoff|resume)\b"
)
_NOISY_TOOL = re.compile(
    r"\b(diff|log|stdout|stderr|test output|cargo test|pytest|npm test|"
    r"listing|grep|trace|verbose|stack trace)\b"
)
_TOOL_HEAVY = re.compile(
    r"\b(bash-style command sequence|inspect the workspace before editing|"
    r"count files/lines|search for todo)\b"
)
_MINIMAL_HELPER = re.compile(
    r"\b(existing helper|helpers\.py|unrelated files|requested api)\b"
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


def _feedback_key(
    scores: dict[int, int],
    noisy_tool: bool,
    task_mode: str = "normal",
    layers: list[int] | None = None,
) -> str:
    effective = set(layers) if layers is not None else {
        layer for layer, score in scores.items() if score
    }
    return (f"mode={task_mode};code={int(2 in effective)};"
            f"tools={int(3 in effective)};context={int(4 in effective)};"
            f"noisy={int(noisy_tool)}")


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
    # A read-only report request often contains domain words such as "API" or
    # "security" and a single validation phrase such as "run one check". Those
    # words describe the subject/deliverable, not a request for code or noisy
    # command output. Suppress the expensive code/tool deltas unless the ticket
    # also contains an implementation verb or an explicit noisy-output signal.
    implementation_text = re.sub(
        r"\bdo not (?:modify|change|add|create|fix|patch)\b", "", lower
    )
    prose_only = bool(_PROSE_DELIVERABLE.search(lower)) and not bool(
        _IMPLEMENTATION.search(implementation_text)
    ) and not noisy_tool
    suppressed_layers: list[int] = []
    if prose_only:
        suppressed_layers = [layer for layer in layers if layer in {2, 3}]
        layers = [layer for layer in layers if layer not in {2, 3}]
        if not layers:
            layers = [1]
    # Explicit tool actions, not generic repository words, justify layer 3.
    if 3 not in layers and (scores[3] > 0 or noisy_tool):
        if not prose_only:
            layers.append(3)
    layers.sort()
    tool_heavy = bool(_TOOL_HEAVY.search(lower)) and not prose_only
    minimal_code = bool(_MINIMAL_HELPER.search(lower)) and 2 in layers and not prose_only
    task_mode = (
        "prose-only" if prose_only else
        "tool-heavy" if tool_heavy else
        "minimal-code" if minimal_code else
        "normal"
    )
    route_key = _feedback_key(scores, noisy_tool, task_mode, layers)
    modules = [MODULES[layer] for layer in layers]
    route = {
        "router_version": ROUTER_VERSION,
        "layers": layers,
        "modules": modules,
        "scores": {str(layer): score for layer, score in scores.items()},
        "task_mode": task_mode,
        "suppressed_layers": suppressed_layers,
        "confidence": {
            str(layer): round(min(1.0, scores[layer] / 2), 2)
            for layer in layers
        },
        "tool_adapter": "rtk-eligible" if noisy_tool and 3 in layers else "native-output",
        "summary_mode": "expanded" if high_stakes else "brief",
        "route_key": route_key,
        "core_budget_tokens": CORE_BUDGET_TOKENS,
        "estimated_module_tokens": sum(MODULE_BUDGET_TOKENS[name] for name in modules),
        "fallback": "native-output",
        "core_only": not modules,
        "reason": (
            "read-only prose deliverable; suppress code/tool deltas"
            if prose_only else
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


def simulate_net_benefit(
    *,
    expected_saving_tokens: int | None,
    policy_overhead_tokens: int = 0,
    extra_turn_tokens: int = 0,
    retry_tokens: int = 0,
    recovery_tokens: int = 0,
    latency_penalty_tokens: int = 0,
) -> dict:
    """Simulate whether a route pays for its own overhead.

    The function is deliberately token-unit based: a gateway can translate
    latency or dollars into a local policy budget, while TokenMe remains
    provider-neutral.  Unknown expected savings stay ``unknown`` rather than
    being converted into a fabricated zero saving.
    """
    costs = {
        "policy_overhead_tokens": max(0, int(policy_overhead_tokens)),
        "extra_turn_tokens": max(0, int(extra_turn_tokens)),
        "retry_tokens": max(0, int(retry_tokens)),
        "recovery_tokens": max(0, int(recovery_tokens)),
        "latency_penalty_tokens": max(0, int(latency_penalty_tokens)),
    }
    overhead = sum(costs.values())
    if expected_saving_tokens is None:
        return {
            "basis": "unknown",
            "expected_saving_tokens": None,
            "overhead_tokens": overhead,
            "net_tokens": None,
            "decision": "observe",
            **costs,
        }
    expected = max(0, int(expected_saving_tokens))
    net = expected - overhead
    return {
        "basis": "host_observation_or_simulation",
        "expected_saving_tokens": expected,
        "overhead_tokens": overhead,
        "net_tokens": net,
        "decision": "apply" if net > 0 else "skip",
        **costs,
    }


def adaptive_route(
    text: str,
    feedback: dict | None = None,
    *,
    expected_saving_tokens: int | None = None,
    observed: dict | None = None,
    policy_overhead_tokens: int | None = None,
) -> dict:
    """Route with an explicit net-benefit decision.

    ``observed`` may contain host telemetry keys matching
    :func:`simulate_net_benefit`.  With no observation the route remains
    usable, but the decision is ``observe``.  If a known negative net benefit
    is supplied, optional code/tool/context deltas are removed while the core
    and prose safety policy remain.
    """
    route = route_text(text, feedback=feedback)
    observed = observed or {}
    expected = observed.get("expected_saving_tokens", expected_saving_tokens)
    if policy_overhead_tokens is None:
        # This is a local estimate used for a decision label, not provider
        # telemetry.  Hosts with exact counts should pass their own value.
        try:
            from . import estimate, prompt
            rendered = prompt.render_instructions(route)
            policy_overhead_tokens = estimate.count(rendered)[0]
            route["policy_overhead_basis"] = "inferred"
        except Exception:
            policy_overhead_tokens = CORE_BUDGET_TOKENS + route.get(
                "estimated_module_tokens", 0)
            route["policy_overhead_basis"] = "label"
    net = simulate_net_benefit(
        expected_saving_tokens=expected,
        policy_overhead_tokens=policy_overhead_tokens,
        extra_turn_tokens=observed.get("extra_turn_tokens", 0),
        retry_tokens=observed.get("retry_tokens", 0),
        recovery_tokens=observed.get("recovery_tokens", 0),
        latency_penalty_tokens=observed.get("latency_penalty_tokens", 0),
    )
    route["net_benefit"] = net
    route["adaptive_action"] = net["decision"]
    if net["decision"] == "observe" and any(layer in {3, 4} for layer in route["layers"]):
        # Unknown economics are not permission to inject a potentially
        # trajectory-changing tool/context policy.  Keep the code contract
        # for implementation work, retain prose safety when present, and let
        # the host activate the optional delta after observing a paired run.
        route["layers"] = [layer for layer in route["layers"] if layer not in {3, 4}] or [1]
        route["modules"] = [MODULES[layer] for layer in route["layers"]]
        route["suppressed_layers"] = sorted(set(route.get("suppressed_layers", [])) | {3, 4})
        route["confidence"] = {
            str(layer): route.get("confidence", {}).get(str(layer), 0)
            for layer in route["layers"]
        }
        route["estimated_module_tokens"] = sum(
            MODULE_BUDGET_TOKENS[name] for name in route["modules"])
        route["tool_adapter"] = "native-output"
        route["fallback"] = "observe-without-optional-deltas"
        route["reason"] = "net benefit unknown; observe without tool/context delta"
        try:
            from .prompt import instruction_chars
            route["compiled_instruction_chars"] = instruction_chars(route)
        except Exception:
            pass
    if net["decision"] == "skip" and any(layer in {3, 4} for layer in route["layers"]):
        # Drop the expensive tool/context deltas first, but retain the code
        # contract for implementation work.  If a host explicitly routes only
        # tools, fall back to the prose safety core.
        route["layers"] = [layer for layer in route["layers"] if layer not in {3, 4}] or [1]
        route["modules"] = [MODULES[layer] for layer in route["layers"]]
        route["suppressed_layers"] = sorted(set(route.get("suppressed_layers", [])) | {3, 4})
        route["confidence"] = {
            str(layer): route.get("confidence", {}).get(str(layer), 0)
            for layer in route["layers"]
        }
        route["estimated_module_tokens"] = sum(
            MODULE_BUDGET_TOKENS[name] for name in route["modules"])
        route["tool_adapter"] = "native-output"
        route["fallback"] = "net-benefit-skip-optional-deltas"
        route["core_only"] = False
        route["reason"] = "net benefit negative; kept core/prose safety policy"
        try:
            from .prompt import instruction_chars
            route["compiled_instruction_chars"] = instruction_chars(route)
        except Exception:
            pass
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

"""Compiled, low-overhead TokenMe instructions.

The filesystem skill is useful for humans and hosts that load references on
demand. A provider prompt should receive only the invariant core plus the
selected delta; injecting the full Markdown manual on every turn can cost more
than the policy saves.
"""
from __future__ import annotations


COMPILED_CORE = (
    "Be concise without losing correctness. Preserve safety/security, validation, "
    "accessibility, compatibility, explicit requirements, exact identifiers, and checks. "
    "Reuse existing code/APIs; avoid speculative, unrelated, or repeated work. "
    "Result first: keep facts, numbers, caveats, and next step; omit process narration "
    "and repeated logs."
)

COMPILED_MODULES = {
    "layer1-prose": (
        "Prose: lead with the result; remove filler and repetition; use complete, "
        "unambiguous sentences. Expand for safety, ambiguity, or requested detail."
    ),
    "layer2-code": (
        "Code: inspect first; make the smallest readable correct change; reuse helpers/stdlib; "
        "no needless dependencies/abstractions; run one focused check. Use tools; no narration."
    ),
    "layer3-tools": (
        "Tools: request the smallest output that answers the question; prefer targeted "
        "searches, summaries, bounded slices, quiet flags, and focused tests; keep dense "
        "or security-sensitive context intact. Quote only decisive lines; preserve paths, "
        "numbers, exit codes, and exact errors. No tool-call narration."
    ),
    "layer4-context": (
        "Context: checkpoint goal, done, files, decisions, and next step before compaction; "
        "restore from the checkpoint instead of rereading known context."
    ),
}

SUMMARY_MODES = {
    "brief": (
        "Summary: final response one sentence when sufficient, at most 2 concise sentences "
        "with result and check; mention useful path/caveat; no narration or repetition."
    ),
    "expanded": (
        "Summary: final response 1-2 complete sentences; state result, critical safeguard or "
        "warning, and check; retain exact errors/numbers; omit exhaustive case lists."
    ),
}


def summary_policy(
    route: dict,
    *,
    state: str = "completed",
    quality_ok: bool | None = None,
    requested_detail: bool = False,
) -> dict:
    """Select an output budget without blindly truncating the answer.

    The policy is advisory: it asks the model for a concise, readable result,
    while high-stakes, failed, or unresolved work receives room for evidence.
    A host quality callback can promote a brief answer to expanded mode.
    """
    state = (state or "completed").lower()
    high_stakes = route.get("summary_mode") == "expanded"
    needs_evidence = high_stakes or requested_detail or quality_ok is False or state not in {
        "completed", "success", "done"
    }
    mode = "expanded" if needs_evidence else "brief"
    return {
        "mode": mode,
        "max_sentences": 2 if mode == "brief" else 5,
        "preserve": ["requirements", "numbers", "paths", "errors", "warnings"],
        "quality_gate": "required" if high_stakes or quality_ok is False else "advisory",
        "reason": (
            "retain evidence for safety/high-stakes or incomplete work"
            if needs_evidence else "routine result can use a concise summary"
        ),
    }


def render_instructions(route: dict, *, header: bool = False) -> str:
    """Render only the selected policy, without the full Markdown references."""
    modules = route.get("modules") or []
    parts = [COMPILED_CORE]
    parts.extend(COMPILED_MODULES[name] for name in modules if name in COMPILED_MODULES)
    policy = summary_policy(
        route,
        state=route.get("task_state", "completed"),
        quality_ok=route.get("quality_ok"),
        requested_detail=bool(route.get("requested_detail")),
    )
    parts.append(SUMMARY_MODES[policy["mode"]])
    if policy["mode"] == "expanded":
        parts.append(
            "Output gate: keep the answer understandable; do not omit required "
            "numbers, paths, errors, warnings, or unresolved next actions."
        )
    else:
        parts.append("Output: concise.")
    text = " ".join(parts)
    if header:
        return "\n## TokenMe compiled policy\n" + text + "\n"
    return "\n" + text + "\n"


def instruction_chars(route: dict) -> int:
    return len(render_instructions(route))

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
        "Code: inspect first; make the smallest correct change; reuse helpers/stdlib; "
        "no needless dependencies; run one focused check; stop on success; no narration."
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


READ_ONLY_PROSE = (
    "Read-only report: preserve safety and exact requirements; read only the named fixture; do not modify files or run shell or "
    "validation commands. Follow exact headings and requested word count; include every "
    "stated fact without invented numbers; write and return the final response only."
)

MINIMAL_CODE = (
    "Minimal patch: preserve safety, validation, and the public API; read only the named helper and target; make "
    "one smallest correct edit, add no dependencies or unrelated files, do not invent "
    "edge cases, run one focused check, and stop on success."
)

BOUNDED_TOOL_ADVISORY = (
    "Bounded tool task: preserve exact paths, errors, and requirements; combine the requested tree/search/fixture/diff/count inspection "
    "into a targeted command, exclude generated files, and cap output; never print a full "
    "diff or rerun sufficient output. Make one minimal edit, run one focused verification, "
    "and stop."
)

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


BOUNDED_TOOL_GUARD = (
    "Bounded inspection: never emit an unbounded recursive search, log dump, or full diff. "
    "Exclude generated and large log files. For rg/grep/find, cap matches (for example "
    "--max-count 50 or Select-Object -First 80); for Get-Content, use -TotalCount 120; "
    "start git diff with --stat and inspect only the target file or hunk. If output is "
    "already sufficient, stop; do not rerun a broad command or print the same output."
)


def bounded_tool_guard() -> str:
    """Return a small, provider-neutral guard against runaway tool output.

    This is an instruction contract rather than a transport-level truncator:
    hosts that need a hard byte/token ceiling must enforce it around the tool
    adapter. The guard is kept separately so a legacy TokenMe policy can be
    benchmarked with the fix without silently changing the historical source.
    """
    return BOUNDED_TOOL_GUARD


def _trajectory_hint(route: dict) -> str:
    """Return a small task-mode hint that can change tool behaviour.

    The hint is intentionally separate from the optional layer-3 module.  An
    adaptive route may suppress that module when economics are unknown, while
    still needing a read-only or bounded-trajectory instruction to avoid
    paying for unnecessary commands.  It is advisory; hosts that need a hard
    output ceiling must enforce it around the tool adapter.
    """
    if route.get("task_mode") == "prose-only":
        return READ_ONLY_PROSE
    if route.get("task_mode") == "minimal-code":
        return MINIMAL_CODE
    if route.get("task_mode") == "tool-heavy":
        return BOUNDED_TOOL_ADVISORY
    suppressed = set(route.get("suppressed_layers") or [])
    if 3 in suppressed:
        return BOUNDED_TOOL_ADVISORY
    return ""


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
    compact_mode = route.get("task_mode")
    if compact_mode in {"prose-only", "minimal-code", "tool-heavy"}:
        text = _trajectory_hint(route)
        if header:
            return "\n## TokenMe compact policy\n" + text + "\n"
        return "\n" + text + "\n"
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

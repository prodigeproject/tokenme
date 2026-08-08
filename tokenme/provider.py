"""Provider-reported usage parsers.

Provider usage is kept separate from tokenizer, LOC, and command-output proxies.
"""
from __future__ import annotations

import json


def parse_codex_jsonl(text: str) -> dict:
    """Sum Codex ``turn.completed`` usage events from a JSONL stream.

    Codex reports cached input as a component of input and reasoning output as a
    component of output. Total token volume is therefore input + output.
    """
    fields = (
        "input_tokens",
        "cached_input_tokens",
        "cache_write_input_tokens",
        "output_tokens",
        "reasoning_output_tokens",
    )
    totals = {field: 0 for field in fields}
    turns = malformed_lines = 0
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            malformed_lines += 1
            continue
        if event.get("type") != "turn.completed":
            continue
        usage = event.get("usage")
        if not isinstance(usage, dict):
            continue
        turns += 1
        for field in fields:
            # Codex currently uses cache_write_input_tokens.  Accept the
            # alternate cache_creation spelling used by other providers while
            # keeping one normalized ledger field.
            value = usage.get(field, 0)
            if field == "cache_write_input_tokens" and not value:
                value = usage.get("cache_creation_input_tokens", 0)
            if isinstance(value, int) and value >= 0:
                totals[field] += value

    totals["total_tokens"] = totals["input_tokens"] + totals["output_tokens"]
    # Cache-write input is new context too.  This is the closest provider
    # endpoint to “fresh input”; it is not the same as billed total tokens.
    totals["uncached_input_tokens"] = max(
        0, totals["input_tokens"] - totals["cached_input_tokens"])
    totals["fresh_input_tokens"] = (
        totals["uncached_input_tokens"] + totals["cache_write_input_tokens"]
    )
    totals["turns"] = turns
    totals["malformed_lines"] = malformed_lines
    totals["source"] = "provider:codex-jsonl"
    return totals

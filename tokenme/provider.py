"""Provider usage and tokenizer adapter contracts.

The parser keeps raw provider counters, local estimates, and unavailable
fields separate.  A flat compatibility dictionary is still returned by
``parse_codex_jsonl`` for existing hosts and benchmark scripts.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Protocol

from . import estimate


USAGE_FIELDS = (
    "input_tokens",
    "cached_input_tokens",
    "cache_write_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
)


@dataclass(frozen=True)
class TokenCount:
    """A count with evidence and scope labels."""

    value: int
    method: str
    confidence: str
    scope: str
    provider: str | None = None
    model: str | None = None
    known: bool = False

    def as_dict(self) -> dict:
        return asdict(self)


class TokenizerAdapter(Protocol):
    """Provider/model tokenizer hook supplied by a host integration."""

    provider: str

    def count(self, text: str, model: str | None = None) -> TokenCount:
        ...


_TOKENIZER_ADAPTERS: dict[str, TokenizerAdapter] = {}


def register_tokenizer_adapter(adapter: TokenizerAdapter) -> None:
    """Register or replace an adapter for one provider in this process."""
    name = str(getattr(adapter, "provider", "")).strip().lower()
    if not name:
        raise ValueError("tokenizer adapter needs a provider name")
    _TOKENIZER_ADAPTERS[name] = adapter


def clear_tokenizer_adapters() -> None:
    _TOKENIZER_ADAPTERS.clear()


def count_text(
    text: str | None,
    *,
    provider: str | None = None,
    model: str | None = None,
    force_heuristic: bool = False,
    scope: str = "visible_text",
) -> TokenCount:
    """Count text through a host adapter or a clearly labelled fallback.

    Public local tokenizers are ``known=False`` unless a provider adapter
    explicitly vouches for them; hidden system/tool framing remains outside
    the count's scope.
    """
    name = (provider or "").strip().lower()
    adapter = _TOKENIZER_ADAPTERS.get(name) if name else None
    if adapter is not None:
        result = adapter.count(text or "", model=model)
        if not isinstance(result, TokenCount):
            raise TypeError("tokenizer adapter must return TokenCount")
        return result
    value, method = estimate.count_for_model(
        text, model=model, force_heuristic=force_heuristic)
    return TokenCount(
        value=value,
        method=method,
        confidence="low" if method == "~est" else "medium",
        scope=scope,
        provider=provider,
        model=model,
        known=False,
    )


def _nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def parse_codex_jsonl_ledger(
    text: str,
    *,
    provider: str = "openai",
    model: str | None = None,
) -> dict:
    """Parse Codex JSONL and attach a raw/inferred/unknown evidence ledger.

    ``total_tokens`` is always ``input_tokens + output_tokens``.  Reasoning is
    a component of output and is never added again.  Missing component fields
    are listed as unknown rather than silently represented as measured zero.
    """
    totals = {field: 0 for field in USAGE_FIELDS}
    turns = malformed_lines = 0
    unknown: set[str] = set()
    invalid: set[str] = set()
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            malformed_lines += 1
            continue
        if not isinstance(event, dict) or event.get("type") != "turn.completed":
            continue
        usage = event.get("usage")
        if not isinstance(usage, dict):
            unknown.update(USAGE_FIELDS)
            continue
        turns += 1
        for field in USAGE_FIELDS:
            raw = usage.get(field)
            if field == "cache_write_input_tokens" and raw in (None, 0):
                alt = usage.get("cache_creation_input_tokens")
                if alt is not None:
                    raw = alt
            value = _nonnegative_int(raw)
            if value is None:
                unknown.add(field)
                if raw is not None:
                    invalid.add(field)
                continue
            totals[field] += value

    if turns == 0:
        unknown.update(USAGE_FIELDS)
    totals["total_tokens"] = totals["input_tokens"] + totals["output_tokens"]
    totals["uncached_input_tokens"] = max(
        0, totals["input_tokens"] - totals["cached_input_tokens"])
    totals["fresh_input_tokens"] = (
        totals["uncached_input_tokens"] + totals["cache_write_input_tokens"]
    )
    totals["turns"] = turns
    totals["malformed_lines"] = malformed_lines
    totals["source"] = "provider:codex-jsonl"
    basis = "raw_provider" if turns and not unknown and not invalid else (
        "partial" if turns else "unknown"
    )
    totals["ledger"] = {
        "basis": basis,
        "provider": provider,
        "model": model,
        "raw": {field: totals[field] for field in USAGE_FIELDS},
        "inferred": {},
        "unknown": sorted(unknown),
        "invalid": sorted(invalid),
        "malformed_lines": malformed_lines,
    }
    return totals


def parse_codex_jsonl(text: str) -> dict:
    """Compatibility wrapper for :func:`parse_codex_jsonl_ledger`."""
    return parse_codex_jsonl_ledger(text)
